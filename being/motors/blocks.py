"""Motor blocks.

These blocks represent motors in the being block network. The primary input of a
motor block accepts *target position* values and the primary output outputs the
*actual position* values.

.. digraph:: motorblock
    :align: center
    :alt: Motor block input and output values.
    :caption: Motor block input and output values.
    :name: Motor block input and output values.

    rankdir="LR"
    in[shape=none, label=""]
    motor[label="Motor Block", shape=box]
    out[shape=none, label=""]
    in -> motor [label="Target Position"]
    motor -> out [label="Actual Position"]

Additionally each motor block offers some helper methods to change its
state during operation (see :class:`being.motors.definitions.MotorInterface` for
more details).

Motor blocks operate with SI values at their in- and outputs.

Available motor blocks are:

- :class:`DummyMotor`
- :class:`LinearMotor`
- :class:`RotaryMotor`
- :class:`BeltDriveMotor`
- :class:`LeadScrewMotor`
- :class:`WindupMotor`

"""
import abc
import itertools
from typing import Optional, Dict, Any, Union

import numpy as np

from being.backends import CanBackend
from being.block import Block
from being.can import load_object_dictionary
from being.can.cia_402 import CiA402Node, OperationMode
from being.configuration import CONFIG
from being.constants import TAU
from being.kinematics import kinematic_filter, State as KinematicState
from being.logging import get_logger
from being.math import ArchimedeanSpiral
from being.motors.controllers import Controller, Mclm3002, Epos4
from being.motors.definitions import MotorState, MotorEvent, MotorInterface
from being.motors.homing import DummyHoming, HomingState
from being.motors.motors import get_motor, Motor
from being.resources import register_resource


__all__ = [
    'DummyMotor',
    'CanMotor',
    'LinearMotor',
    'RotaryMotor',
    'BeltDriveMotor',
    'LeadScrewMotor',
    'WindupMotor',
]


# Look before you leap
INTERVAL = CONFIG['General']['INTERVAL']

CONTROLLER_TYPES: Dict[str, Controller] = {
    'MCLM3002P-CO': Mclm3002,
    'EPOS4': Epos4,
}
"""Device name to Controller type lookup."""


def create_controller_for_node(node: CiA402Node, *args, **kwargs) -> Controller:
    """Controller factory. Different controllers depending on device name. Wraps
    CanOpen node.

    Args:
        node: Drive node to wrap in new controller.
        *args: Variable length argument list for controller.
        **kwargs: Arbitrary keyword arguments for controller.

    Returns:
        New controller instance.

    Todo:
        Move to :class:`Controller`? Second constructor
        ``Controller.from_node``?
    """
    deviceName = node.manufacturer_device_name()
    if deviceName not in CONTROLLER_TYPES:
        raise ValueError(f'No controller registered for device name {deviceName}!')

    controllerType = CONTROLLER_TYPES[deviceName]
    return controllerType(node, *args, **kwargs)


class MotorBlock(Block, MotorInterface):

    """Base class for a motor block.

    Each motor block has an `targetPosition` ValueInput connection and a
    `actualPosition` ValueOutput connection. This base class also takes most of
    the heavy lifting for the serialization for the front-end. Child classes no
    to implement various abstract methods from the MotorInterface class.
    """

    FREE_NUMBERS = itertools.count(1)

    def __init__(self, name: Optional[str] = None):
        """
        Args:
            name (optional): Block name.
        """
        if name is None:
            name = 'Motor %d' % next(self.FREE_NUMBERS)

        super().__init__(name=name)
        MotorInterface.__init__(self)
        self.add_value_input('targetPosition')
        self.add_value_output('actualPosition')

    @abc.abstractmethod
    def get_length(self) -> float:
        """What is the length of the motor that will be shown in the UI?."""

    def to_dict(self):
        dct = super().to_dict()
        dct['state'] = self.motor_state()
        dct['homing'] = self.homing_state()
        dct['length'] = self.get_length()
        return dct


class DummyMotor(MotorBlock):

    """Dummy motor for testing and standalone usage."""

    def __init__(self, length: float = 0.040, name: Optional[str] = None):
        """
        Args:
            length (optional): Length of dummy motor in meters.
            name (optional): Motor name.
        """
        super().__init__(name=name)
        self.length = length
        self.state = KinematicState()
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

    def get_length(self):
        return self.length

    def step(self, target: float):
        """Step kinematic simulation one step further towards target
        position.

        Args:
            target: Target position.
        """
        self.state = kinematic_filter(
            target,
            dt=INTERVAL,
            initial=self.state,
            maxSpeed=1.,
            maxAcc=1.,
            lower=0.,
            upper=self.length,
        )

    def update(self):
        if self.homing.ongoing:
            self.homing.update()
            if not self.homing.ongoing:
                self.publish(MotorEvent.STATE_CHANGED)

        elif self.homing.state is HomingState.HOMED:
            self.step(target=self.input.value)

        self.output.value = self.state.position


