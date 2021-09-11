"""Being object. Encapsulates the various blocks for a given program."""
import contextlib
import threading

from typing import List, Optional

from being.backends import CanBackend
from being.behavior import Behavior
from being.block import Block
from being.can.nmt import OPERATIONAL, PRE_OPERATIONAL
from being.clock import Clock
from being.config import CONFIG
from being.connectables import ValueOutput, MessageOutput
from being.execution import execute, block_network_graph
from being.graph import topological_sort
from being.logging import get_logger
from being.motion_player import MotionPlayer
from being.motors.blocks import MotorBlock
from being.motors.homing import HomingState
from being.resources import register_resource
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


class Once:

    """Value changed detector."""

    def __init__(self, initial):
        self.prev = initial

    def changed(self, value):
        if value == self.prev:
            return False

        self.prev = value
        return True


class Pacemaker(contextlib.AbstractContextManager):

    """Pacemaker / watchdog / dead man's switch daemon thread.

    Can step in to trigger PDO transmission / SYNC message if main thread is not
    on time. In order to prevent RPDO timeouts.
    """

    def __init__(self, network: CanBackend, maxWait: float = 1.2 * INTERVAL):
        """Args:
            network: CanBackend network instance to trigger PDO transmits / SYNC
                messages.

        Kwargs:
            maxWait: Maximum wait duration before stepping in.
        """
        self.network = network
        self.maxWait = maxWait
        self.logger = get_logger('Pacemaker')
        self.pulseEvent = threading.Event()
        self.running = False
        self.thread = None
        self.once = Once(initial=True)

    def tick(self):
        """Push the dead man's switch."""
        self.pulseEvent.set()

    def _run(self):
        while self.running:
            if self.pulseEvent.wait(timeout=self.maxWait):
                if self.once.changed(True):
                    self.logger.warning('Off')

            else:
                self.network.transmit_all_rpdos()
                self.network.send_sync()
                if self.once.changed(False):
                    self.logger.warning('On')

            self.pulseEvent.clear()

    def start(self):
        """Start watchdog daemon thread."""
        if self.running:
            raise RuntimeError('Watchdog thread already running!')

        self.logger.info('Starting watchdog thread')
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop watchdog daemon thread."""
        if not self.running:
            raise RuntimeError('No watchdog thread running!')

        self.logger.info('Stopping watchdog thread')
        self.running = False
        self.tick()
        self.thread.join()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()


class Being:

    """Being core.

    Main application-like object. Container for being components. Block network
    graph and additional components (some back ends, clock, motors...).
    """

    def __init__(self,
            blocks: List[Block],
            clock: Clock,
            network: Optional[CanBackend] = None,
            usePacemaker: bool = True,
        ):
        """Args:
            blocks: Blocks to execute.
            clock: Being clock instance.

        Kwargs:
            network: CanBackend instance (if any).
            usePacemaker: If to use a pacemaker thread (if CanBackend network).
        """
        self.clock = clock
        self.network = network
        self.graph = block_network_graph(blocks)
        self.execOrder = topological_sort(self.graph)

        self.logger = get_logger('Being')

        self.valueOutputs = list(value_outputs(self.execOrder))
        self.messageOutputs = list(message_outputs(self.execOrder))
        self.behaviors = list(filter_by_type(self.execOrder, Behavior))
        self.motionPlayers = list(filter_by_type(self.execOrder, MotionPlayer))
        self.motors = list(filter_by_type(self.execOrder, MotorBlock))

        self.pacemaker = Pacemaker(network)
        if usePacemaker and network:
            register_resource(self.pacemaker)

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
