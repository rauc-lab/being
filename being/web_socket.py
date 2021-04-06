"""Web socket proxy."""
import asyncio
import collections
import logging
import enum

from aiohttp import web

from being.serialization import dumps
from being.pubsub import PubSub


class Event(enum.Enum):

    """Web socket events."""

    OPEN = enum.auto()
    MESSAGE = enum.auto()
    ERROR = enum.auto()
    CLOSE = enum.auto()


class WebSocket(PubSub):

    """WebSocket connections. Interfaces with aiohttp web socket requests. Can
    hold multiple open web socket connections simultaneously.

    Attributes:
        address: Web socket URL.
        sockets: Active web socket connections
    """

    def __init__(self, address):
        super().__init__(events=[Event.OPEN, Event.MESSAGE, Event.ERROR, Event.CLOSE])
        self.address = address
        self.sockets = []
        self.logger = logging.getLogger(str(self))

    @property
    def nConnections(self) -> int:
        """Number of open websocket connections."""
        return len(self.sockets)

    async def handle_web_socket(self, request):
        """Websocket handler."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.logger.info('Opening connection')
        self.sockets.append(ws)
        self.publish(Event.OPEN)
        self.logger.debug('%d open connections', self.nConnections)
        try:
            async for msg in ws:
                # TODO: Do weed error checking here? It seems that closing the
                # web socket is already handled by aiohttp in the background.
                self.publish(Event.MESSAGE, msg)

        finally:
            self.logger.info('Closing connection')
            self.sockets.remove(ws)
            self.publish(Event.CLOSE)
            self.logger.debug('%d open connections', self.nConnections)

        return ws

    async def send_json(self, data):
        """Send data as JSON to all connected web sockets."""
        for ws in self.sockets:
            await ws.send_json(data, dumps=dumps)

    def route(self):
        """Route for web socket handler."""
        return web.get(self.address, self.handle_web_socket)


class Broker:

    """Web socket worker.

    Message queue to separate synchronous code from asynchronous. Web socket
    worker will periodically send all buffered messages via async send call.

    Attributes:
        ws (WebSocket): Web socket instance.
        queue (deque): Message buffer.
    """

    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.queue = collections.deque(maxlen=100)

    def post_json(self, msg):
        """Post JSON message. Will be send out at a later time (if borker is running).

        Args:
            obj: JSON serializable object.
        """
        self.queue.append(msg)

    async def run(self):
        """Start broker."""
        while True:
            while self.queue:
                obj = self.queue.popleft()
                await self.ws.send_json(obj)

            await asyncio.sleep(.1)