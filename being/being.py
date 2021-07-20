"""Being object. Encapsulates the various blocks for a given programm."""
import asyncio
import os
import signal
import time
import warnings
from typing import List, Optional

from being.backends import CanBackend
from being.behavior import Behavior
from being.block import Block
from being.clock import Clock
from being.config import CONFIG
from being.connectables import ValueOutput
from being.execution import execute, block_network_graph
from being.graph import topological_sort
from being.logging import get_logger
from being.motion_player import MotionPlayer
from being.motors import Motor
from being.utils import filter_by_type


INTERVAL = CONFIG['General']['INTERVAL']


def value_outputs(blocks):
    """Collect all value outputs from blocks."""
    for block in blocks:
        yield from filter_by_type(block.outputs, ValueOutput)


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
        self.logger = get_logger('Being')
        self.clock = clock
        self.network = network
        self.graph = block_network_graph(blocks)
        self.execOrder = topological_sort(self.graph)

        self.valueOutputs = list(value_outputs(self.execOrder))
        self.behaviors = list(filter_by_type(self.execOrder, Behavior))
        self.motionPlayers = list(filter_by_type(self.execOrder, MotionPlayer))
        self.motors = list(filter_by_type(self.execOrder, Motor))

    def start_behaviors(self):
        """Start all behaviors."""
        for behavior in self.behaviors:
            behavior.play()

    def pause_behaviors(self):
        """Pause all behaviors."""
        for behavior in self.behaviors:
            behavior.pause()

    def capture_value_outputs(self):
        """Capture current values of all value outputs."""
        return [
            out.value
            for out in self.valueOutputs
        ]

    def single_cycle(self):
        """Execute single cycle of block networks."""
        execute(self.execOrder)
        if self.network:
            self.network.update()

        self.clock.step()

    def run(self):
        """Run being standalone."""
        running = True

        def exit_gracefully(signum, frame):
            """Exit main loop gracefully."""
            self.logger.info('Graceful exit (signum %r)', signum)
            nonlocal running
            running = False

        if os.name == 'posix':
            signal.signal(signal.SIGTERM, exit_gracefully)
        else:
            warnings.warn((
                'No signals available on your OS. Can not register SIGTERM'
                ' signal for graceful program exit'
            ))

        while running:
            now = time.perf_counter()
            self.single_cycle()
            then = time.perf_counter()
            time.sleep(max(0, INTERVAL - (then - now)))

    async def run_async(self):
        """Run being inside async loop."""
        time_func = asyncio.get_running_loop().time
        while True:
            now = time_func()
            self.single_cycle()
            then = time_func()
            await asyncio.sleep(max(0, INTERVAL - (then - now)))


