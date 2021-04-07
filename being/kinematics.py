"""Optimal trajectory and kinematic filtering."""
import collections
import functools

import numpy as np

from being.constants import INF
from being.math import sign, clip


State = collections.namedtuple('State', 'position velocity acceleration', defaults=(0., 0., 0.))


def optimal_trajectory(
    xEnd: float,
    vEnd: float = 0.,
    state: State = State(),
    maxSpeed: float = 1.,
    maxAcc: float = 1.,
    ) -> list:
    """Calculate acceleration bang profiles for optimal trajectory from initial
    `state` to target position / velocity. Respecting the kinematic limits. Bang
    profiles are given by their duration and the acceleration value.

    Args:
        xEnd: Target position.

    Kwargs:
        vEnd: Target velocity.
        state: Initial state.
        maxSpeed: Maximum speed.
        maxAcc: Maximum acceleration (and deceleration).

    Returns:
        List of bang speed profiles.

    Usage:
        >>> optimal_trajectory(xEnd=1., maxSpeed=.5, maxAcc=1.)
        [(0.5, 1.0), (1.5, 0.0), (0.5, -1.0)]

    Resources:
      - Francisco Ramos, Mohanarajah Gajamohan, Nico Huebel and Raffaello
        D’Andrea: Time-Optimal Online Trajectory Generator for Robotic
        Manipulators.
        http://webarchiv.ethz.ch/roboearth/wp-content/uploads/2013/02/OMG.pdf
    """
    x0, v0, _ = state
    dx = xEnd - x0
    dv = vEnd - v0
    if dx == dv == 0:
        return [(0., 0.)]

    # Determine critical profile
    sv = sign(dv)
    tCritical = sv * dv / maxAcc
    dxCritical = .5 * (vEnd + v0) * tCritical
    if dxCritical == dx:
        return [(tCritical, sv * maxAcc)]

    # Reachable peek speed, in relation with maximum speed, determines shape of
    # speed profile. Either triangular or trapezoidal.
    s = sign(dx - dxCritical)  # Direction
    peekSpeed = (.5 * (vEnd**2 + v0**2) + s * dx * maxAcc)**.5
    if peekSpeed <= maxSpeed:
        # Triangular speed profile
        accDuration = (s * peekSpeed - v0) / (s * maxAcc)
        decDuration = (vEnd - s * peekSpeed) / (-s * maxAcc)
        return [
            (accDuration, s * maxAcc),
            (decDuration, -s * maxAcc),
        ]

    # Trapezoidal speed profile
    accDuration = (s * maxSpeed - v0) / (s * maxAcc)
    t2 = ((vEnd**2 + v0**2 - 2 * s * maxSpeed * v0) /
          (2 * maxAcc) + s * dx) / maxSpeed
    cruiseDuration = t2 - accDuration
    decDuration = (vEnd - s * maxSpeed) / (-s * maxAcc)
    return [
        (accDuration, s * maxAcc),
        (cruiseDuration, 0.),
        (decDuration, -s * maxAcc),
    ]


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


def step(state: State, dt: float) -> State:
    """Evolve state for some time interval."""
    x0, v0, a0 = state
    return State(
        x0 + v0 * dt + .5 * a0 * dt**2,
        v0 + a0 * dt,
        a0,
    )


def kinematic_filter(
    targetPosition: float,
    dt: float,
    state: State = State(),
    targetVelocity: float = 0.,
    maxSpeed: float = 1.,
    maxAcc: float = 1.,
    lower: float = -INF,
    upper: float = INF,
    ) -> State:
    """Filter target position with respect to the kinematic limits (maximum
    speed and maximum acceleration / deceleration). Online optimal trajectory.

    Args:
        targetPosition: Target position value.
        dt: Time interval.

    Kwargs:
        state: Initial / current state.
        targetVelocity: Target velocity value. Use with care! Steady sate with
            non-zero targetVelocity leads to oscillation.
        maxSpeed: Maximum speed value.
        maxAcc: Maximum acceleration (and deceleration) value.
        lower: Lower clipping value for target value.
        upper: Upper clipping value for target value.

    Returns:
        The next state.
    """
    bangProfiles = optimal_trajectory(
        clip(targetPosition, lower, upper),
        targetVelocity,
        state,
        maxSpeed,
        maxAcc,
    )

    # Effectively spline evaluation. Go through all segments and see where we
    # are at `dt`. Update state for intermediate steps.
    for duration, acc in bangProfiles:
        if dt <= duration:
            return step((state.position, state.velocity, acc), dt)

        state = step((state.position, state.velocity, acc), duration)
        dt -= duration

    return state._replace(acceleration=0.)


def kinematic_filter_vec(targets, dt, state=State(), **kwargs):
    traj = []
    for target in targets:
        state = kinematic_filter(target, dt, state=state, **kwargs)
        traj.append(state)

    return np.array(traj)
