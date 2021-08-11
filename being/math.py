"""Mathematical helper functions."""
import math
from typing import Tuple
from being.constants import TAU

import numpy as np


def clip(number: float, lower: float, upper: float) -> float:
    """Clip `number` to the closed interval [`lower`, `upper`].

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
    """Signum function.

    Args:
        number: Input value.

    Returns:
        Sign part of the number.
    """
    return math.copysign(1., number)


def solve_quadratic_equation(a: float, b: float, c: float) -> Tuple[float, float]:
    """Both solutions of the quadratic equation a * x^2 + b * x + c = 0.

    x0, x1 = (-b +/- sqrt(b^2 - 4*a*c)) / (2 * a)

    Returns:
        tuple: Solutions.
    """
    discriminant = b**2 - 4 * a * c
    x0 = (-b + discriminant**.5) / (2 * a)
    x1 = (-b - discriminant**.5) / (2 * a)
    return x0, x1


def linear_mapping(xRange, yRange):
    """Get linear coefficients for y = a * x + b.

    Args:
        xRange (tuple): Input range (xmin, xmax).
        yRange (tuple): Output range (xmin, xmax).

    Returns:
        tuple: Linear coefficients a, b.
    """
    xmin, xmax = xRange
    ymin, ymax = yRange
    return np.linalg.solve([
        [xmin, 1.],
        [xmax, 1.],
    ], [ymin, ymax])


def angular_velocity_to_rpm(angVel: float) -> float:
    """Convert angular velocity to rotations per minute.

    Args:
        angVel: Angular velocity [rad / s]

    Returns:
        Velocity in [rpm]

    """
    return angVel * 60 / TAU


def rpm_to_angular_velocity(rpm: float) -> float:
    """Convert rotations per minute to angular velocity.

    Args:
        rpm: rotation per minute [rpm]

    Returns:
        Angular velocity [rad / s]

    """
    return TAU * rpm / 60
