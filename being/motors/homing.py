"""Homing procedures and definitions."""
import abc
import enum
import itertools
import random
import time
from typing import Generator, Callable, Optional

from canopen.variable import Variable

from being.bitmagic import check_bit_mask
from being.can.cia_402 import (
    CONTROLWORD,
    CW,
    Command,
    MODES_OF_OPERATION,
    NEGATIVE,
    OperationMode,
    POSITIVE,
    STATUSWORD,
    SW,
    State as CiA402State,
    UNDEFINED,
    determine_homing_method
)
from being.constants import INF
from being.logging import get_logger
from being.serialization import register_enum
from being.utils import toss_coin


LOGGER = get_logger(name=__name__, parent=None)


class HomingState(enum.Enum):

    """Possible homing states."""

    FAILED = 0
    UNHOMED = 1
    ONGOING = 2
    HOMED = 3


register_enum(HomingState)


def default_homing_method(
        homingMethod: Optional[int] = None,
        homingDirection: int = UNDEFINED,
        endSwitches: bool = False,
        indexPulse: bool = False,
    ) -> int:
    """Determine homing method from default homing kwargs."""
    if homingMethod is not None:
        return homingMethod

    if homingDirection == UNDEFINED:
        return 35

    if endSwitches:
        if homingDirection > 0:
            return determine_homing_method(endSwitch=POSITIVE, indexPulse=indexPulse)
        else:
            return determine_homing_method(endSwitch=NEGATIVE, indexPulse=indexPulse)
    else:
        if homingDirection > 0:
            return determine_homing_method(direction=POSITIVE, hardStop=True, indexPulse=indexPulse)
        else:
            return determine_homing_method(direction=NEGATIVE, hardStop=True, indexPulse=indexPulse)


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


def homing_reference_run(statusword: Variable) -> Generator:
    """Travel down homing road.

    Args:
        controlword: canopen controlword variable.
    """
    while not homing_started(statusword):
        yield

    while not homing_ended(statusword):
        yield


class HomingBase(abc.ABC):

    """Abstract homing base class."""

    def __init__(self):
        self.state = HomingState.UNHOMED
        self.job = None
        self.logger = get_logger('Homing')

    @property
    def ongoing(self) -> bool:
        """True if homing in progress."""
        return self.state is HomingState.ONGOING

    @property
    def homed(self) -> bool:
        """True if homing in progress."""
        return self.state is HomingState.HOMED

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
        if self.job:
            try:
                next(self.job)
            except StopIteration:
                self.job = None
            except TimeoutError as err:
                self.job = None
                self.logger.exception(err)

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
        """Args:
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

    """CiA 402 by the book."""

    def __init__(self, node, timeout=10.0, **kwargs):
        super().__init__()
        self.node = node
        self.timeout = timeout
        self.homingMethod = default_homing_method(**kwargs)

        self.logger = get_logger(f'CiA402Homing(nodeId: {node.id})')
        self.statusword = node.pdo[STATUSWORD]
        self.controlword = node.pdo[CONTROLWORD]
        self.oldState = None
        self.oldOp = None
        self.endTime = -1

    def change_state(self, target) -> Generator:
        """Change to node's state job."""
        return self.node.state_switching_job(target, how='pdo')

    def capture(self):
        """Capture current node's state and operation mode."""
        self.logger.debug('capture()')
        self.oldState = self.node.get_state('pdo')
        self.oldOp = self.node.get_operation_mode()

    def restore(self):
        """Restore node's state and operation mode."""
        self.logger.debug('restore()')
        if self.oldState is None or self.oldOp is None:
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

    def homing_job(self):
        """CiA 402 homing routine."""
        self.logger.debug('homing_job()')
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

    def __str__(self):
        return f'{type(self).__name__}({self.node}, {self.state})'


class CrudeHoming(CiA402Homing):
    """Crude hard stop homing for Faulhaber linear motors.

    Args:
        speed: Speed for homing in device units.
    """

    def __init__(self, node, minWidth, currentLimit, *args, **kwargs):
        super().__init__(node, *args, **kwargs)
        self.minWidth = minWidth
        self.currentLimit = currentLimit
        self.lower = INF
        self.upper = -INF

    @property
    def width(self) -> float:
        """Current homing width in device units."""
        return self.upper - self.lower

    def reset_range(self):
        """Reset homing range."""
        self.lower = INF
        self.upper = -INF

    def expand_range(self, pos: float):
        """Expand homing range."""
        self.lower = min(self.lower, pos)
        self.upper = max(self.upper, pos)

    def halt_drive(self) -> Generator:
        """Stop drive."""
        self.logger.debug('halt_drive()')
        self.controlword.raw = Command.ENABLE_OPERATION | CW.HALT
        yield

    def move_drive(self, velocity: int) -> Generator:
        """Move motor with constant velocity."""
        self.logger.debug('move_drive(%d)', velocity)
        self.controlword.raw = Command.ENABLE_OPERATION
        yield
        self.node.set_target_velocity(velocity)
        yield
        self.controlword.raw = Command.ENABLE_OPERATION | CW.NEW_SET_POINT
        yield

    def on_the_wall(self) -> bool:
        """Check if motor is on the wall."""
        current = self.node.sdo['Current Actual Value'].raw
        return current > self.currentLimit  # Todo: Add percentage threshold?

    def teardown(self):
        yield from self.halt_drive()
        yield from self.restore()

    def homing_job(self, speed: int = 100):
        self.logger.debug('homing_job()')
        self.lower = INF
        self.upper = -INF
        node = self.node
        sdo = self.node.sdo
        if self.homingMethod in {-1, -3}:
            # Forward direction
            velocities = [speed, -speed]
        else:
            # Backward direction
            velocities = [-speed, speed]

        self.capture()

        yield from self.change_state(CiA402State.READY_TO_SWITCH_ON)
        sdo['Home Offset'].raw = 0
        node.set_operation_mode(OperationMode.PROFILE_VELOCITY)

        for vel in velocities:
            yield from self.halt_drive()
            yield from self.move_drive(vel)
            self.logger.debug('Driving towards the wall')
            while not self.on_the_wall():
                self.expand_range(node.get_actual_position())
                yield

            self.logger.debug('Hit the wall')
            yield from self.halt_drive()

            # Turn off voltage to reset current current value
            yield from self.change_state(CiA402State.READY_TO_SWITCH_ON)

        yield from self.teardown()

        width = self.upper - self.lower
        if width < self.minWidth:
            self.logger.info('Homing failed. Width too narrow %f', width)
            final = HomingState.FAILED
        else:
            self.logger.info('Homing successful')
            final = HomingState.HOMED

            # Center in the middle
            margin = .5 * (width - self.minWidth)
            self.lower += margin
            self.upper -= margin

            sdo['Home Offset'].raw = self.lower

        self.state = final
