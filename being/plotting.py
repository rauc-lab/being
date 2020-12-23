import numpy as np
import matplotlib.pyplot as plt

from kinematic.constants import ONE_D


DEFAULT_COLORS = [
    dct['color'] for dct in plt.rcParams['axes.prop_cycle']
]


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
