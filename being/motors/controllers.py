"""Motor controllers."""
import sys
from typing import Optional, Dict, Generator, Set, Any

from canopen.emcy import EmcyError

from being.bitmagic import clear_bit, set_bit
from being.can.cia_402 import (
    CONTROLWORD,
    CW,
    CiA402Node,
    Command,
    HOMING_METHOD,
    NEGATIVE,
    OperationMode,
    POSITION_ACTUAL_VALUE,
    POSITIVE,
    State as CiA402State,
    TARGET_VELOCITY,
    determine_homing_method,
)
from being.can.nmt import OPERATIONAL, PRE_OPERATIONAL
from being.config import CONFIG
from being.constants import FORWARD, INF
from being.error import BeingError
from being.logging import get_logger
from being.math import clip
from being.motors.homing import (
    HomingProgress,
    proper_homing,
)
from being.motors.homing import HomingState
from being.motors.motors import Motor
from being.motors.vendor import (
    FAULHABER_DEVICE_ERROR_CODES,
    FAULHABER_EMERGENCY_DESCRIPTIONS,
    FAULHABER_SUPPORTED_HOMING_METHODS,
    MAXON_DEVICE_ERROR_CODES,
    MAXON_DEVICE_ERROR_REGISTER,
    MAXON_EMERGENCY_DESCRIPTIONS,
    MAXON_SUPPORTED_HOMING_METHODS,
)
from being.utils import merge_dicts


INTERVAL = CONFIG['General']['INTERVAL']


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


def default_homing_method(
        homingDirection: int = FORWARD,
        endSwitches: bool = False,
        indexPulse: bool = False,
    ) -> int:
    """Default non 35/37 homing methods.

    Args:
        homingDirection: In which direction to start homing.

    Kwargs:
        endSwitches: End switches present.

    Returns:
        Homing method number.
    """
    if endSwitches:
        if homingDirection > 0:
            return determine_homing_method(endSwitch=POSITIVE, indexPulse=indexPulse)
        else:
            return determine_homing_method(endSwitch=NEGATIVE, indexPulse=indexPulse)
    else:
        if homingDirection > 0:
            return determine_homing_method(direction=POSITIVE, hardStop=True, indexPulse=indexPulse)
        else:
            return determine_homing_method(direction=NEGATIVE, hardStop=True, indexPulse=indexPulse)


