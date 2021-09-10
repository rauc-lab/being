"""Motor controllers."""
import enum
import logging
import sys
import warnings
from typing import Optional, Dict, Set, Any, Union

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
    STATUSWORD,
    State as CiA402State,
    TARGET_POSITION,
    TARGET_VELOCITY,
    determine_homing_method,
    which_state,
)
from being.config import CONFIG
from being.constants import FORWARD, INF
from being.error import BeingError
from being.logging import get_logger
from being.math import clip
from being.motors.events import MotorEvent
from being.motors.homing import HomingProgress, HomingProgress
from being.motors.homing import HomingState
from being.motors.motors import Motor
from being.motors.vendor import (
    FAULHABER_EMERGENCY_DESCRIPTIONS,
    FAULHABER_SUPPORTED_HOMING_METHODS,
    MAXON_EMERGENCY_DESCRIPTIONS,
    MAXON_SUPPORTED_HOMING_METHODS,
)
from being.pubsub import PubSub
from being.utils import merge_dicts
from being.motors.homing import CiA402Homing
from being.can.cia_402 import CW, Command
from being.can.cia_402 import UNDEFINED, POSITIVE, NEGATIVE


INTERVAL = CONFIG['General']['INTERVAL']
LOGGER = get_logger(__name__)


class ControllerError(BeingError):

    """General Being controller errors."""


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


def format_error_code(errorCode: int, descriptions: list) -> str:
    """Emergency error code -> description.

    Args:
        errorCode: Error code to check.
        descriptions: Description table with (code, mask, description) entries.

    Returns:
        Text error description.
    """
    description = 'Unknown emergency error'
    for code, mask, desc in descriptions:
        if errorCode & mask == code:
            description = desc

    return f'{description} (error code {errorCode:#04x})'


def maybe_int(string: str) -> Union[int, str]:
    """Try to cast string to int.

    Args:
        string: Input string.

    Returns:
        Maybe an int. Pass on input string otherwise.

    Usage:
        >>> maybe_int('123')
        123

        >>> maybe_int('  0x7b')
        123
    """
    string = string.strip()
    if string.isnumeric():
        return int(string)

    if string.startswith('0x'):
        return int(string, base=16)

    if string.startswith('0b'):
        return int(string, base=2)

    return string


def apply_settings_to_node(node, settings: Dict[str, Any]):
    """Apply settings to CANopen node.

    Args:
        settings: Settings to apply. Addresses (path syntax) -> value
            entries.
    """
    for name, value in settings.items():
        *path, last = map(maybe_int, name.split('/'))
        sdo = node.sdo
        for key in path:
            sdo = sdo[key]

        sdo[last].raw = value


def default_homing_method(
        homingDirection: int = UNDEFINED,
        endSwitches: bool = False,
        indexPulse: bool = False,
    ) -> int:
    """Default homing method."""
    if homingDirection == UNDEFINED:
        return 35

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


