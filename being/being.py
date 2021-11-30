"""Being object. Encapsulates the various blocks for a given program."""
from typing import List, Optional

from being.backends import CanBackend
from being.behavior import Behavior
from being.block import Block
from being.can.nmt import OPERATIONAL, PRE_OPERATIONAL
from being.clock import Clock
from being.configuration import CONFIG
from being.connectables import ValueOutput, MessageOutput
from being.execution import execute, block_network_graph
from being.graph import topological_sort
from being.logging import get_logger
from being.motion_player import MotionPlayer
from being.motors.blocks import MotorBlock
from being.motors.homing import HomingState
from being.pacemaker import Pacemaker
from being.params import Parameter
from being.utils import filter_by_type


INTERVAL = CONFIG['General']['INTERVAL']


def value_outputs(blocks):
    """Collect all value outputs from blocks."""
    for block in blocks:
        yield from filter_by_type(block.outputs, ValueOutput)


def message_outputs(blocks):
    """Collect all message outputs from blocks."""
    for block in blocks:
        yield from filter_by_type(block.outputs, MessageOutput)


class Being:

    """Being core.

    Main application-like object. Container for being components. Block network
    graph and additional components (some back ends, clock, motors...).
    """

    def __init__(self,
            blocks: List[Block],
            clock: Clock,
            pacemaker: Pacemaker,
            network: Optional[CanBackend] = None,
        ):
        """Args:
            blocks: Blocks to execute.
            clock: Being clock instance.
            pacemaker: Pacemaker thread (will not be started, used as dummy).

        Kwargs:
            network: CanBackend instance (if any).
            usePacemaker: If to use a pacemaker thread (if CanBackend network).
        """
        self.clock = clock
        self.pacemaker = pacemaker
        self.network = network
        self.graph = block_network_graph(blocks)
        self.execOrder = topological_sort(self.graph)

        self.logger = get_logger('Being')

        self.valueOutputs = list(value_outputs(self.execOrder))
        self.messageOutputs = list(message_outputs(self.execOrder))
        self.behaviors = list(filter_by_type(self.execOrder, Behavior))
        self.motionPlayers = list(filter_by_type(self.execOrder, MotionPlayer))
        self.motors = list(filter_by_type(self.execOrder, MotorBlock))
        self.params = list(filter_by_type(self.execOrder, Parameter))

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
        """Execute single cycle of block networks."""
        if self.network:
            self.network.send_sync()

        self.pacemaker.tick()

        execute(self.execOrder)

        if self.network:
            self.network.transmit_all_rpdos()

        self.clock.step()
