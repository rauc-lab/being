"""Web socket proxy."""
import asyncio
import collections
import weakref

import aiohttp
from aiohttp import web
from aiohttp import WSMsgType

from being.serialization import dumps
from being.logging import get_logger


class WebSocket:

    """WebSocket connections. Interfaces with aiohttp web socket requests. Can
    hold multiple open web socket connections simultaneously. Also has a message
    queue / broker functionality to send messages from non-asyncio world.

    Attributes:
        sockets: Active web socket connections
        queue: Message queue for synchronous senders.
    """

    def __init__(self):
        self.sockets = weakref.WeakSet()
        self.queue = collections.deque(maxlen=100)
        self.logger = get_logger('WebSocket')
        self.brokerTask = None

    async def send_json(self, data):
        """Send data as JSON to all connected web sockets.

        Args:
            data: Data to send as JSON.
        """
        for ws in self.sockets.copy():
            if ws.closed:
                continue
            try:
                await ws.send_json(data, dumps=dumps)
            except ConnectionResetError as err:
                self.logger.exception(err)

    def send_json_buffered(self, data):
        """Synchronous send_json(). Data goes into buffered and send at a later
        stage (if broker task is running).

        Args:
            data: Data to send as JSON.
        """
        self.queue.append(data)

    async def handle_new_connection(self, request) -> web.WebSocketResponse:
        """Aiohttp new web socket connection request handler."""
        ws = web.WebSocketResponse(autoclose=True)
        await ws.prepare(request)
        self.logger.info('Opened web socket')
        self.sockets.add(ws)
        try:
            async for msg in ws:
                if msg.type == WSMsgType.ERROR:
                    self.logger.error('Web socket error with exception %s', ws.exception())
                    break
        finally:
            self.logger.info('Discarding web socket')
            self.sockets.discard(ws)

        self.logger.debug('Web socket closed')
        return ws

    #pylint: disable=unused-argument
    async def close_all_connections(self, app: web.Application = None):
        """Close all web sockets. Can be used with app.on_shutdown() /
        app.on_cleanup().
        """
        for ws in self.sockets.copy():
            await ws.close(code=aiohttp.WSCloseCode.GOING_AWAY, message='Closing web socket')

    async def broker_task(self):
        """Message broker task. Takes messages from queue and sends them over
        all open web socket connections.
        """
        while True:
            for data in self.queue.copy():
                await self.send_json(data)
                self.queue.popleft()

            await asyncio.sleep(.1)

    #pylint: disable=unused-argument
    async def start_broker(self, app: web.Application = None):
        """Start message broker task."""
        await self.stop_broker()
        self.brokerTask = asyncio.create_task(self.broker_task())

    #pylint: disable=unused-argument
    async def stop_broker(self, app: web.Application = None):
        """Stop message broker task."""
        if not self.brokerTask:
            return

        self.brokerTask.cancel()
        await self.brokerTask
        self.brokerTask = None
