"""Math constants and other literals."""
import math


TAU: float = 2 * math.pi
"""Radial circle constant."""

PI: float = math.pi
"""Diameter circle constant."""

INF: float = float('inf')
"""To infinity and beyond."""

ONE_D: int = 1
"""One dimensional."""

TWO_D: int = 2
"""Two dimensional."""

EOT = chr(4)
"""End of transmission character."""

BYTE: int = 8
"""One byte."""

KB: int = 1024 * BYTE
"""One kilo byte."""

MB: int = 1024 * KB
"""One mega byte."""

UP = 1.
"""Up direction."""

FORWARD = 1.
"""Forward direction."""

DOWN = -1.
"""Down direction."""

BACKWARD = -1.
"""Backward direction."""


YOTTA = Y = 1e24
ZETTA = Z = 1e21
EXA = E = 1e18
PETA = P = 1e15
TERA = T = 1e12
GIGA = G = 1e9
MEGA = M = 1e6
KILO = k = 1e3
HECTO = h = 1e2
DECA = da = 1e1
ONE = 1e0
DECI = d = 1e-1
CENTI = c = 1e-2
MILLI = m = 1e-3
MICRO = μ = 1e-6
NANO = n = 1e-9
PICO = p = 1e-12
FEMTO = f = 1e-15
ATTO = a = 1e-18
ZEPTO = z = 1e-21
YOCTO = y = 1e-24
"""SI metric prefix"""
