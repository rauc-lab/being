"""Awaking a being to live. Main start execution entry point."""
import asyncio
import time

from being.backends import CanBackend
from being.clock import Clock
from being.config import INTERVAL
from being.connectables import ValueOutput
from being.execution import execute, block_network_graph
from being.graph import topological_sort
from being.motion_player import MotionPlayer
from being.motor import home_motors, _MotorBase
from being.server import WEB_SOCKET_ADDRESS, init_web_server, run_web_server
from being.utils import filter_by_type
from being.web_socket import WebSocket


def value_outputs(blocks):
    """Collect all value outputs from blocks."""
    for block in blocks:
        yield from filter_by_type(block.outputs, ValueOutput)


class Being:

    """Being core."""

    def __init__(self, blocks):
        """Args:
            blocks: Blocks to execute.
        """
        self.graph = block_network_graph(blocks)
        self.execOrder = topological_sort(self.graph)
        self.network = CanBackend.single_instance_get()
        self.motors = list(filter_by_type(self.execOrder, _MotorBase))
        self.motionPlayers = list(filter_by_type(self.execOrder, MotionPlayer))
        self.clock = Clock.single_instance_setdefault()
        if self.network:
            home_motors(self.motors)
            self.network.enable_drives()

        self.valueOutputs = list(value_outputs(self.execOrder))

    def capture_value_outputs(self):
        """Capture current values of all value outputs."""
        return [
            out.value
            for out in self.valueOutputs
        ]

    def single_cycle(self):
        """Execute single cycle of block networks."""
        execute(self.execOrder)
        if self.network is not None:
            self.network.send_sync()

        self.clock.step()

    def run(self):
        """Run being standalone."""
        while True:
            now = time.perf_counter()
            self.single_cycle()
            then = time.perf_counter()
            time.sleep(max(0, INTERVAL - (then - now)))


def awake(*blocks, web=True):
    """Run being block network.

    Args:
        blocks: Some blocks of the network.

    Kwargs:
        web: Run with web server.
    """
    being = Being(blocks)
    if not web:
        return being.run()

    asyncio.run( _awake_web(being) )


async def _awake_web(being):
    """Run being with web server."""
    ws = WebSocket(WEB_SOCKET_ADDRESS)
    app = init_web_server(being=being)
    app.router.add_get(WEB_SOCKET_ADDRESS, ws.handle_web_socket)


    async def run_async():
        """Run being async."""
        time_func = asyncio.get_running_loop().time
        while True:
            now = time_func()
            being.single_cycle()
            await ws.send_json({
                'type': 'output-values',
                'timestamp': being.clock.now(),
                'values': being.capture_value_outputs()
            })
            then = time_func()
            await asyncio.sleep(max(0, INTERVAL - (then - now)))


    await asyncio.gather(
        #being.run_async(),
        run_async(),
        run_web_server(app),
    )
