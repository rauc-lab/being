"""Being object. Encapsulates the various blocks for a given programm."""
from typing import List, Optional

from being.backends import CanBackend
from being.behavior import Behavior
from being.block import Block
from being.can.nmt import OPERATIONAL, PRE_OPERATIONAL
from being.clock import Clock
from being.connectables import ValueOutput, MessageOutput
from being.execution import execute, block_network_graph
from being.graph import topological_sort
from being.logging import get_logger
from being.motion_player import MotionPlayer
from being.motors.blocks import MotorBlock
from being.motors.homing import HomingState
from being.utils import filter_by_type


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

    def __init__(self, blocks: List[Block], clock: Clock, network: Optional[CanBackend] = None):
        """Args:
            blocks: Blocks to execute.
            clock: Being clock instance.

        Kwargs:
            network: CanBackend instance (if any).
        """
        self.clock = clock
        self.network = network
        self.graph = block_network_graph(blocks)
        self.execOrder = topological_sort(self.graph)

        self.valueOutputs = list(value_outputs(self.execOrder))
        self.messageOutputs = list(message_outputs(self.execOrder))
        self.behaviors = list(filter_by_type(self.execOrder, Behavior))
        self.motionPlayers = list(filter_by_type(self.execOrder, MotionPlayer))
        self.motors = list(filter_by_type(self.execOrder, MotorBlock))

        self.logger = get_logger('Being')

    def enable_motors(self):
        """Enable all motor blocks."""
        self.logger.info('enable_motors()')
        if self.network:
            self.network.disable_pdo_communication()

        for motor in self.motors:
            motor.enable(timeout=0.100)

        if self.network:
            self.network.enable_pdo_communication()

    def disable_motors(self):
        """Disable all motor blocks."""
        self.logger.info('disable_motors()')
        if self.network:
            self.network.disable_pdo_communication()

        for motor in self.motors:
            motor.disable(timeout=0.100)

        if self.network:
            self.network.enable_pdo_communication()

    def home_motors(self):
        """Home all motors."""
        self.logger.info('home_motors()')
        if self.network:
            self.network.disable_pdo_communication()

        for motor in self.motors:
            motor.home()

    def motor_done_homing(self):
        """Motor changed callback. Used to track if all motors are homed and
        then to set global NMT to OPERATIONAL.

        Reasoning:
            CiA 402 state changes can be slow. Slower motors can lead to perform
            hits which would trigger RPDO timeout errors in the motors which
            have homed before.
            -> Wait until all motors are homed before resuming PDO communication
               (NMT OPERATIONAL).
        """
        if all(mot.homing is HomingState.HOMED for mot in self.motors):
            self.logger.info('All motors homed')
            if self.network:
                self.network.enable_pdo_communication()
        else:
            self.logger.info('Not all motors homed')

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

        execute(self.execOrder)
        self.clock.step()
