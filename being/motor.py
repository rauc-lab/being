"""Motor block."""
import logging
import time

from typing import Optional

from being.backends import CanBackend
from being.block import Block
from being.can import load_object_dictionary
from being.can.cia_402 import CiA402Node, OperationMode, Command, CW, State
from being.can.cia_402 import State as State402
from being.can.definitions import (
    CONTROLWORD,
    HOMING_OFFSET,
    POSITION_ACTUAL_VALUE,
    SOFTWARE_POSITION_LIMIT,
    TARGET_VELOCITY,
    TransmissionType,
)
from being.config import SI_2_FAULHABER, INTERVAL
from being.can.nmt import PRE_OPERATIONAL
from being.connectables import ValueInput, ValueOutput
from being.constants import INF
from being.kinematics import kinematic_filter
from being.kinematics import State as KinematicState
from being.math import sign
from being.resources import register_resource


STILL_HOMING = True
DONE_HOMING = False


def create_node(network, nodeId):
    """CiA402Node factory."""
    # TODO: Support for different motors / different CiA402Node subclasses?
    od = load_object_dictionary(network, nodeId)
    node = CiA402Node(nodeId, od)
    network.add_node(node, object_dictionary=od)
    return node


def _move(node, speed: int):
    """Move motor with constant speed."""
    node.sdo[TARGET_VELOCITY].raw = speed
    node.sdo[CONTROLWORD].raw = Command.ENABLE_OPERATION | CW.NEW_SET_POINT


def home_motors(motors, interval=.01, timeout=4., **kwargs):
    """Home multiple drives in parallel."""
    homings = [mot.home(**kwargs) for mot in motors]
    starTime = time.perf_counter()
    while any(map(next, homings)):
        passed = time.perf_counter() - starTime
        if passed > timeout:
            raise RuntimeError('Could not home all motors before timeout')

        time.sleep(interval)

    return True


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
            length: Optional[float] = None,
            # TODO: Which args? direction, maxSpeed, maxAcc, ...?
            network: Optional[CanBackend] = None,
            node: Optional[CiA402Node] = None):
        """Args:
            nodeId: CANopen node id.

        Kwargs:
            length: Rod length (used for homing).
            network: External network (dependency injection).
            node: Drive node (dependency injection).
        """
        super().__init__()
        if network is None:
            network = CanBackend.single_instance_setdefault()
            register_resource(network, duplicates=False)

        if node is None:
            node = create_node(network, nodeId)

        self.nodeId = nodeId
        self.length = length
        #self.direction = sign(direction)
        self.network = network
        self.logger = logging.getLogger(str(self))

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

    def home(self, speed: int = 100):
        """Crude homing procedure. Move with PROFILED_VELOCITY operation mode
        upwards and downwards until reaching limits (position not increasing or
        decreasing anymore). Implemented as Generator so that we can home
        multiple motors in parallel (quasi pseudo coroutine). time.sleep has to
        be handled by the caller.

        Kwargs:
            speed: Homing speed.

        Yields:
            Homing state.
        """
        direction = sign(speed)
        speed = abs(speed)
        node = self.node
        logger = self.logger
        logger.info('Starting homing for %s', node)
        with node.restore_states_and_operation_mode():
            node.nmt.state = 'PRE-OPERATIONAL'
            node.change_state(State.READY_TO_SWITCH_ON)
            node.sdo[HOMING_OFFSET].raw = 0
            #TODO: Do we need to set NMT to 'OPERATIONAL'?
            node.set_operation_mode(OperationMode.PROFILED_VELOCITY)
            node.change_state(State.OPERATION_ENABLE)

            logger.info('Moving upwards')
            pos = node.sdo[POSITION_ACTUAL_VALUE].raw
            upper = -INF
            _move(node, direction * speed)
            while pos > upper:
                upper = pos
                yield STILL_HOMING
                pos = node.sdo[POSITION_ACTUAL_VALUE].raw

            logger.info('Moving downwards')
            lower = INF
            _move(node, -direction * speed)
            while pos < lower:
                lower = pos
                yield STILL_HOMING
                pos = node.sdo[POSITION_ACTUAL_VALUE].raw

            width = upper - lower
            if self.length:
                dx = .5 * (width - self.length * SI_2_FAULHABER)
                if dx > 0:
                    lower, upper = lower + dx, upper - dx

            node.change_state(State.READY_TO_SWITCH_ON)
            node.sdo[HOMING_OFFSET].raw = lower
            node.sdo[SOFTWARE_POSITION_LIMIT][1].raw = 0
            node.sdo[SOFTWARE_POSITION_LIMIT][2].raw = upper - lower

            logger.info('Homed')
            logger.debug('HOMING_OFFSET:              %s', lower)
            logger.debug('SOFTWARE_POSITION_LIMIT[1]: %s', 0)
            logger.debug('SOFTWARE_POSITION_LIMIT[2]: %s', upper - lower)

        self.state = KinematicState(position=node.position)
        while True:
            yield DONE_HOMING

    def update(self):
        # Fetch actual position
        self.output.value = self.node.pdo['Position Actual Value'].raw / SI_2_FAULHABER

        # Kinematic filter input target position
        self.state = kinematic_filter(
            self.input.value,
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
