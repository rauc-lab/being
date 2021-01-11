import unittest

import numpy as np
from numpy.testing import assert_equal
from scipy.interpolate import PPoly, CubicSpline

from being.serialization import dumps, loads, FlyByDecoder, EOT


class TestSerialization(unittest.TestCase):
    def assert_splines_equal(self, a, b):
        assert_equal(a.x, a.x)
        assert_equal(a.c, a.c)
        self.assertEqual(a.extrapolate, b.extrapolate)
        self.assertEqual(a.axis, b.axis)

    def test_splines(self):
        spline = CubicSpline([0, 1, 2, 4,], [[0, 1], [1, 0], [2, 1], [3, 0],])
        splineCpy = loads(dumps(spline))

        self.assert_splines_equal(spline, splineCpy)

    def test_numpy_array(self):
        arrays = [
            np.array(1),
            np.array(1.234),
            np.random.random(10),
            np.random.random((10, 2, 3)),
            (255 * np.random.random((10, 2, 3))).astype(np.uint8),
        ]

        for arr in arrays:
            arrCpy = loads(dumps(arr))
            assert_equal(arrCpy, arr)


class TestFlyByDecoder(unittest.TestCase):
    def test_doc_example(self):
        dec = FlyByDecoder()
        snippets = [
            '"Hello, World!"\x041.23',
            '4\x04[1, 2, 3, 4]\x04{"a":',
            ' 1, "b": 2}\x04'
        ]

        self.assertEqual(list(dec.decode_more(snippets[0])), ['Hello, World!'])
        self.assertEqual(list(dec.decode_more(snippets[1])), [1.234, [1, 2, 3, 4]])
        self.assertEqual(list(dec.decode_more(snippets[2])), [{'a': 1, 'b': 2}])


if __name__ == '__main__':
    unittest.main()
