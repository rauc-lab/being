"""Homing procedures and definitions."""
import enum
import time
import warnings
from typing import Generator, Tuple

from being.can.cia_402 import (
    CiA402Node,
    POSITION_ACTUAL_VALUE,
    VELOCITY_ACTUAL_VALUE,
    TARGET_VELOCITY,
    CONTROLWORD,
    Command,
    CW,
    STATUSWORD,
    target_reached,
    State as CiA402State,
    OperationMode,
    HOMING_METHOD,
    HOMING_SPEEDS,
    SPEED_FOR_SWITCH_SEARCH,
    SPEED_FOR_ZERO_SEARCH,
    HOMING_ACCELERATION,
    SW,
    SOFTWARE_POSITION_LIMIT,
    )
from being.can.definitions import HOMING_OFFSET
from being.can.nmt import OPERATIONAL
from being.constants import INF
from being.error import BeingError
from being.math import clip

HomingRange = Tuple[int, int]
"""Lower and upper homing range."""

MINIMUM_HOMING_WIDTH = 0.010
"""Minimum width of homing range for a successful homing."""


class HomingState(enum.Enum):

    """Possible homing states."""

    FAILED = 0
    UNHOMED = 1
    ONGOING = 2
    HOMED = 3


HomingProgress = Generator[HomingState, None, None]
"""Yielding the current homing state."""


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


def proper_homing(
        node: CiA402Node,
        homingMethod: int,
        maxSpeed: float = 0.100,
        maxAcc: float = 1.,
        timeout: float = 5.,
        #lowerLimit: int = 0,
        #upperLimit: int = 0,
    ) -> HomingProgress:
    """Proper CiA 402 homing."""
    homed = False

    warnings.warn('Proper homing is untested by now. Use at your own risk!')

    with node.restore_states_and_operation_mode():
        node.change_state(CiA402State.READY_TO_SWITCH_ON)
        node.set_operation_mode(OperationMode.HOMING)
        node.nmt.state = OPERATIONAL
        # node.change_state(CiA402State.SWITCHED_ON)
        node.change_state(CiA402State.OPERATION_ENABLE)

        # TODO: Set Homing Switch(Objekt 0x2310). Manufacture dependent
        # node.sdo['Homing Switch'] = ???
        # TODO: Manufacture dependent, done before calling method
        # node.sdo[HOMING_OFFSET].raw = 0
        node.sdo[HOMING_METHOD].raw = homingMethod
        node.sdo[HOMING_SPEEDS][SPEED_FOR_SWITCH_SEARCH].raw = abs(maxSpeed * node.units.speed)
        node.sdo[HOMING_SPEEDS][SPEED_FOR_ZERO_SEARCH].raw = abs(maxSpeed * node.units.speed)
        node.sdo[HOMING_ACCELERATION].raw = abs(maxAcc * node.units.kinematics)

        # Start homing
        node.sdo[CONTROLWORD].raw = Command.ENABLE_OPERATION | CW.START_HOMING_OPERATION
        startTime = time.perf_counter()
        endTime = startTime + timeout

        # Check if homing started (statusword bit 10 and 12 zero)
        homingStarted = False
        while not homingStarted and (time.perf_counter() < endTime):
            yield HomingState.ONGOING
            sw = node.sdo[STATUSWORD].raw
            homingStarted = (not (sw & SW.TARGET_REACHED) and not (sw & SW.HOMING_ATTAINED))

        # Check if homed (statusword bit 10 and 12 one)
        while not homed and (time.perf_counter() < endTime):
            yield HomingState.ONGOING
            sw = node.sdo[STATUSWORD].raw
            homed = (sw & SW.TARGET_REACHED) and (sw & SW.HOMING_ATTAINED)

        node.sdo[CONTROLWORD].raw = Command.ENABLE_OPERATION  # Abort homing
        # node.sdo[CONTROLWORD].raw = 0  # Abort homing

    if homed:
        # lower = node.sdo[SOFTWARE_POSITION_LIMIT][1].raw
        #node.sdo[HOMING_OFFSET].raw = lower
        node.sdo[SOFTWARE_POSITION_LIMIT][1].raw = 0  # 0 == disabled
        node.sdo[SOFTWARE_POSITION_LIMIT][2].raw = 0  # 0 == disabled
        #print(self, 'HOMING_OFFSET:', node.sdo[HOMING_OFFSET].raw)
        #print('SOFTWARE_POSITION_LIMIT:', node.sdo[SOFTWARE_POSITION_LIMIT][1].raw)
        #print('SOFTWARE_POSITION_LIMIT:', node.sdo[SOFTWARE_POSITION_LIMIT][2].raw)
        # node.sdo[HOMING_OFFSET].raw = 0
        yield HomingState.HOMED
    else:
        yield HomingState.FAILED


def crude_homing(
        node,
        homingDirection,
        speed,
        minWidth,
        length=None,
        relMargin=0.01,
    ):
    """Crude homing procedure. Move with PROFILED_VELOCITY operation mode in
    both direction until reaching the limits (position not increasing or
    decreasing anymore). Implemented as Generator so that we can home multiple
    motors in parallel (quasi pseudo coroutine). time.sleep has to be handled by
    the caller.

    Args:
        node: Connected CanOpen node.
        homingDirection: Initial homing direction.
        speed: Homing speed in device units.
        minWidth: Minimum width for homing in device units.

    Kwargs:
        length: Known length of motor in device units.
        relMargin: Relative margin if motor length is not known a priori.
            Relative margin. 0.0 to 0.5 (0% to 50%).  Final length will be the
            measured length from the two homing travels minus `relMargin`
            percent on both sides.

    Yields:
        Homing state.
    """

    forward = (homingDirection > 0)
    speed = abs(speed)
    relMargin = clip(relMargin, 0.00, 0.50)  # In [0%, 50%]!

    upper = -INF
    lower = INF

    def home_forward(speed: int) -> HomingProgress:
        """Home in forward direction until upper limits is not increasing
        anymore.
        """
        nonlocal upper
        upper = -INF
        yield from _move_node(node, velocity=speed)
        while (pos := _fetch_position(node)) > upper:
            upper = pos
            yield HomingState.ONGOING

        yield from _move_node(node, velocity=0.)

    def home_backward(speed: int) -> HomingProgress:
        """Home in backward direction until `lower` is not decreasing
        anymore.
        """
        nonlocal lower
        lower = INF
        yield from _move_node(node, velocity=-speed)
        while (pos := _fetch_position(node)) < lower:
            lower = pos
            yield HomingState.ONGOING

        yield from _move_node(node, velocity=0.)

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
            yield from home_forward(speed)
            yield from home_backward(speed)
        else:
            yield from home_backward(speed)
            yield from home_forward(speed)

        node.change_state(CiA402State.READY_TO_SWITCH_ON)

        homingWidth = (upper - lower)
        if homingWidth < minWidth:
            raise HomingFailed(
                f'Homing width to narrow. Homing range: {[lower, upper]}!'
            )

        # Estimate motor length
        if length is None:
            length = (1. - 2 * relMargin) * homingWidth

        # Center according to rod length
        lower, upper = _align_in_the_middle(lower, upper, length)

        node.sdo[HOMING_OFFSET].raw = lower
        node.sdo[SOFTWARE_POSITION_LIMIT][1].raw = 0
        node.sdo[SOFTWARE_POSITION_LIMIT][2].raw = upper - lower

    yield HomingState.HOMED