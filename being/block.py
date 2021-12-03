"""Block base class and some block related helpers.

Todo:
    - Should ``input_connections()``, ``output_connections()``, ``input_neighbors()`` and ``output_neighbors()`` become ``Block`` methods?
"""
from collections import OrderedDict
import functools
import itertools
from typing import List, ForwardRef, Generator, Union, Optional

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
    """Binary or dyadic pipe operator for connecting blocks and/or connections
    with each other. Used by :meth:`being.block.Block.__or__` and
    :meth:`being.block.Block.__ror__.` for the shorthand

    >>> a | b | c  # Instead of a.output.connect(b.input); b.output.connect(c.input)

    This function also works with :class:`being.connectables.OutputBase` and
    :class:`being.connectables.InputBase` instances.

    Args:
        left: Left operand.
        right: Right operand.

    Returns:
        Block: Owner of rightmost incoming connection.
    """
    output = fetch_output(left)
    input_ = fetch_input(right)
    if not isinstance(output, OutputBase)\
        or not isinstance(input_, InputBase):
        raise TypeError('Can not pipe from %s to %s' % (left, right))

    output.connect(input_)
    return input_.owner


class Block:

    """Blocks are the main *building blocks* (pun intended) of a being program.
    They hold there own state and can communicate with each other via *value* or
    *message* connections. Each block has an :meth:`Block.update` method which
    will be called once during execution. This method should be overridden by
    child classes.

    New connections can be added with the helper methods:
      - :meth:`Block.add_value_input`
      - :meth:`Block.add_message_input`
      - :meth:`Block.add_value_output`
      - :meth:`Block.add_message_output`

    These methods also take an additional `name` argument which can be used to
    store the newly created connection as an attribute.

    Example:

        >>> class MyBlock(Block):
        ...     def __init__(self):
        ...         self.add_message_output(name='mouth')
        ... 
        ...     def update(self):
        ...         self.mouth.send('I am alive!')

    Note:
        Not a ABC so that we can use the base class for testing.
    """

    ID_COUNTER = itertools.count()
    """Counter used for id assignment."""

    def __init__(self, name: Optional[str] = None):
        """
        Args:
            name (optional): Block name for UI. Block type name by default.

        .. automethod:: __or__
        .. automethod:: __ror__
        """
        if name is None:
            name = type(self).__name__

        self.name: str = name
        """Block name. Used in user interface to identify block."""

        self.inputs: List[InputBase] = []
        """Input connections."""

        self.outputs: List[OutputBase] = []
        """Output connections."""

        self.id: int = next(self.ID_COUNTER)
        """Ascending block id number. Starting from zero."""

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

    def add_value_input(self, name: Optional[str] = None) -> ValueInput:
        """Add new value input to block.

        Args:
            name: Attribute name.

        Returns:
            Newly created value input.
        """
        input_ = ValueInput(owner=self)
        self.inputs.append(input_)
        if name:
            setattr(self, name, input_)

        return input_

    def add_message_input(self, name: Optional[str] = None) -> MessageInput:
        """Add new message input to block.

        Args:
            name: Attribute name.

        Returns:
            Newly created message input.
        """
        input_ = MessageInput(owner=self)
        self.inputs.append(input_)
        if name:
            setattr(self, name, input_)

        return input_

    def add_value_output(self, name: Optional[str] = None) -> ValueOutput:
        """Add new value output to block.

        Args:
            name: Attribute name.

        Returns:
            Newly created value output.
        """
        output = ValueOutput(owner=self)
        self.outputs.append(output)
        if name:
            setattr(self, name, output)

        return output

    def add_message_output(self, name: Optional[str] = None) -> MessageOutput:
        """Add new message output to block.

        Args:
            name: Attribute name.

        Returns:
            Newly created message output.
        """
        output = MessageOutput(owner=self)
        self.outputs.append(output)
        if name:
            setattr(self, name, output)

        return output

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

    def to_dict(self) -> OrderedDict:
        """Convert block to dictionary representation which can be used for
        dumping as JSON.

        Returns:
            Block's dictionary representation.
        """
        return OrderedDict([
            ('type', 'Block'),
            ('blockType', type(self).__name__),
            ('name', self.name),
            ('id', self.id),
            ('inputNeighbors', [neighbor.id for neighbor in input_neighbors(self)]),
            ('outputNeighbors', [neighbor.id for neighbor in output_neighbors(self)]),
        ])
