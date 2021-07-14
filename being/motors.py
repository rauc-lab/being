"""Motor blocks.

For now homing is implemented as *homing generators*. This might seem overly
complicated but we do this so that we can move blocking aspects to the caller
and home multiple motors / nodes in parallel. This results in quasi coroutines.
We do not use asyncio because we want to keep the core async free for now.
"""
from typing import Optional, Generator, Tuple, ForwardRef
import enum
import random
import time

from being.backends import CanBackend
from being.block import Block
from being.can import load_object_dictionary
from being.can.cia_402 import (
    CONTROLWORD,
    CW,
    CiA402Node,
    Command,
    HOMING_ACCELERATION,
    HOMING_METHOD,
    HOMING_SPEED,
    OperationMode,
    POSITION_ACTUAL_VALUE,
    SOFTWARE_POSITION_LIMIT,
    STATUSWORD,
    SW,
    State as CiA402State,
    TARGET_VELOCITY,
    VELOCITY_ACTUAL_VALUE,
    target_reached,
    which_state,
)
from being.can.definitions import HOMING_OFFSET
from being.can.nmt import PRE_OPERATIONAL, OPERATIONAL
from being.can.vendor import stringify_faulhaber_error
from being.config import CONFIG
from being.constants import INF, FORWARD
from being.error import BeingError
from being.kinematics import kinematic_filter, State as KinematicState
from being.logging import get_logger
from being.pubsub import PubSub
from being.math import sign, clip
from being.resources import register_resource


# TODO: Implement "non-crude" homings for the different controllers / end-switch
# yes/no etc... Also need to think of a sensible lookup of homing methods. There
# are some tricky differences like:
#   - CanOpen register for end-switch on Faulhaber is not standard CiA402
#   - Homing method 35 is deprecated since a new CiA 402 standard. Got replaced
#     with 37. Maxon Epos 2 and Faulhaber still use 35, Maxon Epos 4 uses the
#     new 37


MOTOR_CHANGED = 'MOTOR_CHANGED'

class DriveError(BeingError):

    """Something went wrong on the drive."""


class HomingState(enum.Enum):

    """Possible homing states."""

    UNHOMED = 0
    HOMED = 1
    ONGOING = 2
    FAILED = 3  # TODO: To be removed since it hides error trace back? Should
                # we always raise an exception?


HomingProgress = Generator[HomingState, None, None]
"""Yielding the current homing state."""

HomingRange = Tuple[int, int]
"""Lower and upper homing range."""

MINIMUM_HOMING_WIDTH = 0.010
"""Minimum width of homing range for a successful homing."""

LinearMotor = ForwardRef('LinearMotor')


class HomingFailed(BeingError):

    """Something went wrong while homing."""


def _fetch_position(node: CiA402Node) -> int:
    """Fetch actual position value from node.

    Args:
        node: Connected CiA402 node.

    Returns:
        Position value in device units.
    """
    return node.pdo[POSITION_ACTUAL_VALUE].raw


def _fetch_velocity(node: CiA402Node) -> int:
    """Fetch actual velocity value from node.

    Args:
        node: Connected CiA402 node.

    Returns:
        Velocity value in device units.
    """
    return node.pdo[VELOCITY_ACTUAL_VALUE].raw


def _move_node(node: CiA402Node, velocity: int, deadTime: float = 2.) -> HomingProgress:
    """Move motor with constant speed.

    Args:
        node: Connected CiA402 node.

    Kwargs:
        speed: Speed value in device units.
        deadTime: Idle time after sending out command.

    Yields:
        HomingState.RUNNING
    """
    #print('_move_node()', velocity)
    node.pdo[TARGET_VELOCITY].raw = int(velocity)
    node.pdo[TARGET_VELOCITY].pdo_parent.transmit()
    node.pdo[CONTROLWORD].raw = Command.ENABLE_OPERATION | CW.NEW_SET_POINT
    node.pdo[CONTROLWORD].pdo_parent.transmit()
    endTime = time.perf_counter() + deadTime
    while time.perf_counter() < endTime:
        yield HomingState.ONGOING  # Wait for sync
        sw = node.pdo[STATUSWORD].raw
        if target_reached(sw):
            #print('Early exit')
            return


