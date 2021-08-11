"""Motor controllers."""
import abc
from typing import Optional, Dict, Generator

from being.can.cia_402 import (
    CiA402Node,
    HOMING_METHOD,
    OperationMode,
    SOFTWARE_POSITION_LIMIT,
    State as CiA402State,
)
from being.can.definitions import HOMING_OFFSET
from being.can.nmt import PRE_OPERATIONAL, OPERATIONAL
from being.can.vendor import Units
from being.constants import INF, FORWARD
from being.math import clip
from being.motors.homing import (
    HomingState,
    HomingProgress,
    MINIMUM_HOMING_WIDTH,
    HomingFailed,
    _fetch_position,
    _move_node,
    _align_in_the_middle,
)


class Controller(abc.ABC):

    """Semi abstract controller base class."""

    DEVICE_ERROR_CODES: Dict[int, str] = {}
    """Device error code -> error message text lookup."""

    EMERGENCY_ERROR_CODES: Dict[int, str] = {}
    """Emergency error code -> error message text lookup."""

    def __init__(self, node: CiA402Node):
        self.node = node

    def switch_off(self):
        """Switch off drive. Same state as on power-up."""
        self.node.switch_off()

    def disable(self):
        """Disable drive (no power)."""
        self.node.disable()

    def enable(self):
        """Enable drive."""
        self.node.enable()

    def enabled(self) -> bool:
        """Is motor enabled?"""
        return self.node.get_state() is CiA402State.OPERATION_ENABLE

    @abc.abstractmethod
    def home(self) -> HomingProgress:
        """Create homing job routine for this controller."""

    def device_error_message(self, errorCode: int) -> str:
        """Device error message from error code."""
        return self.DEVICE_ERROR_CODES.get(
            errorCode,
            f'Unknown device error message for errorCode: {errorCode}',
        )

    def emergency_error_message(self, errorCode: int) -> str:
        """Emergency error message from error code."""
        return self.EMERGENCY_ERROR_CODES.get(
            errorCode,
            f'Unknown emergency error message for errorCode: {errorCode}',
        )

    def iter_emergencies(self) -> Generator[str, None, None]:
        """Iterate over emergency error messages (if any)."""
        for emcy in self.node.emcy.active:
            yield self.emergency_error_message(emcy)


class Mclm3002(Controller):
    DEVICE_ERROR_CODES: {
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

    EMERGENCY_ERROR_CODES: {
        0x0000: 'No error',
        0x1000: 'Generic error',
        0x2000: 'Current',
        0x2300: 'Current, device output side',
        0x2310: 'Continuous over current 0x00',
        0x3000: 'Voltage',
        0x3200: 'Voltage inside the device',
        0x3210: 'Overvoltage 0x00',
        0x4000: 'Temperature',
        0x4300: 'Drive temperature',
        0x4310: 'Overtemperature 0x00',
        0x5000: 'Device hardware',
        0x5500: 'Data storage',
        0x5530: 'Flash memory error 0x00',
        0x6000: 'Device software',
        0x6100: 'Internal software 0x10',
        0x8000: 'Monitoring',
        0x8100: 'Communication',
        0x8110: 'CAN Overrun (objects lost) 0x00',
        0x8120: 'CAN in error passive mode 0x00',
        0x8130: 'Life guard or heartbeat error 0x01',
        0x8140: 'Recovered from bus off 0x02',
        0x8200: 'Protocol error',
        0x8210: 'PDO not processed due to length error 0x40',
        0x8220: 'PDO length exceeded 0x20',
        0x8400: 'Velocity speed controller (deviation) 0x00',
        0x8600: 'Positioning controller',
        0x8611: 'Following error (deviation) 0x00',
        0xFF00: 'Device specific',
        0xFF01: 'Conversion overflow 0x08',
    }

    def __init__(self,
            node: CiA402Node,
            length: Optional[float] = None,
            direction: float = FORWARD,
            homingDirection: Optional[float] = None,
            maxSpeed: float = 1.,
            maxAcc: float = 1.,
        ):
        if homingDirection is None:
            homingDirection = direction

        super().__init__(node)
        self.node = node
        self.length = length
        self.direction = direction
        self.homingDirection = homingDirection
        self.maxSpeed = maxSpeed
        self.maxAcc = maxAcc

        self.units = Units(
            length=1e6,
            current=1000,
            kinematics=1000,
            speed=1000,  # Speeds are in mm/s
        )

        self.lower = -INF
        self.upper = INF

        self.configure_node()

        self.node.nmt.state = PRE_OPERATIONAL
        self.node.set_state(CiA402State.READY_TO_SWITCH_ON)
        self.node.set_operation_mode(OperationMode.CYCLIC_SYNCHRONOUS_POSITION)

    def configure_node(self):
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
        curController['Continuous Current Limit'].raw = 0.550 * self.units.current  # [mA]
        curController['Peak Current Limit'].raw = 1.640 * self.units.current  # [mA]
        curController['Integral Term CI'].raw = 3

        self.node.sdo['Max Profile Velocity'].raw = self.maxSpeed * self.units.kinematics  # [mm / s]
        self.node.sdo['Profile Acceleration'].raw = self.maxAcc * self.units.kinematics  # [mm / s^2]
        self.node.sdo['Profile Deceleration'].raw = self.maxAcc * self.units.kinematics  # [mm / s^2]

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
        speed = abs(maxSpeed * self.units.speed)
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

            homingWidth = (self.upper - self.lower) / self.units.length
            if homingWidth < MINIMUM_HOMING_WIDTH:
                raise HomingFailed(
                    f'Homing width to narrow. Homing range: {[self.lower, self.upper]}!'
                )

            # Estimate motor length
            if self.length is None:
                self.length = (1. - 2 * relMargin) * homingWidth

            # Center according to rod length
            lengthDev = int(self.length * self.units.length)
            self.lower, self.upper = _align_in_the_middle(self.lower, self.upper, lengthDev)

            node.sdo[HOMING_OFFSET].raw = self.lower
            node.sdo[SOFTWARE_POSITION_LIMIT][1].raw = 0
            node.sdo[SOFTWARE_POSITION_LIMIT][2].raw = self.upper - self.lower

        yield HomingState.HOMED

    def home(self):
        return self.crude_homing()

    def set_target_position(self, targetPosition):
        """Set target position in SI units."""
        if self.direction > 0:
            tarPos = targetPosition
        else:
            tarPos = self.length - targetPosition

        self.node.set_target_position(tarPos * self.units.length)

    def get_actual_position(self) -> float:
        """Get actual position in SI units."""
        return self.node.get_actual_position() / self.units.length


# TODO(atheler): Make me.
#class Epos4(Controller):
#    pass
#
