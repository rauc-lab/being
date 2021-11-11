"""Curve set.

Curve is a spline-like which can contain multiple curves / splines.
"""
import collections
import warnings

import numpy as np

from being.spline import spline_dimensions


class Curve:

    """Curve container aka. curve set. Contains multiple curves as splines."""

    def __init__(self, splines):
        self.splines = splines

    @property
    def start(self) -> float:
        """Start time."""
        return min(s.x[0] for s in self.splines)

    @property
    def end(self) -> float:
        """End time."""
        return max(s.x[-1] for s in self.splines)

    @property
    def x(self):
        """Placeholder knot vector, similar to _PPolyBase."""
        return np.unique([s.x for s in self.splines])

    @property
    def duration(self) -> float:
        """Maximum duration of motion."""
        #return max((spline.x[-1] for spline in self.splines), default=0.0)
        return self.end

    @property
    def n_splines(self) -> int:
        """Number of splines."""
        return len(self.splines)

    @property
    def n_channels(self) -> int:
        """Number of channels. Sum of all spline dimensions. Not the same as
        number of splines.
        """
        return sum(
            spline_dimensions(s)
            for s in self.splines
        )

    def __call__(self, t, nu=0):
        return np.concatenate([s(t, nu) for s in self.splines])

    def __str__(self):
        return f'{type(self).__name__}({self.n_channels} curves)'
