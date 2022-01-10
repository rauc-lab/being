"""Being application core object. Encapsulates the various blocks for a given
program and defines the single cycle.
"""
from typing import List, Optional, Iterable, Iterator

from being.backends import CanBackend
from being.behavior import Behavior
from being.block import Block
from being.can.nmt import OPERATIONAL, PRE_OPERATIONAL
from being.clock import Clock
from being.configuration import CONFIG
from being.connectables import ValueOutput, MessageOutput
from being.execution import execute, block_network_graph
from being.graph import Graph, topological_sort
from being.logging import get_logger
from being.motion_player import MotionPlayer
from being.motors.blocks import MotorBlock
from being.motors.homing import HomingState
from being.pacemaker import Pacemaker
from being.params import Parameter
from being.utils import filter_by_type


def value_outputs(blocks: Iterable[Block]) -> Iterator[ValueOutput]:
    """Collect all value outputs from blocks.

    Args:
        blocks: Blocks to traverse.

    Yields:
        All ValueOutputs.
    """
    for block in blocks:
        yield from filter_by_type(block.outputs, ValueOutput)


def message_outputs(blocks: Iterable[Block]) -> Iterator[MessageOutput]:
    """Collect all message outputs from blocks.

    Args:
        blocks: Blocks to traverse.

    Yields:
        All MessageOutputs.
    """
    for block in blocks:
        yield from filter_by_type(block.outputs, MessageOutput)


class Being:

    """Being core.

    Main application-like object. Container for being components. Block network
    graph and additional components (some back ends, clock, motors...). Defines
    the single cycle which be called repeatedly. Also some helper shortcut
    methods.
    """

    def __init__(self,
            blocks: List[Block],
            clock: Clock,
            pacemaker: Pacemaker,
            network: Optional[CanBackend] = None,
        ):
        """
        Args:
            blocks: Blocks (forming a block network) to execute.
            clock: Being clock instance.
            pacemaker: Pacemaker instance. Thread will not be started but will be used as dummy.
            network: CanBackend instance (if any, DI).
        """
        self.clock: Clock = clock
        """Being clock."""

        self.pacemaker: Pacemaker = pacemaker
        """Being pacemaker."""

        self.network: CanBackend = network
        """Being CAN backend / network."""

        self.graph: Graph = block_network_graph(blocks)
        """Block network for running program."""

        self.execOrder: List[Block] = topological_sort(self.graph)
        """Block execution order."""

        self.logger = get_logger(type(self).__name__)

        self.valueOutputs: List[ValueOutput] = list(value_outputs(self.execOrder))
        """All value outputs."""

        self.messageOutputs: List[MessageOutput] = list(message_outputs(self.execOrder))
        """All message outputs."""

        self.behaviors: List[Behavior] = list(filter_by_type(self.execOrder, Behavior))
        """All behavior blocks."""

        self.motionPlayers: List[MotionPlayer] = list(filter_by_type(self.execOrder, MotionPlayer))
        """All motion player blocks."""

        self.motors: List[MotorBlock] = list(filter_by_type(self.execOrder, MotorBlock))
        """All motor blocks."""

        self.params: List[Parameter] = list(filter_by_type(self.execOrder, Parameter))
        """All parameter blocks."""

    def enable_motors(self):
        """Enable all motor blocks."""
        self.logger.info('enable_motors()')
        for motor in self.motors:
            motor.enable()

    def disable_motors(self):
        """Disable all motor blocks."""
        self.logger.info('disable_motors()')
        for motor in self.motors:
            motor.disable()

    def home_motors(self):
        """Home all motors."""
        self.logger.info('home_motors()')
        for motor in self.motors:
            motor.home()

    def start_behaviors(self):
        """Start all behaviors."""
        for behavior in self.behaviors:
            behavior.play()

    def pause_behaviors(self):
        """Pause all behaviors."""
        for behavior in self.behaviors:
            behavior.pause()

    def single_cycle(self):
        """Execute single being cycle. Network sync, executing block network,
        advancing clock.
        """
        if self.network:
            self.network.send_sync()

        self.pacemaker.tick()

        execute(self.execOrder)

        if self.network:
            self.network.transmit_all_rpdos()

        self.clock.step()
