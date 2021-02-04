"""Awaking a being to live. Main start execution entry point."""
import asyncio
import time
from typing import List

from being.backends import CanBackend
from being.config import INTERVAL
from being.execution import ExecOrder, execute
from being.motor import home_motors, Motor
from being.resources import add_callback
from being.server import init_web_server, run_web_server
from being.utils import filter_by_type
from being.graph import topological_sort
from being.execution import block_network_graph


WEB_SOCKET_ADDRESS = '/stream'


def find_all_motors(execOrder: ExecOrder) -> List[Motor]:
    """Find all motor blocks in execOrder.

    Args:
        execOrder: Execution order to execute.
    """
    return filter_by_type(execOrder, Motor)


class Being:

    """Being core."""

    def __init__(self, blocks):
        """Args:
            blocks: Blocks to execute.
        """
        self.graph = block_network_graph(blocks)
        self.execOrder = topological_sort(self.graph)
        self.network = CanBackend.single_instance_get()
        motors = find_all_motors(self.execOrder)
        if motors:
            home_motors(motors)
            self.network.enable_drives()
            add_callback(self.network.disable_drives)

    def single_cycle(self):
        """Execute single cycle of block networks."""
        execute(self.execOrder)
        if self.network is not None:
            self.network.send_sync()

    def run(self):
        """Run being standalone."""
        while True:
            now = time.perf_counter()
            self.single_cycle()
            then = time.perf_counter()
            time.sleep(max(0, INTERVAL - (then - now)))

    async def run_async(self):
        """Run being async."""
        time_func = asyncio.get_running_loop().time
        while True:
            now = time_func()
            self.single_cycle()
            then = time_func()
            await asyncio.sleep(max(0, INTERVAL - (then - now)))


def awake(*blocks, web=True):
    """Run being."""
    being = Being(blocks)
    if not web:
        return being.run()

    asyncio.run( _awake_web(being) )


async def _awake_web(being):
    """Run being with web server."""
    #ws = WebSocket()
    app = init_web_server(being)
    await asyncio.gather(
        being.run_async(),
        run_web_server(app),
    )
