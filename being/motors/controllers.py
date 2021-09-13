"""Motor controllers."""
import abc
import sys
import warnings
from typing import Optional, Set

from canopen.emcy import EmcyError

from being.bitmagic import clear_bit, set_bit
from being.can.cia_402 import CiA402Node, HOMING_METHOD, OperationMode, State
from being.config import CONFIG
from being.constants import FORWARD
from being.logging import get_logger
from being.math import clip
from being.motors.definitions import MotorInterface, MotorState, MotorEvent
from being.motors.homing import CiA402Homing, CrudeHoming, default_homing_method
from being.motors.motors import Motor
from being.motors.vendor import (
    FAULHABER_EMERGENCY_DESCRIPTIONS,
    FAULHABER_SUPPORTED_HOMING_METHODS,
    MAXON_EMERGENCY_DESCRIPTIONS,
    MAXON_SUPPORTED_HOMING_METHODS,
)
from being.utils import merge_dicts


INTERVAL = CONFIG['General']['INTERVAL']
LOGGER = get_logger(name=__name__, parent=None)


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


class Controller(MotorInterface):

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

        super().__init__()

        # Attrs
        self.node: CiA402Node = node
        self.motor: Motor = motor
        self.direction = direction
        self.length = length

        self.logger = get_logger(str(self))
        self.position_si_2_device = float(multiplier * motor.gear * motor.position_si_2_device)
        self.lower = 0.
        self.upper = length * self.position_si_2_device
        self.lastState = node.get_state()
        self.switchJob = None
        self.init_homing(**homingKwargs)

        # Configure node
        self.apply_motor_direction(direction)
        merged = merge_dicts(self.motor.defaultSettings, settings)
        self.node.apply_settings(merged)
        for errMsg in self.error_history_messages():
            self.logger.error(errMsg)

        #self.node.reset_fault()
        self.node.change_state(State.READY_TO_SWITCH_ON, how='sdo', timeout=0.5)

    def disable(self):
        self.switchJob = self.node.change_state(State.READY_TO_SWITCH_ON, how='pdo', generator=True)

    def enable(self):
        self.switchJob = self.node.change_state(State.OPERATION_ENABLED, how='pdo', generator=True)

    def motor_state(self):
        if self.lastState is State.OPERATION_ENABLED:
            return MotorState.ENABLED
        elif self.lastState is State.FAULT:
            return MotorState.FAULT
        else:
            return MotorState.DISABLED

    def home(self):
        """Create homing job routine for this controller."""
        self.logger.debug('home()')
        self.homing.home()
        self.publish(MotorEvent.HOMING_CHANGED)

    def homing_state(self):
        return self.homing.state

    def init_homing(self, **homingKwargs):
        """Setup homing."""
        method = default_homing_method(**homingKwargs)
        if method not in self.SUPPORTED_HOMING_METHODS:
            raise ValueError(f'Homing method {method} not supported for controller {self}')

        self.homing = CiA402Homing(self.node)
        self.node.sdo[HOMING_METHOD].raw = method

    @abc.abstractmethod
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

    def set_target_position(self, targetPosition):
        """Set target position in SI units."""
        if self.homing.homed:
            dev = targetPosition * self.position_si_2_device
            clipped = clip(dev, self.lower, self.upper)
            self.node.set_target_position(clipped)

    def get_actual_position(self) -> float:
        """Get actual position in SI units."""
        return self.node.get_actual_position() / self.position_si_2_device

    def state_changed(self, state: State) -> bool:
        """Check if node state changed since last call."""
        if state is self.lastState:
            return False

        self.lastState = state
        return True

    def publish_errors(self):
        for emcy in self.node.emcy.active:
            msg = self.format_emcy(emcy)
            self.logger.error(msg)
            self.publish(MotorEvent.ERROR, msg)

        self.node.emcy.reset()

    def update(self):
        """Controller tick function. Does the following:
          - Observe state changes and publish
          - Observe errors and publish
          - Drive homing
          - Drive state switching jobs
        """
        state = self.node.get_state('pdo')
        if self.state_changed(state):
            self.publish(MotorEvent.STATE_CHANGED)

        if state is State.FAULT:
            self.publish_errors()

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
    HARD_STOP_HOMING = {-1, -2, -3, -4}

    def __init__(self, *args, homingMethod=None, homingDirection=FORWARD, **kwargs):
        super().__init__(*args, homingMethod=homingMethod, homingDirection=homingDirection, **kwargs)
        self.node.set_operation_mode(OperationMode.CYCLIC_SYNCHRONOUS_POSITION)

    def init_homing(self, **homingKwargs):
        method = default_homing_method(**homingKwargs)
        if method in self.HARD_STOP_HOMING:
            minWidth = self.position_si_2_device * self.length
            self.homing = CrudeHoming(self.node, minWidth, homingMethod=method)
        else:
            super().init_homing(homingMethod=method)

    def apply_motor_direction(self, direction: float):
        if direction >= 0:
            positivePolarity = 0
            self.node.sdo['Polarity'].raw = positivePolarity
        else:
            negativePolarity = (1 << 6) | (1 << 7)  # Position and velocity
            self.node.sdo['Polarity'].raw = negativePolarity


