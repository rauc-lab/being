"""Spline motion player block.


TODO:
  - Changing playback speed on the fly. As separate input? Need some internal
    clock. Or a phasor?
  - Slow and fast crossover between splines?
"""
import json
from typing import NamedTuple, Optional

from scipy.interpolate import BPoly

from being.behavior_tree import SUCCESS
from being.block import Block
from being.clock import Clock
from being.content import Content
from being.logging import get_logger
from being.spline import Spline, sample_spline, spline_shape


"""
# TODO: Urgency. Do we need that? Should we use it for slow and fast crossovers?

from enum import Enum, auto

class Urgency(Enum):
    NOW = auto()
    NEXT = auto()
    ENQUEUE = auto()
"""


def constant_spline(position=0, duration=1.) -> BPoly:
    """Create a constant spline for a given position which extrapolates
    indefinitely.

    Kwargs:
        position: Target position value.
        duration: TODO.

    Returns:
        Constant spline.
    """
    return BPoly(c=[[position]], x=[0., duration], extrapolate=True)


class MotionCommand(NamedTuple):

    """Message to trigger spline playback."""

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

    def __init__(self, ndim=1, clock=None, content=None):
        if clock is None:
            clock = Clock.single_instance_setdefault()

        if content is None:
            content = Content.single_instance_setdefault()

        super().__init__()
        self.add_message_input('mcIn')
        #self.add_message_output('feedbackOut')
        self.positionOutputs = []
        for _ in range(ndim):
            self.add_position_output()

        self.clock = clock
        self.content = content
        self.spline = None
        self.startTime = 0
        self.looping = False
        self.logger = get_logger(str(self))

    @property
    def playing(self) -> bool:
        """Spline playback in progress."""
        return self.spline is not None

    @property
    def ndim(self) -> int:
        """Number of output dimensions."""
        return len(self.positionOutputs)

    def add_position_output(self):
        """Add an additional position out to the motion player."""
        self.add_value_output()
        latestOut = self.outputs[-1]
        self.positionOutputs.append(latestOut)

    def stop(self):
        """Stop spline playback."""
        self.spline = None
        self.startTime = 0
        self.looping = False
        #self.feedbackOut.send(SUCCESS)

    def play_spline(self, spline: Spline, loop: bool = False, offset: float = 0.) -> float:
        """Play a spline directly.

        Args:
            spline: Spline to play.

        Kwargs:
            loop: Loop spline playback.
            offset: Start offset inside spline.

        Returns:
            Scheduled start time of spline.
        """
        self.logger.info('Playing spline')
        self.spline = spline
        self.startTime = self.clock.now() - offset
        self.looping = loop
        return self.startTime

    def process_mc(self, mc: MotionCommand) -> Optional[float]:
        """Process new motion command and schedule next spline to play.

        Args:
            mc: Motion command.

        Returns:
            Scheduled start time of spline (if any).
        """
        try:
            self.logger.info('Playing motion %r', mc.name)
            spline = self.content.load_motion(mc.name)
        except FileNotFoundError:
            self.logger.error('Motion %r does not exist!', mc.name)
            currentVals = [out.value for out in self.positionOutputs]
            spline = constant_spline(currentVals, duration=5.)
        except json.JSONDecodeError:
            self.logger.error('Could not decode %r!', mc.name)
            currentVals = [out.value for out in self.positionOutputs]
            spline = constant_spline(currentVals, duration=5.)

        shape = spline_shape(spline)
        if shape != (self.ndim, ):
            msg = f'Motion {mc.name} (shape {shape}) is not compatible with connected motors ({self.ndim})!'
            self.logger.error(msg)

        return self.play_spline(spline, mc.loop)

    def update(self):
        for mc in self.input.receive():
            self.process_mc(mc)

        if self.playing:
            now = self.clock.now()
            t = now - self.startTime
            samples = sample_spline(self.spline, t, loop=self.looping)
            for val, out in zip(samples, self.positionOutputs):
                out.value = val

            if not self.looping and t >= self.spline.x[-1]:
                self.stop()

    def __str__(self):
        return type(self).__name__
