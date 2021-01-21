"""Block base class.

Some block related helpers."""
import functools
from typing import List, ForwardRef, Generator, Union

from being.connectables import (
    Connection,
    OutputBase,
    ValueOutput,
    MessageOutput,
    InputBase,
    ValueInput,
    MessageInput,
)


Block = ForwardRef('Block')
Inputable = Union[Block, InputBase]
Outputable = Union[Block, OutputBase]
Connections = Generator[Connection, None, None]


# TODO: Move input_connections(), output_connections(), input_neighbors() and
# output_neighbors() to Block methods?
def input_connections(block: Block) -> Connections:
    """Iterate over all incoming connections.

    Args:
        block: Block to inspect.

    Yields:
        tuple: Src -> block input connections.
    """
    for input_ in block.inputs:
        if input_.connected:
            src = input_.incomingConnection
            if src.owner is not block:
                yield src, input_


def output_connections(block: Block) -> Connections:
    """Iterate over all outgoing connections.

    Args:
        block: Block to inspect.

    Yields:
        tuple: Block output -> dst.
    """
    for output in block.outputs:
        for dst in output.outgoingConnections:
            if dst.owner is not block:
                yield output, dst


def collect_connections(block: Block) -> Connections:
    """Get all in- and outgoing connections of a block ((output, input) tuples).
    Exclude loop-around connections (block connected to itself).

    Args:
        block: Block to inspect.

    Yields:
        tuple: Output -> input connections
    """
    yield from input_connections(block)
    yield from output_connections(block)


def input_neighbors(block: Block) -> Connections:
    """Get input neighbors of block.

    Args:
        block: Block to inspect

    Yields:
        Block: ValueInput neighbors / source owners.
    """
    for src, _ in input_connections(block):
        if src.owner:
            yield src.owner


def output_neighbors(block: Block) -> Connections:
    """Get output neighbors of block.

    Args:
        block (Block): Block to inspect

    Yields:
        Block: ValueOutput neighbors / destination owner.
    """
    for _, dst in output_connections(block):
        if dst.owner:
            yield dst.owner


def fetch_input(blockOrInput: Inputable) -> InputBase:
    """Fetch primary input."""
    if isinstance(blockOrInput, Block):
        return blockOrInput.input

    return blockOrInput


def fetch_output(blockOrOutput: Outputable) -> OutputBase:
    """Fetch primary output."""
    if isinstance(blockOrOutput, Block):
        return blockOrOutput.output

    return blockOrOutput


def pipe_operator(left: Outputable, right: Inputable) -> Block:
    """Pipe blocks or connections together. pipe_operator(a, b) is the same as
    a.output.connect(b). Left to right. Return rightmost block for
    concatenation.

    Args:
        left (Block or OutputBase): Left operand.
        right (Block or InputBase): Right operand.

    Returns:
        Block: Owner of incoming connection.
    """
    output = fetch_output(left)
    input_ = fetch_input(right)
    if not isinstance(output, OutputBase)\
        or not isinstance(input_, InputBase):
        raise TypeError('Can not pipe from %s to %s' % (left, right))

    output.connect(input_)
    return input_.owner


class Block:

    """Block base class.

    Child classes have to override the update() method. We leave it as a normal
    method (and not a abstract method) in order for testing. New connections can
    be added with the helper methods:
      - add_value_input()
      - add_message_input()
      - add_value_output()
      - add_message_output()

    These methods also take an additional `name` argument which can be used to
    store the newly created connection as an attribute.

    Attributes:
        inputs: Input connections.
        outputs: Output connections.
    """

    def __init__(self):
        self.inputs: List[InputBase] = []
        self.outputs: List[OutputBase] = []

    @property
    def nInputs(self) -> int:
        """Number of inputs."""
        return len(self.inputs)

    @property
    def nOutputs(self) -> int:
        """Number of outputs."""
        return len(self.outputs)

    @property
    def input(self) -> InputBase:
        """Primary input."""
        if not self.inputs:
            raise AttributeError('%s has no inputs!' % self)

        return self.inputs[0]

    @property
    def output(self) -> OutputBase:
        """Primary output."""
        if not self.outputs:
            raise AttributeError('%s has no outputs!' % self)

        return self.outputs[0]

    def add_value_input(self, name=None):
        """Add new value input to block.

        Kwargs:
            name: Attribute name.
        """
        input_ = ValueInput(owner=self)
        self.inputs.append(input_)
        if name:
            setattr(self, name, input_)

    def add_message_input(self, name=None):
        """Add new message input to block.

        Kwargs:
            name: Attribute name.
        """
        input_ = MessageInput(owner=self)
        self.inputs.append(input_)
        if name:
            setattr(self, name, input_)

    def add_value_output(self, name=None):
        """Add new value output to block.

        Kwargs:
            name: Attribute name.
        """
        output = ValueOutput(owner=self)
        self.outputs.append(output)
        if name:
            setattr(self, name, output)

    def add_message_output(self, name=None):
        """Add new message output to block.

        Kwargs:
            name: Attribute name.
        """
        output = MessageOutput(owner=self)
        self.outputs.append(output)
        if name:
            setattr(self, name, output)

    def update(self):
        """Block's update / run / tick method."""

    def __str__(self):
        infos = []
        if self.nInputs > 0:
            infos.append('%d inputs' % self.nInputs)

        if self.nOutputs > 0:
            infos.append('%d outputs' % self.nOutputs)

        return '%s(%s)' % (type(self).__name__, ', '.join(infos))

    __or__ = pipe_operator

    @functools.wraps(pipe_operator)
    def __ror__(self, output) -> Block:
        # Reverse operands. Maintain order.
        return pipe_operator(output, self)
