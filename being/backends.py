"""Backend resources."""
import sys
import contextlib

import canopen
import pyaudio
if sys.platform == 'darwin':
    from being.pcan_darwin_patch import patch_pcan_on_darwin
    patch_pcan_on_darwin()

from being.utils import SingleInstanceCache


class CanBackend(canopen.Network, SingleInstanceCache, contextlib.AbstractContextManager):

    """CANopen network wrapper. Automatic connect during __enter__."""

    def __init__(self, bitrate=1000000, bustype='pcan', channel='PCAN_USBBUS1'):
        super().__init__(bus=None)
        self.bitrate = bitrate
        self.bustype = bustype
        self.channel = channel

    def __enter__(self):
        self.connect(bitrate=self.bitrate, bustype=self.bustype, channel=self.channel)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
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
