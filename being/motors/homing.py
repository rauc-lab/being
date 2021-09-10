"""Homing procedures and definitions."""
import abc
import enum
import itertools
import logging
import random
import time
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
    which_state,
    MODES_OF_OPERATION,
)
from being.utils import toss_coin


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


# TODO(atheler): Move CiA 402 homing functions -> CiA402Node as methods


def start_homing(controlword):
    """Start homing procedure for node."""
    LOGGER.info('start_homing()')
    # Controlword bit 4 has to go from 0 -> 1
    controlword.raw = Command.ENABLE_OPERATION
    yield
    controlword.raw = Command.ENABLE_OPERATION | CW.START_HOMING_OPERATION


def stop_homing(controlword):
    """Stop homing procedure for node."""
    LOGGER.info('stop_homing()')
    # Controlword bit has to go from 1 -> 0
    controlword.raw = Command.ENABLE_OPERATION | CW.START_HOMING_OPERATION
    yield
    controlword.raw = Command.ENABLE_OPERATION


def homing_started(statusword) -> bool:
    """Check if homing procedure has started."""
    sw = statusword.raw
    started = not check_bit_mask(sw, SW.HOMING_ATTAINED) and not check_bit_mask(sw, SW.TARGET_REACHED)
    #print('homing_started()', started)
    return started


def homing_ended(statusword) -> bool:
    """Check if homing procedure has ended."""
    sw = statusword.raw
    ended = check_bit_mask(sw, SW.HOMING_ATTAINED) and check_bit_mask(sw, SW.TARGET_REACHED)
    #print('homing_ended()', ended)
    return ended


def homing_reference_run(statusword) -> HomingProgress:
    """Travel down homing road."""
    while not homing_started(statusword):
        yield HomingState.ONGOING

    while not homing_ended(statusword):
        yield HomingState.ONGOING


class HomingBase(abc.ABC):

    """Abstract homing base class."""

    def __init__(self):
        self.state = HomingState.UNHOMED
        self.job = None
        self.logger = logging.getLogger('Homing')

    @property
    def ongoing(self) -> bool:
        """True if homing in progress."""
        return self.state is HomingState.ONGOING

    @abc.abstractmethod
    def abort_job(self) -> Generator:
        """Abort homing job."""

    @abc.abstractmethod
    def homing_job(self) -> Generator:
        """Homing job."""

    def home(self):
        """Start homing."""
        self.state = HomingState.ONGOING
        if self.job:
            self.job = itertools.chain(
                self.abort_job(),
                self.homing_job(),
            )
        else:
            self.job = self.homing_job()

    def update(self):
        if not self.job:
            return

        try:
            next(self.job)
        except StopIteration:
            self.job = None
            return

    def __str__(self):
        return f'{type(self).__name__}({self.state})'


class DummyHoming(HomingBase):
    def __init__(self,
            minDuration=1.,
            maxDuration=2.,
            successProbability=0.9,
            time_func=time.perf_counter,
        ):
        super().__init__()
        self.minDuration = minDuration
        self.maxDuration = maxDuration
        self.successProbability = successProbability
        self.time_func = time_func

    def abort_job(self):
        self.state = HomingState.UNHOMED
        return
        yield

    def homing_job(self) -> Generator:
        duration = random.uniform(self.minDuration, self.maxDuration)
        endTime = self.time_func() + duration
        self.state = HomingState.ONGOING
        while self.time_func() < endTime:
            yield

        if toss_coin(self.successProbability):
            self.state = HomingState.HOMED
        else:
            self.state = HomingState.FAILED

    def __str__(self):
        return f'{type(self).__name__}({self.state})'


class CiA402Homing(HomingBase):
    def __init__(self, node, timeout=10.0, useCustomHardStop=False):
        super().__init__()
        self.node = node
        self.timeout = timeout

        self.statusword = node.pdo[STATUSWORD]
        self.controlword = node.pdo[CONTROLWORD]
        self.oldState = None
        self.oldOp = None
        self.logger = logging.getLogger(f'CiA402Homing(nodeId: {node.id})')
        self.endTime = -1

        self.useCustomHardStop = useCustomHardStop

        self.lower = None
        self.upper = None

    def change_state(self, target):
        return self.node.change_state(target, how='pdo', generator=True)

    def capture(self):
        self.logger.debug('capture()')
        self.oldState = which_state(self.statusword.raw)
        self.oldOp = self.node.get_operation_mode()

    def restore(self):
        self.logger.debug('restore()')
        if self.oldState is None or self.oldOp is None:
            return

        yield from self.change_state(CiA402State.SWITCHED_ON)
        self.node.sdo[MODES_OF_OPERATION].raw = self.oldOp
        yield from self.change_state(self.oldState)
        self.oldState = self.oldOp = None

    def timeout_expired(self):
        expired = time.perf_counter() > self.endTime
        if expired:
            self.logger.warning('Timeout expired')
        return expired

    def cia_402_homing_job(self):
        startTime = time.perf_counter()
        self.endTime = startTime + self.timeout
        self.capture()
        yield from self.change_state(CiA402State.SWITCHED_ON)
        self.node.sdo[MODES_OF_OPERATION].raw = OperationMode.HOMING
        yield from start_homing(self.controlword)
        final = HomingState.UNHOMED
        self.logger.debug('homing reference run')
        for _ in homing_reference_run(self.statusword):
            if self.timeout_expired():
                final = HomingState.FAILED
                break

            yield
        else:
            final = HomingState.HOMED

        yield from stop_homing(self.controlword)
        yield from self.restore()
        self.state = final

    def faulhabr_hard_stop_homing(self):
        raise NotImplementedError

    def homing_job(self):
        if self.useCustomHardStop:
            return self.faulhabr_hard_stop_homing()
        else:
            return self.cia_402_homing_job()

    def abort_job(self):
        yield from self.stop()
        yield from self.restore()
        self.state = HomingState.UNHOMED

    def __str__(self):
        return f'{type(self).__name__}({self.node}, {self.state})'


class CrudeHoming(CiA402Homing):
    pass
