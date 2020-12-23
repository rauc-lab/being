import math


def clip(value, lower, upper):
    """Clip `value` to the closed interval [`lower`, `upper`].

    Returns:
        float: Clipped value.

    Supplementary Information:
        https://www.youtube.com/watch?v=2ZUX3j6WLiQ&list=PLBEA362DAD76373B7
    """
    if lower > upper:
        lower, upper = upper, lower

    return max(lower, min(value, upper))


def sign(x):
    """Signum function.

    Args:
        x (float): Number.

    Returns:
        float: Sign part of the number.
    """
    return math.copysign(1., x)


def solve_quadratic_equation(a, b, c):
    """Both solutions of the quadratic equation a * x^2 + b * x + c = 0.

    x0, x1 = (-b +/- sqrt(b^2 - 4*a*c)) / (2 * a)

    Returns:
        tuple: Solutions.
    """
    discriminant = b**2 - 4*a*c
    x0 = (-b + discriminant**.5) / (2 * a)
    x1 = (-b - discriminant**.5) / (2 * a)
    return x0, x1

