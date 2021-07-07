"""Homing of motor blocks / CiA402Nodes.

For now homing is implemented as *homing generators*. This might seem overly
complicated but we do this so that we can move blocking aspects to the caller
and home multiple motors / nodes in parallel. This results in quasi coroutines.
We do not use asyncio because we want to keep the core async free for now.
"""
from typing import Iterable, Generator, Optional, Tuple
import enum
import time

from being.can.cia_402 import OperationMode, Command, CW, CiA402Node
from being.can.cia_402 import State as CiA402State
from being.can.definitions import (
    CONTROLWORD,
    HOMING_METHOD,
    HOMING_OFFSET,
    POSITION_ACTUAL_VALUE,
    TARGET_VELOCITY,
    VELOCITY_ACTUAL_VALUE,
)
from being.constants import INF
from being.error import BeingError
from being.math import sign


# TODO: Implement "non-crude" homings for the different controllers / end-switch
# yes/no etc... Also need to think of a sensible lookup of homing methods. There
# are some tricky differences like:
#   - CanOpen register for end-switch on Faulhaber is not standard CiA402
#   - Homing method 35 is deprecated since a new CiA 402 standard. Got replaced
#     with 37. Maxon Epos 2 and Faulhaber still use 35, Maxon Epos 4 uses the
#     new 37


class HomingState(enum.Enum):

    """Possible homing states."""

    FAILURE = 0  # TODO: To be removed since it hides error trace back? Should
                 # we always raise exception?
    SUCCESS = 1
    RUNNING = 2


HomingProgress = Generator[HomingState, None, None]
"""Yielding the current homing state."""

HomingRange = Tuple[int, int]
"""Lower and upper homing range."""

MINIMUM_HOMING_WIDTH = 0.010
"""Minimum width of homing range for a successful homing."""

DEFAULT_HOMING_VELOCITY_DEV = 50
"""Default homing velocity. In device units!"""


class HomingFailed(BeingError):

    """Something went wrong while homing."""


def _fetch_position(node: CiA402Node) -> int:
    """Fetch actual position value from node.

    Args:
        node: Connected CiA402 node.

    Returns:
        Position value in device units.
    """
    return node.sdo[POSITION_ACTUAL_VALUE].raw


def _fetch_velocity(node: CiA402Node) -> int:
    """Fetch actual velocity value from node.

    Args:
        node: Connected CiA402 node.

    Returns:
        Velocity value in device units.
    """
    return node.sdo[VELOCITY_ACTUAL_VALUE].raw


def _move_node(node: CiA402Node, speed: int, deadTime=1.) -> HomingProgress:
    """Move motor with constant speed.

    Args:
        node: Connected CiA402 node.

    Kwargs:
        speed: Speed value in device units.
        deadTime: Idle time after sending out command.

    Yields:
        HomingState.RUNNING
    """
    node.sdo[TARGET_VELOCITY].raw = int(speed)
    node.sdo[CONTROLWORD].raw = Command.ENABLE_OPERATION | CW.NEW_SET_POINT
    endTime = time.perf_counter() + deadTime
    while time.perf_counter() < endTime:
        # Early exit if speed error below relative 10%
        vel = _fetch_velocity(node)
        if abs(speed - vel) < .1 * abs(speed):
            return

        yield HomingState.RUNNING


def _stop_node(node: CiA402Node):
    """Set target velocity to zero.

    Args:
        node: Connected CiA402 node.
    """
    node.sdo[TARGET_VELOCITY].raw = 0
    node.sdo[CONTROLWORD].raw = Command.ENABLE_OPERATION | CW.NEW_SET_POINT


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


