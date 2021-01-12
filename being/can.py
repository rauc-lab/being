"""Some being specific CAN functionality."""
import contextlib
import enum
import sys
from typing import NamedTuple

from canopen import Network, SdoAbortedError, SdoCommunicationError
from canopen.sdo import SdoClient
from canopen.objectdictionary import ObjectDictionary
from canopen.objectdictionary.eds import import_eds


SUPPORTED_DEVICE_TYPES = {
    b'\x92\x01\x42\x00': 'resources/MCLM3002P-CO.eds',
}


class Address(NamedTuple):

    """CANopen parameter address."""

    index: int
    subindex: int = 0


# Mandatory CiA 302 fields
DEVICE_TYPE = Address(0x1000)
#ERROR_REGISTER = Address(0x1001)
#IDENTITY_OBJECT = Address(0x1018)
#VENDOR_ID = Address(0x1018, 1)
#PRODUCT_CODE = Address(0x1018, 2)
#REVISION_NUMBER = Address(0x1018, 3)
#SERIAL_NUMBER = Address(0x1018, 4)


# Non-mandatory fields
#MANUFACTURER_DEVICE_NAME = Address(0x1008)
STORE_EDS = Address(0x1021, 0)


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


@contextlib.contextmanager
def sdo_client(network: Network, nodeId: int, od=None):
    """Temporary SDO client. For accessing SDO data without an object dictionary
    / EDS.

    Args:
        network: Connected CANopen network.
        nodeId: Node ID.

    Yields:
        SdoClient instance.

    Usage:
        >>> with sdo_client(network, nodeId=8) as client:
        ...     deviceType = client.upload(0x1000, subindex=0)
        ...     print('deviceType:', deviceType)
        deviceType: b'\x92\x01B\x00'
    """
    if od is None:
        od = ObjectDictionary()

    rxCob = FunctionCode.SDOrx + nodeId
    txCob = FunctionCode.SDOtx + nodeId
    client = SdoClient(rxCob,txCob, od)
    client.network = network
    network.subscribe(txCob, client.on_response)
    try:
        yield client

    finally:
        network.unsubscribe(txCob)


def load_object_dictionary(network, nodeId):
    """Get object dictionary for node. Ping node, try to download EDS from it,
    see if we have a fallback. RuntimeError otherwise.
    """
    with sdo_client(network, nodeId) as client:
        # Ping node
        try:
            deviceType = client.upload(*DEVICE_TYPE)
        except SdoCommunicationError as err:
            raise RuntimeError(f'CANopen node {nodeId} is not reachable!')

        # Try to download object dictionary from node
        try:
            edsFp = client.open(*STORE_EDS, mode='rt')
            return import_eds(edsFp, nodeId)
        except SdoAbortedError as err:
            pass

        # Check if we know the node
        if deviceType in SUPPORTED_DEVICE_TYPES:
            fp = SUPPORTED_DEVICE_TYPES[deviceType]
            return import_eds(fp, nodeId)

    raise RuntimeError(f'Unknown CANopen node {nodeId}. Could not load object dictionary!')
