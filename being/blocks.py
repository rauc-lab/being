"""Miscellaneous blocks."""
# TODO: Renaming this module? Almost name conflict with block.py?
import math
import sys
import time

from being.backends import AudioBackend
from being.block import Block
from being.clock import Clock
from being.configuration import CONFIG
from being.constants import TAU
from being.math import linear_mapping
from being.resources import register_resource
from being.sensors import Sensor


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


class DummySensor(Sensor):
    def __init__(self, interval=5.0):
        super().__init__()
        self.add_message_output()
        self.interval = interval
        self.nextUpd = -1

    def update(self):
        now = time.perf_counter()
        if now < self.nextUpd:
            return

        self.nextUpd = now + self.interval
        self.output.send('But hey')


def sine_pulse(phase: float) -> float:
    """Cosine pulse from [0., 1.]."""
    return .5 * (1 - math.cos(phase))


def ranged_sine_pulse(phase: float, lower: float = 0.0, upper: float = 1.0) -> float:
    """Shifted and scaled cosine pulse in interval [lower, upper]."""
    return (upper - lower) * sine_pulse(phase) + lower


def ranged_sine_pulse_integrated(phase: float, lower: float = 0.0, upper: float = 1.0) -> float:
    """Integrated shifted and scaled cosine pulse for derivative range in
    [lower, upper].
    """
    return .5 * (lower - upper) * math.sin(phase) + .5 * (lower + upper) * phase


class Pendulum(Block):
    def __init__(self, frequency=1., lower=0., upper=1.):
        super().__init__()
        self.add_value_output()
        self.frequency = frequency
        self.lower = lower
        self.upper = upper
        self.clock = Clock.single_instance_setdefault()

    def update(self):
        phase = TAU * self.frequency * self.clock.now()
        self.output.value = ranged_sine_pulse(phase, self.lower, self.upper)
