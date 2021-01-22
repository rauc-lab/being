import weakref
from typing import Dict, List


def filter_by_type(sequence, type_) -> List:
    """Filter sequence by type."""
    return [
        ele for ele in sequence
        if isinstance(ele, type_)
    ]


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
