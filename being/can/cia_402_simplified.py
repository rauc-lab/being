from typing import Iterable
try:
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping
import canopen
from canopen.pdo import PdoBase, Map, PDO
from canopen.nmt import NmtMaster
from canopen.emcy import EmcyConsumer
from .cia_402 import CiA402Node

from canopen import ObjectDictionary, RemoteNode
from being.backends import CanBackend
from being.can.definitions import TransmissionType
from being.logging import get_logger
from being.can.cia402_definitions import *


class Maps(Mapping):
    def __init__(self):
        self.maps: Dict[int, "Map"] = {}

    def __getitem__(self, key: int) -> "Map":
        return self.maps[key]

    def __iter__(self) -> Iterable[int]:
        return iter(self.maps)

    def __len__(self) -> int:
        return len(self.maps)


class TPDONoMap(PdoBase):
    """Transmit PDO to broadcast data from the represented node to the network.

    Properties 0x1800 to 0x1803 | Mapping 0x1A00 to 0x1A03.
    :param object node: Parent node for this object.
    """

    def __init__(self, node):
        super(TPDONoMap, self).__init__(node)
        self.map = Maps()

    def stop(self):
        """Stop transmission of all TPDOs.

        :raise TypeError: Exception is thrown if the node associated with the PDO does not
        support this function.
        """
        if isinstance(self.node, canopen.LocalNode):
            for pdo in self.map.values():
                pdo.stop()
        else:
            raise TypeError('The node type does not support this function.')


class RPDONoMap(PdoBase):
    """Receive PDO to transfer data from somewhere to the represented node.

    Properties 0x1400 to 0x1403 | Mapping 0x1600 to 0x1603.
    :param object node: Parent node for this object.
    """

    def __init__(self, node):
        super(RPDONoMap, self).__init__(node)
        self.map = Maps()

    def stop(self):
        """Stop transmission of all RPDOs.

        :raise TypeError: Exception is thrown if the node associated with the PDO does not
        support this function.
        """
        if isinstance(self.node, canopen.RemoteNode):
            for pdo in self.map.values():
                pdo.stop()
        else:
            raise TypeError('The node type does not support this function.')


class StepperCiA402Node(CiA402Node):
    supported_operation_modes = {
        OperationMode.PROFILE_POSITION,
        OperationMode.PROFILE_VELOCITY,
        OperationMode.HOMING
    }

    def __init__(self, nodeId: int, objectDictionary: ObjectDictionary, network: CanBackend):
        # do not use the __init__() of CiA402Node
        super(RemoteNode, self).__init__(nodeId, objectDictionary)

        self.logger = get_logger(str(self))

        network.send_message(0, bytes([0x01, self.id]))

        self.sdo_channels = []
        self.sdo = self.add_sdo(0x600 + self.id, 0x580 + self.id)
        self.tpdo = TPDONoMap(self)
        self.rpdo = RPDONoMap(self)
        self.pdo = PDO(self, self.rpdo, self.tpdo)
        self.nmt = NmtMaster(self.id)
        self.emcy = EmcyConsumer()

        network.add_node(self, objectDictionary)

        rx = Map(self.rpdo, self.sdo[0x1401], 0)
        rx.cob_id = 0x300 + nodeId
        rx.add_variable(CONTROLWORD)
        rx.add_variable(TARGET_POSITION)
        rx.enabled = True
        rx.trans_type = TransmissionType.SYNCHRONOUS_CYCLIC
        rx.subscribe()
        network.register_rpdo(rx)
        self.rpdo.map.maps[2] = rx

        tx = Map(self.tpdo, self.sdo[0x1800], 0)
        tx.cob_id = 0x180 + nodeId
        tx.add_variable(STATUSWORD)
        tx.enabled = True
        tx.trans_type = TransmissionType.ASYNCHRONOUS
        tx.subscribe()
        self.tpdo.map.maps[1] = tx

        self.associate_network(network)

    def get_operation_mode(self) -> OperationMode:
        """Get current operation mode."""
        return OperationMode(self.sdo[MODES_OF_OPERATION].raw)

    def set_operation_mode(self, op: OperationMode):
        """Set operation mode.

        Args:
            op: New target mode of operation.
        """
        self.logger.debug('Switching to %s', op)
        current = self.get_operation_mode()
        if current == op:
            self.logger.debug('Already %s', op)
            return

        state = self.get_state()
        if state not in VALID_OP_MODE_CHANGE_STATES:
            raise RuntimeError(f'Can not change to {op} when in {state}')

        if op not in self.supported_operation_modes:
            raise RuntimeError(f'This drive does not support {op!r}!')

        self.sdo[MODES_OF_OPERATION].raw = op

    def set_target_position(self, pos):
        """Set target position in device units."""
        pos = int(pos * 10)  # TODO: factor!
        self.sdo[CONTROLWORD].raw = Command.ENABLE_OPERATION
        import time
        time.sleep(.1)  # FIXME
        self.rpdo[TARGET_POSITION].raw = pos
        self.rpdo[CONTROLWORD].raw = Command.ENABLE_OPERATION | CW.NEW_SET_POINT

    def get_actual_position(self):
        """Get actual position in device units."""
        return self.sdo[POSITION_ACTUAL_VALUE].raw / 10  # TODO: factor!

    def manufacturer_device_name(self):
        """Get manufacturer device name."""
        return 'PathosStepper'
