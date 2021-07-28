"""Vendor specific definitions and lookups."""
from typing import NamedTuple, Dict

from being.bitmagic import check_bit_mask


class Units(NamedTuple):

    """Device units.

    SI conversion factor for value * factor -> device units.
    """

    length: float = 1.
    current: float = 1.
    kinematics: float = 1.
    speed: float = 1.


UNITS: Dict[bytes, Units] = {
    r'MCLM3002P-CO': Units(
        length=1e6,
        current=1000,
        kinematics=1000,
        speed=1000,  # Speeds are in mm/s
    ),
    r'EPOS4': Units( # TODO: Check units!
        length=1e6,
        current=1000,
        kinematics=1000,
        speed=1000,  # Speeds are in mm/s
    ),
}
"""Raw MANUFACTURER_DEVICE_NAME byte string -> Vendor units lookup."""

# TODO: Generalize for other vendors!
FAULHABER_ERRORS: Dict[int, str] = {
    0x0001: 'Continuous Over Current',
    0x0002: 'Deviation',
    0x0004: 'Over Voltage',
    0x0008: 'Over Temperature',
    0x0010: 'Flash Memory Error',
    0x0040: 'CAN In Error Passive Mode',
    0x0080: 'CAN Overrun (objects lost)',
    0x0100: 'Life Guard Or Heart- beat Error',
    0x0200: 'Recovered From Bus Off',
    0x0800: 'Conversion Overflow',
    0x1000: 'Internal Software',
    0x2000: 'PDO Length Exceeded',
    0x4000: 'PDO not processes due to length error',
}

MAXON_ERRORS = {
    1 << 0: 'Generic Error',
    1 << 1: 'Current Error',
    1 << 2: 'Voltage Error',
    1 << 3: 'Temperature Error',
    1 << 4: 'Communication Error',
    1 << 5: 'Device profile-specific',
    1 << 6: 'Reserved (always 0)',
    1 << 7: 'Motion Error',
}
"""Error code -> Error message string lookup."""


def stringify_error(value: int, errorDict: dict) -> str:
    """Concatenate error messages for a given error value."""
    messages = []
    for mask, message in errorDict.items():
        if check_bit_mask(value, mask):
            messages.append(message)

    return ', '.join(messages)
