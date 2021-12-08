"""CiA 301 object dictionary address definitions."""


# Mandatory CiA 301
DEVICE_TYPE: int = 0x1000
"""Indication of the device type. :hex:"""

ERROR_REGISTER: int = 0x1001
"""Error register. :hex:"""

IDENTITY_OBJECT: int = 0x1018
"""Identity object. :hex:"""

VENDOR_ID: int = 1
"""Identity object vendor id subindex."""

PRODUCT_CODE: int = 2
"""Identity object product code subindex."""

REVISION_NUMBER: int = 3
"""Identity object revision number subindex."""

SERIAL_NUMBER: int = 4
"""Identity object serial number subindex."""

COB_ID_EMCY: int = 0x1014
"""CAN object identifier of the emergency object. :hex:"""

# Optional CiA 301
COB_ID_SYNC: int = 0x1005
"""CAN object identifier of the SYNC object. :hex:"""

MANUFACTURER_DEVICE_NAME: int = 0x1008
"""Device name. :hex:"""

MANUFACTURER_HARDWARE_VERSION: int = 0x1009
"""Hardware version. :hex:"""

MANUFACTURER_SOFTWARE_VERSION: int = 0x100A
"""Software version. :hex:"""
