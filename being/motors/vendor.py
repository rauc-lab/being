"""Vendor specific definitions / helpers."""
import enum
from typing import Dict, Set, NamedTuple

from being.bitmagic import bit_mask
from being.constants import MICRO, MILLI, TAU, DECI


def _to_int(self) -> int:
    """Convert named tuples with _field_bits attribute to int."""
    num = 0
    for value, (_, shift) in zip(self, self._field_bits):
        num |= (value << shift)

    return num


def _from_int(cls, num: int):
    """Construct named tuple with _field_bits attribute instance."""
    kwargs = {}
    for field, (upper, lower) in zip(cls._fields, cls._field_bits):
        mask = bit_mask(width=upper - lower)
        kwargs[field] = (num & (mask << lower)) >> lower

    return cls(**kwargs)


# Faulhaber world


FAULHABER_DEVICE_ERROR_CODES: Dict[int, str] = {
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
FAULHABER_EMERGENCY_ERROR_CODES: Dict[int, str] = {
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
FAULHABER_SUPPORTED_HOMING_METHODS: Set[int] = {
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14,
    17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
    33, 34,
    35,
}
FAULHABER_DEVICE_UNITS: Dict[str, float] = {
    'length': MICRO,
    'current': MILLI,
    'speed': MILLI,
    'Current Control Parameter Set/Continuous Current Limit': MILLI,
    'Current Control Parameter Set/Peak Current Limit': MILLI,
    'Max Profile Velocity': MILLI,
    'Profile Acceleration': MILLI,
    'Profile Deceleration': MILLI,
}


# Maxon world


MAXON_DEVICE_ERROR_REGISTER: Dict[int, str] = {
    1 << 0: 'Generic Error',
    1 << 1: 'Current Error',
    1 << 2: 'Voltage Error',
    1 << 3: 'Temperature Error',
    1 << 4: 'Communication Error',
    1 << 5: 'Device profile-specific',
    1 << 6: 'Reserved (always 0)',
    1 << 7: 'Motion Error',
}
MAXON_DEVICE_ERROR_CODES: Dict[int, str] = {
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
MAXON_EMERGENCY_ERROR_CODES: Dict[int, str] = {
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

# Add value ranges to the dict
for i in range(0x1080, 0x1088 + 1):
    MAXON_DEVICE_ERROR_CODES[i] = 'Generic initialization error'
for i in range(0x5480, 0x5483 + 1):
    MAXON_DEVICE_ERROR_CODES[i] = 'Hardware error'
for i in range(0x6180, 0x61F0 + 1):
    MAXON_DEVICE_ERROR_CODES[i] = 'Internal software error'

MAXON_SUPPORTED_HOMING_METHODS: Set[int] = {
    -4, -3, -2, -1, 1, 2, 7, 11, 17, 18, 23, 27, 33, 34, 37,
}
MAXON_DEVICE_UNITS: Dict[str, float] = {
    'Motor data/Nominal current': MILLI,
    'Motor data/Output current limit': MILLI,
    'Motor data/Thermal time constant winding': DECI,
    'Current threshold for homing mode': MILLI,
    'Motor data/Torque constant': MICRO,
    'Motor rated torque': MICRO,
    # 'length': 1 / TAU,
    # 'speed': TAU / 60,
    # 'kinematics': TAU / 60,
    # 'current': MILLI,
    # 'torque': MICRO,
    # 'Position control parameter set/Position controller P gain': MICRO,
    # 'Position control parameter set/Position controller I gain': MICRO,
    # 'Position control parameter set/Position controller D gain': MICRO,
    # 'Position control parameter set/Position controller FF velocity gain': MICRO,
    # 'Position control parameter set/Position controller FF acceleration gain': MICRO,
    # 'Current control parameter set/Current controller P gain': MICRO,
    # 'Current control parameter set/Current controller I gain': MICRO,
    # 'Gear configuration/Max gear input speed': TAU / 60,
    # 'Max motor speed': TAU / 60,
    # 'Max profile velocity': TAU / 60,
    # 'Max acceleration': TAU / 60,
    # 'Max deceleration': TAU / 60,
}
MAXON_FOLLOWING_ERROR_WINDOW_DISABLED = 4294967295  # (1 << 32) - 1
MAXON_INTERPOLATION_DISABLED = 0
MAXON_NEGATIVE_LIMIT_SWITCH = 0
MAXON_POSITIVE_LIMIT_SWITCH = 1
MAXON_POLARITY_CCW = 0
MAXON_POLARITY_CW = 1
MAXON_INPUT_LOW_ACTIVE = 3 # TODO: Is this correct?


class MaxonMotorType(enum.IntEnum):

    """Maxon motor types."""

    PHASE_MODULATED_DC_MOTOR = 1
    SINUSOIDAL_PM_BL_MOTOR = 10
    TRAPEZOIDAL_PM_BL_MOTOR = 11


class MaxonSensorsConfiguration(NamedTuple):
    sensorType3: int = 0x10  # 0x00: None
                             # 0x10: Digital Hall Sensor (EC motors only)
    sensorType2: int = 0x00  # 0x00: None
                             # 0x01: Digital incremental encoder 2
                             # 0x02: Analog incremental encoder
                             # 0x03: SSI absolute encoder
    sensorType1: int = 0x01  # 0x00: None
                             # 0x01: Digital incremental encoder 1
    _field_bits = [
        #(31, 24),  # Reserved
        (23, 16),
        (15, 8),
        (7, 0),
    ]

    to_int = _to_int
    from_int = classmethod(_from_int)


_MAXON_SENSORS_CONFIGURATION_DEFAULT = 0x00100001
assert MaxonSensorsConfiguration().to_int() == _MAXON_SENSORS_CONFIGURATION_DEFAULT
assert MaxonSensorsConfiguration.from_int(_MAXON_SENSORS_CONFIGURATION_DEFAULT) == MaxonSensorsConfiguration()


class MaxonControlStructure(NamedTuple):

    """Maxon EPOS4 Axis configuration Control structure."""

    mountingPositionSensor3: int = 0   # 0: On motor
    mountingPositionSensor2: int = 0   # 0: On motor (or undefined), 1: On gear
    mountingPositionSensor1: int = 0   # 0: On motor (or undefined), 1: On gear
    auxiliarySensor: int = 0           # 0: None, 1: Sensor 1, 2: Sensor 2, 3: Sensor 3
    mainSensor: int = 1                # 0: None, 1: Sensor 1, 2: Sensor 2, 3: Sensor 3
    processValueReference: int = 0     # 0: On motor (or undefined), 1: On gear
    gear: int = 0                      # 0: None, 1: Gear mounted to the system
    positionControlStructure: int = 1  # 0: None
                                       # 1: PID position controller
                                       # 2: Dual loop position controller
    velocityControlStructure: int = 1  # 0: None
                                       # 1: PI velocity controller (low pass filter)
                                       # 2: PI velocity controller (observer)
    currentControlStructure: int = 1   # 1: PI current controller
    _field_bits = [
        #(31, 30),  # Reserved
        (29, 28),
        (27, 26),
        (25, 24),
        (23, 20),
        (19, 16),
        (15, 14),
        #(14, 13),  # Reserved
        (13, 12),
        (11, 8),
        (7, 4),
        (3, 0),
    ]
    to_int = _to_int
    from_int = classmethod(_from_int)


_DEFAULT_MAXON_CONTROL_STRUCTURE = 0x00010111
assert MaxonControlStructure().to_int() == _DEFAULT_MAXON_CONTROL_STRUCTURE
assert MaxonControlStructure.from_int(_DEFAULT_MAXON_CONTROL_STRUCTURE) == MaxonControlStructure()


class MaxonDigitalIncrementalEncoderType(NamedTuple):

    """Defines the configuration of the digital incremental encoder 1."""

    method: int = 0     # 0: Speed measured as time between two consecutive sensor edges
                        # 1: Speed measured as number of sensor edges per control cycle
    direction: int = 0  # 0: maxon
                        # 1: Inverted (or encoder mounted on motor shaft)
    index: int = 1      # 0: Encoder without index (2-channel)
                        # 1: Encoder with index (3-channel)
    _field_bits = [
        #(15, 10),  # Reserved
        (10, 9),
        #(8, 5),  # Reserved
        (5, 4),
        #(3, 1),  # Reserved
        (1, 0),
    ]
    to_int = _to_int
    from_int = classmethod(_from_int)


_DEFAULT_MAXON_DIGITAL_INCREMENTAL_ENCODER_TYPE = 0x0001
assert MaxonDigitalIncrementalEncoderType().to_int() == _DEFAULT_MAXON_DIGITAL_INCREMENTAL_ENCODER_TYPE
assert MaxonDigitalIncrementalEncoderType.from_int(_DEFAULT_MAXON_DIGITAL_INCREMENTAL_ENCODER_TYPE) == MaxonDigitalIncrementalEncoderType()
