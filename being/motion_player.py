"""Spline motion player block.


TODO:
  - Changing playback speed on the fly. As separate input? Need some internal
    clock. Or a phasor?
  - Slow and fast crossover between splines?
"""
from typing import NamedTuple

from scipy.interpolate import PPoly, BPoly

from being.block import Block
from being.clock import Clock
from being.spline import Spline, shift_spline, sample_spline
from being.content import Content


"""
# TODO: Urgency. Do we need that? Should we use it for slow and fast crossovers?

from enum import Enum, auto

class Urgency(Enum):
    NOW = auto()
    NEXT = auto()
    ENQUEUE = auto()
"""


def constant_spline(position=0) -> BPoly:
    """Create a constant spline for a given position which extrapolates
    indefinitely.

    Kwargs:
        position: Target position value.

    Returns:
        Constant spline.
    """
    return BPoly(c=[[position]], x=[0., 1.], extrapolate=True)


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
        super().__init__()
        if clock is None:
            clock = Clock.single_instance_setdefault()

        if content is None:
            content = Content.single_instance_setdefault()

        self.clock = clock
        self.content = content
        self.add_message_input()
        self.add_value_output()

        self.spline = constant_spline(position=0)
        self.startTime = 0
        self.looping = False

    def play_spline(self, spline: Spline, loop=False):
        """Play a spline directly.

        Args:
            spline: Spline to play.
        """
        if spline.x[0] != 0:
            # TODO: Zeroing spline in time could be done in Content manager. But
            # better safe than sorry.
            spline = shift_spline(spline, offset=-spline.x[0])

        self.spline = spline
        self.startTime = self.clock.now()
        self.looping = loop
        return self.startTime

    def process_mc(self, mc: MotionCommand):
        """Process new motion command and schedule next spline to play.

        Args:
            mc: Motion command.
        """
        spline = self.content.load_motion(mc.name)
        return self.play_spline(spline, mc.loop)

    def update(self):
        for mc in self.input.receive():
            self.process_mc(mc)

        now = self.clock.now()
        self.output.value = sample_spline(self.spline, (now - self.startTime), loop=self.looping)
