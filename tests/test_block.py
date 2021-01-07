"""Test Block class."""
import unittest

from being.block import fetch_output, fetch_input
from being.block import Block as _Block
from being.connectables import IncompatibleConnection, ValueOutput, ValueInput


class Block(_Block):
    def __init__(self, nInputs=0, nOutputs=0):
        super().__init__()
        for _ in range(nInputs):
            self.inputs.append(ValueInput(owner=self))

        for _ in range(nOutputs):
            self.outputs.append(ValueOutput(owner=self))


class TestPipeingOperator(unittest.TestCase):
    def assert_is_connected(self, a, b):
        """Assert that a is connected with b (directional)."""
        output = fetch_output(a)
        input_ = fetch_input(b)
        self.assertIs(output, input_.incomingConnection)
        self.assertIn(input_, output.outgoingConnections)

    def test_pipeing_between_blocks(self):
        # __or__(block, block), no output, no input
        with self.assertRaises(AttributeError):
            Block() | Block()

        # __or__(block, block), no input
        with self.assertRaises(AttributeError):
            Block(0, 1) | Block()

        # __or__(block, block), no output
        with self.assertRaises(AttributeError):
            Block() | Block(1, 0)

        # __or__(block, block)
        a = Block(0, 1)
        b = Block(1, 0)
        self.assertIs(a | b, b)
        self.assert_is_connected(a, b)

    def test_pipeing_between_blocks_and_connections(self):
        # __or__(block, input)
        a = Block(1, 1)
        b = Block(1, 1)
        self.assertIs(a | b.input, b)
        self.assert_is_connected(a, b)

        # __or__(block, output)
        with self.assertRaises(TypeError):
            Block(1, 1) | Block(1, 1).output

        # __ror__(input, block)
        with self.assertRaises(TypeError):
            Block(1, 1).input | Block(1, 1)

        # __ror__(output, block)
        a = Block(1, 1)
        b = Block(1, 1)
        self.assertIs(a.output | b, b)
        self.assert_is_connected(a, b)


class TestMixOperator(unittest.TestCase):
    def assert_is_connected(self, a, b):
        """Assert that a is connected with b (directional)."""
        output = fetch_output(a)
        input_ = fetch_input(b)
        self.assertIs(output, input_.incomingConnection)
        self.assertIn(input_, output.outgoingConnections)


if __name__ == '__main__':
    unittest.main()
