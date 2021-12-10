"""All things CAN / CANopen.

Quick primer on CanOpen. CanOpen is a communication protocol that builds on top
of CAN. There are two main ways of communication: *SDO* and *PDO*.  The
addresses for values are stored in the *Object Dictionary* with an *index* value
and optionally with a *sub-index*. The index is commonly noted in hex.

There are many different standardized communication parameters device profiles.
For motors of main interest are:
- CiA 301 - CANopen application layer and communication profile
- CiA 402 - CANopen device profile for drives and motion control

CiA 301 are some standard addresses. CiA 402 defines a device state machine,
different operation modes, homing and communication procedure for triggering
motion on the motors.

See Also:
    - `CAN bus on Wikipedia <https://en.wikipedia.org/wiki/CAN_bus>`_
    - `CANopen on Wikipedia <https://en.wikipedia.org/wiki/CANopen>`_
    - `Python canopen doc <https://canopen.readthedocs.io/en/latest/index.html>`_
"""
import pkgutil
import contextlib
import io
import os
from typing import Dict, Optional, Iterator

from canopen import Network, ObjectDictionary
from canopen.sdo import SdoClient, SdoCommunicationError, SdoAbortedError
from canopen.objectdictionary.eds import import_eds

from being.can.definitions import FunctionCode
from being.can.cia_301 import DEVICE_TYPE


STORE_EDS: int = 0x1021
"""Some manufacturer use this for downloading the object dictionary directly
from the device. :hex:
"""

SUPPORTED_DEVICE_TYPES: Dict[bytes, str] = {
    b'\x92\x01\x42\x00': 'eds_files/MCLM3002P-CO.eds',
    b'\x92\x01\x02\x00': 'eds_files/maxon_EPOS4_50-5.eds',
}
"""Device type bytes to local EDS file mapping."""


@contextlib.contextmanager
def sdo_client(network: Network, nodeId: int, od: Optional[ObjectDictionary] = None) -> Iterator[SdoClient]:
    """Temporary SDO client connection. Can be used for SDO communication
    connection without having an object dictionary / EDS at hand. Without object
    dictionary only integer based addresses are supported.

    Args:
        network: Connected CANopen network.
        nodeId: Node ID.
        od (optional): Object dictionary.

    Yields:
        SdoClient instance.

    Example:
        >>> with sdo_client(network, nodeId=8) as client:
        ...     deviceType = client.upload(0x1000, subindex=0)
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


def load_object_dictionary(network: Network, nodeId: int) -> ObjectDictionary:
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
