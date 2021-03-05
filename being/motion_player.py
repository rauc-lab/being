"""Spline motion player block."""
from typing import NamedTuple

from scipy.interpolate import PPoly

from being.block import Block
from being.clock import Clock
from being.spline import shift_spline, sample_spline
from being.content import Content


ZERO_SPLINE = PPoly([[0.]], [0., 1.], extrapolate=True)


"""
# TODO: Urgency. Do we need that? Should we use it for slow and fast crossovers?

from enum import Enum, auto

class Urgency(Enum):
    NOW = auto()
    NEXT = auto()
    ENQUEUE = auto()
"""


class MotionCommand(NamedTuple):

    """Message to trigger spline playback."""

    name: str
    loop: bool = False
    playbackSpeed: float = 1.


class MotionPlayer(Block):

    """Spline sampler block. Feeds on motion commands and outputs position
    values for a given spline. Supports different playback speeds and looping
    option.
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
        self.spline = ZERO_SPLINE
        self.startTime = 0
        self.playbackSpeed = 1.
        self.looping = False

    def process_mc(self, mc: MotionCommand, now: float):
        """Process new motion command and schedule next spline to play."""
        self.looping = mc.loop
        self.playbackSpeed = mc.playbackSpeed
        self.startTime = now
        spline = self.content.load_motion(mc.name)
        if spline.x[0] != 0:
            # TODO: Zeroing spline could be done in Content manager. But better
            # safe than sorry
            spline = shift_spline(spline, offset=-spline.x[0])

        self.spline = spline

    def update(self):
        now = self.clock.now()
        for mc in self.input.receive():
            self.process_mc(mc, now)

        t = self.playbackSpeed * (now - self.startTime)
        self.output.value = sample_spline(self.spline, t, loop=self.looping)
