"""Spline related helper functions. Building splines, smoothing splines, Bézier
control points.

Definitions:
  - order = degree + 1

Resources:
    https://ocw.mit.edu/courses/electrical-engineering-and-computer-science/6-837-computer-graphics-fall-2012/lecture-notes/MIT6_837F12_Lec01.pdf
    http://www.idav.ucdavis.edu/education/CAGDNotes/Bernstein-Polynomials.pdf
    https://geom.ivd.kit.edu/downloads/pubs/pub-boehm-prautzsch_2002_preview.pdf
"""
import functools
import math
from typing import Sequence, List
from enum import IntEnum


import numpy as np
from numpy import ndarray
from scipy.interpolate import PPoly, BPoly, splrep, splprep

from being.constants import ONE_D, TWO_D
from being.kinematics import optimal_trajectory
from being.math import clip
from being.typing import Spline


class Degree(IntEnum):

    """Spline / polynomial degree. degree = order - 1."""

    CONSTANT = 0
    LINEAR = 1
    QUADRATIC = 2
    CUBIC = 3


def spline_order(spline: Spline) -> int:
    """Order of spline. order = degree + 1."""
    return spline.c.shape[0]


def spline_dimensions(spline: Spline) -> int:
    """Number of dimensions of spline."""
    if spline.c.ndim == 3:
        return spline.c.shape[2]

    return 1


def spline_shape(spline: Spline) -> tuple:
    """Spline shape."""
    if spline.c.ndim == 3:
        return spline.c.shape[2:]

    scalarShape = ()
    return scalarShape


def spline_duration(spline: Spline) -> float:
    """Spline duration in seconds."""
    knots = spline.x
    return knots[-1] - knots[0]


def copy_spline(spline: Spline) -> Spline:
    """Make a copy of the spline."""
    return type(spline).construct_fast(
        c=spline.c.copy(),
        x=spline.x.copy(),
        extrapolate=spline.extrapolate,
        axis=spline.axis,
    )


def shift_spline(spline: Spline, offset=0.) -> Spline:
    """Shift spline by some offset in time."""
    ret = copy_spline(spline)
    ret.x += offset
    return ret


def remove_duplicates(spline: Spline) -> Spline:
    """Remove duplicates knots from spline."""
    _, uniqueIdx = np.unique(spline.x, return_index=True)
    return type(spline).construct_fast(
        c=spline.c[:, uniqueIdx[:-1]],
        x=spline.x[uniqueIdx],
        extrapolate=spline.extrapolate,
        axis=spline.axis,
    )


def sample_spline(spline: Spline, t, loop: bool = False):
    """Sample spline. Clips time values for non extrapolating splines. Also
    supports looping.

    Args:
        spline: Some spline to sample (must be callable).
        t: Time value(s)
        loop: Loop spline motion.

    Returns:
        Spline value(s).
    """
    start = spline.x[0]  # No fancy indexing. Faster then `start, end = spline.x[[0, -1]]`
    end = spline.x[-1]
    if loop:
        return spline(np.clip(t % end, start, end))

    if spline.extrapolate:
        return spline(t)

    # Note: spline(end) with extrapolate = False -> nan
    #   -> Subtract epsilon for right border
    return spline(np.clip(t, start, end - 1e-15))


def spline_coefficients(spline: Spline, segment: int) -> ndarray:
    """Get spline coefficients for a given segment."""
    nSegments = spline.c.shape[1]
    if 0 <= segment < nSegments:
        return spline.c[:, segment].copy()

    raise ValueError(f'segment number {segment} not in [0, {nSegments})!')


def split_spline(spline: Spline) -> List[Spline]:
    """Split each dimension into its own spline."""
    t = type(spline)
    knots = spline.x
    coeffs = spline.c
    if coeffs.ndim == 2:
        # Promote scalar spline to one dimensional
        coeffs = coeffs[..., np.newaxis]
        return [
            t.construct_fast(coeffs, knots, spline.extrapolate, spline.axis)
        ]

    dims = spline_dimensions(spline)
    parts = np.split(coeffs, dims, axis=-1)
    return [
        t.construct_fast(c, knots, spline.extrapolate, spline.axis)
        for c in parts
    ]


"""PPoly exclusives"""


