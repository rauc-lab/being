"""Miscellaneous blocks."""
# TODO: Renaming this module? Almost name conflict with block.py?
import math
import collections

import matplotlib.pyplot as plt
import numpy as np

from being.backends import AudioBackend
from being.block import Block
from being.clock import Clock
from being.config import INTERVAL
from being.constants import TAU
from being.resources import register_resource, add_callback


class Sine(Block):

    """Sine generator. Outputs sine wave for a given frequency."""

    def __init__(self, frequency: float = 1., startPhase: float = 0.):
        """Kwargs:
            frequency: Initial frequency value.
            startPhase: Inital phase.
        """
        super().__init__()
        self.phase = startPhase
        self.add_value_input('frequency')
        self.add_value_output()
        self.frequency.value = frequency

    def update(self):
        self.output.value = math.sin(self.phase)
        self.phase += TAU * self.frequency.value * INTERVAL
        self.phase %= TAU

    def __str__(self):
        return '%s()' % type(self).__name__


class Trafo(Block):

    """Transforms input signal (by some fixed scale and offset)."""

    def __init__(self, scale: float = 1., offset: float = 0.):
        """Kwargs:
            scale: Scaling factor.
            offset: Offset factor.
        """
        super().__init__()
        self.scale = scale
        self.offset = offset
        self.add_value_input()
        self.add_value_output()

    @classmethod
    def from_ranges(cls, inRange=(0., 1.), outRange=(0., 1.)):
        # TODO: Make me! Calculate scale, offset from (xMin, xMax) and (yMin,
        # yMax).
        pass

    def update(self):
        self.output.value = self.scale * self.input.value + self.offset

    def __str__(self):
        return f'{type(self).__name__}(scale={self.scale:.3f}, offset={self.offset:.3f})'


class Mic(Block):

    # TODO: Make me!

    def __init__(self, audioBackend=None):
        if not audioBackend:
            audioBackend = AudioBackend.single_instance_setdefault()
            register_resource(audioBackend, duplicates=False)

        self.audioBackend = audioBackend


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
