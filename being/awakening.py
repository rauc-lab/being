"""Awake being to life. Main entry point runner. Define a block network and run
them with the :meth:`being.awakening.awake` function.

Example:
    >>> from being.block import Block
    ... from being.awakening import awake
    ... block = Block()
    ... awake(block)  # Will start web server and periodically call block.update()

The interval rate can be configured inside :mod:`being.configuration`.
"""
import asyncio
import os
import signal
import sys
import time
from typing import Optional, Iterable

from being.backends import CanBackend
from being.being import Being
from being.block import Block
from being.clock import Clock
from being.configuration import CONFIG
from being.connectables import MessageInput
from being.logging import get_logger
from being.pacemaker import Pacemaker
from being.resources import register_resource
from being.web.server import init_web_server, run_web_server
from being.web.web_socket import WebSocket


# Look before you leap
_API_PREFIX = CONFIG['Web']['API_PREFIX']
_WEB_SOCKET_ADDRESS = CONFIG['Web']['WEB_SOCKET_ADDRESS']
_INTERVAL = CONFIG['General']['INTERVAL']
_WEB_INTERVAL = CONFIG['Web']['INTERVAL']

LOGGER = get_logger(name=__name__, parent=None)


def _exit_signal_handler(signum=None, frame=None):
    """Signal handler for exit program."""
    #pylint: disable=unused-argument
    sys.exit(0)


def _run_being_standalone(being: Being):
    """Run being standalone without web server / front-end.

    Args:
        being: Being application instance.
    """
    if os.name == 'posix':
        signal.signal(signal.SIGTERM, _exit_signal_handler)

    cycle = int(time.perf_counter() / _INTERVAL)
    while True:
        now = time.perf_counter()
        then = cycle * _INTERVAL
        sleepTime = then - now
        if sleepTime >= 0:
            time.sleep(then - now)

        being.single_cycle()
        cycle += 1


async def _run_being_async(being: Being):
    """Run being inside async loop.

    Args:
        being: Being application instance.
    """
    time_func = asyncio.get_running_loop().time
    cycle = int(time_func() / _INTERVAL)

    while True:
        now = time_func()
        then = cycle * _INTERVAL
        sleepTime = then - now
        if sleepTime >= 0:
            await asyncio.sleep(sleepTime)

        being.single_cycle()
        cycle += 1


async def _send_being_state_to_front_end(being: Being, ws: WebSocket):
    """Keep capturing the current being state and send it to the front-end.
    Taken out from ex being._run_web() because web socket send might block being
    main loop.

    Args:
        being: Being application instance.
        ws: Active web socket.
    """
    dummies = []
    for out in being.messageOutputs:
        dummy = MessageInput(owner=None)
        out.connect(dummy)
        dummies.append(dummy)

    time_func = asyncio.get_running_loop().time
    cycle = int(time_func() / _WEB_INTERVAL)
    while True:
        now = time_func()
        then = cycle * _WEB_INTERVAL
        if then > now:
            await asyncio.sleep(then - now)

        await ws.send_json({
            'type': 'being-state',
            'timestamp': being.clock.now(),
            'values': [out.value for out in being.valueOutputs],
            'messages': [
                list(dummy.receive())
                for dummy in dummies
            ],
        })

        cycle += 1


async def _run_being_with_web_server(being: Being):
    """Run being with web server. Continuation for awake() for asyncio part.

    Args:
        being: Being application instance.
    """
    ws = WebSocket()
    app = init_web_server(being, ws)
    await asyncio.gather(
        _run_being_async(being),
        _send_being_state_to_front_end(being, ws),
        run_web_server(app),
    )


def awake(
        *blocks: Iterable[Block],
        web: bool = True,
        enableMotors: bool = True,
        homeMotors: bool = True,
        usePacemaker: bool = True,
        clock: Optional[Clock] = None,
        network: Optional[CanBackend] = None,
    ):
    """Run being block network.

    Args:
        blocks: Some blocks of the network. Remaining blocks will be auto
            discovered.
        web: Run with web server.
        enableMotors: Enable motors on startup.
        homeMotors: Home motors on startup.
        usePacemaker: If to use an extra pacemaker thread.
        clock: Clock instance.
        network: CanBackend instance.
    """
    if clock is None:
        clock = Clock.single_instance_setdefault()

    if network is None:
        network = CanBackend.single_instance_get()

    pacemaker = Pacemaker(network)
    being = Being(blocks, clock, pacemaker, network)

    if network is not None:
        network.reset_communication()
        network.enable_pdo_communication()
        if usePacemaker:
            pacemaker.start()
            register_resource(pacemaker)

        network.send_sync()  # Update local TXPDOs values
        time.sleep(0.200)

    if enableMotors:
        being.enable_motors()
    else:
        being.disable_motors()

    if homeMotors:
        being.home_motors()

    try:
        if web:
            asyncio.run(_run_being_with_web_server(being))
        else:
            _run_being_standalone(being)

    except Exception as err:
        # Log and throw anti pattern but error should appear in stderr as well.
        LOGGER.fatal(err, exc_info=True)
        raise
