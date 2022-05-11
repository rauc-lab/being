"""Collection of miscellaneous blocks."""
import collections
import math
import sys
from typing import ForwardRef, Sequence

from being.backends import AudioBackend
from being.block import Block
from being.clock import Clock
from being.configuration import CONFIG
from being.constants import TAU
from being.math import linear_mapping
from being.resources import register_resource
from being.sensors import Sensor, SensorEvent
from being.serialization import dumps
from being.logging import get_logger
from being.clock import Clock

# Look before you leap
INTERVAL = CONFIG['General']['INTERVAL']

class Sine(Block):

    """Sine generator. Outputs sine wave for a given frequency."""

    def __init__(self, frequency: float = 1., startPhase: float = 0., **kwargs):
        """
        Args:
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


Trafo = ForwardRef('Trafo')


class Trafo(Block):

    """Transforms input signal (by some fixed scale and offset):

    .. math::
        y = a \cdot x + b.
    """

    def __init__(self, scale: float = 1., offset: float = 0., **kwargs):
        """
        Args:
            scale: Scaling factor.
            offset: Offset factor.
            **kwargs: Arbitrary block keyword arguments.
        """
        super().__init__(**kwargs)
        self.scale = scale
        self.offset = offset
        self.add_value_input()
        self.add_value_output()

    @classmethod
    def from_ranges(cls, inRange: Sequence = (0., 1.), outRange: Sequence = (0., 1.)) -> Trafo:
        """Construct :class:Trafo. instance for a given input and output range.

        Args:
            inRange: Lower and upper value of input range.
            outRange: Lower and upper value of output range.

        Returns:
            Trafo instance.

        Example:
            >>> # This trafo block will map input values from [1, 2] -> [30, 40]
            >>> trafo = Trafo.from_ranges([1, 2], [30, 40])
        """
        scale, offset = linear_mapping(inRange, outRange)
        return cls(scale, offset)

    def update(self):
        self.output.value = self.scale * self.input.value + self.offset

    def __str__(self):
        return f'{type(self).__name__}(scale={self.scale:.3f}, offset={self.offset:.3f})'


class Mic(Block):

    """Microphone block.

    Warning:
        Make me!
    """

    def __init__(self, audioBackend=None, **kwargs):
        """Intentionally left blank."""
        if audioBackend is None:
            audioBackend = AudioBackend.single_instance_setdefault()
            register_resource(audioBackend, duplicates=False)

        self.audioBackend = audioBackend


class Printer(Block):

    """Print input values to stdout."""

    def __init__(self, prefix: str = '', carriageReturn: bool = False, **kwargs):
        """
        Args:
            prefix (optional): Prefix string to prepend.
            carriageReturn (optional). Prepend carriage return character to each output.
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

    """Outputs scaled / shifted sine pulses. Can be used to sway back and forth
    between two extremes.
    """

    def __init__(self, frequency: float = 1., lower: float = 0., upper: float = 1., **kwargs):
        """
        Args:
            frequency (optional): Frequency of output signal.
            lower (optional): Lower output value.
            upper (optional): Upper output value.
            **kwargs: Arbitrary block keyword arguments.
        """
        super().__init__(**kwargs)
        self.add_value_output()
        self.frequency = frequency
        self.lower = lower
        self.upper = upper
        self.clock = Clock.single_instance_setdefault()

    def update(self):
        phase = TAU * self.frequency * self.clock.now()
        self.output.value = ranged_sine_pulse(phase, self.lower, self.upper)


class MessagePipe(Block):

    """Pipes an arbitrary number of message inputs to a single output."""

    def __init__(self, ndim: int = 2, **kwargs):
        """
        Args:
            ndim (optional): Number of message inputs.
        """
        super().__init__(**kwargs)
        self.add_message_output()

        for _ in range(ndim):
            self.add_message_input()

    def update(self):
        for input in self.inputs:
            evts = list(input.receive())
            if evts:
                self.output.send(evts)


class SensorIntegrator(Block):

    """Integrator for sensor message inputs. Only outputs collected messages if
    the total number within the integration time is higher than the threshold.
    Usefull for suppressing events in busy environments."""

    def __init__(self, threshold: int, integrationTime: float = 5.0, **kwargs):
        """
        Args:
            integrationTime (optional): Window time in seconds.
            threshold: Required number of events during window time to trigger output

        """
        super().__init__(**kwargs)
        self.add_message_output()
        self.add_message_input()
        self.collected_events = []
        self.integrationTime = integrationTime
        self.threshold = threshold
        self.logger = get_logger("SensorIntegratorBlock")
        self.clock = Clock.single_instance_setdefault()

    def update(self):
        toc = self.clock.now()
        for events in list(self.input.receive()):
            if events:
                for evt in events:
                    self.collected_events.append(evt)

        self.collected_events.sort(key=lambda x: x.timestamp)

        start = toc - self.integrationTime
        for evt in self.collected_events:
            if evt.timestamp < start:
                self.collected_events.remove(evt)

        if len(self.collected_events) >= self.threshold:
            self.logger.info("Threshold passed, forward collected events to output")
            for evt in self.collected_events:
                self.logger.debug(f'Send collected event: {evt}')
                self.output.send(evt)

            self.collected_events = []
