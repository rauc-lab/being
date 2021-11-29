"""Curve / motion player block.

Todo:
  - Changing playback speed on the fly. As separate input? Need some internal
    clock. Or a phasor?
  - Slow and fast crossover between splines?
"""
import json
from typing import NamedTuple, Optional

import numpy as np
from scipy.interpolate import BPoly

from being.block import Block, output_neighbors
from being.clock import Clock
from being.content import Content
from being.curve import Curve
from being.logging import get_logger
from being.motors.blocks import MotorBlock
from being.utils import filter_by_type


"""
# Todo: Urgency. Do we need that? Should we use it for slow and fast crossovers?

from enum import Enum, auto

class Urgency(Enum):
    NOW = auto()
    NEXT = auto()
    ENQUEUE = auto()
"""


def constant_spline(position=0.0, duration=1.0) -> BPoly:
    """Create a constant spline for a given position which extrapolates
    indefinitely.

    Args:
        position: Target position value.
        duration: Todo.

    Returns:
        Constant spline.
    """
    return BPoly(c=[[position]], x=[0., duration], extrapolate=True)


def constant_curve(positions=0.0, duration=1.0) -> Curve:
    """Create a curve with keeping constant values."""
    return Curve([
        constant_spline(pos, duration)
        for pos in np.atleast_1d(positions)
    ])


class MotionCommand(NamedTuple):

    """Message to trigger curve playback."""

    name: str
    loop: bool = False


class MotionPlayer(Block):

    """Spline sampler block. Feeds on motion commands and outputs position
    values for a given spline. Supports different playback speeds and looping
    option.

    Attributes:
        spline (Spline): Currently playing spline.
        startTime (float): Start time of current spline.
        playbackSpeed (float): Playback speed for current spline.
        looping (bool): Looping motion.
    """

    def __init__(self, ndim=1, clock=None, content=None, **kwargs):
        if clock is None:
            clock = Clock.single_instance_setdefault()

        if content is None:
            content = Content.single_instance_setdefault()

        super().__init__(**kwargs)
        self.add_message_input('mcIn')
        self.positionOutputs = []
        for _ in range(ndim):
            self.add_position_output()

        self.clock = clock
        self.content = content
        self.curve = None
        self.startTime = 0
        self.looping = False
        self.logger = get_logger(str(self))

    @property
    def playing(self) -> bool:
        """Playback in progress."""
        return self.curve is not None

    @property
    def ndim(self) -> int:
        """Number of position outputs."""
        return len(self.positionOutputs)

    def add_position_output(self):
        """Add an additional position out to the motion player."""
        newOutput = self.add_value_output()
        self.positionOutputs.append(newOutput)

    def stop(self):
        """Stop spline playback."""
        self.curve = None
        self.startTime = 0
        self.looping = False

    def play_curve(self, curve: Curve, loop: bool = False, offset: float = 0.) -> float:
        """Play a curve directly.

        Args:
            curve: Curve to play.
            loop: Loop playback.
            offset: Start time offset.

        Returns:
            Scheduled start time.
        """
        self.logger.info('Playing curve')
        self.curve = curve
        self.startTime = self.clock.now() - offset
        self.looping = loop
        return self.startTime

    def process_mc(self, mc: MotionCommand) -> Optional[float]:
        """Process new motion command and schedule next curve to play.

        Args:
            mc: Motion command.

        Returns:
            Scheduled start time.
        """
        try:
            self.logger.info('Playing motion %r', mc.name)
            curve = self.content.load_curve(mc.name)
        except FileNotFoundError:
            self.logger.error('Motion %r does not exist!', mc.name)
            currentVals = [out.value for out in self.positionOutputs]
            curve = constant_curve(currentVals, duration=5.)
        except json.JSONDecodeError:
            self.logger.error('Could not decode %r!', mc.name)
            currentVals = [out.value for out in self.positionOutputs]
            curve = constant_curve(currentVals, duration=5.)

        if curve.n_channels != self.ndim:
            msg = (
                f'Motion {mc.name} is not compatible with connected motors'
                f'({curve.n_channels} != {self.ndim})!'
            )
            self.logger.error(msg)

        return self.play_curve(curve, mc.loop)

    def update(self):
        for mc in self.input.receive():
            self.process_mc(mc)

        if self.playing:
            now = self.clock.now()
            t = now - self.startTime
            if not self.looping and t >= self.curve.end:
                return self.stop()

            samples = self.curve.sample(t, loop=self.looping)
            for val, out in zip(samples, self.positionOutputs):
                out.value = val

    def neighboring_motors(self):
        for out in self.positionOutputs:
            input_ = next(iter(out.connectedInputs))
            if input_.owner:
                yield input_.owner

    def to_dict(self):
        dct = super().to_dict()
        dct['ndim'] = self.ndim
        neighbors = output_neighbors(self)
        dct['motors'] = list(filter_by_type(neighbors, MotorBlock))
        return dct

    def __str__(self):
        return type(self).__name__
