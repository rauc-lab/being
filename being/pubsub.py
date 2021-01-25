"""Publish / subscribe."""
import collections


class PubSub:

    """Publish / subscribe."""

    def __init__(self, events=None, final=True):
        """Args:
            events: Supported events.
        """
        if events is None:
            events = []

        if final:
            subscribers = dict()
        else:
            subscribers = collections.defaultdict(set)

        for evt in events:
            subscribers[evt] = set()

        self.subscribers = subscribers

    def subscribe(self, event, callback):
        self.subscribers[event].add(callback)

    def unsubscribe(self, event, callback):
        self.subscribers[event].remove(callback)

    def publish(self, event, *args, **kwargs):
        for func in self.subscribers[event]:
            func(*args, **kwargs)

    def __str__(self):
        return '%s(events: %s)' % (type(self).__name__, list(self.subscribers))
