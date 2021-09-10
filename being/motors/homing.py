"""Homing procedures and definitions."""
import abc
import enum
import itertools
import logging
import random
import time
from typing import Generator, Tuple, Callable

from canopen.variable import Variable

from being.bitmagic import check_bit_mask
from being.can.cia_402 import (
    CONTROLWORD,
    CW,
    Command,
    MODES_OF_OPERATION,
    OperationMode,
    STATUSWORD,
    SW,
    State as CiA402State,
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


def start_homing(controlword: Variable) -> Generator:
    """Start homing procedure for node.

    Args:
        controlword: canopen control word variable.
    """
    LOGGER.info('start_homing()')
    # Controlword bit 4 has to go from 0 -> 1
    controlword.raw = Command.ENABLE_OPERATION
    yield
    controlword.raw = Command.ENABLE_OPERATION | CW.START_HOMING_OPERATION


def stop_homing(controlword: Variable) -> Generator:
    """Stop homing procedure for node.

    Args:
        controlword: canopen control word variable.
    """
    LOGGER.info('stop_homing()')
    # Controlword bit has to go from 1 -> 0
    controlword.raw = Command.ENABLE_OPERATION | CW.START_HOMING_OPERATION
    yield
    controlword.raw = Command.ENABLE_OPERATION


def homing_started(statusword: Variable) -> bool:
    """Check if homing procedure has started.

    Args:
        statusword: canopen status word variable.
    """
    sw = statusword.raw
    started = not check_bit_mask(sw, SW.HOMING_ATTAINED) and not check_bit_mask(sw, SW.TARGET_REACHED)
    return started


def homing_ended(statusword: Variable) -> bool:
    """Check if homing procedure has ended.

    Args:
        statusword: canopen status word variable.
    """
    sw = statusword.raw
    ended = check_bit_mask(sw, SW.HOMING_ATTAINED) and check_bit_mask(sw, SW.TARGET_REACHED)
    return ended


def homing_reference_run(statusword: Variable) -> HomingProgress:
    """Travel down homing road.

    Args:
        controlword: canopen controlword variable.
    """
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

    def teardown(self) -> Generator:
        """Tear down logic. Will be used to abort an ongoing homing job."""
        return
        yield

    @abc.abstractmethod
    def homing_job(self) -> Generator:
        """Primary homing job."""
        return
        yield

    def home(self):
        """Start homing."""
        if self.job:
            self.job = itertools.chain(self.teardown(), self.homing_job())
        else:
            self.job = self.homing_job()

        self.state = HomingState.ONGOING

    def update(self):
        """Tick homing one step further."""
        if not self.job:
            return

        try:
            next(self.job)
        except StopIteration:
            self.job = None

    def __str__(self):
        return f'{type(self).__name__}({self.state})'


class DummyHoming(HomingBase):

    """Dummy homing for testing with virtual motors."""

    def __init__(self,
            minDuration: float = 1.,
            maxDuration: float = 2.,
            successProbability: float = 0.9,
            time_func: Callable = time.perf_counter,
        ):
        """Kwargs:
            minDuration: Minimum duration of dummy homing.
            maxDuration: Maximum duration of dummy homing.
            successProbability: Success probability of dummy homing.
            time_func: Timing function.
        """
        super().__init__()
        self.minDuration = minDuration
        self.maxDuration = maxDuration
        self.successProbability = successProbability
        self.time_func = time_func

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

    def change_state(self, target) -> Generator:
        """Change to node's state job."""
        return self.node.change_state(target, how='pdo', generator=True)

    def capture(self):
        """Capture current node's state and operation mode."""
        self.logger.debug('capture()')
        self.oldState = self.node.get_state('pdo')
        self.oldOp = self.node.get_operation_mode()

    def restore(self):
        """Restore node's state and operation mode."""
        self.logger.debug('restore()')
        if self.oldState is None or self.oldOp is None:
            print('Nothing to restore')
            return

        self.logger.debug('Restoring oldState: %s, oldOp: %s', self.oldState, self.oldOp)

        yield from self.change_state(CiA402State.SWITCHED_ON)
        self.logger.debug('Setting operation mode %s', self.oldOp)
        self.node.sdo[MODES_OF_OPERATION].raw = self.oldOp
        yield from self.change_state(self.oldState)
        self.oldState = self.oldOp = None
        self.logger.debug('Done with restoring')

    def timeout_expired(self) -> bool:
        """Check if timeout expired."""
        expired = time.perf_counter() > self.endTime
        if expired:
            self.logger.warning('Timeout expired')

        return expired

    def teardown(self):
        yield from stop_homing(self.controlword)
        yield from self.restore()

    def cia_402_homing_job(self):
        """CiA 402 homing routine."""
        startTime = time.perf_counter()
        self.endTime = startTime + self.timeout
        self.capture()
        yield from self.change_state(CiA402State.SWITCHED_ON)
        self.logger.debug('Setting operation mode %s', OperationMode.HOMING)
        self.node.sdo[MODES_OF_OPERATION].raw = OperationMode.HOMING
        yield from start_homing(self.controlword)
        self.final = HomingState.UNHOMED
        self.logger.debug('homing reference run')
        for _ in homing_reference_run(self.statusword):
            if self.timeout_expired():
                final = HomingState.FAILED
                break

            yield
        else:
            final = HomingState.HOMED

        yield from self.teardown()
        self.state = final

    def faulhabr_hard_stop_homing(self):
        raise NotImplementedError

    def homing_job(self):
        self.logger.debug('homing_job()')
        if self.useCustomHardStop:
            return self.faulhabr_hard_stop_homing()
        else:
            return self.cia_402_homing_job()

    def __str__(self):
        return f'{type(self).__name__}({self.node}, {self.state})'


class CrudeHoming(CiA402Homing):
    pass
