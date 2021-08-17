"""Motor blocks.

For now homing is implemented as *homing generators*. This might seem overly
complicated but we do this so that we can move blocking aspects to the caller
and home multiple motors / nodes in parallel. This results in quasi coroutines.
We do not use asyncio because we want to keep the core async free for now.
"""
import abc
import random
import time
from typing import Optional, Dict, Any

from being.backends import CanBackend
from being.block import Block
from being.can import load_object_dictionary
from being.can.cia_402 import (
    CiA402Node,
    STATUSWORD,
    State as CiA402State,
    which_state,
)
from being.config import CONFIG
from being.constants import FORWARD, TAU
from being.error import BeingError
from being.kinematics import kinematic_filter, State as KinematicState
from being.logging import get_logger
from being.math import (
    angular_velocity_to_rpm,
    rpm_to_angular_velocity,
    sign,
)
from being.motors.controllers import Controller, Mclm3002, Epos4
from being.motors.homing import (
    HomingProgress,
    HomingState,
    proper_homing,
)
from being.motors.motors import get_motor, Motor
from being.pubsub import PubSub
from being.resources import register_resource


INTERVAL = CONFIG['General']['INTERVAL']
"""General delta t interval."""

MOTOR_CHANGED = 'MOTOR_CHANGED'
"""Motor changed event."""

CONTROLLER_TYPES: Dict[str, Controller] = {
    'MCLM3002P-CO': Mclm3002,
    'EPOS4': Epos4,
}
"""Device name -> Controller type lookup."""


def create_controller_for_node(node: CiA402Node, *args, **kwargs) -> Controller:
    """Controller factory. Different controllers depending on device name. Wraps
    CanOpen node.
    """
    deviceName = node.manufacturer_device_name()
    if deviceName not in CONTROLLER_TYPES:
        raise ValueError(f'No controller for device name {deviceName}!')

    controllerType = CONTROLLER_TYPES[deviceName]
    return controllerType(node, *args, **kwargs)


class DriveError(BeingError):

    """Something went wrong on the drive."""


class MotorBlock(Block, PubSub, abc.ABC):
    def __init__(self, name=None):
        super().__init__(name=name)
        PubSub.__init__(self, events=[MOTOR_CHANGED])
        self.add_value_input('targetPosition')
        self.add_value_output('actualPosition')
        self.homing = HomingState.UNHOMED
        self.homingJob = None

    # @abc.abstractmethod
    # def switch_off(self, publish=True):
    #    pass

    @abc.abstractmethod
    def enable(self, publish=True):
        """Engage motor. This is switching motor on and engaging its drive.

        Kwargs:
            publish: If to publish motor changes.
        """
        if publish:
            self.publish(MOTOR_CHANGED)

    @abc.abstractmethod
    def disable(self, publish=True):
        """Switch motor on.

        Kwargs:
            publish: If to publish motor changes.
        """
        if publish:
            self.publish(MOTOR_CHANGED)

    @abc.abstractmethod
    def enabled(self) -> bool:
        """Is motor enabled?"""

    @abc.abstractmethod
    def home(self):
        """Start homing routine for this motor. Has then to be driven via the
        update() method.
        """
        self.publish(MOTOR_CHANGED)

    def to_dict(self):
        dct = super().to_dict()
        dct['enabled'] = self.enabled()
        dct['homing'] = self.homing
        return dct


class DummyMotor(MotorBlock):

    """Dummy motor for testing and standalone usage."""

    def __init__(self, length=0.04):
        super().__init__()
        self.length = length
        self.state = KinematicState()
        self.dt = INTERVAL
        self.homing = HomingState.HOMED
        self._enabled = False

    def enable(self, publish=True):
        self._enabled = True
        super().enable(publish)

    def disable(self, publish=True):
        self._enabled = False
        super().disable(publish)

    def enabled(self):
        return self._enabled

    @staticmethod
    def dummy_homing(minDuration: float = 2., maxDuration: float = 5.) -> HomingProgress:
        """Dummy homing for testing.

        Kwargs:
            minDuration: Minimum homing duration.
            maxDuration: Maximum homing duration.

        Yields:
            HomingState ONGOING until HOMED.
        """
        duration = random.uniform(minDuration, maxDuration)
        endTime = time.perf_counter() + duration
        while time.perf_counter() < endTime:
            yield HomingState.ONGOING

        yield HomingState.HOMED

    def home(self):
        self.homingJob = self.dummy_homing()
        self.homing = HomingState.ONGOING
        super().home()

    def update(self):
        # Kinematic filter input target position
        if self.homing is HomingState.ONGOING:
            self.homing = next(self.homingJob)
            if self.homing is not HomingState.ONGOING:
                self.publish(MOTOR_CHANGED)

            target = 0.
        else:
            target = self.input.value

        self.state = kinematic_filter(
            target,
            dt=self.dt,
            initial=self.state,
            maxSpeed=1.,
            maxAcc=1.,
            lower=0.,
            upper=self.length,
        )

        self.output.value = self.state.position

    def to_dict(self):
        dct = super().to_dict()
        dct['length'] = self.length
        return dct


