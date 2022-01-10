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
"""
import contextlib
import sys
import time
import warnings
from typing import List, Generator, Set, Dict, Union
from logging import Logger

try:
    import pyaudio
except ImportError:
    pyaudio = None
    warnings.warn('PyAudio is not installed!')

import numpy as np
import can
import canopen
from canopen.pdo.base import Map

from being.can.cia_402 import CiA402Node
from being.can.nmt import PRE_OPERATIONAL, OPERATIONAL, RESET_COMMUNICATION
from being.configuration import CONFIG
from being.logging import get_logger
from being.math import linear_mapping
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

    def turn_off_motors(self):
        """Turn off all registered drives."""
        for node in self.drives:
            try:
                node.disable()
            except TimeoutError as err:
                self.logger.exception(err)

    def enable_pdo_communication(self):
        """Enable PDO communication by setting NMT state to OPERATIONAL."""
        self.logger.debug('Global NMT -> OPERATIONAL')
        self.nmt.state = OPERATIONAL

    def disable_pdo_communication(self):
        """Disable PDO communication by setting NMT state to PRE-OPERATIONAL."""
        self.logger.debug('Global NMT -> PRE-OPERATIONAL')
        self.nmt.state = PRE_OPERATIONAL

    def reset_communication(self):
        """Reset NMT communication."""
        self.nmt.state = RESET_COMMUNICATION

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
        try:
            self.disable_pdo_communication()
            self.turn_off_motors()
        finally:
            self.disconnect()


def pyaudio_format(dtype: Union[str, np.dtype, type]) -> int:
    """Determine pyaudio format number for data type.

    Args:
        dtype: Datatype.

    Returns:
        Audio format number.
    """
    if not pyaudio:
        raise RuntimeError('pyaudio is not installed!')

    if isinstance(dtype, str):
        dtype = np.dtype(dtype)
    if isinstance(dtype, np.dtype):
        dtype = dtype.type

    return {
        np.uint8: pyaudio.paUInt8,
        np.int16: pyaudio.paInt16,
        np.int32: pyaudio.paInt32,
        np.float32: pyaudio.paFloat32,
    }[dtype]


class SpectralFlux:

    """Spectral flux filter."""

    def __init__(self, bufferSize):
        self.bufferSize = bufferSize
        freqs = np.fft.rfftfreq(bufferSize)
        self.prevMag = np.ones(len(freqs))

    def __call__(self, samples):
        X = np.fft.rfft(samples)
        mag = np.abs(X)
        delta = mag - self.prevMag
        self.prevMag = mag

        # Half-wave rectification
        rectified = (delta + np.abs(delta)) / 2

        # Normalized spectral flux
        return np.sum(rectified) / self.bufferSize**1.5


class AudioBackend(SingleInstanceCache, contextlib.AbstractContextManager):

    """Sound card connection. Collect audio samples with PortAudio / PyAudio."""

    def __init__(self,
            bufferSize: int = 1024,
            dtype: Union[type, str] = np.uint8,
        ):
        """
        Args:
            bufferSize: Audio buffer size.
            dtype: Datatype for samples. Not all data types are supported for
                audio. u8, i16 and i32 should work.
        """
        dtype = np.dtype(dtype)
        self.bufferSize = bufferSize
        self.dtype = dtype

        # Prepare sample normalization
        if np.issubdtype(dtype, np.integer):
            iinfo = np.iinfo(dtype)
            xRange = (iinfo.min, iinfo.max)
        else:
            xRange = (-1.0, 1.0)  # Float samples are already normalized

        self.scale, self.offset = linear_mapping(xRange, yRange=(-1.0, 1.0))

        self.pa: pyaudio.PyAudio = pyaudio.PyAudio()
        self.stream = self.pa.open(
            format=pyaudio_format(dtype),
            channels=1,
            frames_per_buffer=bufferSize,
            rate=44100,
            input=True,
            output=False,
            stream_callback=self.callback,
        )
        self.flux = SpectralFlux(bufferSize)
        self.microphones = []

    def callback(self, in_data, frame_count, time_info, status):
        """pyaudio audio stream callback function."""
        samples = np.frombuffer(in_data, dtype=self.dtype)
        normalized = self.scale * samples + self.offset
        sf = self.flux(normalized)
        for mic in self.microphones:
            mic.new_spectral_flux_value(sf)

        return (None, pyaudio.paContinue)

    def subscribe_microphone(self, mic):
        """Subscribe Mic block to audio backend."""
        self.microphones.append(mic)

    def __enter__(self):
        print('Entering AudioBackend')
        self.stream.start_stream()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        print('Exiting AudioBackend')
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
