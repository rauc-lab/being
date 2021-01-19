"""Homing of motor drives."""
import time
import logging

from being.can.cia_402 import State, Command, OperationMode, CW
from being.can.definitions import (
    CONTROLWORD,
    HOMING_OFFSET,
    POSITION_ACTUAL_VALUE,
    SOFTWARE_POSITION_LIMIT,
    TARGET_VELOCITY,
)
from being.constants import INF
from being.math import sign


SI_2_FAULHABER = 1e6
"""Unit conversion for Lineare DC-Servomotoren Serie LM 0830 ... 01."""


def _move(node, speed: int):
    """Move motor with constant speed."""
    node.sdo[TARGET_VELOCITY].raw = speed
    node.sdo[CONTROLWORD].raw = Command.ENABLE_OPERATION | CW.NEW_SET_POINT


def _home_drive(node, rodLength=None, speed: int = 150):
    """Crude homing procedure. Move with PROFILED_VELOCITY operation mode
    upwards and downwards until reaching limits (position not increasing or
    decreasing anymore). Implemented as Generator so that we can home multiple
    motors in parallel (quasi pseudo coroutine).

    Args:
        node (CiA402Node): Drive to home.

    Kwargs:
        speed: Homing speed.
    """
    direction = sign(speed)
    speed = abs(speed)

    logger = logging.getLogger(str(node))
    logger.info('Starting homing for %s', node)
    with node.restore_states_and_operation_mode():
        node.nmt.state = 'PRE-OPERATIONAL'
        node.change_state(State.READY_TO_SWITCH_ON)
        node.sdo[HOMING_OFFSET].raw = 0
        #TODO: Do we need to set NMT to 'OPERATIONAL'?
        node.set_operation_mode(OperationMode.PROFILED_VELOCITY)
        node.change_state(State.OPERATION_ENABLE)

        logger.info('Moving upwards')
        pos = node.sdo[POSITION_ACTUAL_VALUE].raw
        upper = -INF
        _move(node, direction * speed)
        while pos > upper:
            upper = pos
            yield True
            pos = node.sdo[POSITION_ACTUAL_VALUE].raw

        logger.info('Moving downwards')
        lower = INF
        _move(node, -direction * speed)
        while pos < lower:
            lower = pos
            yield True
            pos = node.sdo[POSITION_ACTUAL_VALUE].raw

        width = upper - lower
        if rodLength:
            dx = .5 * (width - rodLength * SI_2_FAULHABER)
            if dx > 0:
                lower, upper = lower + dx, upper - dx

        node.change_state(State.READY_TO_SWITCH_ON)
        node.sdo[HOMING_OFFSET].raw = lower
        node.sdo[SOFTWARE_POSITION_LIMIT][1].raw = 0
        node.sdo[SOFTWARE_POSITION_LIMIT][2].raw = upper - lower

        logger.info('Homed')
        logger.debug('HOMING_OFFSET:              %s', lower)
        logger.debug('SOFTWARE_POSITION_LIMIT[1]: %s', 0)
        logger.debug('SOFTWARE_POSITION_LIMIT[2]: %s', upper - lower)

    while True:
        yield False


def home_drives(*drives, interval=.01, timeout=2., **kwargs):
    """Home multiple drives in parallel."""
    homings = [_home_drive(drive, **kwargs) for drive in drives]
    starTime = time.perf_counter()
    while any(map(next, homings)):
        passed = time.perf_counter() - starTime
        if passed > timeout:
            raise RuntimeError('Could not home all motors before timeout')

        time.sleep(interval)

    return True