def build_ppoly(
        accelerations: Sequence,
        knots: Sequence,
        x0: float = 0.,
        v0: float = 0.,
        extrapolate: bool = False,
        axis: int = 0,
    ) -> PPoly:
    """Build quadratic position spline from acceleration segments. Also include
    initial velocity and position.

    Args:
        accelerations: Acceleration values.
        knots: Increasing time values.
        x0: Initial position.
        v0: Initial velocity.
        extrapolate (optional): Extrapolate spline. Default is False.
        axis (optional): Spline axis. Default is 0.

    Returns:
        Position spline.

    Example:
        >>> x0 = 1.234
        ... spline = build_ppoly([1, 0, -1], [0, 1, 2, 3], x0=x0)
        ... print(spline(0.) == x0)
        True
    """
    coeffs = np.atleast_2d(accelerations)
    velSpl = PPoly(coeffs, knots, extrapolate, axis).antiderivative(nu=1)
    velSpl.c[-1] += v0
    posSpl = velSpl.antiderivative(nu=1)
    posSpl.c[-1] += x0
    return posSpl


@functools.lru_cache(maxsize=128, typed=False)
def _factorial(x: int) -> int:
    """Cached recursive factorial function in case someone wants to call
    `power_basis` with a large order.
    """
    if x < 0:
        raise ValueError('_factorial() not defined for negative values')

    if x < 2:
        return 1

    return _factorial(x - 1) * x


for x in range(10):
    assert _factorial(x) == math.factorial(x)


def power_basis(order: int) -> ndarray:
    """Create power basis vector. Ordered so that it fits the spline
    coefficients matrix.

    Args:
        order: Order of the spline.

    Returns:
        Power basis coefficients.
    """
    return np.array([
        _factorial(x) for x in reversed(range(order))
    ])


def ppoly_coefficients_at(spline: PPoly, x: float) -> ndarray:
    """Get PPoly coefficients for a given `x` value."""
    order = spline.c.shape[0]
    vals = [spline(x, nu) for nu in range(order)]
    return vals[::-1] / power_basis(order)


def ppoly_insert(newX: float, spline: PPoly, extrapolate: bool = None) -> PPoly:
    """Insert a new knot / breakpoint somewhere in a spline segment."""
    if not isinstance(spline, PPoly):
        raise ValueError('Not a PPoly spline!')

    if extrapolate is None:
        extrapolate = spline.extrapolate

    if newX in spline.x:
        return spline

    # New coefficients to insert
    start = spline.x[0]
    end = spline.x[-1]
    inbetween = (start <= newX <= end)
    if inbetween or extrapolate:
        coeffs = ppoly_coefficients_at(spline, newX)
    else:
        order = spline.c.shape[0]
        coeffs = np.zeros(order)
        coeffs[-1] = spline(clip(newX, start, end))

    idx = np.searchsorted(spline.x, newX)
    nSegments = spline.c.shape[1]
    seg = min(idx, nSegments)
    return type(spline).construct_fast(
        np.insert(spline.c, seg, coeffs, axis=-1),
        np.insert(spline.x, idx, newX),
        spline.extrapolate,
        spline.axis,
    )


"""Smoothing splines"""


def smoothing_factor(smoothing: float, length: int) -> float:
    """Smoothing parameter s for splprep / splprep. Chosen in such a way that 1)
    the smoothing ~ mean square error of fitting the process and 2) it is length
    independent.

    Args:
        smoothing: Smoothing factor.
        length: Number of data points.

    Returns:
        splrep / splprep smoothing parameter s.
    """
    return smoothing * length


