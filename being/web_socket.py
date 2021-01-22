"""Web socket proxy."""
import logging
import enum

from aiohttp import web

from being.serialization import dumps


class Event(enum.Enum):

    """Web socket events."""

    OPEN = enum.auto()
    MESSAGE = enum.auto()
    ERROR = enum.auto()
    CLOSE = enum.auto()


class WebSocket:

    """WebSocket connections. Interfaces with aiohttp web socket requests. Can
    hold multiple open web socket connections simultaneously.

    Attributes:
        sockets: Active web socket connections
        callbacks: Registered on-message-receive callback functions.
    """

    def __init__(self, address):
        self.address = address
        self.sockets = []
        self.callbacks = {
            Event.OPEN: set(),
            Event.MESSAGE: set(),
            Event.ERROR: set(),
            Event.CLOSE: set(),
        }
        self.logger = logging.getLogger(str(self))

    @property
    def nConnections(self) -> int:
        """Number of open websocket connections."""
        return len(self.sockets)

    def add_callback(self, callback, event=Event.MESSAGE):
        """Register on message receive callback."""
        self.callbacks[event].add(callback)

    def remove_callback(self, callback, event=Event.MESSAGE):
        """Remove on message receive callback."""
        self.callbacks.remove(callback)

    async def handle_web_socket(self, request):
        """Websocket handler."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.logger.info('Opening connection')
        self.sockets.append(ws)
        for callback in self.callbacks[Event.OPEN]:
            callback()

        self.logger.debug('%d open connections', self.nConnections)
        try:
            async for msg in ws:
                # TODO: Do weed error checking here? It seems that closing the
                # web socket is already handled by aiohttp in the background.
                for callback in self.callbacks[Event.MESSAGE]:
                    callback(msg)

        finally:
            self.logger.info('Closing connection')
            self.sockets.remove(ws)
            for callback in self.callbacks[Event.CLOSE]:
                callback()

            self.logger.debug('%d open connections', self.nConnections)

        return ws

    async def send_json(self, data):
        """Send data as JSON to all connected websockets."""
        for ws in self.sockets:
            await ws.send_json(data, dumps=dumps)

    def route(self):
        """Route for web socket handler."""
        return web.get(self.address, self.handle_web_socket)