class CanMotor(MotorBlock):

    """Motor blocks for steering a CAN motor.

    Set-point values are taken from the blocks position value input (cyclic
    position mode). If profiled=True use profiled position mode instead. The
    message input targetPosition can than be used to play new PositionProfiles.
    In any case the actual position values are streamed via the `actualPosition`
    value output.

    This class initializes all the necessary components for accessing and
    configuring a CAN motor:

    - :class:`being.backends.CanBackend` network instance (if non has been
      initialized yet)
    - :class:`being.can.cia_402.CiA402Node` CAN node for given node id. Will be
      passed on to the Controller.
    - :class:`being.motors.motors.Motor` named tuple with informations regarding
      motor hardware and default settings.
    - :class:`being.motors.controllers.Controller` subclass instance, depending
      on motor controller manufacturer.

    Components needed for each CAN motor.

    .. graphviz::

        digraph G {
            node [shape=box];
            subgraph cluster_0 {
                label = "CanMotor";
                network[label="Network"]
                motor[label="Motor"]
                subgraph cluster_1 {
                    label = "Controller";
                    homing[label="Homing"]
                    node_[label="Node"]
                }
            }
        }

    Important:
        Since most of the time the network will be created implicitly always use
        this class within :func:`being.resources.manage_resources` context
        manager.

        >>> with manage_resources():
        ...     motor = CanMotor(nodeId=1, 'DC 22')

        Otherwise necessary cleanup can not take place and  the network will not
        get disconnected at the end. Motors would stay enabled and the CAN
        interface could become unreachable on subsequent starts of the program.

    This class relays :class:`being.pubsub.PubSub` publications from the
    underlying controller instance to the outside.

    >>> def error_callback(errMsg):
    ...     print('Something went wrong', errMsg)
    ...
    ... motor.subscribe(MotorEvent.ERROR, error_callback)
    """

    def __init__(self,
             nodeId,
             motor: Union[str, Motor],
             profiled: bool = False,
             name: Optional[str] = None,
             multiplier: float = 1.0,
             length: Optional[float] = None,
             node: Optional[CiA402Node] = None,
             objectDictionary = None,
             network: Optional[CanBackend] = None,
             settings: Optional[Dict[str, Any]] = None,
             **controllerKwargs,
         ):
        """
        Args:
            nodeId: CANopen node id.
            motor: Motor object or motor name.
            profiled (optional): Use profiled position mode instead of cyclic position mode.
            name (optional): Block name.
            multiplier (optional): Multiplier factor which can be used to scale
                target position / actual position values (only for cyclic
                position mode).
            length (optional): Motor length which will be shown in the web UI.
            node (optional): CAN node of motor driver / controller. If non given
                create new one (DI).
            objectDictionary (optional): Object dictionary for CAN node. It will
                be tried to get identified from known EDS files.
            network: External CAN network (DI).
            settings (optional): Motor settings. Dict of EDS variables -> Raw
                value to set. EDS variable with path syntax (slash '/'
                separator) for nested settings. Will be forwarded to the
                controller initialization function.
            **controllerKwargs: Arbitrary keyword arguments for controller.
        """
        super().__init__(name=name)
        self.add_message_input('positionProfile')

        if network is None:
            network = CanBackend.single_instance_setdefault()
            register_resource(network, duplicates=False)

        if node is None:
            if objectDictionary is None:
                objectDictionary = load_object_dictionary(network, nodeId)

            node = CiA402Node(nodeId, objectDictionary, network)

        if isinstance(motor, str):
            motor = get_motor(motor)

        if profiled:
            op = OperationMode.PROFILE_POSITION
        else:
            op = OperationMode.CYCLIC_SYNCHRONOUS_POSITION

        controllerKwargs.setdefault('operationMode', op)

        if length is None:
            length = motor.length

        if settings is None:
            settings = {}

        self.multiplier = multiplier
        self.length = length
        self.controller: Controller = create_controller_for_node(
            node,
            motor,
            multiplier * length,
            settings=settings,
            **controllerKwargs,
        )
        """Motor controller."""

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

    def pre_home(self):
        self.controller.pre_home()

    def homing_state(self):
        return self.controller.homing_state()

    def get_length(self):
        return self.length

    def update(self):
        self.controller.update()
        for profile in self.positionProfile.receive():
            self.controller.play_position_profile(profile)

        self.controller.set_target_position(self.multiplier * self.targetPosition.value)
        self.output.value = self.controller.get_actual_position() / self.multiplier

    def to_dict(self):
        dct = super().to_dict()
        dct['length'] = self.controller.length
        return dct

    def __str__(self):
        return f'{type(self).__name__}({self.controller})'


