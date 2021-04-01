"""Simple behavior "engine".

To be expanded with a proper behavior tree engine (to be discussed).
"""
import enum
import logging
import random
from typing import NamedTuple, List

from being.block import Block
from being.clock import Clock
from being.motion_player import MotionCommand
from being.serialization import register_named_tuple


class State(enum.Enum):

    """Behavior states."""

    SLEEPING = 0
    CHILLED = 1
    EXCITED = 2


# For comforts / declutter
SLEEPING = State.SLEEPING
CHILLED = State.CHILLED
EXCITED = State.EXCITED


class Params(NamedTuple):

    """Behavior parameters.

    Done in this relatively clumsy why so that we can serialize those parameters
    and exchange them with the front end (JSON / API).
    """

    attentionSpan: float
    sleepyMotions: list
    chilledMotions: list
    excitedMotions: list

    @classmethod
    def default(cls, attentionSpan=10., sleepyMotions=None, chilledMotions=None, excitedMotions=None):
        """Constructor with defaults."""
        if sleepyMotions is None:
            sleepyMotions = []

        if chilledMotions is None:
            chilledMotions = []

        if excitedMotions is None:
            excitedMotions = []

        return cls(attentionSpan, sleepyMotions, chilledMotions, excitedMotions)


register_named_tuple(Params)


class Behavior(Block):

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
    def __init__(self, params=None, clock=None):
        if params is None:
            params = Params.default()

        if clock is None:
            clock = Clock.single_instance_setdefault()

        super().__init__()
        self.add_message_input('sensorIn')
        self.add_message_output('mcOut')
        self.add_message_input('feedbackIn')

        self.params = params
        self.clock = clock
        self.state = State.SLEEPING
        self.lastStateChange = 0
        self.logger = logging.getLogger(str(self))

    def associate(self, motionPlayer):
        """Associate behavior engine with motion player block (connect
        bi-directional).

        Args:
            motionPlayer (MotionPlayer): To couple with behavior.
        """
        self.motionPlayer = motionPlayer
        #self.mcOut.connect(motionPlayer.mcIn)
        motionPlayer.feedbackOut.connect(self.feedbackIn)

    def sensor_triggered(self) -> bool:
        """Check if sensor got triggered."""
        triggered = False
        for msg in self.sensorIn.receive():
            triggered = True

        return triggered

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
        self.logger.info('Playing motion %r', motion)
        mc = MotionCommand(motion)
        self.output.send(mc)

    def change_state(self, newState: State):
        """Change state of behavior to `newState`."""
        if newState is self.state:
            return

        self.logger.info('Changed to state %s', newState)
        self.state = newState
        self.lastStateChange = self.clock.now()

    def update(self):
        triggered = self.sensor_triggered()
        playing = self.motion_playing()
        passed = self.clock.now() - self.lastStateChange
        attentionLost = (passed > self.params.attentionSpan)

        if self.state is SLEEPING:
            if triggered:
                self.change_state(EXCITED)
                self.play_random_motion(self.params.excitedMotions)
            elif not playing:
                self.play_random_motion(self.params.sleepyMotions)

        elif self.state is CHILLED:
            if triggered:
                self.change_state(EXCITED)
                self.play_random_motion(self.params.excitedMotions)
            elif attentionLost and not playing:
                self.change_state(SLEEPING)
                self.play_random_motion(self.params.sleepyMotions)
            elif not playing:
                self.play_random_motion(self.params.chilledMotions)

        elif self.state is EXCITED:
            if not playing:
                self.change_state(CHILLED)
                self.play_random_motion(self.params.chilledMotions)
