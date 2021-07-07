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
