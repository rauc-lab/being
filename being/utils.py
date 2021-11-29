"""Miscellaneous helpers."""
import collections
import fnmatch
import glob
import itertools
import os
import random
import weakref
from typing import Dict, List, Generator


def filter_by_type(sequence, type_) -> Generator[object, None, None]:
    """Filter sequence by type."""
    return (
        ele for ele in sequence
        if isinstance(ele, type_)
    )


def rootname(path: str) -> str:
    """Get 'root' part of path (filename without ext)."""
    filename = os.path.basename(path)
    root, ext = os.path.splitext(filename)
    return root


def collect_files(directory, pattern='*') -> Generator[str, None, None]:
    """Recursively walk over all files in directory. With file extension
    filter."""
    # Give full context
    # pylint: disable=unused-variable
    for dirpath, dirnames, filenames in os.walk(directory):
        for fn in fnmatch.filter(filenames, pattern):
            yield os.path.join(dirpath, fn)


def listdir(directory, fullpath=True) -> List[str]:
    """List directory content. Not recursive. No hidden files. Lexicographically
    sorted.

    Args:
        directory: Directory to traverse.
    """
    filepaths = sorted(glob.iglob(os.path.join(directory, '*')))
    if fullpath:
        return filepaths

    return [
        fp.split(directory + '/', maxsplit=1)[1]
        for fp in filepaths
    ]


def read_file(filepath: str) -> str:
    """Read entire data from file."""
    with open(filepath) as file:
        return file.read()


def write_file(filepath: str, data):
    """Write data to file."""
    with open(filepath, 'w') as file:
        file.write(data)


def update_dict_recursively(dct: dict, other: dict, default_factory: type = None) -> dict:
    """Update dictionary recursively.

    Args:
        dct: Dictionary to update.
        other: Other dict to go through.
        default_factory: Default factory for intermediate dicts.
    """
    if default_factory is None:
        default_factory = type(dct)

    for k, v in other.items():
        if isinstance(v, collections.abc.Mapping):
            dct[k] = update_dict_recursively(dct.get(k, default_factory()), v)
        else:
            dct[k] = v

    return dct


def merge_dicts(first: dict, *others) -> dict:
    """Merge dict together. Pre Python 3.5 compatible. Type of first dict is
    used for the returned one.

    Arguments:
        first: First dict to copy and update.
        *others: All the other dicts.

    Returns:
        Updated dict.
    """
    merged = first.copy()
    for dct in others:
        merged.update(dct)

    return merged


class SingleInstanceCache:

    """Aka. almost a Singleton but not quite.

    Use get_or_construct_instance() constructor to access single instance from
    class. Still possible to initialize multiple instances. __init__() /
    __new__() stay untouched.

    Weak references. Pay attention to reference counting. Single instance cache
    will not keep cached instances alive. They can get garbage collected
    (problematic if resource release during deconstruction).

    Resources:
        https://softwareengineering.stackexchange.com/questions/40373/so-singletons-are-bad-then-what

    Example:
        >>> class Foo(SingleInstanceCache):
        ...     pass
        ... print('Instance of Foo exists?', Foo.single_instance_initialized())
        Instance of Foo exists? False

        >>> Foo()
        ... print('Get single instance of Foo:', Foo.single_instance_get())
        Get single instance of Foo: None

        >>> foo = Foo.single_instance_setdefault()
        ... print('Same ref:', foo is Foo.single_instance_setdefault())
    """

    INSTANCES: Dict[type, weakref.ref] = {}
    """Instances cache."""

    @classmethod
    def single_instance_initialized(cls):
        """Check if cached instance of cls."""
        return cls in cls.INSTANCES

    @classmethod
    def single_instance_clear(cls):
        """Clear cached instance of cls."""
        cls.INSTANCES.clear()

    @classmethod
    def single_instance_get(cls):
        """Get cached single instance (if any). None otherwise."""
        ref = cls.INSTANCES.get(cls)
        if ref is None:
            return

        return ref()

    @classmethod
    def single_instance_setdefault(cls, *args, **kwargs):
        """Get cached single instance or create a new one (and add it to the
        cache).
        """
        self = cls.single_instance_get()
        if self is None:
            self = cls(*args, **kwargs)
            cls.INSTANCES[cls] = weakref.ref(self)

        return self


class IdAware:

    """Class mixin for assigning assigning id numbers to each instance. Each
    type has its own counter / starts from zero.
    """

    ID_COUNTERS = collections.defaultdict(itertools.count)

    def __new__(cls, *args, **kwargs):
        self = object.__new__(cls)
        self.id = next(cls.ID_COUNTERS[cls])
        return self


class NestedDict(collections.abc.MutableMapping):

    """Nested dict.
    Tuples as key path for accessing nested dicts within.
    Similar to defaultdict but NestedDict wraps an existing dict-like object
    within.
    """

    # To key error, or not to key error, that is the question. Kind of pointless
    # to have a NestedDict when setting a new nested value always leads to key
    # errors? Also then setdefault works as expected.

    def __init__(self, data=None, default_factory=dict):
        """Args:
            iterable: Initial data.
            default_factory: Default factory for intermediate dicts.
        """
        if data is None:
            data = default_factory()

        self.data = data
        self.default_factory = default_factory

    @staticmethod
    def _as_keys(key) -> tuple:
        """Assure tuple key path."""
        if isinstance(key, tuple):
            return key

        return (key,)

    def __setitem__(self, key, value):
        d = self.data
        *path, last = self._as_keys(key)
        for k in path:
            #d = d[k]
            d = d.setdefault(k, self.default_factory())

        d[last] = value

    def __getitem__(self, key):
        d = self.data
        for k in self._as_keys(key):
            #d = d[k]
            d = d.setdefault(k, self.default_factory())

        return d

    def __delitem__(self, key):
        d = self.data
        *path, last = self._as_keys(key)
        for k in path:
            d = d[k]

        del d[last]

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __repr__(self):
        return f'{type(self).__name__}({self.data!r})'

    def get(self, key, default=None):
        d = self.data
        for k in self._as_keys(key):
            if k not in d:
                return default

            d = d[k]

        return d

    def setdefault(self, key, default=None):
        d = self.data
        *path, last = self._as_keys(key)
        for k in path:
            d = d.setdefault(k, self.default_factory())

        return d.setdefault(last, default)


def toss_coin(probability: float = .5) -> bool:
    """Toss a coin."""
    return random.random() < probability


def unique(iterable):
    """Iterate over unique elements while preserving order."""
    seen = set()
    for item in iterable:
        if item in seen:
            continue

        seen.add(item)
        yield item
