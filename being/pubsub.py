"""Publish / subscribe."""
from typing import Iterable, Callable


class PubSub:

    """Publish / subscribe."""

    def __init__(self, events: Iterable):
        """
        Args:
            events: Supported events.
        """
        # Todo: Final args? defaultdict?
        self.subscribers = {evt: set() for evt in events}

    def subscribe(self, event, callback: Callable):
        """Subscribe callback to event."""
        self.subscribers[event].add(callback)

    def unsubscribe(self, event, callback: Callable):
        """Unsubscribe callback from event."""
        self.subscribers[event].remove(callback)

    def publish(self, event, *args, **kwargs):
        """Publish event."""
        for func in self.subscribers[event]:
            func(*args, **kwargs)

    def __str__(self):
        return '%s(events: %s)' % (type(self).__name__, list(self.subscribers))
