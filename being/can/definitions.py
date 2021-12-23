"""Some CANopen definitions."""
import enum


class FunctionCode(enum.IntEnum):

    """Canopen function operation codes.

    Todo:
        Is ``FunctionCode`` the right name for this?
    """

    NMT = (0b0000 << 7)
    """0x0 + node id :hex:"""

    SYNC = (0b0001 << 7)
    """0x80 + node id :hex:"""

    EMERGENCY = (0b0001 << 7)
    """0x80 + node id :hex:"""

    PDO1tx = (0b0011 << 7)
    """0x180 + node id :hex:"""

    PDO1rx = (0b0100 << 7)
    """0x200 + node id :hex:"""

    PDO2tx = (0b0101 << 7)
    """0x280 + node id :hex:"""

    PDO2rx = (0b0110 << 7)
    """0x300 + node id :hex:"""

    PDO3tx = (0b0111 << 7)
    """0x380 + node id :hex:"""

    PDO3rx = (0b1000 << 7)
    """0x400 + node id :hex:"""

    PDO4tx = (0b1001 << 7)
    """0x480 + node id :hex:"""

    PDO4rx = (0b1010 << 7)
    """0x500 + node id :hex:"""

    SDOtx = (0b1011 << 7)
    """0x580 + node id :hex:"""

    SDOrx = (0b1100 << 7)
    """0x600 + node id :hex:"""

    NMTErrorControl = (0b1110 << 7)
    """0x700 + node id :hex:"""


class TransmissionType(enum.IntEnum):

    """PDO transmission type."""

    SYNCHRONOUS_ACYCLIC = 0

    # 1 - 240 synchronous cyclic. Value = # SYNC objects until PDO is send
    SYNCHRONOUS_CYCLIC = 1
    ...

    SYNCHRONOUS_RTR = 252  # not recommended anymore
    ASYNCHRONOUS_RTR = 253  # not recommended anymore
    ASYNCHRONOUS_INTERNAL = 254
    ASYNCHRONOUS = 255
