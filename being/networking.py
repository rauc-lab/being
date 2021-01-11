"""Networking sending and receiving blocks."""
import socket
from typing import Optional, Tuple

from being.block import Block
from being.resources import register_resource
from being.serialization import EOT, FlyByDecoder, dumps
from being.connectables import MessageOutput, MessageInput


Socket = socket.socket
Address = Tuple[str, int]


TERM: str = EOT
"""Message termination character."""

BUFFER_SIZE: int = 1024
"""Number of bytes for socket recv call."""


class NetworkBlock(Block):

    """Base class for network / socket blocks.

    Attributes:
        address: Socket address.
        sock: Socket instance.
    """

    def __init__(self, address: Address, sock: Optional[Socket] = None):
        """Args:
            address: Network address.

        Kwargs:
            sock: Socket instance.
        """
        super().__init__()
        if sock is None:
            sock = self.create_socket()
            register_resource(sock)

        self.address = address
        self.sock = sock

    @staticmethod
    def create_socket():
        """New non-blocking datagram socket instance."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)
        return sock


class NetworkOut(NetworkBlock):

    """Datagram network out block. Send being messages over UDP."""

    def __init__(self, address: Address, sock: Optional[Socket] = None):
        super().__init__(address, sock)
        self.inputs = [MessageInput(owner=self)]

    def update(self):
        for msg in self.input.receive():
            data = dumps(msg) + TERM
            self.sock.sendto(data.encode(), self.address)


class NetworkIn(NetworkBlock):

    """Datagram network in block. Receive being messages over UDP."""

    def __init__(self, address: Address, sock: Optional[Socket] = None):
        super().__init__(address, sock)
        self.outputs = [MessageOutput(owner=self)]
        self.decoder = FlyByDecoder(term=TERM)
        self.sock.bind(address)

    def update(self):
        try:
            newData = self.sock.recv(BUFFER_SIZE).decode()
        except BlockingIOError:
            return

        for obj in self.decoder.decode_more(newData):
            self.output.send(obj)