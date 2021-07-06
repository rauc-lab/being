"""Vendor specific definitions and lookups."""
from typing import NamedTuple


class Units(NamedTuple):

    """Device units. SI <-> CanOpen vender specific units."""

    length: float = 1.
    current: float = 1.
    kinematics: float = 1.


UNITS = {
    r'MCLM3002P-CO': Units(length=1e6, current=1000, kinematics=1000),
}

FAULHABER_ERRORS = {
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
# TODO: Generalize for other vendors!
