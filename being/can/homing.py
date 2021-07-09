"""Homing of motor blocks / CiA402Nodes.

For now homing is implemented as *homing generators*. This might seem overly
complicated but we do this so that we can move blocking aspects to the caller
and home multiple motors / nodes in parallel. This results in quasi coroutines.
We do not use asyncio because we want to keep the core async free for now.
"""
from typing import Generator, Tuple, ForwardRef
import enum
import math
import time

from being.can.cia_402 import (
    CONTROLWORD,
    CW,
    CiA402Node,
    Command,
    HOMING_METHOD,
    OperationMode,
    POSITION_ACTUAL_VALUE,
    TARGET_VELOCITY,
    VELOCITY_ACTUAL_VALUE,
)
from being.can.cia_402 import State as CiA402State
from being.can.definitions import HOMING_OFFSET
from being.constants import INF, FORWARD
from being.error import BeingError
from being.math import sign, clip


# TODO: Implement "non-crude" homings for the different controllers / end-switch
# yes/no etc... Also need to think of a sensible lookup of homing methods. There
# are some tricky differences like:
#   - CanOpen register for end-switch on Faulhaber is not standard CiA402
#   - Homing method 35 is deprecated since a new CiA 402 standard. Got replaced
#     with 37. Maxon Epos 2 and Faulhaber still use 35, Maxon Epos 4 uses the
#     new 37


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
    return node.sdo[POSITION_ACTUAL_VALUE].raw


def _fetch_velocity(node: CiA402Node) -> int:
    """Fetch actual velocity value from node.

    Args:
        node: Connected CiA402 node.

    Returns:
        Velocity value in device units.
    """
    return node.sdo[VELOCITY_ACTUAL_VALUE].raw


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
    node.sdo[TARGET_VELOCITY].raw = int(velocity)
    node.sdo[CONTROLWORD].raw = Command.ENABLE_OPERATION | CW.NEW_SET_POINT
    endTime = time.perf_counter() + deadTime
    while time.perf_counter() < endTime:
        vel = _fetch_velocity(node)
        if math.isclose(vel, velocity, rel_tol=0.05, abs_tol=1):
            return

        yield HomingState.ONGOING


def _stop_node(node: CiA402Node, deadTime: float = 2.):
    """Set target velocity to zero.

    Args:
        node: Connected CiA402 node.
    """
    yield from _move_node(node, velocity=0, deadTime=deadTime)


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


def crude_linear_homing(
        motor: LinearMotor,
        direction=FORWARD,
        maxSpeed=0.050,
        deadTime: float = 2.,
        relMargin: float = 0.01,
    ) -> HomingProgress:
    """Crude homing procedure. Move with PROFILED_VELOCITY operation mode in
    both direction until reaching the limits (position not increasing or
    decreasing anymore). Implemented as Generator so that we can home multiple
    motors in parallel (quasi pseudo coroutine). time.sleep has to be handled by
    the caller.

    Velocity direction controls initial homing direction.

    Args:
        motor: Linear motor block.

    Kwargs:
        direction: Initial homing direction.
        maxSpeed: Maximum speed of homing travel.
        deadTime: Max wait time until motor reaches set-point velocities (in
            seconds).
        relMargin: Relative margin if motor length is not known a priori. Final
            length will be the measured length from the two homing travels minus
            `relMargin` percent on both sides.

    Yields:
        Homing state.
    """
    node = motor.node
    direction = sign(direction)
    speed = abs(maxSpeed * node.units.speed)
    lower = None
    upper = None
    relMargin = clip(relMargin, 0.00, 0.50)  # In [0%, 50%]!

    def home_forward() -> HomingProgress:
        """Home in forward direction until upper limits is not increasing
        anymore.
        """
        nonlocal upper
        upper = -INF
        yield from _move_node(node, speed, deadTime)
        while (pos := _fetch_position(node)) > upper:
            upper = pos
            yield HomingState.ONGOING

        yield from _stop_node(node)


    def home_backward() -> HomingProgress:
        """Home in backward direction until `lower` is not decreasing
        anymore.
        """
        nonlocal lower
        lower = INF
        yield from _move_node(node, -speed, deadTime)
        while (pos := _fetch_position(node)) < lower:
            lower = pos
            yield HomingState.ONGOING

        yield from _stop_node(node)


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
        node.set_operation_mode(OperationMode.PROFILED_VELOCITY)
        node.change_state(CiA402State.OPERATION_ENABLE)

        node.sdo[HOMING_METHOD].raw = 35
        node.sdo[HOMING_OFFSET].raw = 0

        # Homing travel
        forward = (direction > 0)
        if forward:
            yield from home_forward()
            yield from home_backward()
        else:
            yield from home_backward()
            yield from home_forward()

        node.change_state(CiA402State.READY_TO_SWITCH_ON)

        homingWidth = (upper - lower) / node.units.length
        if homingWidth < MINIMUM_HOMING_WIDTH:
            raise HomingFailed(f'Homing width to narrow. Homing range: {[lower, upper]}!')

        # Estimate motor length
        if motor.length is None:
            motor.length = (1. - 2 * relMargin) * homingWidth

        # Center according to rod length
        lengthDev = int(motor.length * node.units.length)
        lower, upper = _align_in_the_middle(lower, upper, lengthDev)

        node.set_homing_params(lower, upper)

    while True:
        yield HomingState.HOMED
