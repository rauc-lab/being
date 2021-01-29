"""Spline related helper functions. Building splines, smoothing splines, Bézier
control points.

Definitions:
  - order = degree + 1

Resources:
    https://ocw.mit.edu/courses/electrical-engineering-and-computer-science/6-837-computer-graphics-fall-2012/lecture-notes/MIT6_837F12_Lec01.pdf
    http://www.idav.ucdavis.edu/education/CAGDNotes/Bernstein-Polynomials.pdf
    https://geom.ivd.kit.edu/downloads/pubs/pub-boehm-prautzsch_2002_preview.pdf
"""
from typing import Sequence
from enum import IntEnum

import numpy as np
from numpy import ndarray
from scipy.interpolate import PPoly, BPoly, splrep, splprep

from being.constants import ONE_D, TWO_D
from being.kinematics import optimal_trajectory
from being.typing import Spline


Degree = IntEnum('Degree', 'CONSTANT LINEAR QUADRATIC CUBIC')


def build_spline(accelerations: Sequence, knots: Sequence, x0: float = 0.,
        v0: float = 0., extrapolate: bool = False, axis: int = 0) -> PPoly:
    """Build quadratic position spline from acceleration segments. Also include
    initial velocity and position.

    Args:
        accelerations: Acceleration values.
        knots: Increasing time values.

    Kwargs:
        x0: Initial position.
        v0: Initial velocity.
        extrapolate: TODO.
        axis: TODO

    Returns:
        Position spline.

    Usage:
        >>> x0 = 1.234
        ... spline = build_spline([1, 0, -1], [0, 1, 2, 3], x0=x0)
        ... print(spline(0.) == x0)
        True
    """
    coefficients = np.atleast_2d(accelerations)
    velSpl = PPoly(coefficients, knots, extrapolate, axis).antiderivative(nu=1)
    velSpl.c[-1] += v0
    posSpl = velSpl.antiderivative(nu=1)
    posSpl.c[-1] += x0
    return posSpl


def spline_order(spline: Spline) -> int:
    """Order of spline. order = degree + 1."""
    return spline.c.shape[0]


def spline_duration(spline: Spline) -> float:
    """Spline duration in seconds."""
    knots = spline.x
    return knots[-1] - knots[0]


def shitf_spline(spline: Spline, offset=0.) -> PPoly:
    """Shift spline by some offset in time."""
    return type(spline).construct_fast(
        c=spline.c,
        x=spline.x + offset,
        extrapolate=spline.extrapolate,
        axis=spline.axis,
    )


def remove_duplicates(spline: Spline) -> Spline:
    """Remove duplicates knots from spline."""
    _, idx = np.unique(spline.x, return_index=True)
    return type(spline).construct_fast(
        c=spline.c[:, idx[:-1]],
        x=spline.x[idx],
        extrapolate=spline.extrapolate,
        axis=spline.axis,
    )


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


def smoothing_spline(x: Sequence, y: Sequence, degree: Degree = Degree.CUBIC,
        smoothing: float = 1e-3, periodic: bool = False,
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

    # TODO: Should we directly go with BPoly instead of PPoly?
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
        ppoly = PPoly.construct_fast(coeffs, t)

    # TODO: Cutting off excess knots / duplicates in ppoly.x (ppoly.x[:degree]
    # and ppoly.x[-degree:])? Is this necessary?
    return ppoly


def optimal_trajectory_spline(xEnd: float, vEnd: float = 0., x0: float = 0.,
        v0: float = 0., maxSpeed: float = 1., maxAcc: float = 1.) -> PPoly:
    """Build spline following the optimal trajectory.

    Kwargs:
        xEnd: Target position.
        vEnd: Target velocity.
        x0: Initial position.
        v0: Initial velocity.
        maxSpeed: Maximum speed value.
        maxAcc: Maximum acceleration value.

    Returns:
        Optimal trajectory spline.
    """
    profiles = optimal_trajectory(xEnd, vEnd, state=(x0, v0, 0.), maxSpeed=maxSpeed, maxAcc=maxAcc)
    durations, accelerations = zip(*profiles)
    knots = np.r_[0., np.cumsum(durations)]
    return build_spline(accelerations, knots, x0=x0, v0=v0)


def bezier_control_points(spline: Spline) -> ndarray:
    """Bézier control points for a given spline."""
    if isinstance(spline, PPoly):
        spline = BPoly.from_power_basis(spline)

    spline = remove_duplicates(spline)
    order, nSegments = spline.c.shape[:2]
    cps = np.zeros((nSegments, order, 2))
    for seg in range(nSegments):
        x0 = spline.x[seg]
        x1 = spline.x[seg + 1]
        cps[seg, :, 0] = np.linspace(x0, x1, num=order)
        cps[seg, :, 1] = spline.c[:, seg]

    return cps


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


if __name__ == '__main__':
    smoothing_spline_demo()
