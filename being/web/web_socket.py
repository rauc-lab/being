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
    hold multiple open web socket connections simultaneously.

    Attributes:
        sockets: Active web socket connections
        queue: Message queue for synchronous senders.
    """

    def __init__(self):
        self.sockets = weakref.WeakSet()
        self.queue = collections.deque(maxlen=100)
        self.logger = get_logger('WebSocket')

    async def handle_web_socket(self, request):
        """Aiohttp web socket handler."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.logger.info('Opened web socket')
        self.sockets.add(ws)
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    if msg.data == 'close':
                        break
                elif msg.type == WSMsgType.ERROR:
                    self.logger.error('Web socket error with exception %s', ws.exception())
                    break
        finally:
            self.sockets.discard(ws)

            # TODO(atheler): We must wait a bit before closing the socket.
            # Otherwise it can happen, that someone else is writing to a closed
            # transport which crashes the application. Probably by calling
            # send_json() when there are multiple sockets present. There must be
            # a better way?!
            await asyncio.sleep(1.)

            self.logger.info('Closing web socket')
            await ws.close()

        self.logger.debug('Web socket closed')
        return ws

    #pylint: disable=unused-argument
    async def close_all(self, app: web.Application = None):
        """Close all web sockets. Can be used with app.on_cleanup()."""
        for ws in set(self.sockets):  # Mutating while iterating
            await ws.close(code=aiohttp.WSCloseCode.GOING_AWAY, message='Closing web socket')

    def send_json_buffered(self, data):
        """Synchronous send_json(). Data goes into buffered and send at a later
        stage (if broker task is running).

        Args:
            data: Data to send as JSON.
        """
        self.queue.append(data)

    async def send_json(self, data):
        """Send data as JSON to all connected web sockets.

        Args:
            data: Data to send as JSON.
        """
        for ws in self.sockets:
            await ws.send_json(data, dumps=dumps)

    async def run_broker(self):
        """Start message broker task."""
        while True:
            for data in list(self.queue):
                await self.send_json(data)
                self.queue.popleft()

            await asyncio.sleep(.1)
