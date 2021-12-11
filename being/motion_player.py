"""Curve / motion player block. Outputs motion samples to the motors.

.. digraph:: motionplayer
    :align: center
    :alt: Motion Player steering multiple motors
    :caption: Motion Player steering multiple motors
    :name: Motion Player steering multiple motors

    rankdir="LR"
    dummy [label="", shape=none, height=0, width=0]
    MP [shape=box, label="Motion Player"];
    A [shape=box, label="Motor 1"];
    B [shape=box, label="Motor 2"];
    C [shape=box, label="Motor 3"];

    dummy -> MP [label="Motion Command"]
    MP -> A [style=dashed, label="Target Position"]
    MP -> B [style=dashed]
    MP -> C [style=dashed]

Todo:
  - Changing playback speed on the fly. As separate input? Phasor?
  - Motion crossover
"""
import json
from typing import NamedTuple, Optional, List

import numpy as np
from scipy.interpolate import BPoly

from being.block import Block, output_neighbors
from being.clock import Clock
from being.connectables import ValueOutput
from being.content import Content
from being.curve import Curve
from being.logging import get_logger
from being.motors.blocks import MotorBlock
from being.utils import filter_by_type


def constant_spline(position: float = 0.0, duration: float = 1.0) -> BPoly:
    """Create a constant position spline which extrapolates indefinitely.

    Args:
        position: Target position value.
        duration: Duration of the constant motion.

    Returns:
        Constant spline.
    """
    return BPoly(c=[[position]], x=[0., duration], extrapolate=True)


def constant_curve(positions: float = 0.0, duration: float = 1.0) -> Curve:
    """Create a constant curve with a single channel. Keeping a constant value
    indefinitely.

    Args:
        position: Target position value.
        duration: Duration of the constant motion.

    Returns:
        Constant curve.
    """
    return Curve([
        constant_spline(pos, duration)
        for pos in np.atleast_1d(positions)
    ])


class MotionCommand(NamedTuple):

    """Message to trigger motion curve playback."""

    name: str
    """Name of the motion."""

    loop: bool = False
    """Looping the motion indefinitely or not. """


class MotionPlayer(Block):

    """Motion curve sampler block. Receives motion commands on its message
    input, looks up motion curve from :class:`being.content.Content` and samples
    motion curve to position outputs.  Supports looping playback.

    Note:
        :attr:`MotionPlayer.positionOutputs` attributes for the position outputs
        only. In order to distinguish them from other outputs in the future.
    """

    def __init__(self,
            ndim: int = 1,
            clock: Optional[Clock] = None,
            content: Optional[Content] = None,
            **kwargs,
        ):
        """
        Args:
            ndim (optional): Number of dimensions / motors / initial number of
                position outputs. Default is one.
            clock (optional): Clock instance (DI).
            content (optional): Content instance (DI).
            **kwargs: Arbitrary block keyword arguments.
        """
        if clock is None:
            clock = Clock.single_instance_setdefault()

        if content is None:
            content = Content.single_instance_setdefault()

        super().__init__(**kwargs)
        self.add_message_input('mcIn')
        self.positionOutputs: List[ValueOutput] = []
        """Position value outputs."""

        for _ in range(ndim):
            self.add_position_output()

        self.clock = clock
        self.content = content
        self.logger = get_logger(str(self))

        self.curve: Optional[Curve] = None
        """Currently playing motion curve."""

        self.startTime: float = 0.0
        """Start time of current motion curve."""

        self.looping: bool = False
        """If current motion curve is looping."""

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
        self.startTime = 0.0
        self.looping = False

    def play_curve(self, curve: Curve, loop: bool = False, offset: float = 0.0) -> float:
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

    def process_mc(self, mc: MotionCommand) -> float:
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
        """Iterate over neighboring blocks at the position outputs.

        Yields:
            Motor blocks.
        """
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
        return '%s()' % type(self).__name__
