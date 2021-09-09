"""Motor blocks.

For now homing is implemented as *homing generators*. This might seem overly
complicated but we do this so that we can move blocking aspects to the caller
and home multiple motors / nodes in parallel. This results in quasi coroutines.
We do not use asyncio because we want to keep the core async free for now.
"""
import abc
import enum
import random
import time
from typing import Optional, Dict, Any, Union

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
from being.constants import TAU
from being.error import BeingError
from being.kinematics import kinematic_filter, State as KinematicState
from being.logging import get_logger
from being.motors.controllers import Controller, Mclm3002, Epos4, ControllerEvent
from being.motors.homing import (
    HomingProgress,
    HomingState,
)
from being.motors.motors import get_motor, Motor
from being.pubsub import PubSub
from being.resources import register_resource


INTERVAL = CONFIG['General']['INTERVAL']
"""General delta t interval."""

CONTROLLER_TYPES: Dict[str, Controller] = {
    'MCLM3002P-CO': Mclm3002,
    'EPOS4': Epos4,
}
"""Device name -> Controller type lookup."""


class MotorEvent(enum.Enum):
    CHANGED = enum.auto()
    ERROR = enum.auto()
    DONE_HOMING = enum.auto()


def create_controller_for_node(node: CiA402Node, *args, **kwargs) -> Controller:
    """Controller factory. Different controllers depending on device name. Wraps
    CanOpen node.
    """
    deviceName = node.manufacturer_device_name()
    if deviceName not in CONTROLLER_TYPES:
        raise ValueError(f'No controller for device name {deviceName}!')

    controllerType = CONTROLLER_TYPES[deviceName]
    return controllerType(node, *args, **kwargs)


class MotorBlock(Block, PubSub, abc.ABC):
    def __init__(self, name: Optional[str] = None):
        """Kwargs:
            name: Block name.
        """
        super().__init__(name=name)
        PubSub.__init__(self, events=MotorEvent)
        self.add_value_input('targetPosition')
        self.add_value_output('actualPosition')

    # @abc.abstractmethod
    # def switch_off(self, publish=True):
    #    pass

    @abc.abstractmethod
    def enable(self, publish: bool = True, timeout: Optional[float] = None):
        """Engage motor. This is switching motor on and engaging its drive.

        Kwargs:
            publish: If to publish motor changes.
            timeout: Blocking state change with timeout.
        """
        if publish:
            self.publish(MotorEvent.CHANGED)

    @abc.abstractmethod
    def disable(self, publish: bool = True, timeout: Optional[float] = None):
        """Switch motor on.

        Kwargs:
            publish: If to publish motor changes.
            timeout: Blocking state change with timeout.
        """
        if publish:
            self.publish(MotorEvent.CHANGED)

    @abc.abstractmethod
    def enabled(self) -> bool:
        """Is motor enabled?"""
        # TODO: Have some kind of motor state enum: [ERROR, DISABLED, ENABLED]?

    @abc.abstractmethod
    def home(self):
        """Start homing routine for this motor. Has then to be driven via the
        update() method.
        """
        self.publish(MotorEvent.CHANGED)

    @abc.abstractmethod
    def homed(self) -> HomingState:
        raise NotImplementedError

    def to_dict(self):
        dct = super().to_dict()
        dct['enabled'] = self.enabled()
        dct['homing'] = self.homed()
        return dct


class DummyMotor(MotorBlock):

    """Dummy motor for testing and standalone usage."""

    def __init__(self, length: float = 0.040, name=None):
        super().__init__(name=name)
        self.length = length
        self.state = KinematicState()
        self.dt = INTERVAL
        self.homingState = HomingState.HOMED
        self.homingJob = None
        self._enabled = False

    def enable(self, publish: bool = True, timeout: Optional[float] = None):
        self._enabled = True
        super().enable(publish)

    def disable(self, publish: bool = True, timeout: Optional[float] = None):
        self._enabled = False
        super().disable(publish)

    def enabled(self):
        return self._enabled

    def homed(self):
        return self.homingState

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
        self.homingState = HomingState.ONGOING
        self.homingJob = self.dummy_homing()
        super().home()

    def update(self):
        # Kinematic filter input target position
        if self.homingState is HomingState.ONGOING:
            self.homingState = next(self.homingJob)
            if self.homingState is not HomingState.ONGOING:
                self.publish(MotorEvent.CHANGED)
                self.publish(MotorEvent.DONE_HOMING)

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
             motor: Union[str, Motor],
             name: Optional[str] = None,
             node: Optional[CiA402Node] = None,
             objectDictionary=None,
             network: Optional[CanBackend] = None,
             settings: Optional[Dict[str, Any]] = None,
             **controllerKwargs,
         ):
        """Args:
            nodeId: CANopen node id.
            motor: Motor object or motor name [str]

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

        if isinstance(motor, str):
            motor = get_motor(motor)

        self.controller: Controller = create_controller_for_node(
            node,
            motor,
            settings=settings,
            **controllerKwargs,
        )
        self.logger = get_logger(str(self))
        for msg in self.controller.error_history_messages():
            self.publish(MotorEvent.ERROR, msg)

        self.controller.subscribe(ControllerEvent.STATE_CHANGED, lambda: self.publish(MotorEvent.CHANGED))
        self.controller.subscribe(ControllerEvent.ERROR, lambda msg: self.publish(MotorEvent.ERROR, msg))
        self.controller.subscribe(ControllerEvent.HOMING_CHANGED, lambda: self.publish(MotorEvent.CHANGED))
        self.controller.subscribe(ControllerEvent.DONE_HOMING, lambda: self.publish(MotorEvent.DONE_HOMING))

    @property
    def homingState(self):
        return self.controller.homingState

    def enable(self, publish: bool = True, timeout: Optional[float] = None):
        self.controller.enable(timeout)
        super().enable(publish)

    def disable(self, publish: bool = True, timeout: Optional[float] = None):
        self.controller.disable(timeout)
        super().disable(publish)

    def enabled(self):
        return self.controller.enabled()

    def home(self):
        self.controller.home()
        super().home()

    def homed(self):
        return self.controller.homingState

    def update(self):
        self.controller.update()
        self.controller.set_target_position(self.targetPosition.value)
        self.output.value = self.controller.get_actual_position()

    def to_dict(self):
        dct = super().to_dict()
        dct['length'] = self.controller.length
        return dct

    def __str__(self):
        controller = self.controller
        return f'{type(self).__name__}({controller})'


class LinearMotor(CanMotor):

    """Default linear Faulhaber motor."""


    def __init__(self, nodeId, motor='LM 1247', **kwargs):
        super().__init__(nodeId, motor, **kwargs)


class RotaryMotor(CanMotor):

    """Default rotary Maxon motor."""

    def __init__(self, nodeId, motor='DC 22', length=TAU, **kwargs):
        super().__init__(nodeId, motor, length=length, **kwargs)


class WindupMotor(MotorBlock):
    def __init__(self, nodeId, *args, **kwargs):
        raise NotImplementedError
        # TODO: Make me!
