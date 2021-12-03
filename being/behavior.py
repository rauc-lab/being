"""Simple behavior three state behavior engine.

A behavior processes sensor inputs and outputs motion commands to motion players
to trigger motion playback.
"""
import enum
import itertools
import os
import random
import warnings
from typing import Optional, ForwardRef

from being.block import Block, output_neighbors
from being.clock import Clock
from being.constants import INF
from being.content import Content
from being.logging import get_logger
from being.motion_player import MotionPlayer, MotionCommand
from being.pubsub import PubSub
from being.serialization import register_enum, loads, dumps
from being.utils import read_file, write_file, filter_by_type


class State(enum.Enum):

    """Behavior states."""

    STATE_I = 0
    STATE_II = 1
    STATE_III = 2


register_enum(State)

# For comforts / de-clutter
STATE_I = State.STATE_I
STATE_II = State.STATE_II
STATE_III = State.STATE_III

BEHAVIOR_CHANGED: str = 'BEHAVIOR_CHANGED'
"""PubSub event string literal. Triggered when something inside behavior has
changed (behavior state change but also if another motion gets played).
"""

Behavior = ForwardRef('Behavior')


def create_params(attentionSpan: float = 10., motions: Optional[list] = None) -> dict:
    """Create default behavior params dictionary.

    Args:
        attentionSpan (optional): Initial attention span duration (default is 10
            seconds).
        motions (optional): Initial motion lists. List of motion names for each
            behavior state. Lookup happens via index...

    Returns:
        Behavior params dictionary.
    """
    if motions is None:
        motions = [[] for _ in State]

    return {
        'attentionSpan': attentionSpan,
        'motions': motions,
    }


