"""Motor block."""
import time
from typing import Optional, Iterable, Generator

from being.backends import CanBackend
from being.bitmagic import check_bit_mask
from being.block import Block
from being.can import load_object_dictionary
from being.can.cia_402 import CiA402Node, OperationMode, Command, CW
from being.can.cia_402 import State as CiA402State

from being.can.definitions import (
    CONTROLWORD,
    HOMING_OFFSET,
    POSITION_ACTUAL_VALUE,
    SOFTWARE_POSITION_LIMIT,
    TARGET_VELOCITY,
)
from being.can.nmt import PRE_OPERATIONAL
from being.can.vendor import FAULHABER_ERRORS
from being.config import CONFIG
from being.constants import INF, UP
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


class DriveError(BeingError):

    """Something went wrong on the drive."""


def create_node(network, nodeId):
    """CiA402Node factory."""
    # TODO: Support for different motors / different CiA402Node subclasses?
    od = load_object_dictionary(network, nodeId)
    node = CiA402Node(nodeId, od)
    network.add_node(node, object_dictionary=od)
    node._setup()
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


class Motor(Block):

    """Motor base class."""

    def __init__(self):
        super().__init__()
        self.add_value_input('targetPosition')
        self.add_value_output('actualPosition')

    def home(self):
        yield DONE_HOMING


class LinearMotor(Motor):

    """Motor blocks which takes set-point values through its inputs and outputs
    the current actual position value through its output. The input position
    values are filtered with a kinematic filter. Encapsulates a and setups a
    CiA402Node. Currently only tested with Faulhaber linear drive (0.04 m).

    Attributes:
        network (CanBackend): Associsated network:
        node (CiA402Node): Drive node.
    """

    def __init__(self,
             nodeId: int,
             length: Optional[float] = None,
             direction: float = UP,
             # TODO: Which args? direction, maxSpeed, maxAcc, ...?
             network: Optional[CanBackend] = None,
             node: Optional[CiA402Node] = None,
        ):
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

        self.length = length
        self.direction = sign(direction)
        self.network = network
        self.node = node
        self.logger = get_logger(str(self))

        self.configure_node()

        self.node.nmt.state = PRE_OPERATIONAL
        self.node.set_state(CiA402State.READY_TO_SWITCH_ON)
        self.node.set_operation_mode(OperationMode.CYCLIC_SYNCHRONOUS_POSITION)

    @property
    def nodeId(self) -> int:
        """CAN node id."""
        return self.node.id

    def configure_node(self, maxSpeed: float = 1., maxAcc: float = 1.):
        """Configure Faulhaber node (some settings via SDO).

        Kwargs:
            maxSpeed: Maximum speed.
            maxAcc: Maximum acceleration.
        """
        units = self.node.units

        generalSettings = self.node.sdo['General Settings']
        generalSettings['Pure Sinus Commutation'].raw = 1
        #generalSettings['Activate Position Limits in Velocity Mode'].raw = 1
        #generalSettings['Activate Position Limits in Position Mode'].raw = 1

        filterSettings = self.node.sdo['Filter Settings']
        filterSettings['Sampling Rate'].raw = 4
        filterSettings['Gain Scheduling Velocity Controller'].raw = 1

        velocityController = self.node.sdo['Velocity Control Parameter Set']
        #velocityController['Proportional Term POR'].raw = 44
        #velocityController['Integral Term I'].raw = 50

        posController = self.node.sdo['Position Control Parameter Set']
        #posController['Proportional Term PP'].raw = 15
        #posController['Derivative Term PD'].raw = 10
        # Some softer params from pygmies
        #posController['Proportional Term PP'].raw = 8
        #posController['Derivative Term PD'].raw = 14

        curController = self.node.sdo['Current Control Parameter Set']
        curController['Continuous Current Limit'].raw = 0.550 * units.current  # [mA]
        curController['Peak Current Limit'].raw = 1.640 * units.current  # [mA]
        curController['Integral Term CI'].raw = 3

        self.node.sdo['Max Profile Velocity'].raw = maxSpeed * units.kinematics  # [mm / s]
        self.node.sdo['Profile Acceleration'].raw = maxAcc * units.kinematics  # [mm / s^2]
        self.node.sdo['Profile Deceleration'].raw = maxAcc * units.kinematics  # [mm / s^2]

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
            node.change_state(CiA402State.READY_TO_SWITCH_ON)
            node.sdo[HOMING_OFFSET].raw = 0
            #TODO: Do we need to set NMT to 'OPERATIONAL'?
            node.set_operation_mode(OperationMode.PROFILED_VELOCITY)
            node.change_state(CiA402State.OPERATION_ENABLE)

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
                dx = .5 * (width - self.length * node.units.length)
                if dx > 0:
                    lower, upper = lower + dx, upper - dx

            node.change_state(CiA402State.READY_TO_SWITCH_ON)
            node.sdo[HOMING_OFFSET].raw = lower
            node.sdo[SOFTWARE_POSITION_LIMIT][1].raw = 0
            node.sdo[SOFTWARE_POSITION_LIMIT][2].raw = upper - lower

            logger.info('Homed')
            logger.debug('HOMING_OFFSET:              %s', lower)
            logger.debug('SOFTWARE_POSITION_LIMIT[1]: %s', 0)
            logger.debug('SOFTWARE_POSITION_LIMIT[2]: %s', upper - lower)

        while True:
            yield DONE_HOMING

    def update(self):
        from being.can.cia_402 import State, which_state
        err = self.node.pdo['Error Register'].raw
        if err:
            msg = stringify_faulhaber_error(err)
            #raise DriveError(msg)
            self.logger.error('DriveError: %s', msg)

        state = which_state(self.node.pdo['Statusword'].raw)
        if state is CiA402State.OPERATION_ENABLE:
            self.node.set_target_position(self.targetPosition.value)

        self.output.value = self.node.get_actual_position()


class RotaryMotor(Motor):
    def __init__(self, nodeId, *args, **kwargs):
        raise NotImplementedError
        # TODO: Make me!


class WindupMotor(Motor):
    def __init__(self, nodeId, *args, **kwargs):
        raise NotImplementedError
        # TODO: Make me!


class DummyMotor(Motor):

    """Dummy motor for testing and standalone usage."""

    def __init__(self, length=0.04):
        super().__init__()
        self.length = length
        self.state = KinematicState()
        self.dt = CONFIG['General']['INTERVAL']

    def home(self, speed: int = 100):
        yield DONE_HOMING

    def update(self):
        # Kinematic filter input target position
        self.state = kinematic_filter(
            self.input.value,
            dt=self.dt,
            state=self.state,
            maxSpeed=1.,
            maxAcc=1.,
            lower=0.,
            upper=self.length,
        )

        self.output.value = self.state.position