class Epos4(Controller):

    """Maxon EPOS4 controller."""

    EMERGENCY_DESCRIPTIONS = MAXON_EMERGENCY_DESCRIPTIONS
    SUPPORTED_HOMING_METHODS = MAXON_SUPPORTED_HOMING_METHODS

    def __init__(self,
            *args,
            usePositionController=True,
            recoverRpdoTimeoutError=True,
            **kwargs,
        ):
        """Kwargs:
            usePositionController: If True use position controller on EPOS4 with
                operation mode CYCLIC_SYNCHRONOUS_POSITION. Otherwise simple
                custom application side position controller working with the
                CYCLIC_SYNCHRONOUS_VELOCITY.
            recoverRpdoTimeoutError: Re-enable drive after a FAULT because of a
                RPOD timeout error.
        """
        super().__init__(*args, **kwargs)
        self.usePositionController = usePositionController
        self.recoverRpdoTimeoutError = recoverRpdoTimeoutError

        self.rpdoTimeoutOccurred = False

        # TODO: Test if firmwareVersion < 0x170h?
        self.logger.info('Firmware version 0x%04x', self.firmware_version())

        if self.usePositionController:
            self.node.set_operation_mode(OperationMode.CYCLIC_SYNCHRONOUS_POSITION)
        else:
            self.node.set_operation_mode(OperationMode.CYCLIC_SYNCHRONOUS_VELOCITY)

    def init_homing(self, **homingKwargs):
        method = default_homing_method(**homingKwargs)
        if method == 35:
            warnings.warn('Epos4 does not support homing method 35. Using 37 instead.')
            method = 37

        super().init_homing(homingMethod=method)

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
        if self.homing.homed:
            dev = targetPosition * self.position_si_2_device
            posSoll = clip(dev, self.lower, self.upper)

            if self.usePositionController:
                self.node.set_target_position(posSoll)
            else:
                posIst = self.node.get_actual_position()
                self.node.set_target_position(posSoll)
                err = (posSoll - posIst)
                velSoll = 1e-3 / INTERVAL * err
                self.node.set_target_velocity(velSoll)

    def publish_errors(self):
        for emcy in self.node.emcy.active:
            rpodTimeout = 0x8250
            if emcy.code == rpodTimeout:
                self.rpdoTimeoutOccurred = True

            msg = self.format_emcy(emcy)
            self.logger.error(msg)
            self.publish(MotorEvent.ERROR, msg)

        self.node.emcy.reset()

    def update(self):
        super().update()
        if self.recoverRpdoTimeoutError:
            if self.lastState is State.FAULT and self.rpdoTimeoutOccurred:
                self.enable()
                self.rpdoTimeoutOccurred = False
