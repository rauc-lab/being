"""Motor block."""
import time

from typing import Optional, Iterable, Generator

from being.backends import CanBackend
from being.bitmagic import check_bit_mask
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
from being.can.nmt import PRE_OPERATIONAL
from being.config import CONFIG
from being.connectables import ValueInput, ValueOutput
from being.constants import INF
from being.error import BeingError
from being.kinematics import State as KinematicState
from being.kinematics import kinematic_filter
from being.logging import get_logger
from being.math import sign
from being.resources import register_resource


HomingState = bool  # TODO(atheler): We should probabelly switch to an enum.

STILL_HOMING: HomingState = True
"""Indicates that homing job is still in progress."""

DONE_HOMING: HomingState = False
"""Indicates that homing job has finished."""


FAULHABER_ERRORS = {
    0x0001: 'Continuous Over Current',
    0x0002: 'Deviation',
    0x0004: 'Over Voltage',
    0x0008: 'Over Temperature',
    0x0010: 'Flash Memory Error',
    0x0040: 'CAN In Error Passive Mode',
    0x0080: 'CAN Overrun (objects lost)',
    0x0100: 'Life Guard Or Heart- beat Error',
    0x0200: 'Recovered From Bus Off',
    0x0800: 'Conversion Overflow',
    0x1000: 'Internal Software',
    0x2000: 'PDO Length Exceeded',
    0x4000: 'PDO not processes due to length error',
}


SI_2_FAULHABER = CONFIG['Can']['SI_2_FAULHABER']
INTERVAL = CONFIG['General']['INTERVAL']


class DriveError(BeingError):

    """Something went wrong on the drive."""


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


def home_motors(motors: Iterable, interval: float = .01, timeout: float = 5., **kwargs):
    """Home multiple motors in parallel. This operation will block for time of
    homing.

    Args:
        motors: Motors to home.

    Kwargs:
        interval: Tmp. main loop interval for homing.
        timeout: Maximum homing duration. RuntimeError if homing takes to long.
        kwargs: Optional arguments for homing jobs.
    """
    homingJobs = [mot.home(**kwargs) for mot in motors]
    starTime = time.perf_counter()

    while any([next(job) == STILL_HOMING for job in homingJobs]):
        passed = time.perf_counter() - starTime
        if passed > timeout:
            raise RuntimeError(f'Could not home all motors before timeout {timeout} sec.!')

        time.sleep(interval)


def stringify_faulhaber_error(value: int) -> str:
    """Concatenate error messages for a given error value."""
    messages = []
    for mask, message in FAULHABER_ERRORS.items():
        if check_bit_mask(value, mask):
            messages.append(message)

    return ', '.join(messages)


class _MotorBase(Block):

    """Motor base class."""

    def __init__(self):
        super().__init__()
        self.add_value_input()
        self.add_value_output()

    def home(self):
        yield DONE_HOMING


