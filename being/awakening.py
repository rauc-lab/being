"""Awake being to life. Main start execution entry point."""
import asyncio
import os
import signal
import warnings
from typing import Optional

from being.backends import CanBackend
from being.being import Being
from being.clock import Clock
from being.config import CONFIG
from being.logging import get_logger
from being.web.server import init_web_server, init_api, run_web_server
from being.web.web_socket import WebSocket


API_PREFIX = CONFIG['Web']['API_PREFIX']
WEB_SOCKET_ADDRESS = CONFIG['Web']['WEB_SOCKET_ADDRESS']
INTERVAL = CONFIG['General']['INTERVAL']
WEB_INTERVAL = CONFIG['Web']['INTERVAL']
LOGGER = get_logger(__name__)


def _cancel_all_asyncio_tasks():
    """Shutdown all async tasks.

    Resrouces:
      https://gist.github.com/nvgoldin/30cea3c04ee0796ebd0489aa62bcf00a
    """
    LOGGER.info('Cancelling all asyncio tasks')
    for task in asyncio.all_tasks():
        task.cancel()


async def _send_being_state_to_front_end(being: Being, ws: WebSocket):
    """Keep capturing the current being state and send it to the front-end.
    Taken out from ex being._run_web() because web socket send might block being
    main loop.

    Args:
        being: Being instance.
        ws: Active web socket.
    """
    while True:
        await ws.send_json({
            'type': 'output-values',
            'timestamp': being.clock.now(),
            'values': being.capture_value_outputs()
        })
        await asyncio.sleep(WEB_INTERVAL)


async def _awake_web(being):
    """Run being with web server."""
    app = init_web_server(being)
    ws = WebSocket()
    app.router.add_get(WEB_SOCKET_ADDRESS, ws.handle_web_socket)
    app.on_shutdown.append(ws.close_all)
    api = init_api(being, ws)
    app.add_subapp(API_PREFIX, api)
    if os.name == 'posix':
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGTERM, _cancel_all_asyncio_tasks)
    else:
        warnings.warn((
            'No signals available on your OS. Can not register SIGTERM'
            ' signal for graceful program exit'
    ))

    try:
        await asyncio.gather(
            being.run_async(),
            _send_being_state_to_front_end(being, ws),
            run_web_server(app),
            ws.run_broker(),
        )
    except asyncio.CancelledError:
        pass


def awake(*blocks,
        web: bool = True,
        clock: Optional[Clock] = None,
        network: Optional[CanBackend] = None,
    ):
    """Run being block network.

    Args:
        blocks: Some blocks of the network.

    Kwargs:
        web: Run with web server.
        clock: Clock instance.
        network: CanBackend instance.
    """
    if clock is None:
        clock = Clock.single_instance_setdefault()

    if network is None:
        network = CanBackend.single_instance_get()

    being = Being(blocks, clock, network)

    for motor in being.motors:
        motor.home()
        motor.enable()

    try:
        if not web:
            return being.run()

        return asyncio.run(_awake_web(being))
    except Exception as err:
        LOGGER.fatal(err, exc_info=True)
        # TODO(atheler): Log and throw anti pattern but we always want to see
        # the error in stderr
        raise