class Behavior(Block, PubSub):

    """Simple 3x state finite state machine behavior engine. Originally build
    for the ÉCAL workshop in March 2021.

    There are three states (:class:`being.behavior.State`):
      1) STATE_I
      2) STATE_II
      3) STATE_III

    Each state has its own repertoire of motions. The sensor input
    (:class:`being.connectables.MessageInput`) triggers a state transition to
    STATE_III and fires one single animation playback for STATE_III. When this
    motion finishes the behavior transitions to STATE_II where it will stay for
    at least ``params.attentionSpan`` many seconds and play motions for this
    state. Afterwards it transitions back to STATE_I.

    If provided with a filepath the current behavior params get stored / loaded
    from a JSON file (inside current working directory).

    Notes:
      - By setting the ``attentionSpan`` to zero STATE_II can be skipped.
      - Animations are chosen randomly from supplied animation from params.
      - A new sensor trigger will always interrupt STATE_I / STATE_II and jump
        immediately to STATE_III
    """

    FREE_NUMBERS = itertools.count(1)
    """Behavior number counter for default behavior names."""

    def __init__(self,
            params: Optional[dict] = None,
            clock: Optional[Clock] = None,
            content: Optional[Content] = None,
            name: Optional[str] = None,
        ):
        """
        Args:
            params (optional): Behavior params dictionary
            clock (optional): Being clock (DI).
            content (optional): Being content (DI).
            name (optional): Block name.
        """
        if params is None:
            params = create_params()

        if clock is None:
            clock = Clock.single_instance_setdefault()

        if content is None:
            content = Content.single_instance_setdefault()

        if name is None:
            name = 'Behavior %d' % next(self.FREE_NUMBERS)

        super().__init__(name=name)
        PubSub.__init__(self, events=[BEHAVIOR_CHANGED])
        self.add_message_input('sensorIn')
        self.add_message_output('mcOut')

        self._params = params
        self.clock = clock
        self.content = content

        self.active: bool = True
        """If behavior engine is running."""

        self.state: State = State.STATE_I
        """Current behavior state."""

        self.lastChanged: float = -INF
        """Duration since last behavior state change."""

        self.lastPlayed: str = ''
        """Name of the last played motion."""

        self.playingUntil: float = -INF
        """Timestamp until current motion is playing."""

        self.filepath: str = ''
        """Associated behavior config file for storing params."""

        self.logger = get_logger(self.name)

    @classmethod
    def from_config(cls, filepath: str, *args, **kwargs) -> Behavior:
        """
        Construct behavior instance with an associated parms JSON file.
        Remembers ``filepath`` and save each change of params to disk.

        Args:
            filepath: JSON config file.
            *args: Behavior variable length argument list.
            **kwargs: Arbitrary Behavior keyword arguments.

        Returns:
            New Behavior instance.
        """
        if os.path.exists(filepath):
            params = loads(read_file(filepath))
        else:
            params = create_params()

        self = cls(*args, **kwargs)
        self.filepath = filepath
        self.params = params
        return self

    @property
    def params(self) -> dict:
        """Get current behavior params."""
        return self._params

    @params.setter
    def params(self, params: dict):
        """Update behavior params. If ``filepath`` attribute is defined also
        save it to disk.
        """
        self._params = params
        self._purge_params()
        if self.filepath:
            write_file(self.filepath, dumps(self._params, indent=4))

    def associate(self, motionPlayer: MotionPlayer):
        """Associate behavior engine with motion player block (connect
        bi-directional).

        Args:
            motionPlayer: To couple with behavior.

        Warning:
            Deprecated! Behavior runs now in "open loop" and keeps track how
            long motions run for.
        """
        msg = (
            'Behavior.associate(motionPlayer) is deprecated. Just connect'
            ' motion player normally behavior.mcOut.connect(motionPlayer).'
        )
        warnings.warn(msg, DeprecationWarning, stacklevel=2)

    def reset(self):
        """Reset behavior states and attributes. Jump back to STATE_I."""
        self.active = True
        self.state = State.STATE_I
        self.lastChanged = 0.
        self.lastPlayed = ''
        self.playingUntil = 0.

    def play(self):
        """Start behavior playback."""
        self.active = True
        self.publish(BEHAVIOR_CHANGED)

    def pause(self):
        """Pause behavior playback."""
        self.reset()
        self.active = False
        self.publish(BEHAVIOR_CHANGED)
        outputNeighbors = output_neighbors(self)
        for mp in filter_by_type(outputNeighbors, MotionPlayer):
            mp.stop()

    def sensor_triggered(self) -> bool:
        """Check if sensor got triggered. This will drain all input messages.

        Returns:
            True if we received `any` message at the sensor input.
        """
        triggered = False
        for _ in self.sensorIn.receive():  # Consume all trigger messages
            triggered = True

        return triggered

    def _purge_params(self):
        """Check with content and remove all outdated motions from params."""
        existing = self.content.list_curve_names()
        for stateNr, names in enumerate(self._params['motions']):
            self._params['motions'][stateNr] = [
                name
                for name in names
                if name in existing
            ]

    def motion_duration(self, name: str) -> float:
        """Get duration of motion."""
        motion = self.content.load_curve(name)
        return motion.end

    def play_random_motion_for_current_state(self):
        """Pick a random motion name from motions and fire a non-looping motion
        command.
        """
        names = self._params['motions'][self.state.value]
        if len(names) == 0:
            return

        name = random.choice(names)
        self.lastPlayed = name
        self.logger.info('Playing motion %r', name)
        duration = self.motion_duration(name)
        until = self.clock.now() + duration
        self.playingUntil = until
        mc = MotionCommand(name)
        self.mcOut.send(mc)
        self.publish(BEHAVIOR_CHANGED)

    def change_state(self, newState: State):
        """Change behavior state.

        Args:
            newState: New behavior state to change to.
        """
        if newState is self.state:
            return

        self.logger.info('Changed to state %s', newState.name)
        self.state = newState
        self.lastChanged = self.clock.now()
        self.publish(BEHAVIOR_CHANGED)

    def update(self):
        triggered = self.sensor_triggered()  # Consume trigger events also when not active

        if not self.active:
            return

        now = self.clock.now()
        playing = now <= self.playingUntil
        passed = now - self.lastChanged
        attentionLost = (passed >= self._params['attentionSpan'])

        if self.state is STATE_I:
            if triggered:
                self.change_state(STATE_III)
                self.play_random_motion_for_current_state()

        elif self.state is STATE_II:
            if triggered:
                self.change_state(STATE_III)
                self.play_random_motion_for_current_state()
            elif attentionLost and not playing:
                self.change_state(STATE_I)

        elif self.state is STATE_III:
            if not playing:
                if triggered:
                    self.change_state(STATE_III)
                elif self._params['attentionSpan'] > 0:
                    self.change_state(STATE_II)
                else:
                    self.change_state(STATE_I)

        if not playing:
            self.play_random_motion_for_current_state()

    def to_dict(self):
        dct = super().to_dict()
        dct['active'] = self.active
        dct['lastPlayed'] = self.lastPlayed
        dct['params'] = self._params
        dct['state'] = self.state
        return dct
