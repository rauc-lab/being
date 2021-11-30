"""Backend resources.

TODO: Finish Audio Backend.
TODO: VideoBackend.
"""
import contextlib
import sys
import threading
import time
import warnings
from typing import List

try:
    import pyaudio
except ImportError:
    pyaudio = None
    warnings.warn('PyAudio is not installed!')

import can
import canopen

from being.can.cia_402 import CiA402Node
from being.can.nmt import PRE_OPERATIONAL, OPERATIONAL
from being.configuration import CONFIG
from being.logging import get_logger
from being.rpi_gpio import GPIO
from being.utils import SingleInstanceCache, filter_by_type


DEFAULT_CAN_BITRATE = CONFIG['Can']['DEFAULT_CAN_BITRATE']
INTERVAL = CONFIG['General']['INTERVAL']


# Default system dependent CAN bus parameters
if sys.platform.startswith('darwin'):
    _BUS_TYPE = 'pcan'
    _CHANNEL = 'PCAN_USBBUS1'
else:
    _BUS_TYPE = 'socketcan'
    _CHANNEL = 'can0'


SYNC_MSG = can.Message(is_extended_id=False, arbitration_id=0x80, data=[], is_remote_frame=False)


class CanBackend(canopen.Network, SingleInstanceCache, contextlib.AbstractContextManager):

    """CANopen network wrapper.

    Automatic connect during __enter__ phase. Also has custom SYNC sender thread
    which works with a event to sync main loop with periodically sending out
    SYNC messages over CAN.
    """

    def __init__(self,
            bitrate=DEFAULT_CAN_BITRATE,
            bustype=_BUS_TYPE,
            channel=_CHANNEL,
        ):
        super().__init__(bus=None)
        self.bitrate = bitrate
        self.bustype = bustype
        self.channel = channel

        self.logger = get_logger('CanBackend')
        self.rpdos = set()

    @property
    def drives(self) -> List[CiA402Node]:
        """Get list of all drive nodes."""
        return filter_by_type(self.values(), CiA402Node)

    def switch_off_drives(self):
        """Switch off all registered drives."""
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
        self.bus.send(SYNC_MSG)

    def register_rpdo(self, rx):
        """Register RPDO map to be transmitted repeadely by sender thread."""
        self.rpdos.add(rx)

    def transmit_all_rpdos(self):
        """Transmit current value of all registered RPDO maps."""
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
        """Scan for node ids which are online."""
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
