"""Simple behavior "engine".

To be expanded with a proper behavior tree engine (to be discussed).
"""
import enum
import random
from typing import List

from being.block import Block
from being.clock import Clock
from being.content import Content
from being.logging import get_logger
from being.motion_player import MotionPlayer, MotionCommand
from being.pubsub import PubSub
from being.serialization import register_enum


class State(enum.Enum):

    """Behavior states."""

    SLEEPING = 0
    CHILLED = 1
    EXCITED = 2


register_enum(State)


# For comforts / de-clutter
SLEEPING = State.SLEEPING
CHILLED = State.CHILLED
EXCITED = State.EXCITED


BEHAVIOR_CHANGED = 'BEHAVIOR_CHANGED'


def create_params(attentionSpan=10., sleepingMotions=None, chilledMotions=None, excitedMotions=None):
    """Create behavior params dictionary."""
    if sleepingMotions is None:
        sleepingMotions = []

    if chilledMotions is None:
        chilledMotions = []

    if excitedMotions is None:
        excitedMotions = []

    return {
        'attentionSpan': attentionSpan,
        'sleepingMotions': sleepingMotions,
        'chilledMotions': chilledMotions,
        'excitedMotions': excitedMotions,
    }


class Behavior(Block, PubSub):

    """Simple 3x state finite state machine behavior engine for ECAL workshop.
    Based on modified Anima II/III behavior engine. The three states are:
      1) SLEEPING
      2) CHILLED
      3) EXCITED

    Sensor trigger transitions SLEEPING / CHILLED -> EXCITED and fire one
    animation playback. After this single animation behavior will go to CHILLED
    where it will stay for at least `params.attentionSpan` many seconds. After
    that it will transition to SLEEPING state.

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
        self.state = State.SLEEPING
        self.lastChanged = 0.
        self.lastPlayed = ''
        self.logger = get_logger('Behavior')

    @property
    def params(self) -> dict:
        """Get current behavior params."""
        return self._params

    @params.setter
    def params(self, params: dict):
        """Update behavior params."""
        self._params = params
        self._purge_params()

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
        self.state = SLEEPING
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
        for key in ['sleepingMotions', 'chilledMotions', 'excitedMotions']:
            self._params[key] = [
                name
                for name in self._params[key]
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

    def play_random_motion(self, motions: List[str]):
        """Pick a random motion name from `motions` and fire a non-looping
        motion command to the motionPlayer.
        """
        if len(motions) == 0:
            return

        motion = random.choice(motions)
        self.lastPlayed = motion
        self.logger.info('Playing motion %r', motion)
        mc = MotionCommand(motion)
        self.mcOut.send(mc)
        self.publish(BEHAVIOR_CHANGED)

    def change_state(self, newState: State):
        """Change state of behavior to `newState`."""
        if newState is self.state:
            return

        self.logger.info('Changed to state %s', newState)
        self.publish(BEHAVIOR_CHANGED)
        self.state = newState
        self.lastChanged = self.clock.now()

    def update(self):
        triggered = self.sensor_triggered()
        playing = self.motion_playing()
        passed = self.clock.now() - self.lastChanged
        attentionLost = (passed > self._params['attentionSpan'])

        if not self.active:
            return

        if self.state is SLEEPING:
            if triggered:
                self.change_state(EXCITED)
                self.play_random_motion(self._params['excitedMotions'])
            elif not playing:
                self.play_random_motion(self._params['sleepingMotions'])

        elif self.state is CHILLED:
            if triggered:
                self.change_state(EXCITED)
                self.play_random_motion(self._params['excitedMotions'])
            elif attentionLost and not playing:
                self.change_state(SLEEPING)
                self.play_random_motion(self._params['sleepingMotions'])
            elif not playing:
                self.play_random_motion(self._params['chilledMotions'])

        elif self.state is EXCITED:
            if not playing:
                self.change_state(CHILLED)
                self.play_random_motion(self._params['chilledMotions'])

    def infos(self):
        return {
            'type': 'behavior-update',
            'active': self.active,
            'state': self.state,
            'lastPlayed': self.lastPlayed,
            'params': self._params,
        }
