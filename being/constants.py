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

MONO: int = 1
"""Mono audio signal."""

STEREO: int = 2
"""Stereo audio signal."""

EOT = chr(4)
"""End of transmission character."""

BYTE: int = 8
"""One byte."""

KB: int = 1024 * BYTE
"""One kilo byte."""

MB: int = 1024 * KB
"""One mega byte."""
