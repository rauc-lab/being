"""Motor definitions for the actual hardware motor types. Different motor
parameters / settings.
"""
from typing import NamedTuple
from fractions import Fraction

from being.utils import merge_dicts
from being.constants import TAU, MICRO, MILLI, NANO
from being.config import CONFIG
from being.motors.vendor import (
    MAXON_FOLLOWING_ERROR_WINDOW_DISABLED,
    MAXON_INPUT_LOW_ACTIVE,
    MAXON_INTERPOLATION_DISABLED,
    MAXON_POLARITY_CCW,
    MaxonControlStructure,
    MaxonMotorType,
    MaxonSensorsConfiguration,
)


INTERVAL = CONFIG['General']['INTERVAL']
TODO = 0


class Motor(NamedTuple):

    """Hardware motor.

    Definitions, settings for different hardware motors.
    """

    manufacturer: str
    """Manufacturer name."""

    name: str
    """Motor name."""

    length: float = None
    """Linear motor Length."""

    defaultSettings: dict = {}
    """Default settings for this motor."""

    gear: Fraction = Fraction(1, 1)
    """Gear ratio."""

    position_si_2_device: float = 1.0
    """Conversion factor for position SI -> device units."""


FAULHABER_DEFAULT_SETTINGS = {
    'General Settings/Pure Sinus Commutation': 1,
    'Filter Settings/Sampling Rate': 4,
    'Filter Settings/Gain Scheduling Velocity Controller': 1,
    #'Velocity Control Parameter Set/Proportional Term POR': 44,
    #'Velocity Control Parameter Set/Integral Term I': 50,
    'Position Control Parameter Set/Proportional Term PP': 15,  # or 8 (softer)
    'Position Control Parameter Set/Derivative Term PD': 10,  # or 14 (softer)
    'Current Control Parameter Set/Continuous Current Limit': 0.500,
    'Current Control Parameter Set/Peak Current Limit': 1.640,
    'Current Control Parameter Set/Integral Term CI': 3,
    'Max Profile Velocity': 1.0,
    'Profile Acceleration': 1.0,
    'Profile Deceleration': 1.0,
}


MAXON_DC_22_S_12V_DEFAULT_SETTINGS = {
    'Store parameters': 0,
    'Motor type': MaxonMotorType.PHASE_MODULATED_DC_MOTOR,
    'Motor data/Nominal current': 0.379,  # [Ampere]
    'Motor data/Output current limit': 2 * 0.379,  # [Ampere]
    'Motor data/Number of pole pairs': 1,
    'Motor data/Thermal time constant winding': 14.3,
    'Motor data/Torque constant': 0.0308,
    'Motor rated torque': 0.012228,
    'Gear configuration/Gear reduction numerator': 69,
    'Gear configuration/Gear reduction denominator': 13,
    'Gear configuration/Max gear input speed': 837.75,
    'Max motor speed': 942,
    'Axis configuration/Sensors configuration': 1,
    'Axis configuration/Control structure': 0x11121,
    'Axis configuration/Commutation sensors': 0,
    'Axis configuration/Axis configuration miscellaneous': 0x0 | MAXON_POLARITY_CCW,
    'Digital incremental encoder 1/Digital incremental encoder 1 number of pulses': 1024,
    'Digital incremental encoder 1/Digital incremental encoder 1 type': 1,
    'Following error window': MAXON_FOLLOWING_ERROR_WINDOW_DISABLED,
    'Position control parameter set/Position controller P gain': TODO,
    'Position control parameter set/Position controller I gain': TODO,
    'Position control parameter set/Position controller D gain': TODO,
    'Position control parameter set/Position controller FF velocity gain': 0,
    'Position control parameter set/Position controller FF acceleration gain': 0,
    'Current control parameter set/Current controller P gain': TODO,
    'Current control parameter set/Current controller I gain': TODO,
    # Will run smoother if set (0 = disabled).
    # However, will throw an RPDO timeout error when reloading web page
    #INTERVAL * 1000  # [ms]
    'Interpolation time period/Interpolation time period value': MAXON_INTERPOLATION_DISABLED,
    # TODO: check why parameter exeeds value range ?!
    # 'Configuration of digital inputs/Digital input 1 configuration': MAXON_NEGATIVE_LIMIT_SWITCH,
    # 'Configuration of digital inputs/Digital input 2 configuration': MAXON_POSITIVE_LIMIT_SWITCH,
    'Digital input properties/Digital inputs polarity': MAXON_INPUT_LOW_ACTIVE,
    'Max profile velocity': 158,
    'Profile acceleration': 1047,
    'Profile deceleration': 1047,
    'Home offset move distance': 0,
    'Current threshold for homing mode': 0.3,
}


