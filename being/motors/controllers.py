"""Motor controllers."""
from typing import Optional, Dict, Generator, Set, Any, Union

from being.can.cia_402 import (
    CiA402Node,
    HOMING_METHOD,
    OperationMode,
    State as CiA402State,
    default_homing_method,
)
from being.constants import FORWARD, MILLI, MICRO, DECI
from being.constants import TAU
from being.error import BeingError
from being.logging import get_logger
from being.math import rpm_to_angular_velocity
from being.motors.homing import (
    HomingProgress,
    MINIMUM_HOMING_WIDTH,
    crude_homing,
    proper_homing,
)
from being.motors.motors import Motor
from being.motors.vendor import (
    FAULHABER_DEVICE_ERROR_CODES,
    FAULHABER_DEVICE_UNITS,
    FAULHABER_EMERGENCY_ERROR_CODES,
    FAULHABER_SUPPORTED_HOMING_METHODS,
    MAXON_DEVICE_ERROR_CODES,
    MAXON_DEVICE_ERROR_REGISTER,
    MAXON_EMERGENCY_ERROR_CODES,
    MAXON_SUPPORTED_HOMING_METHODS,
)
from being.utils import merge_dicts


def nested_get(dct, keys):
    """Nested dict access."""
    for k in keys:
        dct = dct[k]

    return dct


def inspect(node, name):
    """Inspect node setting / parameter by name."""
    e = nested_get(node.sdo, name.split('/'))
    print(name, e.raw)


def inspect_many(node, names):
    """Inspect many node settings / parameters by name."""
    for name in names:
        inspect(node, name)


class ControllerError(BeingError):

    """General Being controller errors."""


class OnlyOnce:

    """Say it only once."""

    def __init__(self):
        self.before = set()

    def __call__(self, iterable):
        current = set(iterable)
        yield from current - self.before
        self.before = current


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
    EMERGENCY_ERROR_CODES: Dict[int, str] = {}
    SUPPORTED_HOMING_METHODS: Set[int] = {}
    DEVICE_UNITS: Dict[str, float] = {}

    def __init__(self,
            node: CiA402Node,
            motor: Motor,
            settings: Optional[dict] = None,
            direction: int = FORWARD,
            homingMethod: Optional[int] = None,
            homingDirection: Optional[int] = None,
            endSwitches: bool = False,
            multiplier: float = 1.0,
        ):
        """Args:
            node: Connected CanOpen node.
            motor: Motor definitions / settings.

        Kwargs:
            settings: Motor settings.
            direction: Movement direction.
            homingDirection: Homing direction.
            endSwitches: End switches present? Yes or no.
            multiplier: Additional Multiplier factor for SI position ->
                multiplier -> gear -> motor.position_si_2_device. For windup
                module / spindle drive.
        """
        if homingDirection is None:
            homingDirection = direction

        if settings is None:
            settings = {}

        if homingMethod is None:
            homingMethod = default_homing_method(homingDirection, endSwitches)

        self.node: CiA402Node = node
        self.motor: Motor = motor
        self.direction: float = direction
        self.homingDirection: float = homingDirection
        self.homingMethod: int = homingMethod
        self.logger = get_logger(str(self))

        for errMsg in self.error_history_messages():
            self.logger.error(errMsg)

        self.only_new_ones = OnlyOnce()
        self.position_si_2_device = float(multiplier * motor.gear * motor.position_si_2_device)
        self.logger.debug('position_si_2_device: %f', self.position_si_2_device)
        merged = merge_dicts(self.motor.defaultSettings, settings)
        self.apply_settings(merged)
        self.switch_off()
        self.node.set_operation_mode(OperationMode.CYCLIC_SYNCHRONOUS_POSITION)

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
        self.validate_homing_method(self.homingMethod)
        # Configure the homing registers
        # - Modes of operation (object 0x6060) set to Homing mode (6)
        self.node.sdo[HOMING_METHOD].raw = self.homingMethod
        # Assign the desired values to the following objects:
        # - Homing limit switch (object 0x2310)  Homing Method (object 0x6098)
        # - Homing speed (object 0x6099)
        # - Homing Acceleration (object 0x609A)
        return proper_homing(self.node)

    def device_error_message(self, errorCode: int) -> str:
        """Device error message from error code."""
        return self.DEVICE_ERROR_CODES.get(
            errorCode,
            f'Unknown device error message for error code: {errorCode}',
        )

    def new_emergency_messages(self) -> Generator[str, None, None]:
        """Iterate over all new emergency error messages (if any)."""
        for emcy in self.only_new_ones(self.node.emcy.active):
            yield self.EMERGENCY_ERROR_CODES.get(
                emcy.code,
                f'Unknown error code {emcy.code}',
            )

    def error_history_messages(self):
        """Iterate over current error messages in error history register."""
        errorHistory = self.node.sdo[0x1003]
        numErrors = errorHistory[0].raw
        for nr in range(numErrors):
            errCode = errorHistory[nr + 1].raw
            yield self.device_error_message(errCode)

    def validate_homing_method(self, method: int):
        """Validate homing method for this controller. Raises a ControllerError
        if homing method is not support.

        Args:
            method: Homing method to check.
        """
        if method not in self.SUPPORTED_HOMING_METHODS:
            raise ControllerError(f'Homing method {method} not supported for controller {self}')

    def set_target_position(self, targetPosition):
        """Set target position in SI units."""
        if self.direction > 0:
            tarPos = targetPosition
        else:
            tarPos = self.motor.length - targetPosition

        self.node.set_target_position(tarPos * self.position_si_2_device)

    def get_actual_position(self) -> float:
        """Get actual position in SI units."""
        return self.node.get_actual_position() / self.position_si_2_device

    def convert_si_to_device_units(self, value: float, name: str) -> float:
        """Convert SI value to device units."""
        return value / self.DEVICE_UNITS[name]

    def apply_settings(self, settings: Dict[str, Any]):
        """Apply settings to CANopen node. Convert physical SI values to device
        units (if present in DEVICE_UNITS dict).

        Args:
            settings: Settings to apply. Addresses (path syntax) -> value
                entries.
        """
        for name, value in settings.items():
            *path, last = name.split('/')
            sdo = self.node.sdo
            for key in path:
                sdo = sdo[key]

            if name in self.DEVICE_UNITS:
                sdo[last].raw = self.convert_si_to_device_units(value, name)
            else:
                sdo[last].raw = value

    def __str__(self):
        return f'{type(self).__name__}()'


