"""CAN / CANopen related stuff."""
import pkgutil
import contextlib
import io
import os

from canopen import Network, ObjectDictionary
from canopen.sdo import SdoClient, SdoCommunicationError, SdoAbortedError
from canopen.objectdictionary.eds import import_eds

from being.can.definitions import FunctionCode, STORE_EDS
from being.can.cia_301 import DEVICE_TYPE


SUPPORTED_DEVICE_TYPES = {
    b'\x92\x01\x42\x00': 'eds_files/MCLM3002P-CO.eds',
    b'\x92\x01\x02\x00': 'eds_files/maxon_EPOS4_50-5.eds',
}
"""Device type: bytes -> local EDS file."""


@contextlib.contextmanager
def sdo_client(network: Network, nodeId: int, od=None):
    """Temporary SDO client. For accessing SDO data without an object dictionary
    / EDS.

    Args:
        network: Connected CANopen network.
        nodeId: Node ID.

    Yields:
        SdoClient instance.

    Example:
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


def _load_local_eds(deviceType: bytes) -> io.StringIO:
    """Given deviceType try to load local EDS file.

    Args:
        deviceType: Raw device type from node.

    Returns:
        EDS file content wrapped in StringIO buffer.
    """
    fp = SUPPORTED_DEVICE_TYPES[deviceType]
    data = pkgutil.get_data(__name__, fp)
    return io.StringIO(data.decode())


def load_object_dictionary(network, nodeId: int) -> ObjectDictionary:
    """Get object dictionary for node. Ping node, try to download EDS from it,
    see if we have a fallback. RuntimeError otherwise.

    Args:
        network (Network / CanBackend): Connected CAN network.
        nodeId: Node ID to load object dictionary for.

    Returns:
        Object dictionary for node.
    """
    with sdo_client(network, nodeId) as client:
        # Ping node
        try:
            deviceType = client.open(DEVICE_TYPE).read()
        except SdoCommunicationError as err:
            raise RuntimeError(f'CANopen node {nodeId} is not reachable!') from err

        # Try to download remote object dictionary from node
        try:
            edsFp = client.open(STORE_EDS, mode='rt')
            return import_eds(edsFp, nodeId)
        except SdoAbortedError:
            pass

        # Try to load local object dictionary
        if deviceType in SUPPORTED_DEVICE_TYPES:
            filelike = _load_local_eds(deviceType)
            return import_eds(filelike, nodeId)

    raise RuntimeError(f'Unknown CANopen node {nodeId}. Could not load object dictionary!')
