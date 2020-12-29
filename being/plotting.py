"""Plotting util."""
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import PPoly

from being.constants import ONE_D


DEFAULT_COLORS = [
    dct['color'] for dct in plt.rcParams['axes.prop_cycle']
]
"""Default matplotlib colors."""


def plot_trajectory(t, trajectory, *args, ax=None, labelit=False, **kwargs):
    """Plot trajectory."""
    trajectory = np.asarray(trajectory)
    if ax is None:
        ax = plt.gca()

    labels = ['Position', 'Velocity', 'Acceleration']
    if trajectory.ndim == ONE_D:
        if labelit:
            kwargs['label'] = labels[0]

        ax.plot(t, trajectory, *args, color=DEFAULT_COLORS[0], **kwargs)
    else:
        for row, color, label in zip(trajectory.T, DEFAULT_COLORS, labels):
            if labelit:
                kwargs['label'] = label

            ax.plot(t, row, *args, color=color, **kwargs)

    if labelit:
        ax.legend()


def sample_trajectory(spline: PPoly, nSamples: int = 100, rett: bool = False):
    """Sample trajectory values from spline. Optionally also return sample
    times.

    Args:
        spline: Spline to sample.

    Kwargs:
        nSamples: Number of samples
        rett: If to return sample times as well.

    Returns:
        Trajectory.
    """
    start, end = spline.x[[0, -1]]
    t = np.linspace(start, end, nSamples)
    order = spline.c.shape[0]
    trajectory = np.array([
        spline(t, nu) for nu in range(order)
    ])
    if rett:
        return t, trajectory.T

    return trajectory.T


def plot_spline(spline: PPoly, nSamples: int = 100, **kwargs):
    """Plot trajectory of spline.

    Args:
        spline: Spline to plot.

    Kwargs:
        nSamples: Number of samples
        **kwargs -> plot_trajectory()
    """
    t, trajectory = sample_trajectory(spline, nSamples, rett=True)
    plot_trajectory(t, trajectory, **kwargs)