def _align_in_the_middle(lower: int, upper: int, length: int) -> HomingRange:
    """Align homing range in the middle.

    Args:
        lower: Lower homing range.
        upper: Upper homing range.
        length: Desired length:

    Returns:
        Trimmed down version of homing range.
    """
    width = upper - lower
    if width <= length:
        return lower, upper

    margin = (width - length) // 2
    return lower + margin, upper - margin


class Motor(Block, PubSub):

    """Motor base class."""

    def __init__(self):
        super().__init__()
        PubSub.__init__(self, events=[MOTOR_CHANGED])
        self.homing = HomingState.UNHOMED
        self.homingJob = None
        self.add_value_input('targetPosition')
        self.add_value_output('actualPosition')

    def enabled(self):
        return self._enabled

    def home(self):
        """Start homing routine for this motor. Has then to be driven via the update() method."""
        self.publish(MOTOR_CHANGED)

    def disable(self):
        """Switch motor on."""
        self.publish(MOTOR_CHANGED)

    def enable(self):
        """Engage motor. This is switching motor on and engaging its drive."""
        self.publish(MOTOR_CHANGED)


class LinearMotor(Motor):

    """Motor blocks which takes set-point values through its inputs and outputs
    the current actual position value through its output. The input position
    values are filtered with a kinematic filter. Encapsulates a and setups a
    CiA402Node. Currently only tested with Faulhaber linear drive (0.04 m).

    Attributes:
        network (CanBackend): Associsated network:
        node (CiA402Node): Drive node.
    """

    def __init__(self,
             nodeId: int,
             length: Optional[float] = None,
             direction: float = FORWARD,
             homingDirection: Optional[float] = None,
             maxSpeed: float = 1.,
             maxAcc: float = 1.,
             network: Optional[CanBackend] = None,
             node: Optional[CiA402Node] = None,
             objectDictionary = None,
        ):
        """Args:
            nodeId: CANopen node id.

        Kwargs:
            length: Rod length if known.
            direction: Movement orientation.
            homingDirection: Initial homing direction. Default same as `direction`.
            maxSpeed: Maximum speed.
            maxAcc: Maximum acceleration.
            network: External network (dependency injection).
            node: Drive node (dependency injection).
            objectDictionary: Object dictionary for CiA402Node. If will be tried
                to identified from known EDS files.
        """
        super().__init__()
        if homingDirection is None:
            homingDirection = direction

        if network is None:
            network = CanBackend.single_instance_setdefault()
            register_resource(network, duplicates=False)

        if node is None:
            if objectDictionary is None:
                objectDictionary = load_object_dictionary(network, nodeId)

            node = CiA402Node(nodeId, objectDictionary, network)

        self.length = length
        self.direction = sign(direction)
        self.homingDirection = sign(homingDirection)
        self.network = network
        self.node = node
        self.maxSpeed = maxSpeed
        self.maxAcc = maxAcc

        self.lower = -INF
        self.upper = INF
        self.logger = get_logger(str(self))

        self.configure_node()

        self.node.nmt.state = PRE_OPERATIONAL
        self.node.set_state(CiA402State.READY_TO_SWITCH_ON)
        self.node.set_operation_mode(OperationMode.CYCLIC_SYNCHRONOUS_POSITION)

    @property
    def nodeId(self) -> int:
        """CAN node id."""
        return self.node.id

    def configure_node(self):
        """Configure Faulhaber node (some settings via SDO)."""
        units = self.node.units

        # TODO: These parameters have to come from the outside. Question: How
        # can we identify the motor and choose sensible defaults?

        generalSettings = self.node.sdo['General Settings']
        generalSettings['Pure Sinus Commutation'].raw = 1
        #generalSettings['Activate Position Limits in Velocity Mode'].raw = 1
        #generalSettings['Activate Position Limits in Position Mode'].raw = 1

        filterSettings = self.node.sdo['Filter Settings']
        filterSettings['Sampling Rate'].raw = 4
        filterSettings['Gain Scheduling Velocity Controller'].raw = 1

        velocityController = self.node.sdo['Velocity Control Parameter Set']
        #velocityController['Proportional Term POR'].raw = 44
        #velocityController['Integral Term I'].raw = 50

        posController = self.node.sdo['Position Control Parameter Set']
        posController['Proportional Term PP'].raw = 15
        posController['Derivative Term PD'].raw = 10
        # Some softer params from pygmies
        #posController['Proportional Term PP'].raw = 8
        #posController['Derivative Term PD'].raw = 14

        curController = self.node.sdo['Current Control Parameter Set']
        curController['Continuous Current Limit'].raw = 0.550 * units.current  # [mA]
        curController['Peak Current Limit'].raw = 1.640 * units.current  # [mA]
        curController['Integral Term CI'].raw = 3

        self.node.sdo['Max Profile Velocity'].raw = self.maxSpeed * units.kinematics  # [mm / s]
        self.node.sdo['Profile Acceleration'].raw = self.maxAcc * units.kinematics  # [mm / s^2]
        self.node.sdo['Profile Deceleration'].raw = self.maxAcc * units.kinematics  # [mm / s^2]

    def home_forward(self, speed: int) -> HomingProgress:
        """Home in forward direction until upper limits is not increasing
        anymore.
        """
        self.upper = -INF
        yield from _move_node(self.node, velocity=speed)
        while (pos := _fetch_position(self.node)) > self.upper:
            self.upper = pos
            yield HomingState.ONGOING

        yield from _move_node(self.node, velocity=0.)

    def home_backward(self, speed: int) -> HomingProgress:
        """Home in backward direction until `lower` is not decreasing
        anymore.
        """
        self.lower = INF
        yield from _move_node(self.node, velocity=-speed)
        while (pos := _fetch_position(self.node)) < self.lower:
            self.lower = pos
            yield HomingState.ONGOING

        yield from _move_node(self.node, velocity=0.)

    def crude_homing(self, maxSpeed=0.100, relMargin: float = 0.01) -> HomingProgress:
        """Crude homing procedure. Move with PROFILED_VELOCITY operation mode in
        both direction until reaching the limits (position not increasing or
        decreasing anymore). Implemented as Generator so that we can home multiple
        motors in parallel (quasi pseudo coroutine). time.sleep has to be handled by
        the caller.

        Velocity direction controls initial homing direction.

        Kwargs:
            maxSpeed: Maximum speed of homing travel.
            relMargin: Relative margin if motor length is not known a priori. Final
                length will be the measured length from the two homing travels minus
                `relMargin` percent on both sides.

        Yields:
            Homing state.
        """
        node = self.node
        forward = (self.homingDirection > 0)
        speed = abs(maxSpeed * node.units.speed)
        relMargin = clip(relMargin, 0.00, 0.50)  # In [0%, 50%]!

        with node.restore_states_and_operation_mode():
            node.change_state(CiA402State.READY_TO_SWITCH_ON)
            node.set_operation_mode(OperationMode.PROFILED_VELOCITY)
            node.change_state(CiA402State.OPERATION_ENABLE)
            node.nmt.state = OPERATIONAL

            node.sdo[HOMING_METHOD].raw = 35
            node.sdo[HOMING_OFFSET].raw = 0

            # Homing travel
            # TODO: Should we skip 2nd homing travel if we know motor length a
            # priori? Would need to also consider relMargin. Otherwise motor
            # will touch one edge
            if forward:
                yield from self.home_forward(speed)
                yield from self.home_backward(speed)
            else:
                yield from self.home_backward(speed)
                yield from self.home_forward(speed)

            node.change_state(CiA402State.READY_TO_SWITCH_ON)

            homingWidth = (self.upper - self.lower) / node.units.length
            if homingWidth < MINIMUM_HOMING_WIDTH:
                raise HomingFailed(
                    f'Homing width to narrow. Homing range: {[self.lower, self.upper]}!'
                )

            # Estimate motor length
            if self.length is None:
                self.length = (1. - 2 * relMargin) * homingWidth

            # Center according to rod length
            lengthDev = int(self.length * node.units.length)
            self.lower, self.upper = _align_in_the_middle(self.lower, self.upper, lengthDev)

            node.sdo[HOMING_OFFSET].raw = self.lower
            node.sdo[SOFTWARE_POSITION_LIMIT][1].raw = 0
            node.sdo[SOFTWARE_POSITION_LIMIT][2].raw = self.upper - self.lower

        yield HomingState.HOMED
        self.publish(MOTOR_CHANGED)

    def end_switch_homing(self,
              homingMethod: int,
              maxSpeed: float = 0.050,
              maxAcc: float = 1.,
              relMargin: float = 0.01,
              timeout: float = 5.,
        ) -> HomingProgress:

        raise NotImplementedError('Make me!')

        node = self.node
        with node.restore_states_and_operation_mode():
            node.change_state(CiA402State.READY_TO_SWITCH_ON)
            node.set_operation_mode(OperationMode.HOMING)
            node.nmt.state = OPERATIONAL
            node.change_state(CiA402State.OPERATION_ENABLE)

            # TODO: Set Homing Switch(Objekt 0x2310). Manufacture dependent
            # node.sdo['Homing Switch'] = ???
            node.sdo[HOMING_METHOD] = homingMethod
            node.sdo[HOMING_SPEED] = abs(maxSpeed * node.units.speed)
            node.sdo[HOMING_ACCELERATION] = abs(maxAcc * node.units.speed)

            node.sdo[CONTROLWORD].raw = Command.ENABLE_OPERATION | CW.START_HOMING_OPERATION
            homed = False

            # TODO: Check statusword bit 10 and 12 zero
            endTime = time.perf_counter() + timeout
            while (time.perf_counter() < endTime) and not homed:
                yield HomingState.ONGOING
                sw = node.sdo[STATUSWORD].raw
                homed = (sw & SW.TARGET_REACHED) and (sw & SW.HOMING_ATTAINED)

            if homed:
                yield HomingState.HOMED
            else:
                node.sdo[CONTROLWORD].raw = Command.ENABLE_OPERATION  # Abort homing
                yield HomingState.FAILED

            self.publish(MOTOR_CHANGED)

    def enabled(self):
        sw = self.node.sdo['Statusword'].raw  # This takes approx. 2.713 ms
        state = which_state(sw)
        return state is CiA402State.OPERATION_ENABLE

    def home(self):
        self.homingJob = self.crude_homing()
        self.homing = HomingState.ONGOING
        self.publish(MOTOR_CHANGED)

    def disable(self):
        self.node.disable()
        self.publish(MOTOR_CHANGED)

    def enable(self):
        self.node.enable()
        self.publish(MOTOR_CHANGED)

    def update(self):
        err = self.node.pdo['Error Register'].raw
        if err:
            msg = stringify_faulhaber_error(err)
            #raise DriveError(msg)
            self.logger.error('DriveError: %s', msg)

        if self.homing is HomingState.HOMED:
            sw = self.node.pdo['Statusword'].raw  # This takes approx. 0.027 ms
            state = which_state(sw)
            if state is CiA402State.OPERATION_ENABLE:
                if self.direction > 0:
                    tarPos = self.targetPosition.value
                else:
                    tarPos = self.length - self.targetPosition.value

                self.node.set_target_position(tarPos)

        elif self.homing is HomingState.ONGOING:
            self.homing = next(self.homingJob)

        self.output.value = self.node.get_actual_position()


