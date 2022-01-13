import unittest

from scipy.interpolate import CubicSpline

from being.behavior import STATE_I, STATE_II, STATE_III, Behavior, create_params
from being.clock import Clock
from being.connectables import MessageInput
from being.curve import Curve
from being.motion_player import MotionPlayer


SLEEPY_MOTION = 'Sleepy Motion'
CHILLED_MOTION = 'Chilled Motion'
EXCITED_MOTION = 'Excited Motion'


class DummyContent:
    def load_curve(self, name):
        spline = CubicSpline([0., 1.], [[0.], [0.]])
        return Curve(splines=[spline])


class CallCounter:
    def __init__(self, func):
        self.func = func
        self.nCalls = 0

    def reset(self):
        self.nCalls = 0

    def __call__(self, *args, **kwargs):
        self.nCalls += 1
        return self.func(*args, **kwargs)


class TestBehavior(unittest.TestCase):

    """Test behavior with test setup and one single fake motion per state."""

    def setUp(self):
        self.clock = Clock(interval=0.5)
        content = DummyContent()
        self.motionPlayer = MotionPlayer(clock=self.clock, content=content)
        params = create_params(
            attentionSpan=5.,
            motions=[
                [SLEEPY_MOTION],
                [CHILLED_MOTION],
                [EXCITED_MOTION],
            ],
        )
        self.behavior = Behavior(params=params, clock=self.clock, content=content)
        self.behavior.change_state = CallCounter(self.behavior.change_state)
        self.drain = MessageInput()
        self.behavior.mcOut.connect(self.drain)

    def latest_motion(self):
        return self.drain.receive_latest()

    def step_one_cycle(self):
        self.behavior.update()
        self.motionPlayer.update()
        self.clock.step()

    def test_new_behavior_starts_sleeping_and_playing_a_sleepy_animation(self):
        self.assertFalse(self.latest_motion())

        self.step_one_cycle()

        self.assertIs(self.behavior.state, STATE_I)

        mc = self.latest_motion()

        self.assertEqual(mc.name, SLEEPY_MOTION)

    def test_no_unnecessary_state_changes(self):
        self.assertEqual(self.behavior.change_state.nCalls, 0)

        self.step_one_cycle()

        self.assertEqual(self.behavior.change_state.nCalls, 0)

    def test_sleeping_being_stays_dormant(self):
        self.step_one_cycle()

        self.assertEqual(self.behavior.state, STATE_I)

        self.step_one_cycle()

        self.assertEqual(self.behavior.state, STATE_I)

    def test_sensor_trigger_excites_being(self):
        self.step_one_cycle()

        self.assertIs(self.behavior.state, STATE_I)

        self.behavior.sensorIn.push('Something moved...')
        self.step_one_cycle()
        mc = self.latest_motion()

        self.assertIs(self.behavior.state, STATE_III)
        self.assertEqual(mc.name, EXCITED_MOTION)

        self.behavior.change_state(STATE_II)

        self.assertIs(self.behavior.state, STATE_II)

        self.behavior.sensorIn.push('Yet again something moved...')
        self.step_one_cycle()

        self.assertIs(self.behavior.state, STATE_III)
        self.assertEqual(mc.name, EXCITED_MOTION)

    def test_sleeping_being_continues_playing_new_sleepy_animations(self):
        # Clock = 0.0
        self.step_one_cycle()
        mc = self.latest_motion()

        self.assertEqual(self.behavior.state, STATE_I)
        self.assertEqual(mc.name, SLEEPY_MOTION)

        # Clock = 0.5
        self.step_one_cycle()
        mc = self.latest_motion()

        self.assertIs(self.behavior.state, STATE_I)
        self.assertIs(mc, None)

        # Clock = 1.0
        self.step_one_cycle()
        mc = self.latest_motion()

        self.assertIs(self.behavior.state, STATE_I)
        self.assertIs(mc, None)

        # Clock = 1.5
        # Note: We loose one cycle because of the cycle between
        # behavior <-> motionPlayer
        self.step_one_cycle()
        mc = self.latest_motion()

        self.assertIs(self.behavior.state, STATE_I)
        self.assertIs(mc.name, SLEEPY_MOTION)

    def test_sleeping_being_stays_dormant_independent_of_attention_span(self):
        self.step_one_cycle()

        self.assertIs(self.behavior.state, STATE_I)

        for _ in range(100):
            self.step_one_cycle()

        self.assertIs(self.behavior.state, STATE_I)

    def let_motion_play_out(self, excpectedState):
        for _ in range(2):
            self.step_one_cycle()
            mc = self.latest_motion()

            self.assertIs(self.behavior.state, excpectedState)
            self.assertIs(mc, None)

    def test_chilled_being_with_attention_keeps_playing_chilled_animations(self):
        self.behavior.change_state(STATE_II)

        # Clock = 0.0
        self.step_one_cycle()
        mc = self.latest_motion()

        self.assertIs(self.behavior.state, STATE_II)
        self.assertEqual(mc.name, CHILLED_MOTION)

        self.let_motion_play_out(STATE_II)

        # Clock = 1.5
        self.step_one_cycle()
        mc = self.latest_motion()

        self.assertIs(self.behavior.state, STATE_II)
        self.assertEqual(mc.name, CHILLED_MOTION)

        self.let_motion_play_out(STATE_II)

        # Clock = 3.0
        self.step_one_cycle()
        mc = self.latest_motion()

        self.assertIs(self.behavior.state, STATE_II)
        self.assertEqual(mc.name, CHILLED_MOTION)

        self.let_motion_play_out(STATE_II)

        # Clock = 4.5
        self.step_one_cycle()
        mc = self.latest_motion()

        self.assertIs(self.behavior.state, STATE_II)
        self.assertEqual(mc.name, CHILLED_MOTION)

        self.let_motion_play_out(STATE_II)

        # Clock = 6.0 which is over attention span!
        self.step_one_cycle()
        mc = self.latest_motion()

        self.assertIs(self.behavior.state, STATE_I)
        self.assertEqual(mc.name, SLEEPY_MOTION)

    def test_excited_being_only_plays_one_excited_animation(self):
        self.behavior.sensorIn.push('Something moved')

        self.step_one_cycle()
        mc = self.latest_motion()

        self.assertIs(self.behavior.state, STATE_III)
        self.assertEqual(mc.name, EXCITED_MOTION)

        self.let_motion_play_out(STATE_III)

        self.step_one_cycle()
        mc = self.latest_motion()

        self.assertIs(self.behavior.state, STATE_II)
        self.assertEqual(mc.name, CHILLED_MOTION)


    def test_fading_attention_span_does_not_cut_off_chilled_animation(self):
        pass
        # Already tested in test_chilled_being_with_attention_keeps_playing_chilled_animations()


if __name__ == '__main__':
    unittest.main()
