"""Global being resources exit stack. Dynamically manage resources."""
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
    EXIT_STACK.callback(callback, *args, **kwargs)
