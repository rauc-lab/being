import unittest

from numpy.testing import assert_allclose

from being.kinematics import State, optimal_trajectory as _optimal_trajectory, step


def optimal_trajectory(*args, **kwargs):
    """Cut of zero duration segments from optimal_trajectory for testing."""
    profiles = _optimal_trajectory(*args, **kwargs)
    return [
        (dt, acc) for dt, acc in profiles
        if dt != 0
    ]


def final_state(initialState: State, profiles) -> State:
    """Evaluate final state after applying acceleration profiles."""
    state = initialState
    for dt, acc in profiles:
        state = state._replace(acceleration=acc)
        state = step(state, dt)

    return state._replace(acceleration=0.)


class TestOptimalTrajectory(unittest.TestCase):
    def test_standing_still_when_nothing_to_do(self):
        start = target = State(1.234, 0.)
        profiles = optimal_trajectory(target, start)
        final = final_state(start, profiles)

        self.assertEqual(profiles, [])
        self.assertEqual(final, target)

    def test_critical_profiles(self):
        maxAcc = 1.

        # Accelerate upwards
        start = State(0.0, 1.0)
        target = State(1.5, 2.)
        profiles = optimal_trajectory(target, start, maxAcc=maxAcc)

        self.assertEqual(profiles, [(1.0, maxAcc)])
        self.assertEqual(final_state(start, profiles), target)

        # Decelerate upwards
        start = State(0.0, 1.0)
        target = State(0.5, 0.0)
        profiles = optimal_trajectory(target, start, maxAcc=maxAcc)

        self.assertEqual(profiles, [(1.0, -maxAcc)])
        self.assertEqual(final_state(start, profiles), target)

        # Decelerate downwards
        start = State(0.0, -1.0)
        target = State(-0.5, 0.0)
        profiles = optimal_trajectory(target, start, maxAcc=maxAcc)

        self.assertEqual(profiles, [(1.0, maxAcc)])
        self.assertEqual(final_state(start, profiles), target)

        # Accelerate downwards
        start = State(0, -1)
        target = State(-1.5, -2.0)
        profiles = optimal_trajectory(target, start, maxAcc=maxAcc)

        self.assertEqual(profiles, [(1.0, -maxAcc)])
        self.assertEqual(final_state(start, profiles), target)

    def test_steady_state_triangular_profiles(self):
        maxAcc = 1.0

        # Up up
        start = State(1.0)
        target = State(2.0)
        profiles = optimal_trajectory(target, start, maxAcc=maxAcc)

        self.assertEqual(profiles, [(1.0, maxAcc), (1.0, -maxAcc)])
        self.assertEqual(final_state(start, profiles), target)

        # Up down
        start = State(1.0)
        target = State(0.0)
        profiles = optimal_trajectory(target, start, maxAcc=maxAcc)

        self.assertEqual(profiles, [(1.0, -maxAcc), (1.0, maxAcc)])
        self.assertEqual(final_state(start, profiles), target)

        # Down up
        start = State(-1.0)
        target = State(0.0)
        profiles = optimal_trajectory(target, start, maxAcc=maxAcc)

        self.assertEqual(profiles, [(1.0, maxAcc), (1.0, -maxAcc)])
        self.assertEqual(final_state(start, profiles), target)

        # Down down
        start = State(-1.0)
        target = State(-2.0)
        profiles = optimal_trajectory(target, start, maxAcc=maxAcc)

        self.assertEqual(profiles, [(1.0, -maxAcc), (1.0, maxAcc)])
        self.assertEqual(final_state(start, profiles), target)

    def test_steady_state_trapezoidal_profiles(self):
        maxAcc = 1.0

        # Up up
        start = State(2.0)
        target = State(4.0)
        profiles = optimal_trajectory(target, start, maxAcc=maxAcc)

        self.assertEqual(profiles, [(1.0, maxAcc), (1.0, 0.0), (1.0, -maxAcc)])
        self.assertEqual(final_state(start, profiles), target)

        # Up down
        start = State(2.0)
        target = State(0.0)
        profiles = optimal_trajectory(target, start, maxAcc=maxAcc)

        self.assertEqual(profiles, [(1.0, -maxAcc), (1.00, 0.), (1.0, maxAcc)])
        self.assertEqual(final_state(start, profiles), target)

        # Down up
        start = State(-2.0)
        target = State(0.0)
        profiles = optimal_trajectory(target, start, maxAcc=maxAcc)

        self.assertEqual(profiles, [(1.0, maxAcc), (1.0, 0.0), (1.0, -maxAcc)])
        self.assertEqual(final_state(start, profiles), target)

        # Down down up
        start = State(-2.0)
        target = State(-4.0)
        profiles = optimal_trajectory(target, start, maxAcc=maxAcc)

        self.assertEqual(profiles, [(1.0, -maxAcc), (1.0, 0.), (1.0, maxAcc)])
        self.assertEqual(final_state(start, profiles), target)

    def test_right_place_but_not_the_right_speed(self):
        maxAcc = 1.0
        magic = 2 ** .5 / 2
        start = State(10.0)
        target = State(10.0, 1.0)
        profiles = optimal_trajectory(target, start, maxAcc=maxAcc)

        self.assertEqual(profiles, [(magic, -maxAcc), (1.0 + magic, maxAcc)])
        assert_allclose(final_state(start, profiles), target)

    def test_right_velocity_but_not_the_right_position(self):
        maxAcc = 1.0
        start = State(10.0, -1.0)
        target = State(11.0, -1.0)
        profiles = optimal_trajectory(target, start, maxAcc=maxAcc)

        self.assertEqual(profiles, [(2.0, maxAcc), (1.0, 0.0), (2.0, -maxAcc)])
        self.assertEqual(final_state(start, profiles), target)

    def test_we_can_cruise_for_some_time(self):
        start = State(0.0)
        target = State(10.0)
        maxSpeed = 2.0
        maxAcc = 1.0
        profiles = optimal_trajectory(target, start, maxSpeed=maxSpeed, maxAcc=maxAcc)

        self.assertEqual(profiles, [(2.0, maxAcc), (3.0, 0.0), (2.0, -maxAcc)])
        self.assertEqual(final_state(start, profiles), target)


if __name__ == '__main__':
    unittest.main()
