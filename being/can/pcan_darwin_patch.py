"""Temporary workaround for a small bug when using python-can on a Mac with a
PCAN interface running with libPCBUSB == 0.9. More details can be found here:
https://github.com/hardbyte/python-can/issues/957.

Caution:
    This issue seems to be fixed with python-can version >= 4.0.0. See
    https://github.com/hardbyte/python-can/blob/develop/CHANGELOG.md
"""
import re
import sys
import warnings
from ctypes import byref, c_ushort, cdll, create_string_buffer, sizeof

import can
import canopen
from can.interfaces import pcan


PCAN_LIBRARY_NAME = 'libPCBUSB.dylib'
PCAN_NONEBUS = c_ushort(0x00)
PCAN_EXT_SOFTWARE_VERSION = c_ushort(0x86)


def is_pcan_lib_installed() -> bool:
    """Check if PCAN driver library is installed or not."""
    try:
        cdll.LoadLibrary(PCAN_LIBRARY_NAME)
        return True
    except OSError:
        return False


def does_python_can_need_patching() -> bool:
    """Check python-can version number for issue."""
    major = can.__version__.split('.', maxsplit=1)[0]
    return int(major) < 4


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
    if not sys.platform.startswith('darwin'):
        warnings.warn('Not on a Mac. Nothing to patch')
        return

    if not is_pcan_lib_installed():
        warnings.warn('PCAN driver %r seems not to be installed' % PCAN_LIBRARY_NAME)
        return

    if not does_python_can_need_patching():
        warnings.warn('python-can >= 4.0.0 does not need patching')
        return

    # Get version number from dylib
    lib = cdll.LoadLibrary(PCAN_LIBRARY_NAME)
    buf = create_string_buffer(256)
    res = lib.CAN_GetValue(PCAN_NONEBUS, PCAN_EXT_SOFTWARE_VERSION, byref(buf), sizeof(buf))
    if res:
        raise RuntimeError('Could not get value from lib!')

    pattern = b'.+version (\d+)\.(\d+)\.(\d+)\.\d+'
    m = re.match(pattern, buf.value)
    major, minor, micro = map(int, m.groups())
    if minor < 9:
        version = b'.'.join(m.groups())
        warnings.warn('Nothing to patch for PCAN driver version %s' % version.decode())
        return

    for mod in [pcan.basic, pcan.pcan]:
        mod.TPCANMsgMac = mod.TPCANMsg
        mod.TPCANMsgFDMac = mod.TPCANMsgFD
