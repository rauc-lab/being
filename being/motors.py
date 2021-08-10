"""Motor blocks.

For now homing is implemented as *homing generators*. This might seem overly
complicated but we do this so that we can move blocking aspects to the caller
and home multiple motors / nodes in parallel. This results in quasi coroutines.
We do not use asyncio because we want to keep the core async free for now.
"""
import enum
import random
import time
import warnings
from typing import Optional, Generator, Tuple

from being.backends import CanBackend
from being.block import Block
from being.can import load_object_dictionary
from being.can.cia_301 import MANUFACTURER_DEVICE_NAME, ERROR_REGISTER
from being.can.cia_402 import (
    CONTROLWORD,
    CW,
    CiA402Node,
    Command,
    HOMING_ACCELERATION,
    HOMING_METHOD,
    HOMING_SPEEDS,
    SPEED_FOR_SWITCH_SEARCH,
    SPEED_FOR_ZERO_SEARCH,
    OperationMode,
    POSITION_ACTUAL_VALUE,
    SOFTWARE_POSITION_LIMIT,
    STATUSWORD,
    SW,
    State as CiA402State,
    TARGET_VELOCITY,
    VELOCITY_ACTUAL_VALUE,
    target_reached,
    which_state,
    MAX_PROFILE_VELOCITY,
    PROFILE_ACCELERATION,
    PROFILE_DECELERATION,
)
from being.can.definitions import HOMING_OFFSET
from being.can.nmt import PRE_OPERATIONAL, OPERATIONAL
from being.can.vendor import (
    Units,
    stringify_error,
    MAXON_ERROR_REGISTER,
    MAXON_ERROR_CODES,
    FAULHABER_ERROR_REGISTER,
    FAULHABER_ERROR_CODES,
    MCLM3002,
    EPOS4,
)
from being.config import CONFIG
from being.constants import INF, FORWARD, TAU
from being.error import BeingError
from being.kinematics import kinematic_filter, State as KinematicState
from being.logging import get_logger
from being.pubsub import PubSub
from being.math import (
    sign,
    clip,
    rpm_to_angular_velocity,
    angular_velocity_to_rpm,
)
from being.resources import register_resource


# TODO: Implement "non-crude" homings for the different controllers / end-switch
# yes/no etc... Also need to think of a sensible lookup of homing methods. There
# are some tricky differences like:
#   - CanOpen register for end-switch on Faulhaber is not standard CiA402
#   - Homing method 35 is deprecated since a new CiA 402 standard. Got replaced
#     with 37. Maxon Epos 2 and Faulhaber still use 35, Maxon Epos 4 uses the
#     new 37


MOTOR_CHANGED = 'MOTOR_CHANGED'


class DriveError(BeingError):

    """Something went wrong on the drive."""


class HomingState(enum.Enum):

    """Possible homing states."""

    FAILED = 0
    UNHOMED = 1
    ONGOING = 2
    HOMED = 3


HomingProgress = Generator[HomingState, None, None]
"""Yielding the current homing state."""

HomingRange = Tuple[int, int]
"""Lower and upper homing range."""

MINIMUM_HOMING_WIDTH = 0.010
"""Minimum width of homing range for a successful homing."""

INTERVAL = CONFIG['General']['INTERVAL']


class HomingFailed(BeingError):

    """Something went wrong while homing."""


def _fetch_position(node: CiA402Node) -> int:
    """Fetch actual position value from node.

    Args:
        node: Connected CiA402 node.

    Returns:
        Position value in device units.
    """
    return node.pdo[POSITION_ACTUAL_VALUE].raw


def _fetch_velocity(node: CiA402Node) -> int:
    """Fetch actual velocity value from node.

    Args:
        node: Connected CiA402 node.

    Returns:
        Velocity value in device units.
    """
    return node.pdo[VELOCITY_ACTUAL_VALUE].raw


