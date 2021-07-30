import os
from random import uniform, choices

import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import BPoly

from being.kinematics import kinematic_filter_vec, State
from being.serialization import dumps
from being.spline import smoothing_spline
from being.plotting import plot_spline
from being.spline import remove_duplicates


TARGET = 'content'
DT = .01
ROD_LENGTH = 0.04


RANDOM_WORDS = [
    'deep', 'pumped', 'purple', 'scary', 'unequaled', 'serious', 'uninterested',
    'peaceful', 'unknown', 'spurious', 'compact', 'finish', 'blue', 'highway',
    'movie', 'folklore', 'prove', 'uncertainty',
]


def save_spline(spline, name):
    fp = os.path.join(TARGET, name + '.json')
    print('Saving spline to', fp)
    with open(fp, 'w') as f:
        f.write(dumps(spline, indent=2))


def random_name():
    twoWords = choices(RANDOM_WORDS, k=2)
    return '_'.join(twoWords)


def normalize(arr):
    lower = arr.min()
    upper = arr.max()
    width = upper - lower
    assert width != 0
    return (arr - lower) / width


os.makedirs(TARGET, exist_ok=True)


for _ in range(10):
    duration = uniform(5, 20)
    t = np.arange(0, duration, DT)
    n = t.shape[0]
    r = np.random.random(n)
    data = kinematic_filter_vec(r, dt=DT, initial=State(r[0]))
    y, _, _ = data.T

    ppoly = smoothing_spline(t, y, smoothing=1e-3)
    ppoly = remove_duplicates(ppoly)
    bpoly = BPoly.from_power_basis(ppoly)
    bpoly.c *= (ROD_LENGTH / bpoly.c.max())
    name = random_name()
    save_spline(bpoly, name)
