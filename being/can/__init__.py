"""CAN / CANopen related stuff."""
import contextlib

from canopen import Network, ObjectDictionary
from canopen.sdo import SdoClient, SdoCommunicationError, SdoAbortedError
from canopen.objectdictionary.eds import import_eds

from being.can.definitions import FunctionCode, DEVICE_TYPE, STORE_EDS


SUPPORTED_DEVICE_TYPES = {
    b'\x92\x01\x42\x00': 'resources/MCLM3002P-CO.eds',
}


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
            deviceType = client.open(DEVICE_TYPE).read()
        except SdoCommunicationError as err:
            raise RuntimeError(f'CANopen node {nodeId} is not reachable!')

        # Try to download object dictionary from node
        try:
            edsFp = client.open(STORE_EDS, mode='rt')
            return import_eds(edsFp, nodeId)
        except SdoAbortedError as err:
            pass

        # Check if we know the node
        if deviceType in SUPPORTED_DEVICE_TYPES:
            fp = SUPPORTED_DEVICE_TYPES[deviceType]
            return import_eds(fp, nodeId)

    raise RuntimeError(f'Unknown CANopen node {nodeId}. Could not load object dictionary!')