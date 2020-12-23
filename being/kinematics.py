"""Kinematic trajectory filtering."""
import collections
import functools

import numpy as np

from being.constants import INF
from being.math import clip, sign, solve_quadratic_equation


State = collections.namedtuple('State', 'position velocity acceleration', defaults=(0., 0., 0.))


def step(state: State, dt: float) -> State:
    """Evolve state for some time interval."""
    x0, v0, a0 = state
    return State(
        x0 + v0 * dt + .5 * a0 * dt**2,
        v0 + a0 * dt,
        a0,
    )


def sequencable(func):
    """Filter function for an sequence of input values. Carry on state between
    single filter calls.
    """
    @functools.wraps(func)
    def wrapped_func(targets, dt, state=State(), **kwargs):
        if isinstance(targets, float):
            return func(targets, dt, state=state, **kwargs)

        traj = []
        for target in targets:
            state = func(target, dt, state=state, **kwargs)
            traj.append(state)

        return np.array(traj)

    return wrapped_func


#@sequencable
def kinematic_filter(target: float, dt: float, state: State = State(),
        maxSpeed: float = 1., maxAcc: float = 1., lower: float = -INF,
        upper: float = INF) -> State:
    """Filter position trajectory with respect to the kinematic limits (maximum
    speed and maximum acceleration / deceleration).

    Args:
        target: Target position value.
        state: Initial / current state.
        dt: Time interval.
        maxSpeed: Maximum speed value.
        maxAcc: Maximum acceleration (and deceleration) value.
        lower: Lower clipping value for target value.
        upper: Upper clipping value for target value.

    Returns:
        The next state.

    Explanation:
        We ask ourselves how can we reach the target value from the current
        state with a triangular / trapezoidal S-speed profile? Such a profile
        consists of three possible segments:
          - Segment 0 Accelerating
          - Segment 1 Cruising with maxSpeed
          - Segment 2 Decelerating

        This is essentially a piecewise polynomial quadratic spline.

        We use the following nomenclature / variable names:
          - x, v and a: Position, velocity and acceleration at the start of the
            segment.
          - h: Segment duration.
          - d: Position displacement of the segment

        | x0 | x1 | x2 |
        | v0 | v1 | v2 |
        | a0 | a2 | a2 |

          h0   h1   h2

        --------------->
              Time

        x0 and v0 correspond to the initial state / condition (we are in control
        of the acceleration therefore it is not used).

        Depending on the error and the initial state one or two of these
        segments can have zero width. E.g. Already at maxSpeed -> h0 = 0, not
        enough time to accelerate to maxSpeed -> h1 = 0, already breaking -> h0
        = h1 = 0. Etc.

        This function performs essentially the following steps:
          1) Determine thrust direction
          2) How much acceleration headroom do we have?
          3) When do we need to start breaking so to reach the target without
             overshooting and ending up in steady state (vEnd = 0)?
          4) When would we reach maxSpeed?
          5) Calculate and evaluate necessary spline coefficients.
    """
    # Validation
    target = clip(target, lower, upper)
    maxSpeed = abs(maxSpeed)
    maxAcc = abs(maxAcc)
    assert maxSpeed > 0
    assert maxAcc > 0
    x0, v0, _ = state
    v0 = clip(v0, -maxSpeed, maxSpeed)

    # Thrust direction and early exit
    err = target - x0
    if err == 0:
        if v0 == 0:
            return State(position=target, velocity=0., acceleration=0.)

        direction = -sign(v0)  # Already at target overshooting. Row back
    else:
        direction = sign(err)

    # Acceleration headroom / intensity. If target within reach undercut maxAcc.
    # This reduces ringing / oscillation when close to steady state.
    headroom = abs((err - v0 * dt) / (.5 * dt**2))
    accValue = min(headroom, maxAcc)
    a0 = direction * accValue
    a2 = -direction * accValue

    # Time until we have to break in order to reach target. Solve the following
    # quadratic equation for h0. This gives us two time candidates for h0: t0
    # and t1.
    #
    #   err - dBreak(h0) = v0 * h0 + .5 * a0 * h0^2
    #
    # where dBreak(h0) = -v1^2 / (2 * a2) =  -(v0 + a0 * h0)^2 / (2 * a2).
    # We take the larger solution.
    # TODO: How to handle complex solutions? Under which circumstances can they
    # occure and what do they mean?
    t0, t1 = solve_quadratic_equation(a0, 2 * v0, -(err + v0**2 / (2 * a2)))
    timeUntilBreak = max(t0, t1)
    if timeUntilBreak <= 0:
        # Already overshooting. We need to break right now.
        return step((x0, v0, a2), dt)

    # How long until we reach maxSpeed?
    # Solve direction * maxSpeed = v0 + a0 * t for t
    timeUntilMaxSpeed = (direction * maxSpeed - v0) / a0

    # Segment 0 (accelerating)
    h0 = min(timeUntilMaxSpeed, timeUntilBreak)
    d0 = v0 * h0 + .5 * a0 * h0**2

    # Segment 2 (decelerating) kinematics have to be computed before segment 1
    # (cruising).
    v1 = v2 = v0 + a0 * h0  # Constant speed while cruising
    h2 = -v2 / a2
    d2 = v2 * h2 + .5 * a2 * h2**2

    # Segment 1 (cruising). Segment duration h1 can be zero (triangular speed
    # profile)
    d1 = err - d0 - d2
    h1 = max(0., d1 / v1)  # TODO: Zero division?

    # Go through the three segments and exit at the appropriate moment. h0 -> h1
    # -> h2. In which segment are we in at dt? Kind of manual evaluation of
    # piecewise quadratic spline
    if dt <= h0:
        # Accelerating
        return step((x0, v0, a0), dt)

    remaining = dt - h0
    if remaining <= h1:
        # Cruising
        return step((x0 + d0, v1, 0.), dt=remaining)

    remaining -= h1

    # Decelerating
    return step((x0 + d0 + d1, v2, a2), dt=remaining)
