"""Plotting util."""
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import PPoly

from being.block import Block
from being.clock import Clock

from being.constants import ONE_D
from being.resources import add_callback


DEFAULT_COLORS = [
    dct['color'] for dct in plt.rcParams['axes.prop_cycle']
]
"""Default matplotlib colors.

   :meta hide-value:
"""


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
        zorder = 0
        for row, color, label in zip(trajectory.T, DEFAULT_COLORS, labels):
            if labelit:
                kwargs['label'] = label

            ax.plot(t, row, *args, color=color, zorder=zorder, **kwargs)
            zorder -= 1

    if labelit:
        ax.legend()


def sample_trajectory(spline: PPoly, nSamples: int = 100, rett: bool = False):
    """Sample trajectory values from spline. Optionally also return sample
    times.

    Args:
        spline: Spline to sample.
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
        nSamples: Number of samples
        **kwargs -> plot_trajectory()
    """
    t, trajectory = sample_trajectory(spline, nSamples, rett=True)
    plot_trajectory(t, trajectory, **kwargs)


def plot_spline_2(spline, n=100, ax=None, start=None, end=None, **kwargs):
    if ax is None:
        ax = plt.gca()

    knots = spline.x
    if start is None:
        start = knots[0]

    if end is None:
        end = knots[-1]

    x = np.linspace(start, end, n)
    lines = ax.plot(x, spline(x), **kwargs)
    scatters = ax.plot(knots, spline(knots), 'o')
    for line, scatter in zip(lines, scatters):
        scatter.set_color(line._color)


class Plotter(Block):

    """Value plotter. Plot multiple signals after shutdown."""

    def __init__(self, nInputs=1):
        super().__init__()
        for _ in range(nInputs):
            self.add_value_input()

        self.timestamps = []
        self.data = []
        self.clock = Clock.single_instance_setdefault()
        add_callback(self.show_plot)

    def update(self):
        self.timestamps.append(self.clock.now())
        self.data.append([
            in_.value for in_ in self.inputs
        ])

    def _find_labels(self):
        """Check for named inputs as labels."""
        for input_ in self.inputs:
            for key, value in vars(self).items():
                if value is input_:
                    yield key
                    break
            else:
                yield

    def show_plot(self):
        data = np.array(self.data)
        labels = list(self._find_labels())
        for row, label in zip(data.T, labels):
            plt.plot(self.timestamps, row, label=label)

        plt.legend()
        plt.show()
