"""Serialization of being objects.

Supports dynamic named tuples and enums but these types have to be registered
with register_named_tuple() and register_enum().

Notation:
  - obj -> Python object
  - dct -> JSON dict / object

Notes:
  - We use OrderedDict to control key ordering for Python versions before 3.6.
"""
import base64
import json
import logging
from collections import OrderedDict
from enum import EnumMeta
from typing import Generator, Dict

import numpy as np
from numpy import ndarray
from scipy.interpolate import PPoly, BPoly, CubicSpline

from being.block import Block
from being.constants import EOT
from being.curve import Curve
from being.typing import Spline


NAMED_TUPLE_LOOKUP: Dict[str, type] = {}
"""Named tuples type lookup."""

ENUM_LOOKUP: Dict[str, type] = {}
"""Enum type lookup."""

SPLINE_TYPES: Dict[type, type] = {
    CubicSpline: PPoly,
    PPoly: PPoly,
    BPoly: BPoly,
}
"""Supported spline types. CubicSplines get mapped to PPoly."""

SPLINE_LOOKUP: Dict[str, type] = {
    cls.__name__: cls
    for cls in SPLINE_TYPES.values()
}
"""Spline type lookup."""


def register_named_tuple(namedTupleType: type):
    """Register named tuple type for serialization / deserialization."""
    name = namedTupleType.__name__
    if 'type' in namedTupleType._fields:
        raise ValueError(
            "'type' can not be used as field name. Already used as JSON message"
            f" type. Pick something else for named tuple {name!r}!"
        )

    if name in NAMED_TUPLE_LOOKUP:
        raise RuntimeError(f'Named tuple {name!r} is already registered!')

    NAMED_TUPLE_LOOKUP[name] = namedTupleType


def _enum_type_qualname(enumType: EnumMeta) -> str:
    """Quasi qualname for enum types. So to distinguish different enum types
    with the same name in different modules.

    Example:
        >>> import enum
        ...
        ... class Foo(enum.Enum):
        ...     FIRST = 0
        ...     SECOND = 1
        ...
        ... print(_enum_type_qualname(Foo))
        __main__.Foo
    """
    return enumType.__module__ + '.' + enumType.__name__


def register_enum(enumType: EnumMeta):
    """Register enum for serialization / deserialization."""
    name = _enum_type_qualname(enumType)
    if name in ENUM_LOOKUP:
        raise RuntimeError(f'Enum {name!r} is already registered!')

    ENUM_LOOKUP[name] = enumType


def spline_to_dict(spline: Spline) -> OrderedDict:
    """Convert spline to serializable dict representation."""
    cls = type(spline)
    if cls not in SPLINE_TYPES:
        raise ValueError(f'Spline type {cls.__name__} not supported!')

    return OrderedDict([
        ('type', SPLINE_TYPES[cls].__name__),
        ('extrapolate', spline.extrapolate),
        ('axis', spline.axis),
        ('knots', spline.x.tolist()),
        ('coefficients', spline.c.tolist()),
    ])


def spline_from_dict(dct: dict) -> Spline:
    """Reconstruct spline from dict representation."""
    typeName = dct['type']
    if typeName not in SPLINE_LOOKUP:
        raise ValueError(f'Spline type {typeName} not supported!')

    cls = SPLINE_LOOKUP[dct['type']]
    return cls(
        c=dct['coefficients'],
        x=dct['knots'],
        extrapolate=dct['extrapolate'],
        axis=dct['axis'],
    )


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


def enum_to_dict(enum) -> OrderedDict:
    """Convert enum instance to dct representation."""
    enumType = type(enum)
    return OrderedDict([
        ('type', _enum_type_qualname(enumType)),
        ('members', list(enumType.__members__)),
        ('value', enum.value),
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
    """Resolve named tuple from dict representation."""
    dct = dct.copy()
    msgType = dct.pop('type')
    if msgType not in NAMED_TUPLE_LOOKUP:
        raise RuntimeError(f'Do not know type of named tuple {msgType!r}!')

    type_ = NAMED_TUPLE_LOOKUP[msgType]
    kwargs = type_._field_defaults.copy()
    kwargs.update(**dct)
    return type_(**kwargs)


def being_object_hook(dct):
    """Being object hook for custom JSON deserialization."""
    msgType = dct.get('type')
    if msgType in SPLINE_LOOKUP:
        return spline_from_dict(dct)

    if msgType == 'ndarray':
        return ndarray_from_dict(dct)

    if msgType in ENUM_LOOKUP:
        return enum_from_dict(dct)

    if msgType in NAMED_TUPLE_LOOKUP:
        return named_tuple_from_dict(dct)

    if msgType == set.__name__:
        return set(dct['values'])

    if msgType == Curve.__name__:
        return Curve(splines=dct['splines'])

    return dct


class BeingEncoder(json.JSONEncoder):

    """Being JSONEncoder object hook for custom JSON serialization."""

    def iterencode(self, o, _one_shot=False):
        objType = type(o)
        if objType in NAMED_TUPLE_LOOKUP.values():
            o = named_tuple_as_dict(o)

        yield from super().iterencode(o, _one_shot)

    def default(self, o):
        if isinstance(o, tuple(SPLINE_TYPES)):
            return spline_to_dict(o)

        if isinstance(o, ndarray):
            if o.ndim == 0:  # Scalar shape
                return float(o)

            return ndarray_to_dict(o)

        objType = type(o)
        if objType in ENUM_LOOKUP.values():
            return enum_to_dict(o)

        if objType is set:
            return {'type': set.__name__, 'values': list(o)}

        if isinstance(o, Block):
            return o.to_dict()

        if isinstance(o, logging.LogRecord):
            return {
                'type': 'LogRecord',
                'name': o.name,
                #'msg': o.msg,
                #'args': o.args,
                'message': o.msg % o.args,
                'levelname': o.levelname,
                'levelno': o.levelno,
            }

        if isinstance(o, Curve):
            return OrderedDict([
                ('type', type(o).__name__),
                ('splines', o.splines),
            ])

        return json.JSONEncoder.default(self, o)


def dumps(obj, *args, **kwargs):
    """Serialize being object to JSON string."""
    return json.dumps(obj, cls=BeingEncoder, *args, **kwargs)


def loads(string):
    """Deserialize being object from JSON string."""
    return json.loads(string, object_hook=being_object_hook)


class FlyByDecoder:

    """Continuously decode objects from partial messages.

    Example:
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
        """Args:
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
