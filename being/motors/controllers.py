"""Motor controllers."""
from typing import Optional, Dict, Generator, Set, Any

from being.constants import TAU

from being.can.cia_402 import (
    CiA402Node,
    HOMING_METHODS,
    HomingParam,
    NEGATIVE,
    OperationMode,
    POSITIVE,
    State as CiA402State,
)
from being.constants import FORWARD, MILLI, MICRO, DECI
from being.error import BeingError
from being.motors.homing import (
    HomingProgress,
    MINIMUM_HOMING_WIDTH,
    crude_homing,
    proper_homing,
)
from being.motors.motors import Motor
from being.utils import merge_dicts
from being.math import (
    rpm_to_angular_velocity,
)


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
    DEVICE_UNITS = {}

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
        self.gearRatio = motor.gearRatio

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
            f'Unknown device error message for error code: {errorCode}',
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
            raise ControllerError(
                f'Homing method {method} not supported for controller {self}')

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

        tarPos = tarPos * float(self.gearRatio)

        self.node.set_target_position(tarPos / self.DEVICE_UNITS['length'])

    def get_actual_position(self) -> float:
        """Get actual position in SI units."""
        actualPosition = self.node.get_actual_position()
        return actualPosition * self.DEVICE_UNITS['length'] / self.gearRatio

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
                sdo[last].raw = value / self.DEVICE_UNITS[name]
            else:
                sdo[last].raw = value

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

    DEVICE_UNITS = {
        'length': MICRO,
        'current': MILLI,
        'speed': MILLI,
        'Current Control Parameter Set/Continuous Current Limit': MILLI,
        'Current Control Parameter Set/Peak Current Limit': MILLI,
        'Max Profile Velocity': MILLI,
        'Profile Acceleration': MILLI,
        'Profile Deceleration': MILLI,
    }

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

    def __init__(self,
        node: CiA402Node,
        motor: Motor,
        settings: Optional[dict] = None,
        direction: int = FORWARD,
        homingDirection: Optional[int] = None,
        endSwitches: bool = False,
        length: Optional[float] = None,
        ):

        super().__init__(node,
                motor,
                settings,
                direction,
                homingDirection,
                endSwitches)

        # TODO: Hold these values on controller level? In case one overwrites the 
        # default settings, the configuration held on motor level is not correct
        gearConfig = node.sdo['Gear configuration']
        numerator = gearConfig['Gear reduction numerator'].raw
        denumerator = gearConfig['Gear reduction denominator'].raw
        encoder = node.sdo['Digital incremental encoder 1']
        encoderNumberOfPulses = encoder['Digital incremental encoder 1 number of pulses'].raw
        # Hacky implementation. Since we want to keep symmetry between both controller classes,
        # we overwrite the gearRatio with the final conversion factor
        gear = numerator / denumerator
        self.gearRatio = gear * encoderNumberOfPulses * 4 / TAU

        if length:
            self.DEVICE_UNITS['length'] = length

    DEVICE_ERROR_REGISTER: Dict[int, str] = {
        1 << 0: 'Generic Error',
        1 << 1: 'Current Error',
        1 << 2: 'Voltage Error',
        1 << 3: 'Temperature Error',
        1 << 4: 'Communication Error',
        1 << 5: 'Device profile-specific',
        1 << 6: 'Reserved (always 0)',
        1 << 7: 'Motion Error',
    }

    DEVICE_ERROR_CODES: Dict[int, str] = {
        0x0000: 'No Error',
        0x1000: 'Generic error',
        0x1090: 'Firmware incompatibility error',
        0x2310: 'Overcurrent error',
        0x2320: 'Power stage protection error',
        0x3210: 'Overvoltage error',
        0x3220: 'Undervoltage error',
        0x4210: 'Thermal overload error',
        0x4380: 'Thermal motor overload error',
        0x5113: 'Logic supply voltage too low error',
        0x5280: 'Hardware defect error',
        0x5281: 'Hardware incompatibility error',
        0x6080: 'Sign of life error',
        0x6081: 'Extension 1 watchdog error',
        0x6320: 'Software parameter error',
        0x6380: 'Persistent parameter corrupt error',
        0x7320: 'Position sensor error',
        0x7380: 'Position sensor breach error',
        0x7381: 'Position sensor resolution error',
        0x7382: 'Position sensor index error',
        0x7388: 'Hall sensor error',
        0x7389: 'Hall sensor not found error',
        0x738A: 'Hall angle detection error',
        0x738C: 'SSI sensor error',
        0x738D: 'SSI sensor frame error',
        0x7390: 'Missing main sensor error',
        0x7391: 'Missing commutation sensor error',
        0x7392: 'Main sensor direction error',
        0x8110: 'CAN overrun error(object lost)',
        0x8111: 'CAN overrun error',
        0x8120: 'CAN passive mode error',
        0x8130: 'CAN heartbeat error',
        0x8150: 'CAN PDO COB-ID collision',
        0x8180: 'EtherCAT communication error',
        0x8181: 'EtherCAT initialization error',
        0x8182: 'EtherCAT Rx queue overflow',
        0x8183: 'EtherCAT communication error(internal)',
        0x8184: 'EtherCAT communication cycle time error',
        0x81FD: 'CAN bus turned off',
        0x81FE: 'CAN Rx queue overflow',
        0x81FF: 'CAN Tx queue overflow',
        0x8210: 'CAN PDO length error',
        0x8250: 'RPDO timeout',
        0x8280: 'EtherCAT PDO communication error',
        0x8281: 'EtherCAT SDO communication error',
        0x8611: 'Following error',
        0x8A80: 'Negative limit switch error',
        0x8A81: 'Positive limit switch error',
        0x8A82: 'Software position limit error',
        0x8A88: 'STO error',
        0xFF01: 'System overloaded error',
        0xFF02: 'Watchdog error',
        0xFF0B: 'System peak overloaded error',
        0xFF10: 'Controller gain error',
        0xFF11: 'Auto tuning identification error',
        0xFF12: 'Auto tuning current limit error',
        0xFF13: 'Auto tuning identification current error',
        0xFF14: 'Auto tuning data sampling error',
        0xFF15: 'Auto tuning sample mismatch error',
        0xFF16: 'Auto tuning parameter error',
        0xFF17: 'Auto tuning amplitude mismatch error',
        0xFF19: 'Auto tuning timeout error',
        0xFF20: 'Auto tuning standstill error',
        0xFF21: 'Auto tuning torque invalid error',
        0xFF22: 'Auto tuning max system speed error',
        0xFF23: 'Auto tuning motor connection error',
        0xFF24: 'Auto tuning sensor signal error',
    }

    """Add value ranges to the dict"""
    for i in range(0x1080, 0x1088 + 1):
        DEVICE_ERROR_CODES[i] = 'Generic initialization error'
    for i in range(0x5480, 0x5483 + 1):
        DEVICE_ERROR_CODES[i] = 'Hardware error'
    for i in range(0x6180, 0x61F0 + 1):
        DEVICE_ERROR_CODES[i] = 'Internal software error'

    SUPPORTED_HOMING_METHODS = {
        -4, -3, -2, -1, 1, 2, 7, 11, 17, 18, 23, 27, 33, 34, 37,
    }

    DEVICE_UNITS = {
        'length': 1 / TAU,
        'speed': TAU / 60,
        'kinematics': TAU / 60,
        'current': MILLI,
        'torque': MICRO,
        'Motor data/Nominal current': MILLI,
        'Motor data/Output current limit': MILLI,
        'Motor data/Thermal time constant winding': DECI,
        'Motor data/Torque constant': MICRO,
        'Motor rated torque': MICRO,
        'Position control parameter set/Position controller P gain': MICRO,
        'Position control parameter set/Position controller I gain': MICRO,
        'Position control parameter set/Position controller D gain': MICRO,
        'Position control parameter set/Position controller FF velocity gain': MICRO,
        'Position control parameter set/Position controller FF acceleration gain': MICRO,
        'Current control parameter set/Current controller P gain': MICRO,
        'Current control parameter set/Current controller I gain': MICRO,
        'Gear configuration/Max gear input speed': TAU / 60,
        'Max motor speed': TAU / 60,
        'Max profile velocity': TAU / 60,
        'Max acceleration': TAU / 60,
        'Max deceleration': TAU / 60,

    }

    def home(self):
        method = self.homing_method()

        # Homing method 35 deprecated since new CiA 402 standard. Got replaced
        # with 37. Maxon EPOS4 uses the newer definition
        if method == 35:
            method = 37

        units = self.DEVICE_UNITS
        self.validate_homing_method(method)
        maxSpeed = rpm_to_angular_velocity(60) / units.speed
        maxAcc = 100 / units.kinematics
        return proper_homing(self.node, method, maxSpeed, maxAcc)
