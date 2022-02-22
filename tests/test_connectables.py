"""Test various connection types. Result of multiple development iterations
therefore some duplicated tests.
"""
import unittest

from being.connectables import (
    IncompatibleConnection,
    InputAlreadyConnected,
    InputBase,
    MessageInput,
    MessageOutput,
    OutputBase,
    ValueInput,
    ValueOutput,
    are_connected,
)


class TestConnections(unittest.TestCase):

    """Helper functions for connection testing."""

    def assert_connected(self, *connectables):
        """Assert that each pair of connectables is connected to each other."""
        for con in connectables:
            self.assertTrue(con.connected)

        self.assertTrue(are_connected(*connectables))

    def assert_not_connected(self, *connectables):
        """Assert that each pair of connectables is NOT connected to each
        other.
        """
        for con in connectables:
            self.assertFalse(con.connected)

        self.assertFalse(are_connected(*connectables))


class TestConnectables(TestConnections):
    def test_connect_and_disconnect(self):
        src = OutputBase()
        dst = InputBase()

        self.assert_not_connected(src, dst)

        src.connect(dst)

        self.assert_connected(src, dst)

        src.disconnect(dst)

        self.assert_not_connected(src, dst)

        # And reverse direction
        dst.connect(src)

        self.assert_connected(src, dst)

    def test_incompatible_connections(self):
        with self.assertRaises(IncompatibleConnection):
            InputBase().connect(InputBase())

        with self.assertRaises(IncompatibleConnection):
            OutputBase().connect(OutputBase())

    def test_one_to_many_connections(self):
        src = OutputBase()
        destinatons = [
            InputBase(),
            InputBase(),
            InputBase(),
        ]

        for dst in destinatons:
            src.connect(dst)

        for dst in destinatons:
            self.assert_connected(src, dst)

    def test_input_already_connected(self):
        input_ = InputBase()
        input_.connect(OutputBase())

        with self.assertRaises(InputAlreadyConnected):
            input_.connect(OutputBase())


class TestValueConnections(TestConnections):
    def test_output_value_access(self):
        output = ValueOutput(value='nothingSet')

        self.assertEqual(output.value, 'nothingSet')
        self.assertEqual(output.get_value(), 'nothingSet')

        output.set_value(42)

        self.assertEqual(output.value, 42)
        self.assertEqual(output.get_value(), 42)

        output.value = 666

        self.assertEqual(output.value, 666)
        self.assertEqual(output.get_value(), 666)

    def test_input_value_access(self):
        input_ = ValueInput(value='nothingSet')

        self.assertEqual(input_.value, 'nothingSet')
        self.assertEqual(input_.get_value(), 'nothingSet')

        input_.set_value(42)

        self.assertEqual(input_.value, 42)
        self.assertEqual(input_.get_value(), 42)

        input_.value = 666

        self.assertEqual(input_.value, 666)
        self.assertEqual(input_.get_value(), 666)

    def test_input_value_when_connected_to_an_output(self):
        src = ValueOutput(value='something')
        dst = ValueInput()
        src.connect(dst)

        self.assertTrue('something' == src.value == dst.value == dst.get_value())

        src.set_value(42)

        self.assertTrue(42 == src.value == dst.value == dst.get_value())

    def test_only_input_to_output_connections(self):
        with self.assertRaises(IncompatibleConnection):
            ValueOutput().connect(ValueOutput())

        with self.assertRaises(IncompatibleConnection):
            ValueInput().connect(ValueInput())


class TestMessageConnections(unittest.TestCase):
    def test_message_flow_from_one_to_many(self):
        src = MessageOutput()
        destinatons = [
            MessageInput(),
            MessageInput(),
            MessageInput(),
        ]

        for dst in destinatons:
            src.connect(dst)

        messages = ['This', 'is', 'it']
        for msg in messages:
            src.send(msg)

        for dst in destinatons:
            self.assertEqual(list(dst.queue), messages)

    def test_receive(self):
        input_ = MessageInput()
        messages = list(range(10))
        for msg in messages:
            input_.push(msg)

        self.assertEqual(len(input_.queue), 10)
        self.assertEqual(list(input_.receive()), messages)
        self.assertEqual(len(input_.queue), 0)

    def test_receive_latest(self):
        input_ = MessageInput()

        self.assertIs(input_.receive_latest(), None)

        messages = list(range(10))
        for msg in messages:
            input_.push(msg)

        self.assertEqual(len(input_.queue), 10)
        self.assertEqual(input_.receive_latest(), 9)
        self.assertEqual(len(input_.queue), 0)


if __name__ == '__main__':
    unittest.main()
