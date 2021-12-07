"""Miscellaneous helpers."""
import collections
import fnmatch
import glob
import itertools
import os
import random
import weakref
from typing import Any, Iterable, Dict, List, Generator, Callable, Optional


def filter_by_type(sequence: Iterable, type_) -> Generator[Any, None, None]:
    """Filter sequence by type.

    Args:
        sequence: Input sequence to filter.
        type_: Type to filter.

    Returns:
        Filtered types generator.

    Example:
        >>> data = ['Everyone', 1, 'Likes', 2.0, 'Ice', 'Cream']
        ... for txt in filter_by_type(data, str):
        ...     print(txt)
        Everyone
        Likes
        Ice
        Cream
    """
    return (
        ele for ele in sequence
        if isinstance(ele, type_)
    )


def rootname(path: str) -> str:
    """Get 'root' part of path (filename without ext).

    Args:
        path: Input path.

    Returns:
        Root name.

    Example:
        >>> rootname('swedish-chef/chocolate-moose.txt')
        'chocolate-moose'
    """
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
    """Update dictionary recursively in-place.

    Args:
        dct: Dictionary to update.
        other: Other dict to go through.
        default_factory: Default factory for intermediate dicts.

    Returns:
        Mutated input dictionary (for recursive calls).

    Example:
        >>> kermit = {'type': 'Frog', 'skin': {'type': 'Skin', 'color': 'green',}}
        ... update_dict_recursively(kermit, {'skin': {'color': 'blue'}})
        ... print(kermit['skin']['color'])
        blue
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

    Args:
        first: First dict to copy and update.
        *others: All the other dicts.

    Returns:
        Updated dict.

    Example:
        >>> merge_dicts({'name': 'Sid'}, {'item': 'cookie'}, {'mood': 'happy'})
        {'name': 'Sid', 'item': 'cookie', 'mood': 'happy'}
    """
    merged = first.copy()
    for dct in others:
        merged.update(dct)

    return merged


class SingleInstanceCache:

    """Aka. almost a Singleton but not quite.

    Use :meth:`SingleInstanceCache.single_instance_setdefault` to construct and
    / or access single instance for class.

    It is still possible to initialize multiple instances of the class.
    :meth:`__init__` and :meth:`__new__` stay untouched.

    Uses weak references inside. Pay attention to reference counting. Single
    instance cache will not keep cached instances alive. They can get garbage
    collected (problematic if resource release during deconstruction).

    References:
        `So Singletons are bad, then what? <https://softwareengineering.stackexchange.com/questions/40373/so-singletons-are-bad-then-what>`_

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
    def single_instance_initialized(cls) -> bool:
        """Check if cached instance of cls exists."""
        return cls in cls.INSTANCES

    @classmethod
    def single_instance_clear(cls):
        """Clear cached instance of cls."""
        cls.INSTANCES.clear()

    @classmethod
    def single_instance_get(cls) -> Optional[object]:
        """Get cached single instance (if any). None otherwise."""
        ref = cls.INSTANCES.get(cls)
        if ref is None:
            return

        return ref()

    @classmethod
    def single_instance_setdefault(cls, *args, **kwargs):
        """Get cached single instance or create a new one (and add it to the
        cache).

        Args:
            *args: Variable length argument list for :class:`cls`.
            **kwargs: Arbitrary keyword arguments for :class:`cls`.

        Returns:
            :class:`cls` instance.
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

    """Nested dictionary. Supports :class:`tuple` as keys for accessing
    intermediate dictionaries within.

    Example:
        >>> dct = NestedDict()
        ... dct[1, 2, 3] = 'Fozzie'
        ... print(dct)
        NestedDict({1: {2: {3: 'Fozzie'}}})
    """

    # To key error, or not to key error, that is the question. Kind of pointless
    # to have a NestedDict when setting a new nested value always leads to key
    # errors? Also then setdefault works as expected.

    def __init__(self, data=None, default_factory=dict):
        """
        Args:
            data (optional): Initial data object. If non given (default) use
                `default_factory` to create a new one.
            default_factory (optional): Default factory for intermediate
                dictionaries (:class:`dict` by default).
        """
        if data is None:
            data = default_factory()

        self.data: Dict = data
        """Dict-like data container."""

        self.default_factory: Callable = default_factory
        """Default factory for intermediate dictionaries."""

    @staticmethod
    def _as_keys(key) -> tuple:
        """Assure key as tuple."""
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


def toss_coin(probability: float = 0.5) -> bool:
    """Toss a coin.

    Args:
        probability: Success probability. Fifty-fifty by default.

    Returns:
        True or False.
    """
    return random.random() < probability


def unique(iterable: Iterable) -> Generator[Any, None, None]:
    """Iterate over unique elements while preserving order.

    Args:
        iterable: Elements to iterate through.

    Yields:
        Unique elements.
    """
    seen = set()
    for item in iterable:
        if item in seen:
            continue

        seen.add(item)
        yield item