class Motor(_MotorBase):

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
            length: Rod length if known.
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
        self.logger = get_logger(str(self))

        self.targetPosition, = self.inputs = [ValueInput(owner=self)]
        self.actualPosition, = self.outputs = [ValueOutput(owner=self)]

        self.node = node

        self.setup_node()
        self.setup_pdos()

        node.nmt.state = PRE_OPERATIONAL
        node.set_state(State402.READY_TO_SWITCH_ON)
        node.set_operation_mode(OperationMode.CYCLIC_SYNCHRONOUS_POSITION)

    def setup_node(self, maxSpeed: float = 5., maxAcc: float = 5.):
        """Configure Faulhaber node (some settings via SDO).

        Kwargs:
            maxSpeed: Maximum speed.
            maxAcc: Maximum acceleration.
        """
        generalSettings = self.node.sdo['General Settings']
        generalSettings['Pure Sinus Commutation'].raw = 1
        #generalSettings['Activate Position Limits in Velocity Mode'].raw = 1
        #generalSettings['Activate Position Limits in Position Mode'].raw = 1

        filterSettings = self.node.sdo['Filter Settings']
        filterSettings['Sampling Rate'].raw = 4
        filterSettings['Gain Scheduling Velocity Controller'].raw = 1

        velocityController = self.node.sdo['Velocity Control Parameter Set']
        velocityController['Proportional Term POR'].raw = 44
        velocityController['Integral Term I'].raw = 50

        posController = self.node.sdo['Position Control Parameter Set']
        posController['Proportional Term PP'].raw = 15
        posController['Derivative Term PD'].raw = 10
        # Some softer params from pygmies
        #posController['Proportional Term PP'].raw = 8
        #posController['Derivative Term PD'].raw = 14

        curController = self.node.sdo['Current Control Parameter Set']
        curController['Continuous Current Limit'].raw = 1000 * 0.550  # [mA]
        curController['Peak Current Limit'].raw = 1000 * 1.640  # [mA]
        curController['Integral Term CI'].raw = 3

        self.node.sdo['Max Profile Velocity'].raw = 1000 * maxSpeed  # [mm / s]
        self.node.sdo['Profile Acceleration'].raw = 1000 * maxAcc  # [mm / s^2]
        self.node.sdo['Profile Deceleration'].raw = 1000 * maxAcc  # [mm / s^2]

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
        for nr, tx in enumerate(node.tpdo.values(), start=1):
            tx.clear()
            if nr == 1:
                tx.add_variable('Statusword')
                tx.add_variable('Error Register')
                tx.add_variable('Position Actual Value')
                tx.enabled = True
                tx.trans_type = TransmissionType.SYNCHRONOUS_CYCLIC
                tx.event_timer = 0
            else:
                tx.enabled = False

            tx.save()

        # Clear all rx PDOs and Target Position -> PDO2
        for nr, rx in enumerate(node.rpdo.values(), start=1):
            rx.clear()
            if nr == 1:
                rx.add_variable('Target Position')
                rx.enabled = True
            else:
                rx.enabled = False

            rx.save()

    def home(self, speed: int = 100, deadCycles: int = 20) -> Generator[HomingState, None, None]:
        """Crude homing procedure. Move with PROFILED_VELOCITY operation mode
        upwards and downwards until reaching limits (position not increasing or
        decreasing anymore). Implemented as Generator so that we can home
        multiple motors in parallel (quasi pseudo coroutine). time.sleep has to
        be handled by the caller.

        Kwargs:
            speed: Homing speed.
            deadCycles: Number of cycles we give the motor to start moving in a direction.

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
            node.change_state(State402.READY_TO_SWITCH_ON)
            node.sdo[HOMING_OFFSET].raw = 0
            #TODO: Do we need to set NMT to 'OPERATIONAL'?
            node.set_operation_mode(OperationMode.PROFILED_VELOCITY)
            node.change_state(State402.OPERATION_ENABLE)

            # Move upwards
            logger.info('Moving upwards')
            pos = node.sdo[POSITION_ACTUAL_VALUE].raw
            upper = -INF
            _move(node, direction * speed)
            for _ in range(deadCycles):
                yield STILL_HOMING

            while pos > upper:
                #logger.debug('Homing up pos: %d', pos)
                upper = pos
                yield STILL_HOMING
                pos = node.sdo[POSITION_ACTUAL_VALUE].raw

            # Move downwards
            logger.info('Moving downwards')
            lower = INF
            _move(node, -direction * speed)
            for _ in range(deadCycles):
                yield STILL_HOMING

            while pos < lower:
                #logger.debug('Homing down pos: %d', pos)
                lower = pos
                yield STILL_HOMING
                pos = node.sdo[POSITION_ACTUAL_VALUE].raw

            # Take into account rod length
            width = upper - lower
            if self.length is not None:
                dx = .5 * (width - self.length * SI_2_FAULHABER)
                if dx > 0:
                    lower, upper = lower + dx, upper - dx

            node.change_state(State402.READY_TO_SWITCH_ON)
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
        err = self.node.pdo['Error Register'].raw
        if err:
            msg = stringify_faulhaber_error(err)
            #raise DriveError(msg)
            self.logger.error('DriveError: %s', msg)

        # Set target position
        soll = SI_2_FAULHABER * self.input.value
        self.node.pdo['Target Position'].raw = soll
        self.node.rpdo[1].transmit()

        # Fetch actual position
        self.output.value = self.node.pdo['Position Actual Value'].raw / SI_2_FAULHABER

    def __str__(self):
        return f'{type(self).__name__}(nodeId={self.nodeId})'


class DummyMotor(_MotorBase):

    """Dummy motor for testing and standalone usage."""

    def __init__(self, length=0.04):
        super().__init__()
        self.length = length
        self.add_value_input()
        self.add_value_output()
        self.state = KinematicState()

    def home(self, speed: int = 100):
        yield DONE_HOMING

    def update(self):
        # Kinematic filter input target position
        self.state = kinematic_filter(
            self.input.value,
            dt=INTERVAL,
            state=self.state,
            maxSpeed=1.,
            maxAcc=1.,
            lower=0.,
            upper=self.length,
        )

        self.output.value = self.state.position
