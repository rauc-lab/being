"""Awaking a being to live. Main start execution entry point."""
import asyncio
import os
import signal
import time
import warnings

from being.backends import CanBackend
from being.behavior import Behavior
from being.clock import Clock
from being.config import CONFIG
from being.connectables import ValueOutput
from being.execution import execute, block_network_graph
from being.graph import topological_sort
from being.logging import get_logger
from being.motion_player import MotionPlayer
from being.motor import home_motors, _MotorBase
from being.utils import filter_by_type
from being.web.server import init_web_server, run_web_server, init_api
from being.web.web_socket import WebSocket


INTERVAL = CONFIG['General']['INTERVAL']
API_PREFIX = CONFIG['Web']['API_PREFIX']
WEB_SOCKET_ADDRESS = CONFIG['Web']['WEB_SOCKET_ADDRESS']
FILE_LOGGING = bool(CONFIG['Logging']['DIRECTORY'])
LOGGER = get_logger(__name__)


def value_outputs(blocks):
    """Collect all value outputs from blocks."""
    for block in blocks:
        yield from filter_by_type(block.outputs, ValueOutput)


class Being:

    """Being core.

    Main application-like object. Container for being components. Block network
    graph and additional components (some back ends, clock, motors...).
    """

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
        self.valueOutputs = list(value_outputs(self.execOrder))
        self.behaviors = list(filter_by_type(self.execOrder, Behavior))
        if self.network is not None:
            self.execOrder.append(self.network)
            home_motors(self.motors)
            self.network.enable_drives()

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
        self.clock.step()

    def run(self):
        """Run being standalone."""
        running = True

        def exit_gracefully(signum, frame):
            """Exit main loop gracefully."""
            LOGGER.info('Graceful exit (signum %r)', signum)
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


async def send_being_state_to_front_end(being: Being, ws: WebSocket):
    """Keep capturing the current being state and send it to the front-end.
    Taken out from ex being._run_web() because web socket send might block our
    main loop.
    """
    while True:
        await ws.send_json({
            'type': 'output-values',
            'timestamp': being.clock.now(),
            'values': being.capture_value_outputs()
        })
        await asyncio.sleep(2 * INTERVAL)


def awake(*blocks, web=True):
    """Run being block network.

    Args:
        blocks: Some blocks of the network.

    Kwargs:
        web: Run with web server.
    """
    being = Being(blocks)
    try:
        if not web:
            return being.run()

        asyncio.run(_awake_web(being))
    except Exception as err:
        LOGGER.fatal(err, exc_info=True)
        # TODO(atheler): Log and throw anti pattern but we always want to see
        # the error in stderr
        raise


def cancel_all_tasks():
    """Shutdown all async tasks.

    Resrouces:
      https://gist.github.com/nvgoldin/30cea3c04ee0796ebd0489aa62bcf00a
    """
    LOGGER.info('Cancelling all async tasks')
    for task in asyncio.all_tasks():
        task.cancel()


async def _awake_web(being):
    """Run being with web server."""
    app = init_web_server()
    ws = WebSocket()
    app.router.add_get(WEB_SOCKET_ADDRESS, ws.handle_web_socket)
    app.on_shutdown.append(ws.close_all)
    api = init_api(being, ws)
    app.add_subapp(API_PREFIX, api)
    if os.name == 'posix':
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGTERM, cancel_all_tasks)
    else:
        warnings.warn((
            'No signals available on your OS. Can not register SIGTERM'
            ' signal for graceful program exit'
    ))


    try:
        await asyncio.gather(
            being.run_async(),
            send_being_state_to_front_end(being, ws),
            run_web_server(app),
            ws.run_broker(),
        )
    except asyncio.CancelledError:
        pass