def crude_homing(
        node: CiA402Node,
        velocity: int = DEFAULT_HOMING_VELOCITY_DEV,
        length: Optional[float] = None,
        deadTime: float = 1.,
    ) -> HomingProgress:
    """Crude homing procedure. Move with PROFILED_VELOCITY operation mode in
    both direction until reaching the limits (position not increasing or
    decreasing anymore). Implemented as Generator so that we can home multiple
    motors in parallel (quasi pseudo coroutine). time.sleep has to be handled by
    the caller.

    Velocity direction controls initial homing direction.

    Args:
        node: Connected CiA402 node.

    Kwargs:
        speed: Homing speed.
        deadCycles: Number of cycles we give the motor to start moving in a direction.

    Yields:
        Homing state.
    """
    direction = sign(velocity)
    speed = abs(velocity)
    lower = upper = None
    """Lower and upper bound of homing range."""

    def home_forward() -> HomingProgress:
        """Home in forward direction until upper limits is not increasing
        anymore.
        """
        nonlocal upper
        upper = -INF
        yield from _move_node(node, speed, deadTime)
        while (pos := _fetch_position(node)) > upper:
            upper = pos
            yield HomingState.RUNNING

        _stop_node(node)


    def home_backward() -> HomingProgress:
        """Home in backward direction until `lower` is not decreasing
        anymore.
        """
        nonlocal lower
        lower = INF
        yield from _move_node(node, -speed, deadTime)
        while (pos := _fetch_position(node)) < lower:
            lower = pos
            yield HomingState.RUNNING

        _stop_node(node)


    # TODO: Design decision: Should we skip the second homing travel when we
    # know the length a priori?
    #   + Would fasten up homing procedure
    #   - Motor will probably always hit on one side
    #
    # -> Let's stick with 2x homing travels (forward / backward) and use the
    # length information to center the known region in the middle of the homing
    # range (adding a small margin on both sides).
    #
    # Second homing travel could be replaced with:
    #
    #    >>> # Homing travel
    #    ... forward = (direction > 0)
    #    ... if forward:
    #    ...     yield from home_forward()
    #    ...     if length is None:
    #    ...         yield from home_backward()
    #    ...     else:
    #    ...         lower = int(upper - length * node.units.length)
    #    ... else:
    #    ...     yield from home_backward()
    #    ...     if length is None:
    #    ...         yield from home_forward()
    #    ...     else:
    #    ...         upper = int(lower + length * node.units.length)


    with node.restore_states_and_operation_mode():
        node.nmt.state = 'PRE-OPERATIONAL'
        node.change_state(CiA402State.READY_TO_SWITCH_ON)
        node.sdo[HOMING_METHOD].raw = 35
        node.sdo[HOMING_OFFSET].raw = 0

        #TODO: Do we need to set NMT to 'OPERATIONAL'?
        node.set_operation_mode(OperationMode.PROFILED_VELOCITY)
        node.change_state(CiA402State.OPERATION_ENABLE)

        # Homing travel
        forward = (direction > 0)
        if forward:
            yield from home_forward()
            yield from home_backward()
        else:
            yield from home_backward()
            yield from home_forward()

        # Homing width validation
        if abs(upper - lower) < MINIMUM_HOMING_WIDTH * node.units.length:
            raise HomingFailed(f'Homing width to narrow. Homing range: {[lower, upper]}!')

        # Center according to rod length
        if length is not None:
            lengthDev = int(length * node.units.length)
            lower, upper = _align_in_the_middle(lower, upper, lengthDev)

        node.change_state(CiA402State.READY_TO_SWITCH_ON)
        node.set_homing_params(lower, upper)

    while True:
        yield HomingState.SUCCESS


def home_motors(motors: Iterable, interval: float = .05, timeout: float = 5., velocity: int = DEFAULT_HOMING_VELOCITY_DEV):
    """Home multiple motors in parallel. This operation will block for time of
    homing but home all motors at the same time / in parallel.

    Args:
        motors: Motors to home.

    Kwargs:
        interval: Tmp. main loop interval for homing.
        timeout: Maximum homing duration. RuntimeError if homing takes to long.
        kwargs: Optional arguments for homing jobs.
    """
    jobs = [
        crude_homing(motor.node, velocity=motor.direction * velocity, length=motor.length)
        for motor in motors
    ]
    starTime = time.perf_counter()
    endTime = starTime + timeout

    while True:
        # Check timeout
        if time.perf_counter() > endTime:
            raise HomingFailed(f'Could not home all motors before timeout {timeout} sec.!')

        states = [next(job) for job in jobs]
        if HomingState.FAILURE in states:
            raise HomingFailed('At least one motor could not be homed!')

        if not HomingState.RUNNING in states:
            break

        time.sleep(interval)
