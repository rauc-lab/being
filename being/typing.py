"""Some being typing.

Warning:
    Deprecated

Todo:
    There is a new Spline type in :mod:`being.spline`. Remove this module.
"""
from typing import Union
from scipy.interpolate import PPoly, BPoly


Spline = Union[PPoly, BPoly]
