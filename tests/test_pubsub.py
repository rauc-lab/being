import enum
import unittest

from being.pubsub import PubSub


class Event(enum.Enum):

    """Some testing event."""

    EVENT = 0
    ANOTHER = 1


class CallCounter:

    """Keeping track of calls and latest args / kwargs."""

    def __init__(self):
        self.nCalls = 0

    def __call__(self, *args, **kwargs):
        self.nCalls += 1
        self.args = args
        self.kwargs = kwargs


class TestPubSub(unittest.TestCase):
    def test_subscribers_receive_notifications(self):
        pubsub = PubSub(Event)
        subscriber = CallCounter()
        pubsub.subscribe(Event.EVENT, subscriber)

        self.assertEqual(subscriber.nCalls, 0)

        pubsub.publish(Event.EVENT)

        self.assertEqual(subscriber.nCalls, 1)

    def test_subscribers_receive_provided_arguments(self):
        pubsub = PubSub(Event)
        subscriber = CallCounter()
        pubsub.subscribe(Event.EVENT, subscriber)
        pubsub.publish(Event.EVENT, 'Hello', thing='world')

        self.assertEqual(subscriber.args, ('Hello', ))
        self.assertEqual(subscriber.kwargs, {'thing': 'world'})

    def test_no_more_notifications_when_unsubscribed(self):
        pubsub = PubSub(Event)
        subscriber = CallCounter()
        pubsub.subscribe(Event.EVENT, subscriber)
        pubsub.unsubscribe(Event.EVENT, subscriber)
        pubsub.publish(Event.EVENT)

        self.assertEqual(subscriber.nCalls, 0)

    def test_multiple_subscribtions_lead_to_single_notificaiton(self):
        pubsub = PubSub(Event)
        subscriber = CallCounter()
        pubsub.subscribe(Event.EVENT, subscriber)
        pubsub.subscribe(Event.EVENT, subscriber)
        pubsub.publish(Event.EVENT)

        self.assertEqual(subscriber.nCalls, 1)

    def test_multiple_subscribers_get_called_idividually(self):
        pubsub = PubSub(Event)
        first = CallCounter()
        second = CallCounter()
        pubsub.subscribe(Event.EVENT, first)
        pubsub.subscribe(Event.EVENT, second)
        pubsub.publish(Event.EVENT)

        self.assertEqual(first.nCalls, 1)
        self.assertEqual(second.nCalls, 1)

    def test_two_event_types_one_by_one(self):
        pubsub = PubSub(Event)
        first = CallCounter()
        second = CallCounter()
        pubsub.subscribe(Event.EVENT, first)
        pubsub.subscribe(Event.ANOTHER, second)

        self.assertEqual(first.nCalls, 0)
        self.assertEqual(second.nCalls, 0)

        pubsub.publish(Event.EVENT)

        self.assertEqual(first.nCalls, 1)
        self.assertEqual(second.nCalls, 0)

        pubsub.publish(Event.ANOTHER)

        self.assertEqual(first.nCalls, 1)
        self.assertEqual(second.nCalls, 1)


if __name__ == '__main__':
    unittest.main()
