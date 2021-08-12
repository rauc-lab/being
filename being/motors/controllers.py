"""Motor controllers."""
from typing import Optional, Dict, Generator, Set

from being.can.cia_402 import (
    CiA402Node,
    HOMING_METHODS,
    HomingParam,
    NEGATIVE,
    OperationMode,
    POSITIVE,
    State as CiA402State,
)
from being.can.vendor import Units
from being.constants import FORWARD
from being.error import BeingError
from being.motors.homing import (
    HomingProgress,
    MINIMUM_HOMING_WIDTH,
    crude_homing,
    proper_homing,
)


class ControllerError(BeingError):

    """General Being controller errors."""


class Controller:

    """Semi abstract controller base class."""

    DEVICE_ERROR_CODES: Dict[int, str] = {}
    """Device error code -> error message text lookup."""

    SUPPORTED_HOMING_METHODS: Set[int] = {}
    """Supported homing methods."""

    DEVICE_UNITS = Units()
    """SI -> device units conversion."""

    def __init__(self,
            node: CiA402Node,
            length = None,
            direction: int = FORWARD,
            homingDirection: Optional[int] = None,
            endSwitches: bool = False,
        ):
        """Args:
            node: Connected CanOpen node.

        Kwargs:
            length: Length of position range.
            homingDirection: Homing direction.
            endSwitches: End switches present?
        """
        if homingDirection is None:
            homingDirection = direction

        self.node = node
        self.length = length
        self.direction = direction
        self.homingDirection = homingDirection
        self.endSwitches = endSwitches

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

    def device_error_message(self, errorCode: int) -> str:
        """Device error message from error code."""
        return self.DEVICE_ERROR_CODES.get(
            errorCode,
            f'Unknown device error message for errorCode: {errorCode}',
        )

    def iter_emergencies(self) -> Generator[object, None, None]:
        """Iterate over emergency error messages (if any)."""
        yield from self.node.emcy.active

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

    def validate_homing_method(self, method: int):
        """Validate homing method for this controller. Raises a ControllerError
        if homing method is not support.

        Args:
            method: Homing method to check.
        """
        if method not in self.SUPPORTED_HOMING_METHODS:
            raise ControllerError(f'Homing method {method} not supported for controller {self}')

    def home(self) -> HomingProgress:
        """Create homing job routine for this controller."""
        method = self.homing_method()
        self.validate_homing_method(method)
        return proper_homing(self.node, method)

    def set_target_position(self, targetPosition):
        """Set target position in SI units."""
        if self.direction > 0:
            tarPos = targetPosition
        else:
            tarPos = self.length - targetPosition

        self.node.set_target_position(tarPos * self.DEVICE_UNITS.length)

    def get_actual_position(self) -> float:
        """Get actual position in SI units."""
        return self.node.get_actual_position() / self.DEVICE_UNITS.length

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

    DEVICE_UNITS = Units(
        length=1e6,  # Lengths in µm
        current=1000,
        kinematics=1000,
        speed=1000,  # Speeds are in mm/s
    )

    def home(self):
        method = self.homing_method()

        # Faulhaber does not support homing methods -1 and -2. Use crude_homing
        # instead
        if method in {-1, -2}:
            units = self.DEVICE_UNITS
            return crude_homing(
                self.node,
                self.homingDirection,
                speed=0.100 * units.speed,
                minWidth=MINIMUM_HOMING_WIDTH * units.length,
                length=self.length * units.length,
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
