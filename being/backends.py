"""Backend resources."""
import contextlib
import sys
from typing import List, ForwardRef

import pyaudio
import canopen
from being.utils import SingleInstanceCache
from being.can.homing import home_drives


CiA402Node = ForwardRef('CiA402Node')


# Default CAN args
if sys.platform == 'darwin':
    _BUS_TYPE = 'pcan'
    _CHANNEL = 'PCAN_USBBUS1'
else:
    _BUS_TYPE = 'socketcan'
    _CHANNEL = 'can0'


class CanBackend(canopen.Network, SingleInstanceCache, contextlib.AbstractContextManager):

    """CANopen network wrapper. Automatic connect during __enter__."""

    def __init__(self, bitrate=1000000, bustype=_BUS_TYPE, channel=_CHANNEL):
        super().__init__(bus=None)
        self.bitrate = bitrate
        self.bustype = bustype
        self.channel = channel

    @property
    def drives(self) -> List[CiA402Node]:
        """Get list of all drive nodes."""
        from being.can.cia_402 import CiA402Node  # Circular import for comforts
        return [
            node for node in self.values()
            if isinstance(node, CiA402Node)
        ]

    def enable_drives(self):
        """Enable all drives."""
        for drive in self.drives:
            drive.enable()

    def disable_drives(self):
        """Disable all drives."""
        for drive in self.drives:
            drive.disable()

    def home_drives(self, **kwargs):
        """Home all connected drives."""
        home_drives(*self.drives, **kwargs)

    def send_sync(self):
        """Send out sync message."""
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


# TODO: VideoBackend
