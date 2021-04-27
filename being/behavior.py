"""Simple behavior "engine".

To be expanded with a proper behavior tree engine (to be discussed).
"""
import enum
import os
import random

from being.block import Block
from being.clock import Clock
from being.content import Content
from being.logging import get_logger
from being.motion_player import MotionPlayer, MotionCommand
from being.pubsub import PubSub
from being.serialization import register_enum, loads, dumps
from being.utils import read_file, write_file


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


BEHAVIOR_CHANGED = 'BEHAVIOR_CHANGED'


def create_params(attentionSpan=10., motions=None):
    """Create default behavior params dictionary."""
    if motions is None:
        motions = [[] for _ in State]

    return {
        'attentionSpan': attentionSpan,
        'motions': motions,
    }


class Behavior(Block, PubSub):

    """Simple 3x state finite state machine behavior engine for ECAL workshop.
    Based on modified Anima II/III behavior engine. The three states are:
      1) STATE_I
      2) STATE_II
      3) STATE_III

    Sensor trigger transitions STATE_I / STATE_II -> STATE_III and fire one
    animation playback. After this single animation behavior will go to STATE_II
    where it will stay for at least `params.attentionSpan` many seconds. After
    that it will transition to STATE_I state.

    Animations are chosen randomly from supplied animation from params.

    Extra Params class for JSON serialization / API.
    """

    def __init__(self, params=None, clock=None, content=None):
        if params is None:
            params = create_params()

        if clock is None:
            clock = Clock.single_instance_setdefault()

        if content is None:
            content = Content.single_instance_setdefault()

        super().__init__()
        PubSub.__init__(self, events=[BEHAVIOR_CHANGED])
        self.add_message_input('sensorIn')
        self.add_message_output('mcOut')
        #self.add_message_input('feedbackIn')

        self._params = params
        self.clock = clock
        self.content = content

        self.active = True
        self.motionPlayer = None
        self.state = State.STATE_I
        self.lastChanged = 0.
        self.lastPlayed = ''
        self.logger = get_logger('Behavior')
        self.filepath = ''

    @classmethod
    def from_config(cls, filepath: str, *args, **kwargs):
        """Create behavior instance with params from config file. Remembers
        filepath and save each change of params to disk.

        Args:
            filepath: JSON config file.
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
        """Update behavior params."""
        self._params = params
        self._purge_params()
        if self.filepath:
            write_file(self.filepath, dumps(self._params, indent=4))

    def associate(self, motionPlayer: MotionPlayer):
        """Associate behavior engine with motion player block (connect
        bi-directional).

        Args:
            motionPlayer: To couple with behavior.
        """
        self.motionPlayer = motionPlayer
        self.mcOut.connect(motionPlayer.mcIn)
        #motionPlayer.feedbackOut.connect(self.feedbackIn)

    def play(self):
        """Start behavior playback."""
        self.active = True
        self.publish(BEHAVIOR_CHANGED)

    def pause(self):
        """Pause behavior playback."""
        self.active = False
        self.lastPlayed = ''
        self.motionPlayer.stop()
        self.state = STATE_I
        self.publish(BEHAVIOR_CHANGED)

    def sensor_triggered(self) -> bool:
        """Check if sensor got triggered."""
        triggered = False
        for _ in self.sensorIn.receive():
            triggered = True

        return triggered

    def _purge_params(self):
        """Check with content and remove all non existing motion names from _params."""
        existing = list(self.content._sorted_names())
        for i, names in enumerate(self._params['motions']):
            self._params['motions'][i] = [
                name
                for name in names
                if name in existing
            ]

    def motion_playing(self) -> bool:
        """Check if associated motionPlayer is playing a motion at the moment or
        idling.
        """
        # TODO(atheler): Dirty hack following
        # Reasoning: We should feed that via the feedback messages from the
        # motionPlayer. But then we have to take special care for if there is
        # nothing playing at the start (e.g. extra playing flag in behavior).
        # For now, let's just look at this state directly from the
        # motionPlayer, even though it's ugly...
        return self.motionPlayer.playing

    def play_random_motion_for_current_state(self):
        """Pick a random motion name from `motions` and fire a non-looping
        motion command to the motionPlayer.
        """
        names = self._params['motions'][self.state.value]
        if len(names) == 0:
            return

        name = random.choice(names)
        self.lastPlayed = name
        #self.logger.info('Playing motion %r', name)
        mc = MotionCommand(name)
        self.mcOut.send(mc)
        self.publish(BEHAVIOR_CHANGED)

    def change_state(self, newState: State):
        """Change state of behavior to `newState`."""
        if newState is self.state:
            return

        self.logger.info('Changed to state %s', newState.name)
        self.state = newState
        self.lastChanged = self.clock.now()
        self.publish(BEHAVIOR_CHANGED)

    def update(self):
        if not self.active:
            return

        triggered = self.sensor_triggered()
        playing = self.motion_playing()
        passed = self.clock.now() - self.lastChanged
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

    def infos(self):
        return {
            'type': 'behavior-update',
            'active': self.active,
            'state': self.state,
            'lastPlayed': self.lastPlayed,
            'params': self._params,
        }