class Controller(PubSub):

    """Semi abstract controller base class.

    Attributes:
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

    EMERGENCY_DESCRIPTIONS: list = []
    SUPPORTED_HOMING_METHODS: Set[int] = {}
    HOMING_TYPE = CiA402Homing

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

        super().__init__(events=MotorEvent)

        # Attrs
        self.node: CiA402Node = node
        self.motor: Motor = motor
        self.direction = direction
        self.position_si_2_device = float(multiplier * motor.gear * motor.position_si_2_device)
        self.length = length
        #self.logger = get_logger(str(self))
        self.logger = logging.getLogger(str(self))
        self.lower = 0.
        self.upper = length * self.position_si_2_device

        self.lastState = node.get_state()
        self.switchJob = None

        self.homing = self.HOMING_TYPE(node)

        # Configure node
        self.apply_motor_direction(direction)
        homingMethod = self.determine_homing_method(**homingKwargs)
        self.logger.debug('homingMethod: %d', homingMethod)
        self.validate_homing_method(homingMethod)
        node.sdo[HOMING_METHOD].raw = homingMethod
        merged = merge_dicts(self.motor.defaultSettings, settings)
        apply_settings_to_node(self.node, merged)

        for errMsg in self.error_history_messages():
            self.logger.error(errMsg)

        self.node.change_state(CiA402State.READY_TO_SWITCH_ON, how='sdo', timeout=0.5)

    def disable(self):
        """Disable drive (no power)."""
        self.logger.debug('disable()')
        self.switchJob = self.node.change_state(CiA402State.READY_TO_SWITCH_ON, how='pdo', generator=True)

    def enable(self):
        """Enable drive."""
        self.logger.debug('enable()')
        self.switchJob = self.node.change_state(CiA402State.OPERATION_ENABLED, how='pdo', generator=True)

    def enabled(self) -> bool:
        """Is motor enabled?"""
        return self.node.get_state() is CiA402State.OPERATION_ENABLED

    def home(self) -> HomingProgress:
        """Create homing job routine for this controller."""
        self.logger.debug('home()')
        self.homing.home()
        self.publish(MotorEvent.HOMING_CHANGED)

    @staticmethod
    def determine_homing_method(homingMethod: Optional[int] = None, **kwargs) -> int:
        """Determine homing method from homing kwargs."""
        if homingMethod is None:
            return default_homing_method(**kwargs)

        return homingMethod

    def apply_motor_direction(self, direction: float):
        """Configure direction or orientation of controller / motor."""
        raise NotImplementedError

    def format_emcy(self, emcy: EmcyError) -> str:
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
        if self.homing.state is HomingState.HOMED and self.lastState is CiA402State.OPERATION_ENABLED:
            dev = targetPosition * self.position_si_2_device
            clipped = clip(dev, self.lower, self.upper)
            self.node.set_target_position(clipped)

    def get_actual_position(self) -> float:
        """Get actual position in SI units."""
        return self.node.get_actual_position() / self.position_si_2_device

    def state_changed(self, state: CiA402State) -> bool:
        """Check if node state changed since last call."""
        if state is self.lastState:
            return False

        self.lastState = state
        return True

    def update(self):
        #state = which_state(self.node.pdo[STATUSWORD].raw)
        state = self.node.get_state('pdo')
        if self.state_changed(state):
            self.publish(MotorEvent.STATE_CHANGED)

        if state is CiA402State.FAULT:
            for emcy in self.node.emcy.active:
                msg = self.format_emcy(emcy)
                self.logger.error(msg)
                self.publish(MotorEvent.ERROR, msg)

            self.node.emcy.reset()

        if self.homing.ongoing:
            self.homing.update()
            if not self.homing.ongoing:
                self.publish(MotorEvent.HOMING_CHANGED)
        else:
            if self.switchJob:
                try:
                    next(self.switchJob)
                except StopIteration:
                    self.switchJob = None

    def __str__(self):
        return f'{type(self).__name__}({self.node}, {self.motor})'


class Mclm3002(Controller):

    """Faulhaber MCLM 3002 controller."""

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

        final = HomingState.UNHOMED

        with node.restore_states_and_operation_mode():
            node.change_state(CiA402State.READY_TO_SWITCH_ON)
            node.sdo['Home Offset'].raw = 0
            node.set_operation_mode(OperationMode.PROFILED_VELOCITY)

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

                node.sdo['Home Offset'].raw = lower
                sdo['Software Position Limit'][1].raw = -1e7
                sdo['Software Position Limit'][2].raw = +1e7

                self.lower = 0
                self.upper = upper - lower

        yield final

    def home(self):
        # Faulhaber does not support unofficial hard stop homing methods
        if self.homingMethod in {-1, -2, -3, -4}:
            self.homingState = HomingState.ONGOING
            self.homingJob = self.hard_stop_homing()
            self.publish(MotorEvent.HOMING_CHANGED)

        else:
            super().home()


class Epos4(Controller):

    """Maxon EPOS4 controller."""

    EMERGENCY_DESCRIPTIONS = MAXON_EMERGENCY_DESCRIPTIONS
    SUPPORTED_HOMING_METHODS = MAXON_SUPPORTED_HOMING_METHODS

    def __init__(self, *args, usePositionController=True, **kwargs):
        """Kwargs:
            usePositionController: If True use position controller on EPOS4 with
                operation mode CYCLIC_SYNCHRONOUS_POSITION. Otherwise simple
                custom application side position controller working with the
                CYCLIC_SYNCHRONOUS_VELOCITY.
        """
        super().__init__(*args, **kwargs)
        self.usePositionController = usePositionController

        # TODO: Test if firmwareVersion < 0x170h?
        self.logger.info('Firmware version 0x%04x', self.firmware_version())

        if self.usePositionController:
            self.node.set_operation_mode(OperationMode.CYCLIC_SYNCHRONOUS_POSITION)
        else:
            self.node.set_operation_mode(OperationMode.CYCLIC_SYNCHRONOUS_VELOCITY)

    @staticmethod
    def determine_homing_method(homingMethod=None, **homingKwargs):
        if homingMethod is None:
            homingMethod = default_homing_method(**homingKwargs)

        if homingMethod == 35:
            homingMethod = 37
            warnings.warn('Epos4 does not support homing method 35. Using 37 instead.')

        return homingMethod

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

    def set_target_position(self, targetPosition):
        #print('set_target_position()', self.homing.state, self.lastState)
        #print('set_target_position()', targetPosition)
        if self.homing.state is HomingState.HOMED and self.lastState is CiA402State.OPERATION_ENABLED:
            dev = targetPosition * self.position_si_2_device
            posSoll = clip(dev, self.lower, self.upper)

            if self.usePositionController:
                self.node.pdo[TARGET_POSITION].raw = posSoll
            else:
                posIst = self.node.pdo[POSITION_ACTUAL_VALUE]
                err = (posSoll - posIst)
                velSoll = 1e-3 / INTERVAL * err
                self.node.pdo[TARGET_VELOCITY].raw = velSoll
