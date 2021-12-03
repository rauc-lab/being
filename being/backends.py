""" Backend resources are wrapped as context managers and can be used with

Example:
    >>> with SomeResource() as resource:
    ...     # Do something with resource
    ...     pass

.. Context Manager:
   https://docs.python.org/3/glossary.html#term-context-manager

Handling dynamic context managers can be done with
:class:`contextlib.contextlib.ExitStack`. This functionality accessed in the
:mod:`being.resources`.

Todo:
    - Finish Audio Backend.
    - Video backend?
"""
import contextlib
import sys
import time
import warnings
from typing import List, Generator, Set
from logging import Logger

try:
    import pyaudio
except ImportError:
    pyaudio = None
    warnings.warn('PyAudio is not installed!')

import can
import canopen
from canopen.pdo.base import Map

from being.can.cia_402 import CiA402Node
from being.can.nmt import PRE_OPERATIONAL, OPERATIONAL
from being.configuration import CONFIG
from being.logging import get_logger
from being.rpi_gpio import GPIO
from being.utils import SingleInstanceCache, filter_by_type


# Look before you leap
_DEFAULT_CAN_BITRATE = CONFIG['Can']['DEFAULT_CAN_BITRATE']
_INTERVAL = CONFIG['General']['INTERVAL']

# Default system dependent CAN bus parameters
if sys.platform.startswith('darwin'):
    _DEFAULT_BUS_TYPE = 'pcan'
    _DEFAULT_CHANNEL = 'PCAN_USBBUS1'
else:
    _DEFAULT_BUS_TYPE = 'socketcan'
    _DEFAULT_CHANNEL = 'can0'

_CAN_SYNC_MSG: can.Message = can.Message(
    is_extended_id=False,
    arbitration_id=0x80,
    data=[],
    is_remote_frame=False,
)
"""Ready to send CAN SYNC message."""


class CanBackend(canopen.Network, SingleInstanceCache, contextlib.AbstractContextManager):

    """CANopen network wrapper.

    Holds the actual CAN bus. Connects to the CAN interface during `__enter__`,
    shutdown drives and disconnects from interface during `__exit__` phase.
    Controls the global NMT state and PDO. RPDO maps from the nodes have to
    register them self with the network. Transmitting all RPDOs can than be done
    with :meth:`CanBackend.transmit_all_rpdos`.
    """

    def __init__(self,
            bitrate: int =_DEFAULT_CAN_BITRATE,
            bustype: str =_DEFAULT_BUS_TYPE,
            channel: str =_DEFAULT_CHANNEL,
        ):
        """
        Args:
            bitrate (optional): Bitrate of CAN bus.
            bustype (optional): CAN bus type. Default value is system dependent.
            channel (optional): CAN bus channel. Default value is system dependent.
        """
        super().__init__(bus=None)
        self.bitrate: str = bitrate
        """CAN bus bit rate."""

        self.bustype: str = bustype
        """CAN bus type."""

        self.channel: str = channel
        """CAN bus channel."""

        self.logger: Logger = get_logger('CanBackend')
        """Dedicated logger."""

        self.rpdos: Set[Map] = set()
        """All registered RPDO maps."""

    @property
    def drives(self) -> Generator[CiA402Node, None, None]:
        """Iterate over all known drive nodes.

        Returns:
            Drives generator.
        """
        return filter_by_type(self.values(), CiA402Node)

    def switch_off_drives(self):
        """Switch off all registered drive nodes."""
        for drive in self.drives:
            drive.switch_off()

    def enable_pdo_communication(self):
        """Enable PDO communication by setting NMT state to OPERATIONAL."""
        self.logger.debug('Global NMT -> OPERATIONAL')
        self.nmt.state = OPERATIONAL

    def disable_pdo_communication(self):
        """Disable PDO communication by setting NMT state to PRE-OPERATIONAL."""
        self.logger.debug('Global NMT -> PRE-OPERATIONAL')
        self.nmt.state = PRE_OPERATIONAL

    def send_sync(self):
        """Send SYNC message over CAN network."""
        # self.send_message(0x80, [])  # send_message() has a lock inside
        self.bus.send(_CAN_SYNC_MSG)

    def register_rpdo(self, rx: Map):
        """Register RPDO map to be transmitted repeatedly by sender thread."""
        self.rpdos.add(rx)

    def transmit_all_rpdos(self):
        """Transmit all current values of all registered RPDO maps."""
        for rx in self.rpdos:
            #self.pdo_node.network.send_message(rx.cob_id, rx.data)  # Lock inside
            msg = can.Message(
                is_extended_id=rx.cob_id > 0x7FF,
                arbitration_id=rx.cob_id,
                data=rx.data,
                is_remote_frame=False,
            )
            self.bus.send(msg)

    def scan_for_node_ids(self) -> List[int]:
        """Scan for node ids which are online.

        Returns:
            Ascending list of all detected CAN ids.
        """
        self.scanner.search()
        time.sleep(0.1)
        return sorted(self.scanner.nodes)

    def __enter__(self):
        self.connect(bitrate=self.bitrate, bustype=self.bustype, channel=self.channel)
        self.check()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.disable_pdo_communication()
        self.switch_off_drives()
        self.disconnect()


class AudioBackend(SingleInstanceCache, contextlib.AbstractContextManager):

    """Sound card connection. Collect audio samples with PortAudio / PyAudio.

    Warning:
        Unfinished.
    """

    def __init__(self):
        self.pa: pyaudio.PyAudio = pyaudio.PyAudio()
        """PyAudio instance."""

        self.stream = self.pa.open(
            format=self.pa.get_format_from_width(2),
            channels=1,
            rate=44100,
            input=True,
            output=False,
            stream_callback=self.callback,
        )

    def callback(self, in_data, frame_count, time_info, status):
        """pyaudio callback function."""
        #print('callback()', frame_count, time_info, status)
        return (None, pyaudio.paContinue)

    def __enter__(self):
        self.stream.start_stream()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stream.stop_stream()
        self.stream.close()
        self.pa.terminate()


class Rpi(SingleInstanceCache, contextlib.AbstractContextManager):

    """Raspberry Pi GPIO backend. This only works running on a Raspberry Pi. On
    non Raspberry Pi system a dummy backend will be loaded (see
    :mod:`being.rpi_gpio`).
    """

    def __init__(self):
        self.logger = get_logger(str(self))
        self.gpio = GPIO

    def __enter__(self):
        GPIO.setmode(GPIO.BCM)

    def __exit__(self, exc_type, exc_value, traceback):
        GPIO.cleanup()
