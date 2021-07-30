import unittest

import numpy as np
from numpy.testing import assert_almost_equal, assert_equal
from scipy.interpolate import BPoly

from being.spline import (
    build_ppoly,
    ppoly_coefficients_at,
    ppoly_insert,
    smoothing_spline,
    spline_coefficients,
)


class TestBuildSpline(unittest.TestCase):
    def test_simple_acceleration_segment(self):
        spline = build_ppoly([0.5, 0.0, -0.5], [0.0, 1.0, 2.0, 3.0])

        self.assertEqual(spline(0.0), 0.0)
        self.assertEqual(spline(0.0, nu=1), 0.0)
        self.assertEqual(spline(3.0), 1.0)
        self.assertEqual(spline(3.0, nu=1), 0.0)

    def test_spline_follows_initial_conditions(self):
        x0 = 1.234
        v0 = 2.345
        spline = build_ppoly([0.5, 0.0, -0.5], [0.0, 1.0, 2.0, 3.0], x0=x0, v0=v0)

        self.assertEqual(spline(0.0, nu=0), x0)
        self.assertEqual(spline(0.0, nu=1), v0)


class TestSmoothingSpline(unittest.TestCase):
    def test_spline_follows_linear_data(self):
        x = np.linspace(0.0, 10.0)
        y = np.linspace(1.0, -1.0)
        spline = smoothing_spline(x, y)

        assert_almost_equal(spline(x), y)

    def test_spline_follows_multivariate_linear_data(self):
        x = np.linspace(0.0, 10.0)
        pts = np.stack([
            np.linspace(0.0, 1.0),
            np.linspace(1.0, 0.0),
        ]).T
        spline = smoothing_spline(x, pts)

        assert_almost_equal(spline(x), pts)


class TestHelpers(unittest.TestCase):
    def test_spline_coefficients(self):
        spline = build_ppoly([1, 0, -1], [0, 1, 3, 4])

        with self.assertRaises(ValueError):
            spline_coefficients(spline, -1)

        assert_equal(spline_coefficients(spline, 0), [ 0.5, 0.0, 0.0])
        assert_equal(spline_coefficients(spline, 1), [ 0.0, 1.0, 0.5])
        assert_equal(spline_coefficients(spline, 2), [-0.5, 1.0, 2.5])

        with self.assertRaises(ValueError):
            spline_coefficients(spline, 3)

    def test_ppoly_coefficients_at(self):
        spline = build_ppoly([1, 0, -1], [0.0, 1.0, 3.0, 4.0])

        assert_equal(ppoly_coefficients_at(spline, 0.0), spline_coefficients(spline, 0))
        assert_equal(ppoly_coefficients_at(spline, 1.0), spline_coefficients(spline, 1))
        assert_equal(ppoly_coefficients_at(spline, 3.0), spline_coefficients(spline, 2))


class TestPPolyKnotInsertion(unittest.TestCase):
    def assert_splines_equal(self, a, b):
        self.assertIs(type(a), type(b))
        assert_equal(a.x, b.x)
        assert_equal(a.c, b.c)
        self.assertEqual(a.extrapolate, b.extrapolate)
        self.assertEqual(a.axis, b.axis)

    def test_duplicate_knots_get_not_inserted(self):
        a = build_ppoly([1, 0, -1], [0, 1, 3, 4])
        b = ppoly_insert(0.0, a)

        self.assert_splines_equal(a, b)

    def test_only_ppoly_can_get_inserted_to(self):
        not_a_ppoly = BPoly(np.zeros((4, 1)), [0, 1])

        with self.assertRaises(ValueError):
            ppoly_insert(not_a_ppoly, 1234)

    def test_prepending_knot(self):
        orig = build_ppoly([1, 0, -1], [0, 1, 3, 4], extrapolate=False)
        spline = ppoly_insert(-1.0, orig)

        assert_equal(spline.x, np.r_[-1.0, orig.x])
        assert_equal(spline.c[:, 1:], orig.c)

    def test_insertin_knot(self):
        # Inserting in segment 0
        orig = build_ppoly([1, 0, -1], [0, 1, 3, 4], extrapolate=False)
        spline = ppoly_insert(0.5, orig)

        assert_equal(spline.x, [0, 0.5, 1, 3, 4])
        assert_equal(spline.c[:, :1], orig.c[:, :1])
        assert_equal(spline.c[:, 2:], orig.c[:, 1:])

        # Inserting in segment 1
        orig = build_ppoly([1, 0, -1], [0, 1, 3, 4], extrapolate=False)
        spline = ppoly_insert(1.5, orig)

        assert_equal(spline.x, [0, 1, 1.5, 3, 4])
        assert_equal(spline.c[:, :2], orig.c[:, :2])
        assert_equal(spline.c[:, 3:], orig.c[:, 2:])

        # Inserting in segment 2
        orig = build_ppoly([1, 0, -1], [0, 1, 3, 4], extrapolate=False)
        spline = ppoly_insert(3.5, orig)

        assert_equal(spline.x, [0, 1, 3, 3.5, 4])
        assert_equal(spline.c[:, :3], orig.c[:, :3])
        assert_equal(spline.c[:, 4:], orig.c[:, 3:])

    def test_appending_knot(self):
        orig = build_ppoly([1, 0, -1], [0, 1, 3, 4], extrapolate=False)
        spline = ppoly_insert(6.0, orig)

        assert_equal(spline.x, np.r_[orig.x, 6.0])
        assert_equal(spline.c[:, :-1], orig.c)


if __name__ == '__main__':
    unittest.main()