class LinearMotor(CanMotor):

    """Default linear Faulhaber CAN motor."""

    def __init__(self, nodeId, motor='LM 1247', **kwargs):
        """
        Args:
            nodeId: CANopen node id.
            motor (optional): Motor object or motor name.
            **kwargs: Arbitrary keyword arguments for :class:`CanMotor`.
        """
        super().__init__(nodeId, motor, **kwargs)


class RotaryMotor(CanMotor):

    """Default rotary Maxon CAN motor."""

    def __init__(self, nodeId, motor='DC 22', length=TAU, **kwargs):
        """
        Args:
            nodeId: CANopen node id.
            motor (optional): Motor object or motor name.
            length (optional): Length of rotary motor in radian.
            **kwargs: Arbitrary keyword arguments for :class:`CanMotor`.
        """
        super().__init__(nodeId, motor, length=length, **kwargs)


class BeltDriveMotor(CanMotor):

    """Default belt drive motor with Maxon controller where the object to be
    moved is attached on the belt.
    """

    def __init__(self, nodeId, length: float, diameter: float, motor='DC 22', **kwargs):
        """
        Args:
            nodeId: CANopen node id.
            length: Length of belt in meter
            diameter: Diameter of pinion belt wheel.
            motor (optional): Motor object or motor name.
            **kwargs: Arbitrary keyword arguments for :class:`CanMotor`.
        """
        radius = .5 * diameter
        multiplier = 1 / radius
        super().__init__(nodeId, motor, length=length, multiplier=multiplier, **kwargs)


class LeadScrewMotor(CanMotor):

    """Default lead screw motor with Maxon controller."""

    def __init__(self, nodeId, length: float, threadPitch: float, motor='DC 22', **kwargs):
        """
        Args:
            nodeId: CANopen node id.
            length: Total length of the lead screw in meter.
            threadPitch: Pitch on lead screw thread ("heigth" per revolution) in meter.
            motor (optional): Motor object or motor name.
            **kwargs: Arbitrary keyword arguments for :class:`CanMotor`.
        """
        multiplier = TAU / threadPitch
        super().__init__(nodeId, motor, length=length, multiplier=multiplier, **kwargs)


class WindupMotor(CanMotor):

    """Default windup motor with Maxon controller.

    Archimedean spiral is used to map angle onto the arc length of the winch.
    """

    def __init__(self,
            nodeId,
            diameter: float,
            length: float,
            motor: str = 'EC 45',
            outerDiameter: Optional[float] = None,
            **kwargs,
        ):
        """
        Args:
            nodeId: CANopen node id.
            diameter: Inner diameter of the spool / coil. Filament is completely
                unwind. In meters.
            length: Length of the filament. Corresponds to the arc length on the coil.
            motor: Motor object or motor name.
            outerDiameter (optional): Outer diameter of the spool / coil. This
                is the diameter when the filament is completely windup. Can be
                used to compensate of the windup effect of thicker filament.
                Default is the same as `diameter` resulting in a circle.
            **kwargs: Arbitrary keyword arguments for :class:`CanMotor`.
        """
        if outerDiameter is None:
            outerDiameter = diameter

        spiral, phiEst = ArchimedeanSpiral.fit(diameter, outerDiameter, arcLength=length)
        super().__init__(nodeId, motor, length=phiEst, **kwargs)
        self.length = length  # Overwrite length (=phiEst) sine we are doing our own transformation

        # xp, yp for linear position <-> angle target position interpolation
        self.angles = np.linspace(0, phiEst, 100)
        self.positions = np.array([spiral.arc_length(phi) for phi in self.angles])

    def update(self):
        self.controller.update()
        for profile in self.positionProfile.receive():
            adjustedPos = np.interp(profile.position, self.positions, self.angles)
            adjustedProfile = profile._replace(position=adjustedPos)
            self.controller.play_position_profile(adjustedProfile)

        pos = np.interp(self.targetPosition.value, self.positions, self.angles)
        self.controller.set_target_position(pos)
        actual = np.interp(self.controller.get_actual_position(), self.angles, self.positions)
        self.output.value = actual

    def to_dict(self):
        dct = super().to_dict()
        dct['length'] = self.length
        return dct