def _move_node(node: CiA402Node, velocity: int, deadTime: float = 2.) -> HomingProgress:
    """Move motor with constant speed.

    Args:
        node: Connected CiA402 node.

    Kwargs:
        speed: Speed value in device units.
        deadTime: Idle time after sending out command.

    Yields:
        HomingState.RUNNING
    """
    #print('_move_node()', velocity)
    node.pdo[TARGET_VELOCITY].raw = int(velocity)
    node.pdo[TARGET_VELOCITY].pdo_parent.transmit()
    node.pdo[CONTROLWORD].raw = Command.ENABLE_OPERATION | CW.NEW_SET_POINT
    node.pdo[CONTROLWORD].pdo_parent.transmit()
    endTime = time.perf_counter() + deadTime
    while time.perf_counter() < endTime:
        yield HomingState.ONGOING  # Wait for sync
        sw = node.pdo[STATUSWORD].raw
        if target_reached(sw):
            #print('Early exit')
            return


def _align_in_the_middle(lower: int, upper: int, length: int) -> HomingRange:
    """Align homing range in the middle.

    Args:
        lower: Lower homing range.
        upper: Upper homing range.
        length: Desired length:

    Returns:
        Trimmed down version of homing range.
    """
    width = upper - lower
    if width <= length:
        return lower, upper

    margin = (width - length) // 2
    return lower + margin, upper - margin


def proper_homing(
        node: CiA402Node,
        homingMethod: int,
        maxSpeed: float = 0.100,
        maxAcc: float = 1.,
        timeout: float = 5.,
        lowerLimit: int = 0,
        upperLimit: int = 0,
    ) -> HomingProgress:
    """Proper CiA 402 homing."""
    homed = False

    warnings.warn('Proper homing is untested by now. Use at your own risk!')

    with node.restore_states_and_operation_mode():
        node.change_state(CiA402State.READY_TO_SWITCH_ON)
        node.set_operation_mode(OperationMode.HOMING)
        node.nmt.state = OPERATIONAL
        # node.change_state(CiA402State.SWITCHED_ON)
        node.change_state(CiA402State.OPERATION_ENABLE)

        # TODO: Set Homing Switch(Objekt 0x2310). Manufacture dependent
        # node.sdo['Homing Switch'] = ???
        # TODO: Manufacture dependent, done before calling method
        # node.sdo[HOMING_OFFSET].raw = 0
        node.sdo[HOMING_METHOD].raw = homingMethod
        node.sdo[HOMING_SPEEDS][SPEED_FOR_SWITCH_SEARCH].raw = abs(maxSpeed * node.units.speed)
        node.sdo[HOMING_SPEEDS][SPEED_FOR_ZERO_SEARCH].raw = abs(maxSpeed * node.units.speed)
        node.sdo[HOMING_ACCELERATION].raw = abs(maxAcc * node.units.kinematics)

        # Start homing
        node.sdo[CONTROLWORD].raw = Command.ENABLE_OPERATION | CW.START_HOMING_OPERATION
        startTime = time.perf_counter()
        endTime = startTime + timeout

        # Check if homing started (statusword bit 10 and 12 zero)
        homingStarted = False
        while not homingStarted and (time.perf_counter() < endTime):
            yield HomingState.ONGOING
            sw = node.sdo[STATUSWORD].raw
            homingStarted = (not (sw & SW.TARGET_REACHED) and not (sw & SW.HOMING_ATTAINED))

        # Check if homed (statusword bit 10 and 12 one)
        while not homed and (time.perf_counter() < endTime):
            yield HomingState.ONGOING
            sw = node.sdo[STATUSWORD].raw
            homed = (sw & SW.TARGET_REACHED) and (sw & SW.HOMING_ATTAINED)

        node.sdo[CONTROLWORD].raw = Command.ENABLE_OPERATION  # Abort homing
        # node.sdo[CONTROLWORD].raw = 0  # Abort homing

    if homed:
        # lower = node.sdo[SOFTWARE_POSITION_LIMIT][1].raw
        #node.sdo[HOMING_OFFSET].raw = lower
        node.sdo[SOFTWARE_POSITION_LIMIT][1].raw = 0  # 0 == disabled
        node.sdo[SOFTWARE_POSITION_LIMIT][2].raw = 0  # 0 == disabled
        #print(self, 'HOMING_OFFSET:', node.sdo[HOMING_OFFSET].raw)
        #print('SOFTWARE_POSITION_LIMIT:', node.sdo[SOFTWARE_POSITION_LIMIT][1].raw)
        #print('SOFTWARE_POSITION_LIMIT:', node.sdo[SOFTWARE_POSITION_LIMIT][2].raw)
        # node.sdo[HOMING_OFFSET].raw = 0
        yield HomingState.HOMED
    else:
        yield HomingState.FAILED


