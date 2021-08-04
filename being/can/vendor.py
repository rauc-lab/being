"""Vendor specific definitions and lookups."""
import enum
from typing import NamedTuple, Dict

from being.bitmagic import check_bit_mask


class Units(NamedTuple):

    """Device units.

    SI conversion factor for value * factor -> device units.
    """

    length: float = 1.
    current: float = 1.
    kinematics: float = 1.
    speed: float = 1.
    torque: float = 1.


UNITS: Dict[bytes, Units] = {
    r'MCLM3002P-CO': Units(
        length=1e6,
        current=1000,
        kinematics=1000,
        speed=1000,  # Speeds are in mm/s
    ),
    # TODO: conversion depends on system configuration (-> gear ratio). How to solve?
    r'EPOS4': Units(  # set conversions on node configuration
        length=1,  # [increments]
        current=1000,
        kinematics=1000,  # [rad/s^2]
        speed=1000,  # [rad/s]
    ),
}
"""Raw MANUFACTURER_DEVICE_NAME byte string -> Vendor units lookup."""

# TODO: Generalize for other vendors!
FAULHABER_ERROR_REGISTER: Dict[int, str] = {
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

MAXON_ERROR_REGISTER: Dict[int, str] = {
    1 << 0: 'Generic Error',
    1 << 1: 'Current Error',
    1 << 2: 'Voltage Error',
    1 << 3: 'Temperature Error',
    1 << 4: 'Communication Error',
    1 << 5: 'Device profile-specific',
    1 << 6: 'Reserved (always 0)',
    1 << 7: 'Motion Error',
}
"""Error code -> Error message string lookup."""


def stringify_error(value: int, errorDict: dict) -> str:
    """Concatenate error messages for a given error value."""
    messages = []
    for mask, message in errorDict.items():
        if check_bit_mask(value, mask):
            messages.append(message)

    return ', '.join(messages)


class MCLM3002:
    """Faulhaber MCLM3002 motor controller definitions.
    Vendor specific or not available with Maxon EPOS4.
    For Faulhaber MCLM3002 registers, see page 103 in
    https://www.faulhaber.com/fileadmin/Import/Media/DE_7000_00039.pdf
    """

    # Manufacturer specific objects
    DIGITAL_INPUT_SETTINGS = 0x2310
    DIGIAL_INPUT_STATUS = 0x2311
    ANALOG_INPUT_STATUS = 0x2313
    ANALOG_INPUT_STATUS_RAW = 0x2314
    FAULT_PIN_SETTINGS = 0x2315

    FILTER_SETTINGS = 0x2330
    SAMPLING_RATE = 1
    GAIN_SCHEDULING = 2

    GENERAL_SETTINGS = 0x2338
    PURE_SINUS_COMMUTATION = 2
    ACITVATE_POSITION_LIMITS_IN_VELOCITY_MODE = 2
    ACITVATE_POSITION_LIMITS_IN_POSITION_MODE = 3

    VELOCITY_CONTROL_PARAMETER_SET = 0x2331
    PROPORTIONAL_TERM_POR = 1
    INTEGRAL_TERM_I = 2

    POSITION_CONTROL_PARAMETER_SET = 0x2332
    PROPORTIONAL_TERM_PP = 1
    DERIVATIVE_TERM_PD = 2

    CURRENT_CONTROL_PARAMETER_SET = 0x2333
    CONTINUOUS_CURRENT_LIMIT = 1
    PEAK_CURRENT_LIMIT = 2
    INTEGRAL_TERM_CI = 3

    MOTOR_DATA = 0x2350
    ENCODER_DATA = 0x2351

    # CiA 402 Objects but not with Maxon EPOS4!
    POSITION_ACTUAL_INTERNAL_VALUE = 0x6063
    VELOCITY_WINDOW = 0x606D
    VELOCITY_WINDOW_TIME = 0x606E
    VELOCITY_THRESHOLD = 0x606F
    VELOCITY_THRESHOLD_TIME = 0x6070
    CURRENT_ACTUAL_VALUE = 0x6078
    HOMING_OFFSET = 0x607C
    POLARITY = 0x607E
    POSITION_ENCODER_RESOLUTION = 0x608F
    GEAR_RATIO = 0x6091
    FEED_CONSTANT = 0x6092
    POSITION_FACTOR = 0x6093
    CONTROL_EFFORT = 0x60FA


class EPOS4:

    """Maxon EPOS4 motor controller definitions.
    Registers are listed starting at page 66 in
     https://www.maxongroup.ch/medias/sys_master/root/8884070187038/EPOS4-Firmware-Specification-En.pdf
    """

    # Manufacturer specific objects

    AXIS_CONFIGURATION = 0x3000
    SENSORS_CONFIGURATION = 1
    CONTROL_STRUCTURE = 2
    COMMUTATION_SENSORS = 3
    AXIS_CONFIGURATION_MISCELLANEOUS = 4
    MAIN_SENSOR_RESOLUTION = 5
    MAX_SYSTEM_SPEED = 6

    MOTOR_DATA_MAXON = 0x3001
    NOMINAL_CURRENT = 1
    OUTPUT_CURRENT_LIMIT = 2
    NUMBER_OF_POLE_PAIRS = 3
    THERMAL_TIME_CONSTANT_WINDING = 4
    MOTOR_TORQUE_CONSTANT = 5

    GEAR_CONFIGURATION = 0x3003
    GEAR_REDUCTION_NUMERATOR = 1
    GEAR_REDUCTION_DENOMINATOR = 2
    MAX_GEAR_INPUT_SPEED = 3

    DIGITAL_INCREMENTAL_ENCODER_1 = 0x3010
    DIGITAL_INCREMENTAL_ENCODER_1_NUMBER_OF_PULSES = 1
    DIGITAL_INCREMENTAL_ENCODER_1_TYPE = 2
    DIGITAL_INCREMENTAL_ENCODER_1_INDEX_POSITION = 4

    CURRENT_CONTROL_PARAMETER_SET = 0x30A0
    CURRENT_CONTROLLER_P_GAIN = 1
    CURRENT_CONTROLLER_I_GAIN = 2

    POSITION_CONTROL_PARAMETER_SET = 0x30A1
    POSITION_CONTROLLER_P_GAIN = 1
    POSITION_CONTROLLER_I_GAIN = 2
    POSITION_CONTROLLER_D_GAIN = 3
    POSITION_CONTROLLER_FF_VELOCITY_GAIN = 4
    POSITION_CONTROLLER_FF_ACCELERATION_GAIN = 5

    VELOCITY_CONTROL_PARAMETER_SET_MAXON = 0x30A2
    VELOCITY_CONTROLLER_P_GAIN = 1
    VELOCITY_CONTROLLER_I_GAIN = 2

    HOME_OFFSET_MOVE_DISTANCE = 0x30B1

    # Standardized but not available with Faulhaber

    ABORT_CONNECTION_OPTION_CODE = 0x6007
    FOLLOWING_ERROR_WINDOW = 0x6065
    MOTOR_RATED_TORQUE = 0x6076
    MAX_MOTOR_SPEED = 0x6080

    INTERPOLATION_TIME_PERIOD = 0x60C2
    INTERPOLATION_TIME_PERIOD_VALUE = 1

    MOTOR_TYPE = 0x6402

    class AxisPolarity(enum.IntEnum):
        """Axis polarity for DC motors"""
        CCW = 0
        CW = 1
