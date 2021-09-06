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
    OperationMode,
    STATUSWORD,
    SW,
    State as CiA402State,
)
from being.can.nmt import OPERATIONAL, PRE_OPERATIONAL
from being.error import BeingError


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


def change_state_gen(node, target):
    """Generator based change_state() function. Some controllers are slow..."""
    node.change_state(target)
    while not node.get_state() is target:
        yield HomingState.ONGOING


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


def proper_homing(node: CiA402Node, timeout: float = 5.0) -> HomingProgress:
    """Proper CiA 402 homing.

    Args:
        node: Node to home

    Kwargs:
        timeout: Max duration of homing
        node: Node to home

    """
    startTime = time.perf_counter()
    endTime = startTime + timeout

    def timeout_expired():
        expired = time.perf_counter() > endTime
        return expired

    state = HomingState.ONGOING

    with node.restore_states_and_operation_mode():
        yield from change_state_gen(node, CiA402State.SWITCHED_ON)
        node.set_operation_mode(OperationMode.HOMING)
        yield from change_state_gen(node, CiA402State.OPERATION_ENABLE)

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

        yield from change_state_gen(node, CiA402State.SWITCHED_ON)

    yield state
