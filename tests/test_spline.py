import unittest

import numpy as np
from numpy.testing import assert_almost_equal

from being.spline import build_spline, smoothing_spline


class TestBuildSpline(unittest.TestCase):
    def test_simple_acceleration_segment(self):
        spline = build_spline([.5, 0., -.5], [0., 1., 2., 3.])

        self.assertEqual(spline(0.), 0.)
        self.assertEqual(spline(0., nu=1), 0.)
        self.assertEqual(spline(3.), 1.)
        self.assertEqual(spline(3., nu=1), 0.)

    def test_spline_follows_initial_conditions(self):
        x0 = 1.234
        v0 = 2.345
        spline = build_spline([.5, 0., -.5], [0., 1., 2., 3.], x0=x0, v0=v0)

        self.assertEqual(spline(0., nu=0), x0)
        self.assertEqual(spline(0., nu=1), v0)


class TestSmoothingSpline(unittest.TestCase):
    def test_spline_follows_linear_data(self):
        x = np.linspace(0., 10.)
        y = np.linspace(1., -1.)
        spline = smoothing_spline(x, y)

        assert_almost_equal(spline(x), y)

    def test_spline_follows_multivariate_linear_data(self):
        x = np.linspace(0., 10.)
        pts = np.stack([
            np.linspace(0., 1.),
            np.linspace(1., 0.),
        ]).T
        spline = smoothing_spline(x, pts)

        assert_almost_equal(spline(x), pts)


if __name__ == '__main__':
    unittest.main()
