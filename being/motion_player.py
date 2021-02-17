from typing import NamedTuple
from enum import Enum, auto

import numpy as np
from scipy.interpolate import PPoly

from being.block import Block
from being.clock import Clock
from being.spline import shitf_spline
from being.math import clip
from being.content import Content


ZERO_SPLINE = PPoly([[0.]], [0., 1.], extrapolate=True)


"""
class Urgency(Enum):
    NOW = auto()
    NEXT = auto()
    ENQUEUE = auto()
"""


class MotionCommand(NamedTuple):
    name: str
    #urgency: str = Urgency.NEXT
    loop: bool = False
    playbackSpeed: float = 1.


def sample_spline(spline: PPoly, t, loop: bool = False):
    """Sample spline. Clips time values for non extrapolating splines. Also
    supports looping.

    Args:
        spline: PPoly spline to sample.
        t: Time value(s)

    Kwargs:
        loop: Loop spline motion.

    Returns:
        Spline value(s).
    """
    start = spline.x[0]  # No fancy indexing. Faster then `start, end = spline.x[[0, -1]]`
    end = spline.x[-1]

    if loop:
        duration = end - start
        return spline((t - start) % duration + start)

    if spline.extrapolate:
        return spline(t)

    return spline(np.clip(t, start, end))


class MotionPlayer(Block):
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
        self.queue = []
        self.spline = ZERO_SPLINE

    def schedule_spline(self, spline, start=None):
        """Schedule new spline. Shift according to the current time."""
        if start is None:
            start = self.clock.now()

        offset = spline.x[0] - start
        self.spline = shitf_spline(spline, offset)

    def process_mc(self, now, mc):
        """
        if mc.urgency == Urgency.NOW:
            pass
        elif mc.urgency == Urgency.NEXT:
            pass
        elif mc.urgency == Urgency.ENQUEUE:
            pass
        """

        spline = self.content.load_motion(mc.name)
        self.schedule_spline(spline)

    def update(self):
        now = self.clock.now()
        for mc in self.input.receive():
            self.process_mc(now, mc)

        self.output.value = sample_spline(self.spline, now)
