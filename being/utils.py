import weakref
from typing import Dict


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
    """

    INSTANCES: Dict[type, weakref.ref] = {}

    @classmethod
    def initialized(cls):
        return cls in cls.INSTANCES

    @classmethod
    def default(cls, *args, **kwargs):
        """Get cached single instance or setdefault it from dache."""
        ref = cls.INSTANCES.get(cls, lambda: None)
        if ref() is not None:
            return ref()

        self = cls(*args, **kwargs)
        cls.INSTANCES[cls] = weakref.ref(self)
        return self
