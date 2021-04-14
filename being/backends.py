"""Backend resources.

TODO: Finish Audio Backend.
TODO: VideoBackend.
"""
import contextlib
import sys
import warnings
from typing import List, ForwardRef

from being.config import CONFIG
from being.rpi_gpio import GPIO

try:
    import pyaudio
except ImportError:
    pyaudio = None
    warnings.warn('PyAudio is not installed!')

import canopen
from being.utils import SingleInstanceCache, filter_by_type
from being.logging import get_logger


CiA402Node = ForwardRef('CiA402Node')
DEFAULT_CAN_BITRATE = CONFIG['Can']['DEFAULT_CAN_BITRATE']


# Default system dependent CAN bus parameters
if sys.platform == 'darwin':
    _BUS_TYPE = 'pcan'
    _CHANNEL = 'PCAN_USBBUS1'
else:
    _BUS_TYPE = 'socketcan'
    _CHANNEL = 'can0'


class CanBackend(canopen.Network, SingleInstanceCache, contextlib.AbstractContextManager):

    """CANopen network wrapper. Automatic connect during __enter__."""

    def __init__(self, bitrate=DEFAULT_CAN_BITRATE, bustype=_BUS_TYPE, channel=_CHANNEL):
        super().__init__(bus=None)
        self.bitrate = bitrate
        self.bustype = bustype
        self.channel = channel

    @property
    def drives(self) -> List[CiA402Node]:
        """Get list of all drive nodes."""
        from being.can.cia_402 import CiA402Node  # Circular import for comforts
        return filter_by_type(self.values(), CiA402Node)

    def disengage_drives(self):
        for drive in self.drives:
            drive.disengage()

    def disable_drives(self):
        for drive in self.drives:
            drive.disable()

    def engage_drives(self):
        for drive in self.drives:
            drive.engage()

    def disenable_drives(self):
        for drive in self.drives:
            drive.disenable()

    def enable_drives(self):
        for drive in self.drives:
            drive.enable()

    def update(self):
        """Custom update method so that we can include CanBackend in execOrder
        for sending out sync messages at the end of the cycle for driving the
        PDO communication.
        """
        self.send_message(0x80, [])

    def __enter__(self):
        self.connect(bitrate=self.bitrate, bustype=self.bustype, channel=self.channel)
        self.check()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.disable_drives()
        self.disconnect()


class AudioBackend(SingleInstanceCache, contextlib.AbstractContextManager):

    """Sound card connection. Collect audio samples."""

    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(
            format=self.pa.get_format_from_width(2),
            channels=1,
            rate=44100,
            input=True,
            output=False,
            stream_callback=self.callback,
        )

    def callback(self, in_data, frame_count, time_info, status):
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
    def __init__(self):
        self.logger = get_logger(str(self))
        self.gpio = GPIO

    def __enter__(self):
        GPIO.setmode(GPIO.BCM)

    def __exit__(self, exc_type, exc_value, traceback):
        GPIO.cleanup()
