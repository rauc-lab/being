"""Serialization of being objects."""
# obj -> Python object
# dct -> JSON dict / object
import json
import collections

from scipy.interpolate import PPoly


def being_object_hook(dct):
    if dct.get('type') == 'PPoly':  # Or Spline?
        c = np.array(dct['coefficients'])
        x = np.array(dct['knots'])
        return PPoly(c, x)

    return dct


def dumps(obj, *args, **kwargs):
    """Dumps being object to string."""
    return json.dumps(obj, cls=BeingEncoder, *args, **kwargs)


def loads(string):
    """Loads being object from string."""
    return json.loads(string, object_hook=being_object_hook)


class BeingEncoder(json.JSONEncoder):
    def default(self, obj):
        # OrderedDict to control key ordering for Python versions before 3.6
        if isinstance(obj, PPoly):
            return collections.OrderedDict([
                ('type', 'Spline'),
                ('knots', obj.x.tolist()),
                ('coefficients', obj.c.tolist()),
            ])

        return json.JSONEncoder.default(self, obj)



def demo():
    from scipy.interpolate import CubicSpline

    spline = CubicSpline([0, 1, 2, 4], [1, -1, 1, -1])

    s = dumps(spline)

    other = loads(s)


if __name__ == '__name__':
    demo()
