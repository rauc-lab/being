"""Serialization of being objects.

Notation:
  - obj -> Python object
  - dct -> JSON dict / object
"""
from typing import Generator, OrderedDict, Dict
import base64
import collections
import json

import numpy as np
from numpy import ndarray
from scipy.interpolate import PPoly

from being.constants import EOT


def ppoly_to_dict(spline: PPoly) -> OrderedDict:
    """Convert spline to serializable dict representation."""
    # OrderedDict to control key ordering for Python versions before 3.6
    return collections.OrderedDict([
        ('type', 'PPoly'),
        ('extrapolate', spline.extrapolate),
        ('axis', spline.axis),
        ('knots', spline.x.tolist()),
        ('coefficients', spline.c.tolist()),
    ])


def ppoly_from_dict(dct: Dict) -> PPoly:
    """Reconstruct spline from dict representation."""
    c = np.array(dct['coefficients'])
    x = np.array(dct['knots'])
    extrapolate = dct['extrapolate']
    axis = dct['axis']
    return PPoly(c=c, x=x, extrapolate=extrapolate, axis=axis)


def ndarray_to_dict(arr: ndarray) -> Dict:
    """Convert numpy array to serializable dict representation."""
    raw = base64.b64encode(arr.data)
    return {
        'type': 'ndarray',
        'dtype': str(arr.dtype),
        'shape': arr.shape,
        'data': raw.decode(),
    }


def ndarray_from_dict(dct: Dict) -> ndarray:
    """Reconstruct numpy array from dict representation."""
    data = base64.b64decode(dct['data'])
    return np.frombuffer(data, dct['dtype']).reshape(dct['shape'])


def being_object_hook(dct):
    """Being object hook for custom JSON deserialization."""
    if dct.get('type') == 'PPoly':  # Or Spline?
        return ppoly_from_dict(dct)

    if dct.get('type') == 'ndarray':
        return ndarray_from_dict(dct)

    return dct


class BeingEncoder(json.JSONEncoder):

    """Being JSONEncoder object hook for custom JSON deserialization."""

    def default(self, obj):
        if isinstance(obj, PPoly):
            return ppoly_to_dict(obj)

        if isinstance(obj, ndarray):
            return ndarray_to_dict(obj)

        return json.JSONEncoder.default(self, obj)


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
    from scipy.interpolate import CubicSpline

    spline = CubicSpline([0, 1, 2, 4], [1, -1, 1, -1])

    s = dumps(spline)

    other = loads(s)

    snippets = ['"Hello, World!"\x041.23', '4\x04[1, 2, 3, 4]\x04{"a":', ' 1, "b": 2}\x04']
    dec = FlyByDecoder()
    for snippet in snippets:
        for obj in dec.decode_more(snippet):
            print(obj)


if __name__ == '__name__':
    demo()
