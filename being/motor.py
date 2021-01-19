"""Motor block."""
from typing import Optional

from being.backends import CanBackend
from being.block import Block
from being.can import load_object_dictionary
from being.can.cia_402 import CiA402Node, OperationMode
from being.can.cia_402 import State as State402
from being.can.definitions import TransmissionType
from being.config import SI_2_FAULHABER, INTERVAL
from being.can.nmt import PRE_OPERATIONAL
from being.connectables import ValueInput, ValueOutput
from being.kinematics import kinematic_filter
from being.kinematics import State as KinematicState
from being.resources import register_resource


def create_node(network, nodeId):
    od = load_object_dictionary(network, nodeId)
    node = CiA402Node(nodeId, od)
    network.add_node(node, object_dictionary=od)
    return node


class Motor(Block):

    """Motor blocks which takes set-point values through its inputs and outputs
    the current actual position value through its output. The input position
    values are filtered with a kinematic filter. Encapsulates a and setups a
    CiA402Node. Currently only tested with Faulhaber linear drive (0.04 m).

    Attributes:
        network (CanBackend): Associsated network:
        node (CiA402Node): Drive node.
        state (State): Kinematic state.
    """
    def __init__(self, nodeId: int,
            # TODO: Which args? Rod length, direction, maxSpeed, maxAcc, ...?
            network: Optional[CanBackend] = None,
            node: Optional[CiA402Node] = None):
        """Args:
            nodeId: CANopen node id.

        Kwargs:
            network: External network (dependency injection).
            node: Drive node (dependency injection).
        """
        super().__init__()
        if network is None:
            network = CanBackend.default()
            register_resource(network, duplicates=False)

        if node is None:
            node = create_node(network, nodeId)

        self.nodeId = nodeId
        #self.length = length
        #self.direction = sign(direction)
        self.network = network

        self.targetPosition, = self.inputs = [ValueInput(owner=self)]
        self.actualPosition, = self.outputs = [ValueOutput(owner=self)]

        self.state = KinematicState(position=node.position)
        self.node = node

        self.setup_pdos()
        node.nmt.state = PRE_OPERATIONAL
        node.set_state(State402.READY_TO_SWITCH_ON)
        node.set_operation_mode(OperationMode.CYCLIC_SYNCHRONOUS_POSITION)

    def setup_pdos(self):
        """Configure PDOs of node. We only use 'Position Actual Value' and
        'Target Position' in PDO2.
        """
        # We overwrite and clear all the defaults. By default the Controlword
        # and Statusword appear in multiple PDOs. This can lead to unexpected
        # behavior since for example:
        #
        #     node.pdo['Controlword'] = Command.ENABLE_OPERATION
        #
        # will only set the value in the first PDO with one Controlword but not
        # the others. In these the controlword will stay zero and subsequently
        # shut down the motor.
        node = self.node
        node.pdo.read()  # Load both node.tpdo and node.rpdo

        # Clear all rx PDOs and Position Actual Value -> PDO2
        for i, tx in enumerate(node.tpdo.values(), start=1):
            tx.clear()
            if i == 2:
                tx.add_variable('Position Actual Value')
                tx.enabled = True
                tx.trans_type = TransmissionType.SYNCHRONOUS_CYCLIC
                tx.event_timer = 0
            else:
                tx.enabled = False

            tx.save()

        # Clear all rx PDOs and Target Position -> PDO2
        for i, rx in enumerate(node.rpdo.values(), start=1):
            rx.clear()
            if i == 2:
                rx.add_variable('Target Position')
                rx.enabled = True
            else:
                rx.enabled = False

            rx.save()

    def update(self):
        # Fetch actual position
        self.output.value = self.node.pdo['Position Actual Value'].raw / SI_2_FAULHABER

        # Kinematic filter input target position
        self.state = kinematic_filter(
            targets=self.input.value,
            dt=INTERVAL,
            state=self.state,
            maxSpeed=1.,
            maxAcc=1.,
        )

        # Set target position
        soll = SI_2_FAULHABER * self.state.position
        self.node.pdo['Target Position'].raw = soll
        self.node.rpdo[2].transmit()

    def __str__(self):
        return f'{type(self).__name__}(nodeId={self.nodeId})'
