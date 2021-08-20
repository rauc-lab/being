"""Miscellaneous blocks."""
# TODO: Renaming this module? Almost name conflict with block.py?
import math
import sys

from being.backends import AudioBackend
from being.block import Block
from being.config import CONFIG
from being.constants import TAU
from being.math import linear_mapping
from being.resources import register_resource


INTERVAL = CONFIG['General']['INTERVAL']


class Sine(Block):

    """Sine generator. Outputs sine wave for a given frequency."""

    def __init__(self, frequency: float = 1., startPhase: float = 0., **kwargs):
        """Kwargs:
            frequency: Initial frequency value.
            startPhase: Inital phase.
        """
        super().__init__(**kwargs)
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


class Sawtooth(Block):

    """Sawtooth generator. Outputs [0, TAU] for a given frequency."""

    def __init__(self, frequency=1., interval=INTERVAL, **kwargs):
        super().__init__(**kwargs)
        self.add_value_input('frequency')
        self.add_value_output()

        self.frequency.value = frequency
        self.interval = interval

        self.phase = 0.

    def update(self):
        self.output.value = self.phase
        self.phase += self.interval * TAU * self.frequency.value
        # self.phase %= TAU

    def __str__(self):
        return '%s()' % type(self).__name__


class Trafo(Block):

    """Transforms input signal (by some fixed scale and offset)."""

    def __init__(self, scale: float = 1., offset: float = 0., **kwargs):
        """Kwargs:
            scale: Scaling factor.
            offset: Offset factor.
        """
        super().__init__(**kwargs)
        self.scale = scale
        self.offset = offset
        self.add_value_input()
        self.add_value_output()

    @classmethod
    def from_ranges(cls, inRange=(0., 1.), outRange=(0., 1.)):
        scale, offset = linear_mapping(inRange, outRange)
        return cls(scale, offset)

    def update(self):
        self.output.value = self.scale * self.input.value + self.offset

    def __str__(self):
        return f'{type(self).__name__}(scale={self.scale:.3f}, offset={self.offset:.3f})'


class Mic(Block):

    # TODO: Make me!

    def __init__(self, audioBackend=None, **kwargs):
        if audioBackend is None:
            audioBackend = AudioBackend.single_instance_setdefault()
            register_resource(audioBackend, duplicates=False)

        self.audioBackend = audioBackend


class Printer(Block):

    """Print input values to stdout."""

    def __init__(self, prefix: str = '', carriageReturn: bool = False, **kwargs):
        """Kwargs:
            prefix: Prefix string to prepend.
        """
        super().__init__(**kwargs)
        self.prefix = prefix
        self.carriageReturn = carriageReturn
        self.add_value_input()

    def update(self):
        if self.carriageReturn:
            print('\r\033c', self.prefix, self.input.value, end='')
            sys.stdout.flush()
        else:
            print(self.prefix, self.input.value)