def smoothing_spline(
        x: Sequence,
        y: Sequence,
        degree: Degree = Degree.CUBIC,
        smoothing: float = 1e-3,
        periodic: bool = False,
        extrapolate: bool = False,
    ) -> PPoly:
    """Fit smoothing spline through uni- or multivariate data points.

    Args:
        x, y: The data points defining a curve y = f(x).
        degree: The degree of the spline fit. It is recommended to use cubic splines.
        smoothing: Tradeoff between closeness and smoothness of fit.
        extrapolate: If to extrapolate data.
        periodic: Periodic data. Will overwrite extrapolate = 'periodic'.

    Returns:
        Piecewise polynomial smoothing spline.

    Resources:
      - https://en.wikipedia.org/wiki/Smoothing_spline
      - https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.splrep.html
      - https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.splprep.html
    """
    ndim = np.ndim(y)
    if ndim > TWO_D:
        raise ValueError('Only uni- and multivariate data is supported!')

    s = smoothing_factor(smoothing, len(x))
    if periodic:
        extrapolate = 'periodic'

    # Todo: Should we directly go with BPoly instead of PPoly?
    if ndim == ONE_D:
        tck = splrep(x, y, k=degree, s=s, per=periodic)
        ppoly = PPoly.from_spline(tck, extrapolate)

    else:
        (t, cMatrix, k), _ = splprep(y.T, u=x, k=degree, s=s, per=periodic)

        # PPoly.from_spline does not support multivariate data.
        # Workaround: Construct multiple 1d splines, stack their coefficients
        # and create a new multivariate PPoly.
        splines = [PPoly.from_spline((t, cRow, k), extrapolate) for cRow in cMatrix]
        coeffs = np.stack([spline.c for spline in splines], axis=-1)
        ppoly = PPoly.construct_fast(coeffs, t, extrapolate)

    # Todo: Cutting off excess knots / duplicates in ppoly.x (ppoly.x[:degree]
    # and ppoly.x[-degree:])? Is this necessary?
    return ppoly


def fit_spline(trajectory, smoothing=1e-6) -> BPoly:
    """Fit a smoothing spline through a trajectory."""
    trajectory = np.asarray(trajectory)
    if trajectory.ndim != TWO_D:
        raise ValueError('trajectory has to be 2d!')

    t = trajectory[:, 0]
    x = trajectory[:, 1:]
    x = x.squeeze()
    ppoly = smoothing_spline(t, x, smoothing=smoothing, extrapolate=False)
    ppoly = remove_duplicates(ppoly)
    return BPoly.from_power_basis(ppoly)


def smoothing_spline_demo():
    """Demo of smoothing splines with multivariate and periodic data."""
    import matplotlib.pyplot as plt
    from being.constants import TAU

    np.random.seed(0)

    def add_noise(x, covariance=.01):
        """Add normal noise to data points."""
        stdDeviation = covariance ** .5
        return np.random.normal(loc=x, scale=stdDeviation)


    # 2d spline fitting
    t = np.linspace(0, TAU)
    noisy = add_noise([
        np.cos(t),
        np.sin(t),
    ]).T

    x, y = noisy.T
    plt.scatter(t, x)
    plt.scatter(t, y)

    spline = smoothing_spline(t, noisy, smoothing=.05)
    x, y = spline(t).T
    plt.plot(t, x)
    plt.plot(t, y)

    plt.title('Smoothing Spline Fitting')
    plt.show()

    # Periodic spline
    per = .5 * TAU
    t = np.linspace(0, per)
    noisy = add_noise(np.sin(t))
    plt.scatter(t, noisy)

    t2 = np.linspace(-per, 2*per, 200)
    for periodic in [False, True]:
        spline = smoothing_spline(t, noisy, smoothing=.01, periodic=periodic)
        plt.plot(t2, spline(t2 % per), label=f'Periodic {periodic}')

    plt.legend()
    plt.title('Periodic vs. Non-Periodic Spline Fitting')
    plt.show()


"""Optimal trajectory spline"""


def optimal_trajectory_spline(
        initial,
        target,
        maxSpeed: float = 1.,
        maxAcc: float = 1.,
        extrapolate: bool = False,
    ) -> PPoly:
    """Build spline following the optimal trajectory.

    Args:
        initial: Start state.
        target: Final end state.
        maxSpeed: Maximum speed.
        maxAcc: Maximum acceleration (and deceleration).
        extrapolate: Extrapolate splines over borders.

    Returns:
        Optimal trajectory spline.
    """
    profiles = optimal_trajectory(initial, target, maxSpeed=maxSpeed, maxAcc=maxAcc)
    durations, accelerations = zip(*profiles)
    knots = np.r_[0., np.cumsum(durations)]
    return build_ppoly(accelerations, knots, x0=initial.position, v0=initial.velocity, extrapolate=extrapolate)


if __name__ == '__main__':
    smoothing_spline_demo()