def format_error_code(errorCode: int, descriptions: list) -> str:
    """Emergency error code -> description.

    Args:
        errorCode: Error code to check.
        descriptions: Description table with (code, mask, description) entries.

    Returns:
        Text error description.
    """
    description = ''
    for code, mask, desc in descriptions:
        if errorCode & mask == code:
            description = desc

    if description == '':
        return f'Unknown emergency error for code 0x{errorCode:#04x}'

    return description


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
        EMERGENCY_ERROR_CODES: TODO.
        SUPPORTED_HOMING_METHODS: Supported homing methods.
        node: Connected CiA 402 CANopen node.
        motor: Associated hardware motor.
        direction: Motor direction.
        homingMethod: Homing method.
        homingDirection: Homing direction.
        lower: Lower clipping value for target position in device units.
        upper: Upper clipping value for target position in device units.
        logger: Controller logging instance.
        only_new_ones: Filter for showing error messages only once.
    """

    DEVICE_ERROR_CODES: Dict[int, str] = {}
    EMERGENCY_DESCRIPTIONS: list = []
    SUPPORTED_HOMING_METHODS: Set[int] = {}

    def __init__(self,
            node: CiA402Node,
            motor: Motor,
            direction: int = FORWARD,
            length: Optional[float] = None,
            settings: Optional[dict] = None,
            multiplier: float = 1.0,
            **homingKwargs,
        ):
        """Args:
            node: Connected CanOpen node.
            motor: Motor definitions / settings.

        Kwargs:
            direction: Movement direction.
            length: Length of associated motor. Motor length by default.
            settings: Motor settings.
            multiplier: Additional Multiplier factor for SI position ->
                multiplier -> gear -> motor.position_si_2_device. For windup
                module / spindle drive.
            **homingKwargs: Homing parameters.
        """
        # Defaults
        if settings is None:
            settings = {}

        if length is None:
            length = motor.length

        homingKwargs.setdefault('homingDirection', FORWARD)  # TODO: Or direction as default?
        if 'homingMethod' in homingKwargs:
            homingMethod = homingKwargs['homingMethod']
        else:
            homingMethod = default_homing_method(**homingKwargs)

        # Attrs
        self.node: CiA402Node = node
        self.motor: Motor = motor
        self.direction = direction
        self.position_si_2_device = float(multiplier * motor.gear * motor.position_si_2_device)
        self.homingMethod = homingMethod
        self.homingDirection = homingKwargs['homingDirection']
        self.length = min(length, motor.length)
        self.lower = 0.
        self.upper = length * self.position_si_2_device
        self.logger = get_logger(str(self))
        self.only_new_ones = OnlyOnce()

        # Init
        self.apply_motor_direction(direction)
        merged = merge_dicts(self.motor.defaultSettings, settings)
        self.apply_settings(merged)

        for errMsg in self.error_history_messages():
            self.logger.error(errMsg)

        if node.get_state() is CiA402State.FAULT:
            node.reset_fault()

        self.switch_off()

        self.logger.debug('direction: %f', self.direction)
        self.logger.debug('homingDirection: %f', self.homingDirection)
        self.logger.debug('homingMethod: %d', self.homingMethod)
        self.logger.debug('position_si_2_device: %f', self.position_si_2_device)

    def apply_motor_direction(self, direction: float):
        """Configure direction or orientation of controller / motor."""
        raise NotImplementedError

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

    def device_error_message(self, code: int) -> str:
        """Device error message from error code."""
        return self.DEVICE_ERROR_CODES.get(
            code,
            f'Unknown device error message for error code: {code}',
        )

    def new_emcy_errors(self) -> Generator[EmcyError, None, None]:
        """Iterate over all new emergency error message frames (if any)."""
        yield from self.only_new_ones(self.node.emcy.active)

    def emcy_message(self, emcy: EmcyError) -> str:
        """Get vendor specific description of EMCY error."""
        return format_error_code(emcy.code, self.EMERGENCY_DESCRIPTIONS)

    def error_history_messages(self):
        """Iterate over current error messages in error history register."""
        errorHistory = self.node.sdo[0x1003]
        numErrors = errorHistory[0].raw
        for nr in range(numErrors):
            number = errorHistory[nr + 1].raw
            raw = number.to_bytes(4, sys.byteorder)
            code = int.from_bytes(raw[:2], 'little')
            yield format_error_code(code, self.EMERGENCY_DESCRIPTIONS)

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
        tarPosDev = targetPosition * self.position_si_2_device
        self.node.set_target_position(clip(tarPosDev, self.lower, self.upper))

    def get_actual_position(self) -> float:
        """Get actual position in SI units."""
        return self.node.get_actual_position() / self.position_si_2_device

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

            sdo[last].raw = value

    def __str__(self):
        return f'{type(self).__name__}({self.node}, {self.motor})'


class Mclm3002(Controller):

    """Faulhaber MCLM 3002 controller."""

    DEVICE_ERROR_CODES = FAULHABER_DEVICE_ERROR_CODES
    EMERGENCY_DESCRIPTIONS = FAULHABER_EMERGENCY_DESCRIPTIONS
    SUPPORTED_HOMING_METHODS = FAULHABER_SUPPORTED_HOMING_METHODS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.node.set_operation_mode(OperationMode.CYCLIC_SYNCHRONOUS_POSITION)

    def apply_motor_direction(self, direction: float):
        if direction >= 0:
            positivePolarity = 0
            self.node.sdo['Polarity'].raw = positivePolarity
        else:
            negativePolarity = (1 << 6) | (1 << 7)  # Position and velocity
            self.node.sdo['Polarity'].raw = negativePolarity

    def hard_stop_homing(self, speed: int = 100):
        """Crude hard stop homing for Faulhaber linear motors.

        Kwargs:
            speed: Speed for homing in device units.
        """
        lower = INF
        upper = -INF

        def expand(pos):
            """Expand homing range."""
            nonlocal lower, upper
            lower = min(lower, pos)
            upper = max(upper, pos)

        node = self.node
        sdo = self.node.sdo

        def halt():
            """Stop drive."""
            sdo[CONTROLWORD].raw = Command.ENABLE_OPERATION | CW.HALT

        def move(velocity: int):
            """Move motor with constant velocity."""
            sdo[CONTROLWORD].raw = Command.ENABLE_OPERATION
            sdo[TARGET_VELOCITY].raw = velocity
            sdo[CONTROLWORD].raw = Command.ENABLE_OPERATION | CW.NEW_SET_POINT

        limit = sdo['Current Control Parameter Set']['Continuous Current Limit'].raw

        def on_the_wall() -> bool:
            """Check if motor is on the wall."""
            current = sdo['Current Actual Value'].raw
            return current > limit  # TODO: Add percentage threshold?

        faulhaberHomingOffset = 0x607C
        final = HomingState.UNHOMED
        with node.restore_states_and_operation_mode():
            node.change_state(CiA402State.READY_TO_SWITCH_ON)
            node.sdo[faulhaberHomingOffset].raw = 0
            node.set_operation_mode(OperationMode.PROFILED_VELOCITY)
            node.nmt.state = OPERATIONAL

            if self.homingDirection >= 0:
                velocities = [speed, -speed]
            else:
                velocities = [-speed, speed]

            for vel in velocities:
                halt()
                move(vel)
                while not on_the_wall():
                    pos = sdo[POSITION_ACTUAL_VALUE].raw
                    expand(pos)
                    yield HomingState.ONGOING

                # Turn off voltage to disable current current value
                node.change_state(CiA402State.READY_TO_SWITCH_ON)

            halt()
            node.nmt.state = PRE_OPERATIONAL
            node.change_state(CiA402State.READY_TO_SWITCH_ON)

            width = upper - lower
            length = self.position_si_2_device * self.length
            if width < length:
                final = HomingState.FAILED
            else:
                final = HomingState.HOMED

                # Center in the middle
                margin = .5 * (width - length)
                lower += margin
                upper -= margin

                sdo[faulhaberHomingOffset].raw = lower
                sdo['Software Position Limit'][1].raw = -1e7
                sdo['Software Position Limit'][2].raw = +1e7

                self.lower = 0
                self.upper = upper - lower

        yield final

    def home(self):
        # Faulhaber does not support unofficial hard stop homing methods
        if self.homingMethod in {-1, -2, -3, -4}:
            return self.hard_stop_homing()

        return super().home()


class Epos4(Controller):

    """Maxon EPOS4 controller."""

    DEVICE_ERROR_CODES = MAXON_DEVICE_ERROR_CODES
    DEVICE_ERROR_REGISTER = MAXON_DEVICE_ERROR_REGISTER
    EMERGENCY_DESCRIPTIONS = MAXON_EMERGENCY_DESCRIPTIONS
    SUPPORTED_HOMING_METHODS = MAXON_SUPPORTED_HOMING_METHODS
    USE_POSITION_CONTROLLER = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # TODO: Test if firmwareVersion < 0x170h?
        self.logger.info('Firmware version 0x%04x', self.firmware_version())
        if self.USE_POSITION_CONTROLLER:
            self.node.set_operation_mode(OperationMode.CYCLIC_SYNCHRONOUS_POSITION)
        else:
            self.node.set_operation_mode(OperationMode.CYCLIC_SYNCHRONOUS_VELOCITY)

    def firmware_version(self) -> int:
        """Firmware version of EPOS4 node."""
        revisionNumber = self.node.sdo['Identity object']['Revision number'].raw
        lowWord = 16
        firmwareVersion = revisionNumber >> lowWord
        return firmwareVersion

    def apply_motor_direction(self, direction: float):
        variable = self.node.sdo['Axis configuration']['Axis configuration miscellaneous']
        misc = variable.raw
        if direction >= 0:
            newMisc = clear_bit(misc, bit=0)
        else:
            newMisc = set_bit(misc, bit=0)

        variable.raw = newMisc

    def home(self):
        if self.homingMethod == 35:
            homingMethod = 37
        else:
            homingMethod = self.homingMethod

        self.node.sdo[HOMING_METHOD].raw = homingMethod
        return proper_homing(self.node)

    def set_target_position(self, targetPosition):
        tarPosDev = targetPosition * self.position_si_2_device
        posSoll = clip(tarPosDev, self.lower, self.upper)
        if self.USE_POSITION_CONTROLLER:
            self.node.set_target_position(posSoll)
        else:
            posIst = self.node.get_actual_position()
            velSoll = 1e-3 / INTERVAL * (posSoll - posIst)
            self.node.set_target_velocity(velSoll)
