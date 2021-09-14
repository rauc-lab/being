"""Motor blocks.

For now homing is implemented as *homing generators*. This might seem overly
complicated but we do this so that we can move blocking aspects to the caller
and home multiple motors / nodes in parallel. This results in quasi coroutines.
We do not use asyncio because we want to keep the core async free for now.
"""
import itertools
from typing import Optional, Dict, Any, Union
from scipy.interpolate import interp1d

from being.backends import CanBackend
from being.block import Block
from being.can import load_object_dictionary
from being.can.cia_402 import CiA402Node
from being.config import CONFIG
from being.constants import TAU
from being.kinematics import kinematic_filter, State as KinematicState
from being.logging import get_logger
from being.motors.controllers import Controller, Mclm3002, Epos4
from being.motors.definitions import MotorState, MotorEvent, MotorInterface
from being.motors.homing import DummyHoming, HomingState
from being.motors.motors import get_motor, Motor
from being.resources import register_resource


INTERVAL = CONFIG['General']['INTERVAL']
"""General delta t interval."""

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
        raise ValueError(f'No controller registered for device name {deviceName}!')

    controllerType = CONTROLLER_TYPES[deviceName]
    return controllerType(node, *args, **kwargs)


class MotorBlock(Block, MotorInterface):

    FREE_NUMBERS = itertools.count(1)

    def __init__(self, name: Optional[str] = None):
        """Kwargs:
            name: Block name.
        """
        if name is None:
            name = 'Motor %d' % next(self.FREE_NUMBERS)

        super().__init__(name=name)
        MotorInterface.__init__(self)
        self.add_value_input('targetPosition')
        self.add_value_output('actualPosition')

    def to_dict(self):
        dct = super().to_dict()
        dct['state'] = self.motor_state()
        dct['homing'] = self.homing_state()
        return dct


class DummyMotor(MotorBlock):

    """Dummy motor for testing and standalone usage."""

    def __init__(self, length: float = 0.040, name=None):
        super().__init__(name=name)
        self.length = length
        self.state = KinematicState()
        self.dt = INTERVAL
        self._enabled = False

        self.homing = DummyHoming()

    def enable(self, publish: bool = True):
        self._enabled = True
        super().enable(publish)

    def disable(self, publish: bool = True):
        self._enabled = False
        super().disable(publish)

    def motor_state(self):
        if self._enabled:
            return MotorState.ENABLED
        else:
            return MotorState.DISABLED

    def home(self):
        self.homing.home()
        super().home()

    def homing_state(self):
        return self.homing.state

    def update(self):
        if self.homing.ongoing:
            self.homing.update()
            if not self.homing.ongoing:
                self.publish(MotorEvent.STATE_CHANGED)
        elif self.homing.state is HomingState.HOMED:
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

        self.controller.subscribe(MotorEvent.STATE_CHANGED, lambda: self.publish(MotorEvent.STATE_CHANGED))
        self.controller.subscribe(MotorEvent.ERROR, lambda msg: self.publish(MotorEvent.ERROR, msg))
        self.controller.subscribe(MotorEvent.HOMING_CHANGED, lambda: self.publish(MotorEvent.STATE_CHANGED))

    def enable(self, publish: bool = False):
        self.controller.enable()

    def disable(self, publish: bool = True):
        self.controller.disable()

    def motor_state(self):
        return self.controller.motor_state()

    def home(self):
        self.controller.home()
        super().home()

    def homing_state(self):
        return self.controller.homing_state()

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


class WindupMotor(CanMotor):

    """Default windup motor with Maxon controller"""

    def __init__(self, nodeId, motor="EC 45", spoolDiameter: float = 1.0, length: float = 1.0, **kwargs):
        """Args:
            spool_diameter: (average) diameter [m] of spool where the filament is winded up
            length: length of filament [m]
        """
        multiplier = 1 / (spoolDiameter / 2)
        super().__init__(nodeId, motor, length=length, multiplier=multiplier, **kwargs)


class WindupMotorAlternative(CanMotor):

    """Alternative windup motor with Maxon controller for more accuracy"""

    def __init__(self,
        nodeId, 
        motor="EC 45",
        spoolDiameterEmpty: float = 1.0,
        spoolDiameterFull: float = 1.0,
        length: float = 1.0,
        **kwargs):
        """Args:
            spool_diameter: (Average) diameter [m] of spool where the filament is winded up
            length: Length of filament [m]
        """

        self.interpFunc = interp1d([0, length], [spoolDiameterFull, spoolDiameterEmpty])
        super().__init__(nodeId, motor, length=length, **kwargs)

    def update(self):
        spoolDiameter = self.interpFunc(self.targetPosition.value)
        multiplier = 1 / (spoolDiameter / 2)
        motor = self.controller.motor
        self.controller.position_si_2_device = float(multiplier * motor.gear * motor.position_si_2_device)
        self.controller.upper = self.controller.length * self.controller.position_si_2_device
        super().update()


class LeadScrewMotor(CanMotor):

    """Default lead screw motor with Maxon controller"""

    def __init__(self, nodeId, motor="DC 22", threadPitch: float = 1.0, length: float = 1.0, **kwargs):
        """Args:
            threadPitch: Pitch on lead screw thread ("heigth" per revolution) [m]
            length: Total length of the lead screw [m]
        """
        multiplier = TAU / threadPitch
        super().__init__(nodeId, motor, length=length, multiplier=multiplier, **kwargs)


class BeltDriveMotor(CanMotor):

    """Default belt drive motor with Maxon controller where the object
    to be moved is attached on the belt
    """

    def __init__(self, nodeId, motor="DC 22", pinionDiameter: float = 1.0, length: float = 1.0, **kwargs):
        """Args:
            pinionDiameter: Diameter of the pinion including the belt
            length: Total length of the beltt drive [m]
        """
        multiplier = 1 / (pinionDiameter / 2)
        super().__init__(nodeId, motor, length=length, multiplier=multiplier, **kwargs)