class Mclm3002(Controller):

    """Faulhaber MCLM 3002 controller."""


    DEVICE_ERROR_CODES = FAULHABER_DEVICE_ERROR_CODES
    EMERGENCY_ERROR_CODES = FAULHABER_EMERGENCY_ERROR_CODES
    SUPPORTED_HOMING_METHODS = FAULHABER_SUPPORTED_HOMING_METHODS
    DEVICE_UNITS = FAULHABER_DEVICE_UNITS

    def home(self):
        # Faulhaber does not support homing methods -1 and -2. Use crude_homing
        # instead
        if self.homingMethod in {-1, -2}:
            return crude_homing(
                self.node,
                self.homingDirection,
                speed=self.convert_si_to_device_units(0.100, 'speed'),
                minWidth=self.convert_si_to_device_units(MINIMUM_HOMING_WIDTH, 'length'),
                length=self.convert_si_to_device_units(self.motor.length, 'length'),
            )

        self.validate_homing_method(method)
        return proper_homing(self.node, method)


class Epos4(Controller):

    """Maxon EPOS4 controller."""

    DEVICE_ERROR_REGISTER = MAXON_DEVICE_ERROR_REGISTER
    DEVICE_ERROR_CODES = MAXON_DEVICE_ERROR_CODES
    EMERGENCY_ERROR_CODES = MAXON_EMERGENCY_ERROR_CODES
    SUPPORTED_HOMING_METHODS = MAXON_SUPPORTED_HOMING_METHODS
    DEVICE_UNITS = {}  # TODO

    def __init__(self, *args, homingMethod=37, **kwargs):
        super().__init__(*args, homingMethod=homingMethod, **kwargs)
        # TODO : Check EPOS4 firmware version

    def home(self):
        if self.homingMethod == 35:
            homingMethod = 37
        else:
            homingMethod = self.homingMethod

        self.node.sdo[HOMING_METHOD].raw = homingMethod
        return proper_homing(self.node)
