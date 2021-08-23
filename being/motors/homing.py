"""Homing procedures and definitions."""
import enum
import time
import logging
from typing import Generator, Tuple

from being.bitmagic import check_bit_mask
from being.can.cia_402 import (
    CONTROLWORD,
    CW,
    CiA402Node,
    Command,
    HOMING_ACCELERATION,
    HOMING_METHOD,
    HOMING_SPEEDS,
    OperationMode,
    POSITION_ACTUAL_VALUE,
    SOFTWARE_POSITION_LIMIT,
    SPEED_FOR_SWITCH_SEARCH,
    SPEED_FOR_ZERO_SEARCH,
    STATUSWORD,
    SW,
    State as CiA402State,
    TARGET_VELOCITY,
    VELOCITY_ACTUAL_VALUE,
    target_reached,
)
from being.can.cia_402 import which_state
from being.can.definitions import HOMING_OFFSET
from being.can.nmt import OPERATIONAL
from being.constants import FORWARD, BACKWARD, INF
from being.error import BeingError
from being.math import clip


LOGGER = logging.getLogger(__name__)


HomingRange = Tuple[int, int]
"""Lower and upper homing range."""


class HomingState(enum.Enum):

    """Possible homing states."""

    FAILED = 0
    UNHOMED = 1
    ONGOING = 2
    HOMED = 3


HomingProgress = Generator[HomingState, None, None]
"""Yielding the current homing state."""

MINIMUM_HOMING_WIDTH = 0.010
"""Minimum width of homing range for a successful homing."""


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
        print('Not enough space to align')
        return lower, upper

    margin = (width - length) // 2
    return lower + margin, upper - margin


# TODO(atheler): Move CiA 402 homing functions -> CiA402Node as methods


def start_homing(node):
    """Start homing procedure for node."""
    LOGGER.info('start_homing()')
    # Controlword bit 4 has to go from 0 -> 1
    node.sdo[CONTROLWORD].raw = Command.ENABLE_OPERATION
    node.sdo[CONTROLWORD].raw = Command.ENABLE_OPERATION | CW.START_HOMING_OPERATION


def stop_homing(node):
    """Stop homing procedure for node."""
    LOGGER.info('stop_homing()')
    # Controlword bit has to go from 1 -> 0
    node.sdo[CONTROLWORD].raw = Command.ENABLE_OPERATION | CW.START_HOMING_OPERATION
    node.sdo[CONTROLWORD].raw = Command.ENABLE_OPERATION


def homing_started(node) -> bool:
    """Check if homing procedure has started."""
    sw = node.sdo[STATUSWORD].raw
    started = not check_bit_mask(sw, SW.HOMING_ATTAINED) and not check_bit_mask(sw, SW.TARGET_REACHED)
    #print('homing_started()', started)
    return started


def homing_ended(node) -> bool:
    """Check if homing procedure has ended."""
    sw = node.sdo[STATUSWORD].raw
    ended = check_bit_mask(sw, SW.HOMING_ATTAINED) and check_bit_mask(sw, SW.TARGET_REACHED)
    #print('homing_ended()', ended)
    return ended


def homing_reference_run(node: CiA402Node) -> HomingProgress:
    """Travel down homing road."""
    while not homing_started(node):
        yield HomingState.ONGOING

    while not homing_ended(node):
        yield HomingState.ONGOING


def proper_homing(node: CiA402Node, timeout: float = 10.0) -> HomingProgress:
    """Proper CiA 402 homing."""
    with node.restore_states_and_operation_mode():
        node.change_state(CiA402State.READY_TO_SWITCH_ON)
        node.set_operation_mode(OperationMode.HOMING)
        node.nmt.state = OPERATIONAL
        node.change_state(CiA402State.OPERATION_ENABLE)

        startTime = time.perf_counter()
        endTime = startTime + timeout

        def timeout_expired():
            expired = time.perf_counter() > endTime
            return expired

        start_homing(node)

        for state in homing_reference_run(node):
            if timeout_expired():
                LOGGER.error('Homing for %s: Timeout expired!', node)
                state = HomingState.FAILED
                break

            yield state
        else:  # If no break
            state = HomingState.HOMED

        stop_homing(node)

        node.change_state(CiA402State.READY_TO_SWITCH_ON)

    yield state


def crude_homing(
        node,
        homingDirection,
        speed,
        minLength,
        relMargin=0.010,
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
        minLength: Minimum width for homing in device units.

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
        if homingWidth < minLength:
            raise HomingFailed(f'Homing width to narrow. Homing range: {[lower, upper]}!')

        lower += relMargin * homingWidth
        upper -= relMargin * homingWidth

        node.sdo[HOMING_OFFSET].raw = lower
        node.sdo[SOFTWARE_POSITION_LIMIT][1].raw = 0
        node.sdo[SOFTWARE_POSITION_LIMIT][2].raw = upper - lower

    yield HomingState.HOMED
