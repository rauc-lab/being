"""Temporary workaround for a small bug when using python-can on a Mac with a
PCAN interface running with libPCBUSB == 0.9. More details can be found here:
https://github.com/hardbyte/python-can/issues/957.
"""
import re
import sys
import warnings
from ctypes import byref, c_ushort, cdll, create_string_buffer, sizeof

import can
import canopen
from can.interfaces import pcan


PCAN_NONEBUS = c_ushort(0x00)
PCAN_EXT_SOFTWARE_VERSION = c_ushort(0x86)


def patch_pcan_on_darwin():
    """Temporary workaround for an issue with the PCAN interface on a Mac and
    libPCBUSB version 0.9 (32/64 bit data type issue). Patches PCAN message
    structures in python-can (can.interfaces.pcan).

    Example:
        >>> import can
        ... import canopen
        ... # Import can & canopen before patching
        ... patch_pcan_on_darwin()
    """
    if sys.platform == 'darwin':
        # Get version number from dylib
        lib = cdll.LoadLibrary('libPCBUSB.dylib')
        buf = create_string_buffer(256)
        res = lib.CAN_GetValue(PCAN_NONEBUS, PCAN_EXT_SOFTWARE_VERSION, byref(buf), sizeof(buf))
        if res:
            raise RuntimeError('Could not get value from lib!')

        ptr = b'.+version (\d+)\.(\d+)\.(\d+)\.\d+'
        m = re.match(ptr, buf.value)
        major, minor, micro = map(int, m.groups())
        if minor >= 9:
            for mod in [pcan.basic, pcan.pcan]:
                mod.TPCANMsgMac = mod.TPCANMsg
                mod.TPCANMsgFDMac = mod.TPCANMsgFD
    else:
        warnings.warn('Not on a Mac. Nothing to patch')