class Motor(Block, PubSub):

    """Motor base class."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        PubSub.__init__(self, events=[MOTOR_CHANGED])
        self.homing = HomingState.UNHOMED
        self.homingJob = None
        self._enabled = False
        self.add_value_input('targetPosition')
        self.add_value_output('actualPosition')

    @property
    def homed(self) -> bool:
        """Is motor homed?"""
        return self.homing is HomingState.HOMED

    def enabled(self) -> bool:
        """Is motor enabled?"""
        return self._enabled

    def enable(self, publish=True):
        """Engage motor. This is switching motor on and engaging its drive."""
        self._enabled = True
        if publish:
            self.publish(MOTOR_CHANGED)

    def disable(self, publish=True):
        """Switch motor on."""
        self._enabled = False
        if publish:
            self.publish(MOTOR_CHANGED)

    def home(self):
        """Start homing routine for this motor. Has then to be driven via the update() method."""
        self.publish(MOTOR_CHANGED)

    def to_dict(self):
        dct = super().to_dict()
        dct['enabled'] = self.enabled()
        dct['homing'] = self.homing
        return dct


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
             direction: float = FORWARD,
             homingDirection: Optional[float] = None,
             maxSpeed: float = 1.,
             maxAcc: float = 1.,
             network: Optional[CanBackend] = None,
             node: Optional[CiA402Node] = None,
             objectDictionary = None,
             **kwargs,
        ):
        """Args:
            nodeId: CANopen node id.

        Kwargs:
            length: Rod length if known.
            direction: Movement orientation.
            homingDirection: Initial homing direction. Default same as `direction`.
            maxSpeed: Maximum speed.
            maxAcc: Maximum acceleration.
            network: External network (dependency injection).
            node: Drive node (dependency injection).
            objectDictionary: Object dictionary for CiA402Node. If will be tried
                to identified from known EDS files.
        """
        super().__init__(**kwargs)
        if homingDirection is None:
            homingDirection = direction

        if network is None:
            network = CanBackend.single_instance_setdefault()
            register_resource(network, duplicates=False)

        if node is None:
            if objectDictionary is None:
                objectDictionary = load_object_dictionary(network, nodeId)

            node = CiA402Node(nodeId, objectDictionary, network)
            # EPOS4 has no PDO mapping for Error Regiser, thus re-register here
            node.setup_txpdo(1, 'Statusword', 'Error Register')

        self.length = length
        self.direction = sign(direction)
        self.homingDirection = sign(homingDirection)
        self.network = network
        self.node = node
        self.maxSpeed = maxSpeed
        self.maxAcc = maxAcc

        self.lower = -INF
        self.upper = INF
        self.logger = get_logger(str(self))

        self.configure_node()

        self.node.nmt.state = PRE_OPERATIONAL
        self.node.set_state(CiA402State.READY_TO_SWITCH_ON)
        self.node.set_operation_mode(OperationMode.CYCLIC_SYNCHRONOUS_POSITION)

    @property
    def nodeId(self) -> int:
        """CAN node id."""
        return self.node.id

    def configure_node(self):
        """Configure Faulhaber node (some settings via SDO)."""
        units = self.node.units

        # TODO: These parameters have to come from the outside. Question: How
        # can we identify the motor and choose sensible defaults?

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
        posController['Proportional Term PP'].raw = 15
        posController['Derivative Term PD'].raw = 10
        # Some softer params from pygmies
        #posController['Proportional Term PP'].raw = 8
        #posController['Derivative Term PD'].raw = 14

        curController = self.node.sdo['Current Control Parameter Set']
        curController['Continuous Current Limit'].raw = 0.550 * units.current  # [mA]
        curController['Peak Current Limit'].raw = 1.640 * units.current  # [mA]
        curController['Integral Term CI'].raw = 3

        self.node.sdo['Max Profile Velocity'].raw = self.maxSpeed * units.kinematics  # [mm / s]
        self.node.sdo['Profile Acceleration'].raw = self.maxAcc * units.kinematics  # [mm / s^2]
        self.node.sdo['Profile Deceleration'].raw = self.maxAcc * units.kinematics  # [mm / s^2]

    def home_forward(self, speed: int) -> HomingProgress:
        """Home in forward direction until upper limits is not increasing
        anymore.
        """
        self.upper = -INF
        yield from _move_node(self.node, velocity=speed)
        while (pos := _fetch_position(self.node)) > self.upper:
            self.upper = pos
            yield HomingState.ONGOING

        yield from _move_node(self.node, velocity=0.)

    def home_backward(self, speed: int) -> HomingProgress:
        """Home in backward direction until `lower` is not decreasing
        anymore.
        """
        self.lower = INF
        yield from _move_node(self.node, velocity=-speed)
        while (pos := _fetch_position(self.node)) < self.lower:
            self.lower = pos
            yield HomingState.ONGOING

        yield from _move_node(self.node, velocity=0.)

    def crude_homing(self, maxSpeed=0.100, relMargin: float = 0.01) -> HomingProgress:
        """Crude homing procedure. Move with PROFILED_VELOCITY operation mode in
        both direction until reaching the limits (position not increasing or
        decreasing anymore). Implemented as Generator so that we can home multiple
        motors in parallel (quasi pseudo coroutine). time.sleep has to be handled by
        the caller.

        Velocity direction controls initial homing direction.

        Kwargs:
            maxSpeed: Maximum speed of homing travel.
            relMargin: Relative margin if motor length is not known a priori. Final
                length will be the measured length from the two homing travels minus
                `relMargin` percent on both sides.

        Yields:
            Homing state.
        """
        node = self.node
        forward = (self.homingDirection > 0)
        speed = abs(maxSpeed * node.units.speed)
        relMargin = clip(relMargin, 0.00, 0.50)  # In [0%, 50%]!

        with node.restore_states_and_operation_mode():
            node.change_state(CiA402State.READY_TO_SWITCH_ON)
            node.set_operation_mode(OperationMode.PROFILED_VELOCITY)
            node.change_state(CiA402State.OPERATION_ENABLE)
            node.nmt.state = OPERATIONAL

            node.sdo[HOMING_METHOD].raw = 35
            node.sdo[HOMING_OFFSET].raw = 0

            # Homing travel
            # TODO: Should we skip 2nd homing travel if we know motor length a
            # priori? Would need to also consider relMargin. Otherwise motor
            # will touch one edge
            if forward:
                yield from self.home_forward(speed)
                yield from self.home_backward(speed)
            else:
                yield from self.home_backward(speed)
                yield from self.home_forward(speed)

            node.change_state(CiA402State.READY_TO_SWITCH_ON)

            homingWidth = (self.upper - self.lower) / node.units.length
            if homingWidth < MINIMUM_HOMING_WIDTH:
                raise HomingFailed(
                    f'Homing width to narrow. Homing range: {[self.lower, self.upper]}!'
                )

            # Estimate motor length
            if self.length is None:
                self.length = (1. - 2 * relMargin) * homingWidth

            # Center according to rod length
            lengthDev = int(self.length * node.units.length)
            self.lower, self.upper = _align_in_the_middle(self.lower, self.upper, lengthDev)

            node.sdo[HOMING_OFFSET].raw = self.lower
            node.sdo[SOFTWARE_POSITION_LIMIT][1].raw = 0
            node.sdo[SOFTWARE_POSITION_LIMIT][2].raw = self.upper - self.lower

        yield HomingState.HOMED

    def enabled(self):
        sw = self.node.sdo[STATUSWORD].raw  # This takes approx. 2.713 ms
        state = which_state(sw)
        return state is CiA402State.OPERATION_ENABLE

    def enable(self, publish=True):
        self.node.enable()
        super().enable(publish)

    def disable(self, publish=True):
        self.node.disable()
        super().disable(publish)

    def home(self):
        self.homingJob = self.crude_homing()
        #if self.homingDirection > 0:
        #    self.homingJob = proper_homing(self.node, homingMethod=34)
        #else:
        #    self.homingJob = proper_homing(self.node, homingMethod=33)

        self.homing = HomingState.ONGOING
        self.publish(MOTOR_CHANGED)

    def update(self):

        if self.node.emcy.active:
            #raise DriveError(msg)
            for emcy in self.node.emcy.active:
                msg = stringify_error(emcy.register, FAULHABER_ERROR_REGISTER)
                description = FAULHABER_ERROR_CODES[emcy.code]
                self.logger.error(f'DriveError: {msg} with \
                    Error code {emcy.code}: {description}')

        if self.homing is HomingState.HOMED:
            sw = self.node.pdo[STATUSWORD].raw  # This takes approx. 0.027 ms
            state = which_state(sw)
            if state is CiA402State.OPERATION_ENABLE:
                if self.direction > 0:
                    tarPos = self.targetPosition.value
                else:
                    tarPos = self.length - self.targetPosition.value

                self.node.set_target_position(tarPos)

        elif self.homing is HomingState.ONGOING:
            self.homing = next(self.homingJob)
            if self.homing is not HomingState.ONGOING:
                self.publish(MOTOR_CHANGED)

        self.output.value = self.node.get_actual_position()

    def to_dict(self):
        dct = super().to_dict()
        dct['length'] = self.length
        return dct

    def __str__(self):
        return f'{type(self).__name__}(nodeId: {self.nodeId!r})'


class RotaryMotor(Motor):

    """Motor block which takes set-point values through its inputs and outputs
    the current actual position value through its output. The input position
    values are filtered with a kinematic filter. Encapsulates a and setups a
    CiA402Node. Currently only tested with Maxon EPOS4 controller.

    Attributes:
        network (CanBackend): Associsated network:
        node (CiA402Node): Drive node.
    """

    def __init__(self,
                 nodeId: int,
                 arc: float = TAU,
                 direction: float = FORWARD,
                 homingDirection: Optional[float] = None,
                 homingMethod: Optional[int] = None,
                 maxSpeed: float = 942,  # [rad /s ] -> 9000 rpm
                 maxAcc: float = 4294967295,
                 network: Optional[CanBackend] = None,
                 node: Optional[CiA402Node] = None,
                 objectDictionary=None,
                 motor: Optional[dict] = {},
                 **kwargs,
                 ):
        """Args:
            nodeId: CANOpen node id.

        Kwargs:
            direction: Movement orientation.
            homingDirection: Initial homing direction. Default same as `direction`.
            maxSpeed: Maximum speed [rad / s].
            maxAcc: Maximum acceleration. Not taken into account in CSP mode
            network: External network (dependency injection).
            node: Drive node (dependency injection).
            objectDictionary: Object dictionary for CiA402Node. Will be tried
                to be identified from known EDS files.
        """
        super().__init__(**kwargs)
        if homingDirection is None:
            homingDirection = direction

        if network is None:
            network = CanBackend.single_instance_setdefault()
            register_resource(network, duplicates=False)

        if node is None:
            if objectDictionary is None:
                objectDictionary = load_object_dictionary(network, nodeId)

            node = CiA402Node(nodeId, objectDictionary, network)

            deviceName = node.sdo[MANUFACTURER_DEVICE_NAME].raw
            # TODO: Support other controllers
            if deviceName != "EPOS4":
                raise DriveError("Attached motor controller (%s) is not an EPOS4!", deviceName)

        self.motor = motor
        self.direction = sign(direction)
        self.homingDirection = sign(homingDirection)

        if homingMethod is None:
            # Axis polarirty also affects homing direction!
            if (self.homingDirection * self.direction) > 0:
                self.homingMethod = -3
            else:
                self.homingMethod = -4
        else:
            self.homingMethod = homingMethod

        self.network = network
        self.arc = arc
        self.node = node

        if self.motor.get('maxRatedSpeed', 900) < maxSpeed:
            self.maxSpeed = self.motor.get('maxRatedSpeed', maxSpeed)
        else:
            self.maxSpeed = maxSpeed

        self.maxAcc = maxAcc

        self.logger = get_logger(str(self))

        self.node.nmt.state = PRE_OPERATIONAL
        self.node.set_state(CiA402State.READY_TO_SWITCH_ON)

        self.configure_node()  # Some registers dont' have write access when in OPERATION_ENABLE mode!

        self.node.set_operation_mode(OperationMode.CYCLIC_SYNCHRONOUS_POSITION)

    @property
    def nodeId(self) -> int:
        """CAN node id."""
        return self.node.id

    def configure_node(self,
                       maxGearInputSpeed: float = 8000,  # [rpm]
                       hasGear: bool = False,
                       gearNumerator: int = 1,
                       gearDenumerator: int = 1,
                       encoderNumberOfPulses=1024,
                       encoderHasIndex=True,
                       ):
        """Configure Maxon EPOS4 node (some settings via SDO)."""

        gearRatio = gearNumerator / gearDenumerator
        self.node.units = Units(
            # length here: convertion factor radians to increments
            length=gearRatio * encoderNumberOfPulses * 4 / TAU,
            current=1000,
            kinematics=gearRatio * 60 / TAU,
            speed=gearRatio * 60 / TAU,
            thermal=10,
            torque=1e6,
        )
        units = self.node.units

        # TODO: These parameters have to come from the outside. Question: How
        # can we identify the motor and choose sensible defaults?

        # Set motor parameters

        isBrushed = self.motor.get('isBrushed', True)

        self.node.sdo[EPOS4.MOTOR_TYPE].raw = 1 if isBrushed else 10
        motorData = self.node.sdo[EPOS4.MOTOR_DATA_MAXON]

        # Reducing the nominal current helps to make the motor quiter
        nominalCurrent = self.motor.get('nominalCurrent', 0.3) * units.current
        motorData[EPOS4.NOMINAL_CURRENT].raw = nominalCurrent  # [mA]

        # Recommended to set current limit to double of nominal current
        motorData[EPOS4.OUTPUT_CURRENT_LIMIT].raw = 2 * nominalCurrent  # [mA]

        # only relevant for BLDC motors
        numberOfPolePairs = self.motor.get('numberOfPolePairs', 1)
        motorData[EPOS4.NUMBER_OF_POLE_PAIRS].raw = numberOfPolePairs

        thermalTimeConstant = self.motor.get('thermalTimeConstant', 14.3) * units.thermal
        motorData[EPOS4.THERMAL_TIME_CONSTANT_WINDING].raw = thermalTimeConstant  # [0.1 s]

        motorTorqueConstant = self.motor.get('motorTorqueConstant', 0.03) * units.torque
        motorData[EPOS4.MOTOR_TORQUE_CONSTANT].raw = motorTorqueConstant  # [μNm/A]
        self.node.sdo[EPOS4.MAX_MOTOR_SPEED].raw = angular_velocity_to_rpm(self.maxSpeed)  # [rpm]

        if hasGear:
            gearConf = self.node.sdo[EPOS4.GEAR_CONFIGURATION]
            gearConf[EPOS4.GEAR_REDUCTION_NUMERATOR].raw = gearNumerator  # [rpm]
            gearConf[EPOS4.GEAR_REDUCTION_DENOMINATOR].raw = gearDenumerator  # [rpm]
            gearConf[EPOS4.MAX_GEAR_INPUT_SPEED].raw = maxGearInputSpeed  # [rpm]

        # Set position sensor parameters

        axisConf = self.node.sdo[EPOS4.AXIS_CONFIGURATION]

        if isBrushed:
            # Digital incremental encoder 1
            axisConf[EPOS4.SENSORS_CONFIGURATION].raw = 1
        else:
            # Digital Hall Sensor (EC motors only) & Digital Hall Sensor (EC motors only)
            axisConf[EPOS4.SENSORS_CONFIGURATION].raw = 0x100001

        # TODO: Break down more, see table page 141 in EPOS4-Firmware-Specification-En.pdf
        axisConf[EPOS4.CONTROL_STRUCTURE].raw = 0x00010121 | (hasGear << 12)
        axisConf[EPOS4.COMMUTATION_SENSORS].raw = 0 if isBrushed else 0x31

        if self.direction > 0:
            polarity = EPOS4.AxisPolarity.CCW
        else:
            polarity = EPOS4.AxisPolarity.CW
        axisConf[EPOS4.AXIS_CONFIGURATION_MISCELLANEOUS].raw = 0x0 | polarity

        encoder = self.node.sdo[EPOS4.DIGITAL_INCREMENTAL_ENCODER_1]
        #  4 * (pulses / revolutions) = increments / revolutions
        # eg 4 * 1024 = 4096 increments / rev.
        encoder[EPOS4.DIGITAL_INCREMENTAL_ENCODER_1_NUMBER_OF_PULSES].raw = encoderNumberOfPulses
        encoder[EPOS4.DIGITAL_INCREMENTAL_ENCODER_1_TYPE].raw = 1 if encoderHasIndex else 0

        # TODO: add SSI configuration. Required for BLDC?

        # Set current control gains

        currentCtrlParamSet = self.node.sdo[EPOS4.CURRENT_CONTROL_PARAMETER_SET]
        currentCtrlParamSet[EPOS4.CURRENT_CONTROLLER_P_GAIN].raw = 9138837  # [uV / A]
        currentCtrlParamSet[EPOS4.CURRENT_CONTROLLER_I_GAIN].raw = 133651205  # [uV / (A * ms)]

        # Set position PID
        # Adapt to application
        positionPID = self.node.sdo[EPOS4.POSITION_CONTROL_PARAMETER_SET]
        positionPID[EPOS4.POSITION_CONTROLLER_P_GAIN].raw = 1500000
        positionPID[EPOS4.POSITION_CONTROLLER_I_GAIN].raw = 780000
        positionPID[EPOS4.POSITION_CONTROLLER_D_GAIN].raw = 16000
        positionPID[EPOS4.POSITION_CONTROLLER_FF_VELOCITY_GAIN].raw = 0
        positionPID[EPOS4.POSITION_CONTROLLER_FF_ACCELERATION_GAIN].raw = 0

        # Set additional parameters

        torque = self.motor.get('ratedTorque', 0.01) * units.torque  # [μNm]
        self.node.sdo[EPOS4.MOTOR_RATED_TORQUE].raw = torque

        interpolPer = self.node.sdo[EPOS4.INTERPOLATION_TIME_PERIOD]
        # Will run smoother if set (0 = disabled).
        # However, will throw an RPDO timeout error when reloading web page
        # This error can't be disabled, only the reaction behavior can
        # be changed (quickstop vs disable voltage)
        interpolPer[EPOS4.INTERPOLATION_TIME_PERIOD_VALUE].raw = 0  #INTERVAL * 1000  # [ms]

        self.maxSystemSpeed = self.node.sdo[EPOS4.AXIS_CONFIGURATION][EPOS4.MAX_SYSTEM_SPEED].raw
        self.node.sdo[MAX_PROFILE_VELOCITY].raw = self.maxSystemSpeed
        self.node.sdo[PROFILE_ACCELERATION].raw = self.maxAcc
        self.node.sdo[PROFILE_DECELERATION].raw = self.maxAcc

        self.node.sdo[EPOS4.FOLLOWING_ERROR_WINDOW].raw = 4294967295  # disabled

    def enabled(self):
        sw = self.node.sdo[STATUSWORD].raw  # This takes approx. 2.713 ms
        state = which_state(sw)
        return state is CiA402State.OPERATION_ENABLE

    def enable(self, publish=True):
        self.node.enable()
        super().enable(publish)

    def disable(self, publish=True):
        self.node.disable()
        super().disable(publish)

    def home(self, offset: int = 0):
        self.node.sdo[EPOS4.HOME_OFFSET_MOVE_DISTANCE].raw = offset

        self.homingJob = proper_homing(self.node,
                                       homingMethod=self.homingMethod,
                                       timeout=5,
                                       maxSpeed=rpm_to_angular_velocity(60),
                                       maxAcc=100)
        self.homing = HomingState.ONGOING
        self.publish(MOTOR_CHANGED)

    def update(self):
        if self.node.emcy.active:
            #raise DriveError(msg)
            for emcy in self.node.emcy.active:
                msg = stringify_error(emcy.register, MAXON_ERROR_REGISTER)
                description = MAXON_ERROR_CODES[emcy.code]
                self.logger.error(f'DriveError: {msg} with \
                    Error code {emcy.code}: {description}')

        if self.homing is HomingState.HOMED:
            sw = self.node.pdo[STATUSWORD].raw  # This takes approx. 0.027 ms
            state = which_state(sw)
            if state is CiA402State.OPERATION_ENABLE:
                self.logger.debug(f'Next position: {self.targetPosition.value}')
                self.node.set_target_position(self.targetPosition.value)

        elif self.homing is HomingState.ONGOING:
            self.homing = next(self.homingJob)
            if self.homing is not HomingState.ONGOING:
                self.publish(MOTOR_CHANGED)

        self.output.value = self.node.get_actual_position()

    def to_dict(self):
        dct = super().to_dict()
        dct['length'] = self.arc
        return dct

    def __str__(self):
        return f'{type(self).__name__}(nodeId: {self.nodeId!r})'


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
        self.dt = INTERVAL
        self.homing = HomingState.HOMED

    def dummy_homing(self, minDuration: float = 2., maxDuration: float = 5.) -> HomingProgress:
        duration = random.uniform(minDuration, maxDuration)
        endTime = time.perf_counter() + duration
        while time.perf_counter() < endTime:
            yield HomingState.ONGOING

        yield HomingState.HOMED

    def home(self):
        self.homingJob = self.dummy_homing()
        self.homing = HomingState.ONGOING
        self.publish(MOTOR_CHANGED)

    def update(self):
        # Kinematic filter input target position
        if self.homing is HomingState.ONGOING:
            self.homing = next(self.homingJob)
            if self.homing is not HomingState.ONGOING:
                self.publish(MOTOR_CHANGED)

            target = 0.
        else:
            target = self.input.value

        self.state = kinematic_filter(
            target,
            dt=self.dt,
            state=self.state,
            maxSpeed=1.,
            maxAcc=1.,
            lower=0.,
            upper=self.length,
        )

        self.output.value = self.state.position

    def to_dict(self):
        dct = super().to_dict()
        dct['length'] = self.length
        return dct