MAXON_DC_22_S_24V_DEFAULT_SETTINGS = merge_dicts(MAXON_DC_22_S_12V_DEFAULT_SETTINGS, {
    'Motor rated torque': 0.0118,
    'Position control parameter set/Position controller P gain': 1.5,
    'Position control parameter set/Position controller I gain': 0.78,
    'Position control parameter set/Position controller D gain': 0.016,
    'Current control parameter set/Current controller P gain': 19,
    'Current control parameter set/Current controller I gain': 152,
})



MAXON_EC_45_DEFAULT_SETTINGS = {
    'Store parameters': 0,
    'Motor type': MaxonMotorType.SINUSOIDAL_PM_BL_MOTOR,
    'Motor data/Number of pole pairs': 8,
    'Digital incremental encoder 1/Digital incremental encoder 1 number of pulses': 2048,
    'Digital incremental encoder 1/Digital incremental encoder 1 type': 0,
    'Interpolation time period/Interpolation time period value': INTERVAL / MILLI,
    'Digital input properties/Digital inputs polarity': MAXON_INPUT_LOW_ACTIVE,
}


MAXON_DC_22_DEFAULT_SETTINGS = {
    'Store parameters': 0,
    'Motor type': MaxonMotorType.PHASE_MODULATED_DC_MOTOR,
    'Axis configuration/Sensors configuration': MaxonSensorsConfiguration(sensorType3=0, sensorType2=0, sensorType1=1).to_int(),
    'Axis configuration/Control structure': MaxonControlStructure(gear=1).to_int(),
    'Axis configuration/Commutation sensors': 0,
    'Axis configuration/Axis configuration miscellaneous': 0x0 | MAXON_POLARITY_CCW,
    'Digital incremental encoder 1/Digital incremental encoder 1 number of pulses': 1024,
    'Digital incremental encoder 1/Digital incremental encoder 1 type': 1,
    'Interpolation time period/Interpolation time period value': INTERVAL / MILLI,
    #'Interpolation time period/Interpolation time index': -3,
    #'Following error window': MAXON_FOLLOWING_ERROR_WINDOW_DISABLED,
    #'Following error window': 0,
    'Digital input properties/Digital inputs polarity': MAXON_INPUT_LOW_ACTIVE,

    #'Gear configuration/Gear reduction numerator': 69,
    #'Gear configuration/Gear reduction denominator': 13,
    'Gear configuration/Gear reduction numerator': 1,
    'Gear configuration/Gear reduction denominator': 1,

    #'Profile acceleration': 1,  # Default 10000
    #'Profile deceleration': 1,  # Default 10000
    #'Quick stop deceleration': 2,  # Default 10000
    #'Max motor speed': 50,  # Default 50000
    #'Gear configuration/Max gear input speed': 100   , # Default 100000

    'Position control parameter set/Position controller P gain': 1.5 / MICRO,
    'Position control parameter set/Position controller I gain': 0.78 / MICRO,
    'Position control parameter set/Position controller D gain': .1*0.016 / MICRO,
    'Current control parameter set/Current controller P gain': 19 / MICRO,
    'Current control parameter set/Current controller I gain': 152 / MICRO,
}


MOTORS = {
    'LM1247': Motor('Faulhaber', 'LM 1247', length=0.120, defaultSettings=FAULHABER_DEFAULT_SETTINGS, position_si_2_device=1 / MICRO),
    'LM0830': Motor('Faulhaber', 'LM 0830', length=0.040, defaultSettings=FAULHABER_DEFAULT_SETTINGS, position_si_2_device=1 / MICRO),
    'LM1483': Motor('Faulhaber', 'LM 1483', length=0.080, defaultSettings=FAULHABER_DEFAULT_SETTINGS, position_si_2_device=1 / MICRO),
    'LM2070': Motor('Faulhaber', 'LM 2070', length=0.220, defaultSettings=FAULHABER_DEFAULT_SETTINGS, position_si_2_device=1 / MICRO),
    'EC45': Motor('Maxon', 'EC 45', length=TAU, defaultSettings=MAXON_EC_45_DEFAULT_SETTINGS, position_si_2_device=4 * 2048 / TAU),
    'DC22': Motor('Maxon', 'DC 22', length=TAU, defaultSettings=MAXON_DC_22_DEFAULT_SETTINGS, position_si_2_device=4 * 1024 / TAU, gear=Fraction(69, 13)),
}


def get_motor(name) -> Motor:
    """Lookup motor by name.

    Args:
        name: Motor name. Can be lowercase and spaces get deleted for easy
            lookup.

    Returns:
        Motor
    """
    key = name.replace(' ', '').upper()
    if key not in MOTORS:
        raise KeyError(f'Unknown motor {name}!')

    return MOTORS[key]
