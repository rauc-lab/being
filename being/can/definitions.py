import enum

# Mandatory CiA 302
DEVICE_TYPE = 0x1000
#ERROR_REGISTER = 0x1001
#IDENTITY_OBJECT = 0x1018
#VENDOR_ID = 0x1018, 1
#PRODUCT_CODE = 0x1018, 2
#REVISION_NUMBER = 0x1018, 3
#SERIAL_NUMBER = 0x1018, 4

# Non-mandatory fields
#MANUFACTURER_DEVICE_NAME = 0x1008
STORE_EDS = 0x1021

# CiA 402
CONTROLWORD = 0x6040
STATUSWORD = 0x6041
TARGET_VELOCITY = 0x60FF
TARGET_POSITION = 0x607A
TARGET_TORQUE = 0x6071
OPERATION_MODE = 0x6070
OPERATION_MODE_DISPLAY = 0x6071
SUPPORTED_DRIVE_MODES = 0x6502


class FunctionCode(enum.IntEnum):

    """Canopen function operation codes.
    TODO: Is 'FunctionCode' the right name for this?
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