class RotaryMotor(Motor):
    def __init__(self, nodeId, *args, **kwargs):
        raise NotImplementedError
        # TODO: Make me!


class WindupMotor(Motor):
    def __init__(self, nodeId, *args, **kwargs):
        raise NotImplementedError
        # TODO: Make me!


class DummyMotor(Motor):

    """Dummy motor for testing and standalone usage."""

    def __init__(self, length=0.04):
        super().__init__()
        self.length = length
        self.state = KinematicState()
        self.dt = CONFIG['General']['INTERVAL']
        self.homed = HomingState.HOMED
        self._enabled = True

    def enabled(self):
        return self._enabled

    def disable(self):
        self._enabled = False
        self.publish(MOTOR_CHANGED)

    def enable(self):
        self._enabled = True
        self.publish(MOTOR_CHANGED)

    def dummy_homing(self, minDuration: float = 1., maxDuration: float = 2.) -> HomingProgress:
        duration = random.uniform(minDuration, maxDuration)
        endTime = time.perf_counter() + duration
        while time.perf_counter() < endTime:
            yield HomingState.ONGOING

        yield HomingState.HOMED
        self.publish(MOTOR_CHANGED)

    def home(self):
        self.homingJob = self.dummy_homing()
        self.homed = HomingState.ONGOING
        self.publish(MOTOR_CHANGED)

    def update(self):
        # Kinematic filter input target position
        if self.homing is HomingState.ONGOING:
            target = 0.
        else:
            target = self.input.value

        self.state = kinematic_filter(
            target,
            dt=self.dt,
            state=self.state,
            maxSpeed=1.,
            maxAcc=1.,
            lower=0.,
            upper=self.length,
        )

        self.output.value = self.state.position
