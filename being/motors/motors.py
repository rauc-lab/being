"""Motor definitions for the actual hardware motor types. Different motor
parameters / settings.
"""
from typing import NamedTuple
from fractions import Fraction

from being.constants import TAU, INF, MICRO, MILLI
from being.config import CONFIG
from being.motors.vendor import (
    MAXON_FOLLOWING_ERROR_WINDOW_DISABLED,
    MAXON_INPUT_LOW_ACTIVE,
    MaxonControlStructure,
    MaxonMotorType,
    MaxonSensorsConfiguration,
)


INTERVAL = CONFIG['General']['INTERVAL']


class Motor(NamedTuple):

    """Hardware motor.

    Definitions, settings for different hardware motors.
    """

    manufacturer: str
    """Manufacturer name."""

    name: str
    """Motor name."""

    position_si_2_device: float = 1.0
    """Conversion factor for position SI -> device units. Motor only. Not with
    gear.
    """

    defaultSettings: dict = {}
    """Default settings for this motor."""

    length: float = INF
    """Linear motor Length."""

    gear: Fraction = Fraction(1, 1)
    """Gear ratio."""

    def __str__(self):
        return f'{self.manufacturer} {self.name}'


FAULHABER_DEFAULT_SETTINGS = {
    'General Settings/Pure Sinus Commutation': 1,
    'Filter Settings/Sampling Rate': 4,
    'Filter Settings/Gain Scheduling Velocity Controller': 1,
    #'Velocity Control Parameter Set/Proportional Term POR': 44,
    #'Velocity Control Parameter Set/Integral Term I': 50,
    'Position Control Parameter Set/Proportional Term PP': 15,  # or 8 (softer)
    'Position Control Parameter Set/Derivative Term PD': 10,  # or 14 (softer)
    'Current Control Parameter Set/Continuous Current Limit': 500,  # mA
    'Current Control Parameter Set/Peak Current Limit': 1640,  # mA
    'Current Control Parameter Set/Integral Term CI': 3,
    'Max Profile Velocity': 1000,  # milli
    'Profile Acceleration': 1000,  # milli
    'Profile Deceleration': 1000,  # milli
}


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
    'Axis configuration/Commutation sensors': 0,
    'Axis configuration/Control structure': MaxonControlStructure(gear=1).to_int(),
    'Axis configuration/Sensors configuration': MaxonSensorsConfiguration(sensorType3=0, sensorType2=0, sensorType1=1).to_int(),
    'Digital incremental encoder 1/Digital incremental encoder 1 number of pulses': 1024,
    'Digital incremental encoder 1/Digital incremental encoder 1 type': 1,
    'Digital input properties/Digital inputs polarity': MAXON_INPUT_LOW_ACTIVE,
    'Disable operation option code': 0,  # Otherwise we loose to much time when disabling drive (timeout)
    'Following error window': MAXON_FOLLOWING_ERROR_WINDOW_DISABLED,
    'Gear configuration/Gear reduction denominator': 13,
    'Gear configuration/Gear reduction numerator': 69,
    'Gear configuration/Max gear input speed': 8000,  # RPM
    'Interpolation time period/Interpolation time period value': INTERVAL / MILLI,
    'Max motor speed': 9000,  # RPM
    'Motor data/Nominal current': 379,  # mA
    'Motor data/Output current limit': 2 * 379,  # mA
    'Motor data/Thermal time constant winding': 143,
    'Motor data/Torque constant': 30800,
    'Motor rated torque': 12228,
    'Motor type': MaxonMotorType.PHASE_MODULATED_DC_MOTOR,
    'Store parameters': 0,
}


MOTORS = {
    'LM1247': Motor(
        'Faulhaber',
        'LM 1247',
        position_si_2_device=1 / MICRO,
        defaultSettings=FAULHABER_DEFAULT_SETTINGS,
        length=0.100,
    ),
    'LM0830': Motor(
        'Faulhaber',
        'LM 0830',
        position_si_2_device=1 / MICRO,
        defaultSettings=FAULHABER_DEFAULT_SETTINGS,
        length=0.040,
    ),
    'LM1483': Motor(
        'Faulhaber',
        'LM 1483',
        position_si_2_device=1 / MICRO,
        defaultSettings=FAULHABER_DEFAULT_SETTINGS,
        length=0.080,
    ),
    'LM2070': Motor(
        'Faulhaber',
        'LM 2070',
        position_si_2_device=1 / MICRO,
        defaultSettings=FAULHABER_DEFAULT_SETTINGS,
        length=0.220,
    ),
    'EC45': Motor(
        'Maxon',
        'EC 45',
        position_si_2_device=4 * 2048 / TAU,
        defaultSettings=MAXON_EC_45_DEFAULT_SETTINGS,
    ),
    'DC22': Motor(
        'Maxon',
        'DC 22',
        position_si_2_device=4 * 1024 / TAU,
        defaultSettings=MAXON_DC_22_DEFAULT_SETTINGS,
        gear=Fraction(69, 13),
    ),
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
