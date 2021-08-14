"""Motor controllers."""
from typing import Optional, Dict, Generator, Set, Any
from collections import defaultdict

from being.can.cia_402 import ( CiA402Node, HOMING_METHODS, HomingParam, NEGATIVE, OperationMode, POSITIVE, State as CiA402State, )
from being.can.vendor import Units
from being.constants import FORWARD, ONE, MILLI, MICRO
from being.error import BeingError
from being.motors.homing import ( HomingProgress, MINIMUM_HOMING_WIDTH, crude_homing, proper_homing, )
from being.motors.motors import Motor, get_motor
from being.utils import merge_dicts


def unity() -> float:
    """We are one."""
    return ONE


def device_units(units: Optional[dict] = None) -> defaultdict:
    """Create defaultdict for device units -> SI conversion factors."""
    if units is None:
        units = {}

    return defaultdict(unity, units)


class ControllerError(BeingError):

    """General Being controller errors."""


class Controller:

    """Semi abstract controller base class.

    Attributes:
        DEVICE_ERROR_CODES: Device error code -> error message text lookup.
        SUPPORTED_HOMING_METHODS: Supported homing methods.
        DEVICE_UNITS: Device units -> SI conversion factor.
        node: Connected CiA 402 CANopen node.
        motor: Associated hardware motor.
        direction: Movement direction
        homingDirection: Homing direction.
        endSwitches: End switches present or not.
    """

    DEVICE_ERROR_CODES: Dict[int, str] = {}
    SUPPORTED_HOMING_METHODS: Set[int] = {}
    DEVICE_UNITS = device_units()

    def __init__(self,
            node: CiA402Node,
            motor: Motor,
            settings: Optional[dict] = None,
            direction: int = FORWARD,
            homingDirection: Optional[int] = None,
            endSwitches: bool = False,
        ):
        """Args:
            node: Connected CanOpen node.
            motor: Motor definitions / settings.

        Kwargs:
            settings: Motor settings.
            direction: Movement direction.
            homingDirection: Homing direction.
            endSwitches: End switches present? Yes or no.
        """
        if homingDirection is None:
            homingDirection = direction

        if settings is None:
            settings = {}

        self.node: CiA402Node = node
        self.motor: Motor = motor
        self.direction: float = direction
        self.homingDirection: float = homingDirection
        self.endSwitches: bool = endSwitches

        self.switch_off()
        self.node.set_operation_mode(OperationMode.CYCLIC_SYNCHRONOUS_POSITION)
        merged = merge_dicts(motor.defaultSettings, settings)
        self.apply_settings(merged)

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

    def home(self) -> HomingProgress:
        """Create homing job routine for this controller."""
        method = self.homing_method()
        self.validate_homing_method(method)
        return proper_homing(self.node, method)

    def device_error_message(self, errorCode: int) -> str:
        """Device error message from error code."""
        return self.DEVICE_ERROR_CODES.get(
            errorCode,
            f'Unknown device error message for errorCode: {errorCode}',
        )

    def iter_emergencies(self) -> Generator[object, None, None]:
        """Iterate over emergency error messages (if any)."""
        yield from self.node.emcy.active

    def validate_homing_method(self, method: int):
        """Validate homing method for this controller. Raises a ControllerError
        if homing method is not support.

        Args:
            method: Homing method to check.
        """
        if method not in self.SUPPORTED_HOMING_METHODS:
            raise ControllerError(f'Homing method {method} not supported for controller {self}')

    def homing_method(self) -> int:
        """Homing method for this controller."""
        if self.endSwitches:
            if self.homingDirection >= 0:
                param = HomingParam(endSwitch=POSITIVE)
            else:
                param = HomingParam(endSwitch=NEGATIVE)
        else:
            if self.homingDirection >= 0:
                param = HomingParam(direction=POSITIVE, hardStop=True)
            else:
                param = HomingParam(direction=NEGATIVE, hardStop=True)

        return HOMING_METHODS[param]

    def set_target_position(self, targetPosition):
        """Set target position in SI units."""
        if self.direction > 0:
            tarPos = targetPosition
        else:
            tarPos = self.motor.length - targetPosition

        self.node.set_target_position(tarPos / self.DEVICE_UNITS['length'])

    def get_actual_position(self) -> float:
        """Get actual position in SI units."""
        return self.node.get_actual_position() * self.DEVICE_UNITS['length']

    def apply_settings(self, settings: Dict[str, Any]):
        """Apply settings to CANopen node. Convert physical SI values to device units."""
        for name, physValue in settings.items():
            *path, last = name.split('/')
            d = self.node.sdo
            for k in path:
                d = d[k]

            d[last].raw = physValue / self.DEVICE_UNITS[name]

    def __str__(self):
        return f'{type(self).__name__}()'


class Mclm3002(Controller):

    """Faulhaber MCLM 3002 controller."""

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

    SUPPORTED_HOMING_METHODS = {
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14,
        17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
        33, 34,
        35,
    }

    DEVICE_UNITS = device_units({
        'length': MICRO,
        'current': MILLI,
        'speed': MILLI,
        'Current Control Parameter Set/Continuous Current Limit': MILLI,
        'Current Control Parameter Set/Peak Current Limit': MILLI,
        'Max Profile Velocity': MILLI,
        'Profile Acceleration': MILLI,
        'Profile Deceleration': MILLI,
    })

    def home(self):
        method = self.homing_method()

        # Faulhaber does not support homing methods -1 and -2. Use crude_homing
        # instead
        if method in {-1, -2}:
            units = self.DEVICE_UNITS
            return crude_homing(
                self.node,
                self.homingDirection,
                speed=0.100 / units['speed'],
                minWidth=MINIMUM_HOMING_WIDTH / units['length'],
                length=self.motor.length / units['length'],
            )

        self.validate_homing_method(method)
        return proper_homing(self.node, method)


class Epos4(Controller):

    """Maxon EPOS4 controller."""

    # TODO(atheler): Make me.

    SUPPORTED_HOMING_METHODS = {
        -4, -3, -2, -1, 1, 2, 7, 11, 17, 18, 23, 27, 33, 34, 37,
    }

    def home(self):
        method = self.homing_method()

        # Homing method 35 deprecated since new CiA 402 standard. Got replaced
        # with 37. Maxon EPOS4 uses the newer definition
        if method == 35:
            method = 37

        self.validate_homing_method(method)
        return proper_homing(self.node, method)
