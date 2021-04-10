"""Global being resources exit stack. Dynamically manage resources."""
import contextlib
import warnings
from typing import ContextManager


EXIT_STACK = contextlib.ExitStack()
"""Global exit stack for all resources in being."""


def register_resource(resource: ContextManager, duplicates=False):
    """Register context manager in global being exit stack.

    Args:
        resource: Resource to enter into global exit stack.

    Kwargs:
        duplicates: Skip duplicate entries.
    """
    if resource in EXIT_STACK._exit_callbacks:
        warnings.warn(f'{resource} already in exit stack!')
        if not duplicates:
            return

    EXIT_STACK.enter_context(resource)


#def release_all_resources():
#    """Release all registered resources."""
#    EXIT_STACK.close()


def manage_resources():
    """Manage all acquired resources in EXIT_STACK."""
    return EXIT_STACK


def add_callback(callback, *args, **kwargs):
    EXIT_STACK.callback(callback, *args, **kwargs)
