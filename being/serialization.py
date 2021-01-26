"""Serialization of being objects.

Notation:
  - obj -> Python object
  - dct -> JSON dict / object
"""
import base64
import json
from collections import OrderedDict
from typing import Generator, Dict

import numpy as np
from numpy import ndarray
from scipy.interpolate import PPoly

from being.constants import EOT


NAMED_TUPLE_LOOKUP: Dict[str, type] = {}
"""Named tuples type lookup."""

ENUM_LOOKUP: Dict[str, type] = {}
"""Enum type lookup."""


def register_named_tuple(namedTupleType: type):
    """Register namedtuple type for serialization / deserialization."""
    if 'type' in namedTupleType._fields:
        raise ValueError((
            "'type' can not be used as field. Already used as JSON message"
            " type. Pick something else!"
        ))

    NAMED_TUPLE_LOOKUP[namedTupleType.__name__] = namedTupleType


def register_enum(enum: type):
    """Register enum for serialization / deserialization."""
    ENUM_LOOKUP[enum.__name__] = enum


def ppoly_to_dict(spline: PPoly) -> OrderedDict:
    """Convert spline to serializable dict representation."""
    # OrderedDict to control key ordering for Python versions before 3.6
    return OrderedDict([
        ('type', 'PPoly'),
        ('extrapolate', spline.extrapolate),
        ('axis', spline.axis),
        ('knots', spline.x.tolist()),
        ('coefficients', spline.c.tolist()),
    ])


def ppoly_from_dict(dct: dict) -> PPoly:
    """Reconstruct spline from dict representation."""
    c = np.array(dct['coefficients'])
    x = np.array(dct['knots'])
    extrapolate = dct['extrapolate']
    axis = dct['axis']
    return PPoly(c=c, x=x, extrapolate=extrapolate, axis=axis)


def ndarray_to_dict(arr: ndarray) -> OrderedDict:
    """Convert numpy array to serializable dict representation."""
    raw = base64.b64encode(arr.data)
    return OrderedDict([
        ('type', 'ndarray'),
        ('dtype', str(arr.dtype)),
        ('shape', arr.shape),
        ('data', raw.decode()),
    ])


def ndarray_from_dict(dct: dict) -> ndarray:
    """Reconstruct numpy array from dict representation."""
    data = base64.b64decode(dct['data'])
    return np.frombuffer(data, dct['dtype']).reshape(dct['shape'])


def enum_to_dict(obj) -> OrderedDict:
    """Convert enum instance to dct representation."""
    return OrderedDict([
        ('type', type(obj).__name__),
        ('value', obj.value),
    ])


def enum_from_dict(dct: dict):
    """Reconstruct enum instance from dict representation."""
    msgType = dct.get('type')
    if msgType not in ENUM_LOOKUP:
        raise RuntimeError(f'Do not know how to deserialize enum {msgType!r}!')

    enumType = ENUM_LOOKUP[dct['type']]
    return enumType(dct['value'])


def named_tuple_as_dict(obj) -> OrderedDict:
    """Convert named tuple instance to dict representation. Named tuple type has
    to be registered with register_named_tuple().
    """
    dct = OrderedDict([
        ('type', type(obj).__name__),
    ])
    dct.update(**obj._asdict())
    return dct


def named_tuple_from_dict(dct: dict):
    """Resolve namedtuple from dict representation."""
    dct = dct.copy()
    msgType = dct.pop('type')
    if msgType not in NAMED_TUPLE_LOOKUP:
        msg = f'Do not know type of named tuple {msgType!r}!'
        raise RuntimeError(msg)

    type_ = NAMED_TUPLE_LOOKUP[msgType]
    kwargs = type_._field_defaults.copy()
    kwargs.update(**dct)
    return type_(**kwargs)


def being_object_hook(dct):
    """Being object hook for custom JSON deserialization."""
    msgType = dct.get('type')
    if msgType == 'PPoly':
        return ppoly_from_dict(dct)

    if msgType == 'ndarray':
        return ndarray_from_dict(dct)

    if msgType in ENUM_LOOKUP:
        return enum_from_dict(dct)

    if msgType in NAMED_TUPLE_LOOKUP:
        return named_tuple_from_dict(dct)

    return dct


class BeingEncoder(json.JSONEncoder):

    """Being JSONEncoder object hook for custom JSON serialization."""

    def iterencode(self, o, _one_shot=False):
        objType = type(o)
        if objType in NAMED_TUPLE_LOOKUP.values():
            o = named_tuple_as_dict(o)

        yield from super().iterencode(o, _one_shot)

    def default(self, o):
        if isinstance(o, PPoly):
            return ppoly_to_dict(o)

        if isinstance(o, ndarray):
            return ndarray_to_dict(o)

        objType = type(o)
        if objType in ENUM_LOOKUP.values():
            return enum_to_dict(o)

        return json.JSONEncoder.default(self, o)


def dumps(obj, *args, **kwargs):
    """Serialize being object to JSON string."""
    return json.dumps(obj, cls=BeingEncoder, *args, **kwargs)


def loads(string):
    """Deserialize being object from JSON string."""
    return json.loads(string, object_hook=being_object_hook)


class FlyByDecoder:

    """Continuously decode objects from partial messages.

    Usage:
        >>> snippets = ['"Hello, World!"\x041.23', '4\x04[1, 2, 3, 4]\x04{"a":', ' 1, "b": 2}\x04']
        ... dec = FlyByDecoder()
        ... for snippet in snippets:
        ...     for obj in dec.decode_more(snippet):
        ...         print(obj)
        Hello, World!
        1.234
        [1, 2, 3, 4]
        {'a': 1, 'b': 2}
    """

    def __init__(self, term: str = EOT):
        """Kwargs:
            term: Termination character.
        """
        self.term = term
        self.incomplete = ''

    def decode_more(self, new: str) -> Generator:
        """Try to decode more objects."""
        self.incomplete += new
        while self.term in self.incomplete:
            complete, self.incomplete = self.incomplete.split(self.term, maxsplit=1)
            yield loads(complete)


def demo():
    """Some serialization and deserialization demo."""
    from scipy.interpolate import CubicSpline

    spline = CubicSpline([0, 1, 2, 4], [1, -1, 1, -1])
    other = loads(dumps(spline))
    print(spline == other)

    snippets = ['"Hello, World!"\x041.23', '4\x04[1, 2, 3, 4]\x04{"a":', ' 1, "b": 2}\x04']
    dec = FlyByDecoder()
    for snippet in snippets:
        for obj in dec.decode_more(snippet):
            print(obj)


if __name__ == '__name__':
    demo()
