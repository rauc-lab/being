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
from being.can.nmt import OPERATIONAL
from being.error import BeingError


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
