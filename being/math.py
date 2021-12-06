"""Mathematical helper functions."""
import math
from typing import Tuple, NamedTuple

from being.constants import TAU

import numpy as np
from numpy import ndarray
import scipy.optimize


def clip(number: float, lower: float, upper: float) -> float:
    r"""Clip `number` to the closed interval [`lower`, `upper`].

    .. math::
        f_\mathrm{clip}(x; a, b) = \begin{cases}
            a & x < a \\
            x & a \leq x \leq b \\
            b & b < x \\
        \end{cases}

    Args:
        number: Input value.
        lower: Lower bound.
        upper: Upper bound.

    Returns:
        Clipped value.
    """
    if lower > upper:
        lower, upper = upper, lower

    return max(lower, min(number, upper))


def sign(number: float) -> float:
    """`Signum function <https://en.wikipedia.org/wiki/Sign_function>`_

    Args:
        number: Input value.

    Returns:
        Sign part of the number.

    Example:
        >>> sign(-12.34)
        -1.0
    """
    return math.copysign(1., number)


def solve_quadratic_equation(a: float, b: float, c: float) -> Tuple[float, float]:
    """Both solutions of the quadratic equation

    .. math::
        x_{1,2} = \\frac{-b \pm \sqrt{b^2 - 4ac}}{2a}

    Returns:
        tuple: Solutions.
    """
    discriminant = b**2 - 4 * a * c
    x0 = (-b + discriminant**.5) / (2 * a)
    x1 = (-b - discriminant**.5) / (2 * a)
    return x0, x1


def linear_mapping(xRange: Tuple[float, float], yRange: Tuple[float, float]) -> ndarray:
    """Get linear coefficients for

    .. math::
        y = a \cdot x + b.

    Args:
        xRange: Input range (xmin, xmax).
        yRange: Output range (xmin, xmax).

    Returns:
        Linear coefficients [a, b].
    """
    xmin, xmax = xRange
    ymin, ymax = yRange
    return np.linalg.solve([
        [xmin, 1.],
        [xmax, 1.],
    ], [ymin, ymax])


class ArchimedeanSpiral(NamedTuple):

    """`Archimedean spiral <https://en.wikipedia.org/wiki/Archimedean_spiral>`_
    defined by

    .. math::
        r(\phi) = a + b\phi
    """

    a: float
    """Centerpoint offset from origin."""

    b: float = 0.  # Trivial case circle
    """Distance between loops. Default is zero (trivial case spiral as
    circle).
    """

    def radius(self, angle: float) -> float:
        """Calculate radius of spiral for a given angle."""
        return self.a + self.b * angle

    @staticmethod
    def arc_length_helper(anlge: float, b: float) -> float:
        """Helper function for arc length calculations."""
        return b / 2 * (
            anlge * math.sqrt(1 + anlge ** 2)
            + math.log(anlge + math.sqrt(1 + anlge ** 2))
        )

    def _arc_length(self, angle: float) -> float:
        return self.arc_length_helper(angle, self.b) + self.a * angle

    def arc_length(self, endAngle: float, startAngle: float = 0) -> float:
        """Arc length of spiral from a `startAngle` to an `endAngle`."""
        return self._arc_length(endAngle) - self._arc_length(startAngle)

    @classmethod
    def fit(cls, diameter, outerDiameter, arcLength) -> tuple:
        """Fit :class:`ArchimedeanSpiral` to a given `diameter`, `outerDiameter`
        and `arcLength`.

        Args:
            diameter: Inner diameter of spiral.
            outerDiameter: Outer diameter of spiral. If equal to diameter -> Circle.
            arcLength: Measured arc length.

        Returns:
            Fitted spiral and estimated maximum angle.
        """
        if outerDiameter < diameter:
            raise ValueError('outerDiameter >= diameter!')

        a = .5 * diameter
        phi0 = arcLength / a  # Naive phi if spiral is a circle
        if diameter == outerDiameter:
            # Trivial circle case
            return ArchimedeanSpiral(a, b=0.0), phi0

        def func(x):
            b, phi = x
            return [
                a + b * phi - .5 * outerDiameter,
                cls.arc_length_helper(phi, b) + a * phi - arcLength,
            ]

        x0 = [0.0, phi0]
        bEst, phiEst = scipy.optimize.fsolve(func, x0)
        return cls(a, b=bEst), phiEst
