"""Spline motion player block.


TODO:
  - Changing playback speed on the fly. As separate input? Need some internal
    clock. Or a phasor?
  - Slow and fast crossover between splines?
"""
import logging
from typing import NamedTuple

from scipy.interpolate import BPoly

from being.block import Block
from being.clock import Clock
from being.spline import Spline, sample_spline
from being.content import Content
from being.behavior_tree import SUCCESS


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

    def __init__(self, clock=None, content=None):
        if clock is None:
            clock = Clock.single_instance_setdefault()

        if content is None:
            content = Content.single_instance_setdefault()

        super().__init__()
        self.add_message_input('mcIn')
        self.add_value_output('setpointPosition')
        self.add_message_output('feedbackOut')

        self.clock = clock
        self.content = content
        self.spline = None
        self.startTime = 0
        self.looping = False
        self.logger = logging.getLogger(str(self))

    @property
    def playing(self) -> bool:
        """Spline playback in progress."""
        return self.spline is not None

    def stop(self):
        """Stop spline playback."""
        self.spline = None
        self.startTime = 0
        self.looping = False
        self.feedbackOut.send(SUCCESS)

    def play_spline(self, spline: Spline, loop=False, offset=0):
        """Play a spline directly.

        Args:
            spline: Spline to play.

        Kwargs:
            loop: Loop spline playback.
            offset: Start offset inside spline.
        """
        self.spline = spline
        self.startTime = self.clock.now() - offset
        self.looping = loop
        return self.startTime

    def live_preview(self, position):
        """Reset spline and output position value directly."""
        if self.playing:
            self.stop()

        self.output.value = position

    def process_mc(self, mc: MotionCommand):
        """Process new motion command and schedule next spline to play.

        Args:
            mc: Motion command.
        """
        try:
            spline = self.content.load_motion(mc.name)
        except FileNotFoundError:
            self.logger.error('Motion %r does not exist!', mc.name)
            spline = constant_spline(self.output.value, duration=5.)

        return self.play_spline(spline, mc.loop)

    def update(self):
        for mc in self.input.receive():
            self.process_mc(mc)

        if self.playing:
            now = self.clock.now()
            t = now - self.startTime
            sample = sample_spline(self.spline, t, loop=self.looping)
            self.output.value = sample

            if not self.looping and t >= self.spline.x[-1]:
                self.stop()
