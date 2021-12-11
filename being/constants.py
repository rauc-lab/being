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

EOT: str = chr(4)
"""End of transmission character."""

BYTE: int = 8
"""One byte."""

KB: int = 1024 * BYTE
"""One kilo byte."""

MB: int = 1024 * KB
"""One mega byte."""

UP: float = 1.
"""Up direction."""

FORWARD: float = 1.
"""Forward direction."""

DOWN: float = -1.
"""Down direction."""

BACKWARD: float = -1.
"""Backward direction."""

YOTTA = Y = 1e24
"""Yotta metric SI prefix"""

ZETTA = Z = 1e21
"""Zetta metric SI prefix"""

EXA = E = 1e18
"""Exa metric SI prefix"""

PETA = P = 1e15
"""Peta metric SI prefix"""

TERA = T = 1e12
"""Tera metric SI prefix"""

GIGA = G = 1e9
"""Giga metric SI prefix"""

MEGA = M = 1e6
"""Mega metric SI prefix"""

KILO = k = 1e3
"""Kilo metric SI prefix"""

HECTO = h = 1e2
"""Hecto metric SI prefix"""

DECA = da = 1e1
"""Deca metric SI prefix"""

ONE = 1e0
"""One metric SI prefix"""

DECI = d = 1e-1
"""Deci metric SI prefix"""

CENTI = c = 1e-2
"""Centi metric SI prefix"""

MILLI = m = 1e-3
"""Milli metric SI prefix"""

MICRO = μ = 1e-6
"""Micro metric SI prefix"""

NANO = n = 1e-9
"""Nano metric SI prefix"""

PICO = p = 1e-12
"""Pico metric SI prefix"""

FEMTO = f = 1e-15
"""Femto metric SI prefix"""

ATTO = a = 1e-18
"""Atto metric SI prefix"""

ZEPTO = z = 1e-21
"""Zepto metric SI prefix"""

YOCTO = y = 1e-24
"""Yocto metric SI prefix"""
