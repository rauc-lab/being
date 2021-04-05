import collections
import fnmatch
import glob
import os
import weakref
from typing import Dict, List, Generator


Filepath = str



def filter_by_type(sequence, type_) -> Generator:
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


def collect_files(directory, pattern='*') -> Generator[Filepath, None, None]:
    """Recursively walk over all files in directory. With file extension
    filter."""
    # Give full context
    # pylint: disable=unused-variable
    for dirpath, dirnames, filenames in os.walk(directory):
        for fn in fnmatch.filter(filenames, pattern):
            yield os.path.join(dirpath, fn)


def listdir(directory, fullpath=True) -> List[Filepath]:
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


def read_file(filepath):
    with open(filepath) as file:
        return file.read()


def write_file(filepath, data):
    with open(filepath, 'w') as file:
        file.write(data)


def any_item(iterable):
    """Pick first element of iterable."""
    return next(iter(iterable))


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

    Usage:
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

    """Assign ascending id numbers to instances."""

    COUNTERS = collections.defaultdict(int)

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls, *args, **kwargs)
        self.id = cls.COUNTERS[cls]
        cls.COUNTERS[cls] += 1
        return self
