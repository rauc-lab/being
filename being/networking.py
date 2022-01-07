"""Networking blocks which can send / receive data via UDP over the network.

Warning:
    Untested.
"""
import socket
from typing import Optional, Tuple

from being.block import Block
from being.resources import register_resource
from being.serialization import EOT, FlyByDecoder, dumps


Socket = socket.socket
Address = Tuple[str, int]


TERM: str = EOT
"""Message termination character."""

BUFFER_SIZE: int = 1024
"""Number of bytes for socket recv call."""


def format_address(address: Address) -> str:
    """Format socket address."""
    host, port = address
    if host == '':
        host = '0.0.0.0'

    return '%s:%d' % (host, port)


class NetworkBlock(Block):

    """Base class for network / socket blocks. Sockets get registered as
    resources with :func:`register_resource`. Default :mod:`being.serialization`
    is used for data serialization.
    """

    def __init__(self, address: Address, sock: Optional[Socket] = None, **kwargs):
        """
        Args:
            address: Network address.
            sock (optional): Socket instance (DI).
            **kwargs: Arbitrary block keyword arguments.
        """
        super().__init__(**kwargs)
        if sock is None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setblocking(False)
            register_resource(sock)

        self.address: Address = address
        """Socket address."""

        self.sock: Socket = sock
        """Underlying socket instance."""

    def __str__(self):
        return '%s(address: %s)' % (type(self).__name__, format_address(self.address))


class NetworkOut(NetworkBlock):

    """Datagram network out block. Send being messages over UDP."""

    def __init__(self, address: Address, sock: Optional[Socket] = None, **kwargs):
        super().__init__(address, sock, **kwargs)
        self.add_message_input()

    def update(self):
        for msg in self.input.receive():
            data = dumps(msg) + TERM
            self.sock.sendto(data.encode(), self.address)


class NetworkIn(NetworkBlock):

    """Datagram network in block. Receive being messages over UDP."""

    def __init__(self, address: Address, sock: Optional[Socket] = None, **kwargs):
        super().__init__(address, sock, **kwargs)
        self.add_message_output()
        self.decoder = FlyByDecoder(term=TERM)
        self.sock.bind(address)

    def update(self):
        try:
            newData = self.sock.recv(BUFFER_SIZE).decode()
        except BlockingIOError:
            return

        for obj in self.decoder.decode_more(newData):
            self.output.send(obj)
