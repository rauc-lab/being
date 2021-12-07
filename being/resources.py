"""Dynamic resources handling with a global exit stack.

Example:
    >>> from being.resources import manage_resources, register_resource, add_callback
    ... 
    ... 
    ... class Foo:
    ...     def __enter__(self):
    ...         print('Foo.__enter__()')
    ...         return self
    ... 
    ...     def __exit__(self, exc_type, exc_value, traceback):
    ...         print('Foo.__exit__()')
    ... 
    ... 
    ... class Bar:
    ...     def close(self):
    ...         print('Bar.close()')
    ... 
    ... 
    ... with manage_resources():
    ...     foo = Foo()
    ...     register_resource(foo)  # Calls __enter__ here and __exit__ at the end
    ...     bar = Bar()
    ...     add_callback(bar.close)
    Foo.__enter__()
    Bar.close()
    Foo.__exit__()
"""
import contextlib
import warnings
from typing import ContextManager


EXIT_STACK = contextlib.ExitStack()
"""Global exit stack for all resources in being."""

_ALREADY_REGISTERED = set()
"""Set of already registered memory addresses. We can not keep track of already
registered resources by inspecting EXIT_STACK._exit_callbacks because of method
re-mappings.
"""


def register_resource(resource: ContextManager, duplicates=False):
    """Register context manager in global being exit stack.

    Args:
        resource: Resource to enter into global exit stack.
        duplicates: Skip duplicate entries.
    """
    addr = id(resource)
    if addr in _ALREADY_REGISTERED:
        if duplicates:
            warnings.warn(f'{resource} already in exit stack!')
        else:
            return

    _ALREADY_REGISTERED.add(addr)
    EXIT_STACK.enter_context(resource)


#def release_all_resources():
#    """Release all registered resources."""
#    EXIT_STACK.close()


def manage_resources():
    """Manage all acquired resources in EXIT_STACK."""
    return EXIT_STACK


def add_callback(callback, *args, **kwargs):
    """Add closing callback to EXIT_STACK.

    Args:
        callback: Callback function
        *args: Variable length argument list for callback.
        **kwargs: Arbitrary keyword arguments for callback.
    """
    EXIT_STACK.callback(callback, *args, **kwargs)