class CanMotor(MotorBlock):

    """Motor blocks which takes set-point values through its inputs and outputs
    the current actual position value through its output. The input position
    values are filtered with a kinematic filter. Encapsulates a and setups a
    CiA402Node. Currently only tested with Faulhaber linear drive (0.04 m).

    Attributes:
        controller (Controller): Motor controller.
        logger (Logger): CanMotor logger.
    """

    def __init__(self,
                 nodeId,
                 motorName: Optional[str] = None,
                 motor: Optional[Motor] = None,
                 node: Optional[CiA402Node] = None,
                 objectDictionary=None,
                 network: Optional[CanBackend] = None,
                 settings: Optional[Dict[str, Any]] = None,
                 name: Optional[str] = None,
                 **controllerKwargs,
                 ):
        """Args:
            nodeId: CANopen node id.
            motorName: Motor name / type of actual hardware motor.

        Kwargs:
            node: CiA402Node driver node. If non given create new one
                (dependency injection).
            objectDictionary: Object dictionary for CiA402Node. If will be tried
                to identified from known EDS files.
            network: External CAN network (dependency injection).
            settings: Motor settings. Dict of EDS variables -> Raw value to set.
                EDS variable with path syntax (slash '/' separator) for nested
                settings.
            name: Block name
            **controllerKwargs: Key word arguments for controller.
        """
        super().__init__(name=name)
        if network is None:
            network = CanBackend.single_instance_setdefault()
            register_resource(network, duplicates=False)

        if node is None:
            if objectDictionary is None:
                objectDictionary = load_object_dictionary(network, nodeId)

            node = CiA402Node(nodeId, objectDictionary, network)

        if settings is None:
            settings = {}

        if motor is None:
            if motorName is None:
                raise BeingError("No motor object or motor name provided.")
            else:
                motor = get_motor(motorName)

        self.controller: Controller = create_controller_for_node(
            node,
            motor,
            settings=settings,
            **controllerKwargs,
        )
        self.logger = get_logger(str(self))

    def enable(self, publish=True):
        self.controller.enable()
        super().enable(publish)

    def disable(self, publish=True):
        self.controller.disable()
        super().disable(publish)

    def enabled(self):
        return self.controller.enabled()

    def home(self):
        self.homingJob = self.controller.home()
        self.homing = HomingState.ONGOING
        super().home()

    def update(self):
        for emcy in self.controller.iter_emergencies():
            self.logger.error(emcy)

        if self.homing is HomingState.HOMED:
            # PDO instead of SDO for speed
            # This takes approx. 0.027 ms
            sw = self.controller.node.pdo[STATUSWORD].raw
            state = which_state(sw)
            if state is CiA402State.OPERATION_ENABLE:
                self.controller.set_target_position(self.targetPosition.value)

        elif self.homing is HomingState.ONGOING:
            self.homing = next(self.homingJob)
            if self.homing is not HomingState.ONGOING:
                self.publish(MOTOR_CHANGED)

        self.output.value = self.controller.get_actual_position()

    def to_dict(self):
        dct = super().to_dict()
        dct['length'] = self.controller.motor.length
        return dct

    def __str__(self):
        controller = self.controller
        node = self.controller.node
        motor = self.controller.motor
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join([
                'nodeId: %r' % (node.id),
                'controller: %r' % type(controller).__name__,
                'motor: %s %s' % (motor.manufacturer, motor.name),
            ])
        )


class LinearMotor(CanMotor):

    """Default linear Faulhaber motor."""

    def __init__(self, nodeId, motorName='LM 1247', **kwargs):
        super().__init__(nodeId, motorName, **kwargs)


class RotaryMotor(CanMotor):

    """Default rotary Maxon motor."""

    def __init__(self, nodeId, motorName='DC22', **kwargs):
        # TODO : Check Firmware version
        super().__init__(nodeId, motorName, **kwargs)


class WindupMotor(MotorBlock):
    def __init__(self, nodeId, *args, **kwargs):
        raise NotImplementedError
        # TODO: Make me!
