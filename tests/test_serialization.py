import unittest
import enum
from typing import NamedTuple

import numpy as np
from numpy.testing import assert_equal
from scipy.interpolate import PPoly, CubicSpline, BPoly

from being.serialization import (
    ENUM_LOOKUP, EOT, NAMED_TUPLE_LOOKUP, FlyByDecoder, dumps, enum_from_dict,
    enum_to_dict, loads, named_tuple_as_dict, named_tuple_from_dict,
    register_enum, register_named_tuple, _enum_type_qualname,
)


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

    def test_that_we_end_up_with_the_correct_spline_types(self):
        spline = CubicSpline([0, 1, 3, 6], [0, 1, 0, -1])
        ppoly = PPoly(spline.c, spline.x)
        bpoly = BPoly.from_power_basis(spline)

        self.assert_splines_equal(loads(dumps(spline)), ppoly)
        self.assert_splines_equal(loads(dumps(ppoly)), ppoly)
        self.assert_splines_equal(loads(dumps(bpoly)), bpoly)

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

    def test_with_new_named_tuple(self):
        Foo = NamedTuple('Foo', name=str, id=int)
        foo = Foo('Calimero', 42)
        dct = named_tuple_as_dict(foo)

        self.assertEqual(dct, {
            'type': 'Foo',
            'name': 'Calimero',
            'id': 42,
        })

        with self.assertRaises(RuntimeError):
            named_tuple_from_dict(dct)

        register_named_tuple(Foo)


        foo2 = named_tuple_from_dict(dct)

        self.assertEqual(foo, foo2)
        self.assertEqual(foo, loads(dumps(foo)))

        NAMED_TUPLE_LOOKUP.pop('Foo')

    def test_with_enum(self):
        Foo = enum.Enum('Foo', 'FIRST SECOND THIRD')
        foo = Foo.SECOND
        dct = enum_to_dict(foo)

        self.assertEqual(dct, {
            'type': _enum_type_qualname(Foo),
            'members': list(Foo.__members__),
            'value': foo.value,
        })

        with self.assertRaises(RuntimeError):
            enum_from_dict(dct)

        register_enum(Foo)

        foo2 = enum_from_dict(dct)

        self.assertEqual(foo, foo2)
        self.assertEqual(foo, loads(dumps(foo)))

        ENUM_LOOKUP.pop(_enum_type_qualname(Foo))

    def test_a_set_mapps_back_to_itself(self):
        x = {1, 2, 'Hello, world!'}
        y = loads(dumps(x))

        self.assertEqual(x, y)


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
