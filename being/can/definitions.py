"""Some CANopen definitions. EDS independent."""
import enum


# Some non-mandatory fields and vendor specific object dictionary entries. Index
# ranges:
#   0x0000:          Reserved
#   0x0001 - 0x009f: Data types
#   0x00a0 - 0x0fff: Reserved
#   0x1000 - 0x1fff: Communication Profile Area (CiA 301)
#   0x2000 - 0x5fff: Manufacturer-specific Profile Area
#   0x6000 - 0x9fff: Standardized Device Area (CiA 402)
#   0xa000 - 0xffff: Reserved
STORE_EDS = 0x1021  # Some manufacturer use this for downloading object
                    # dictionary from device.
                    # Not with Maxon nor Faulhaber ?!

# Faulhaber specific registers (not with Maxon!)
MOTOR_DATA = 0x2350
ENCODER_DATA = 0x2351


class FunctionCode(enum.IntEnum):

    """Canopen function operation codes.

    Todo:
        Is ``FunctionCode`` the right name for this?
    """

    NMT = (0b0000 << 7)  # 0x0 + node id
    SYNC = (0b0001 << 7)  # 0x80 + node id
    EMERGENCY = (0b0001 << 7)  # 0x80 + node id
    PDO1tx = (0b0011 << 7)  # 0x180 + node id
    PDO1rx = (0b0100 << 7)  # 0x200 + node id
    PDO2tx = (0b0101 << 7)  # 0x280 + node id
    PDO2rx = (0b0110 << 7)  # 0x300 + node id
    PDO3tx = (0b0111 << 7)  # 0x380 + node id
    PDO3rx = (0b1000 << 7)  # 0x400 + node id
    PDO4tx = (0b1001 << 7)  # 0x480 + node id
    PDO4rx = (0b1010 << 7)  # 0x500 + node id
    SDOtx = (0b1011 << 7)  # 0x580 + node id
    SDOrx = (0b1100 << 7)  # 0x600 + node id
    NMTErrorControl = (0b1110 << 7)  # 0x700 + node id


class TransmissionType(enum.IntEnum):

    """PDO transmission type."""

    SYNCHRONOUS_ACYCLIC = 0

    # 1 - 240 synchronous cyclic. Value = # SYNC objects until PDO is send
    SYNCHRONOUS_CYCLIC = 1
    ...

    ASYNCHRONOUS_RTR = 253
    ASYNCHRONOUS = 255
