"""Curve set. Spline-like which can contain multiple splines."""
from typing import List

import numpy as np

from being.constants import INF
from being.math import clip
from being.spline import spline_dimensions
from being.typing import Spline


class Curve:

    """Curve container aka. curve set. Contains multiple curves as splines."""

    def __init__(self, splines: List[Spline]):
        """
        Args:
            splines: List of splines.
        """
        self.splines: List[Spline] = splines

    @property
    def start(self) -> float:
        """Start time."""
        return min(s.x[0] for s in self.splines)

    @property
    def end(self) -> float:
        """End time."""
        return max(s.x[-1] for s in self.splines)

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
        """Number of channels. Sum of all spline dimensions.

        Tip:
            This is not the same as number of splines :meth:`Curve.n_splines`.
        """
        return sum(
            spline_dimensions(s)
            for s in self.splines
        )

    def sample(self, timestamp: float, loop: bool = False) -> List[float]:
        """Sample curve. Returns :attr:`Curve.n_channels` many samples.
        Subsequent child splines get clamped.

        Args:
            timestamp: Time value to sample for.
            loop (optional): Loop curve playback. False by default.

        Returns:
            Curve samples.
        """
        if loop:
            period = self.duration
        else:
            period = INF

        samples = []
        for spline in self.splines:
            # Subtracting a small epsilon from upper clipping border. Non
            # extrapolating splines *can* return NaN when on the edge
            # (spline(spline.x[-1])). But not always :(
            samples.extend(spline(clip(timestamp % period, spline.x[0], spline.x[-1] - 1e-15)))

        #return np.array(samples)
        return samples

    def __call__(self, x, nu=0, extrapolate=None) -> np.ndarray:
        return np.concatenate([
            s(x, nu, extrapolate)
            for s in self.splines
        ], axis=-1)

    def __str__(self):
        return f'{type(self).__name__}({self.n_channels} curves)'
