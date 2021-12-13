"""Effective hardware motors. Represents the effective motor itself. Different
default settings.
"""
import collections
from typing import NamedTuple, Sequence
from fractions import Fraction

from being.constants import TAU, INF, MICRO, MILLI
from being.configuration import CONFIG
from being.motors.vendor import (
    MAXON_FOLLOWING_ERROR_WINDOW_DISABLED,
    MAXON_INPUT_LOW_ACTIVE,
    MaxonControlStructure,
    MaxonMotorType,
    MaxonSensorsConfiguration,
)


INTERVAL = CONFIG['General']['INTERVAL']


class DeviceUnits(NamedTuple):

    """Motor device units factor. Gear factor not included.

    Todo:
        Should this move to to :class:`being.motors.controllers.Controller`? Is
        it motor or controller dependent?
    """

    position: float = 1.0
    """Position factor."""

    velocity: float = 1.0
    """Velocity factor."""

    acceleration: float = 1.0
    """Acceleration factor."""


class Motor(NamedTuple):

    """Hardware motor.

    Definitions, settings for different hardware motors.
    """

    manufacturer: str
    """Manufacturer name."""

    name: str
    """Motor name."""

    length: float = INF
    """Default motor length."""

    units: DeviceUnits = DeviceUnits()
    """Device units."""

    gear: Fraction = Fraction(1, 1)
    """Gear ratio."""

    defaultSettings: dict = {}
    """Default settings for this motor."""

    def si_2_device_units(self, which: str) -> float:
        """Determines the conversion factor from SI units to unit units. The
        gear ratio is also taken into account.

        Args:
            which: Which factor? Either 'position', 'velocity' or 'acceleration'.

        Returns:
            Conversion factor.
        """
        return self.gear / getattr(self.units, which)

    def __str__(self):
        return f'{self.manufacturer} {self.name}'


FAULHABER_DEFAULT_SETTINGS = collections.OrderedDict([
    ('General Settings/Pure Sinus Commutation', 1),
    ('Filter Settings/Sampling Rate', 4),
    ('Filter Settings/Gain Scheduling Velocity Controller', 1),
    # ('Velocity Control Parameter Set/Proportional Term POR', 44),
    # ('Velocity Control Parameter Set/Integral Term I', 50),
    ('Position Control Parameter Set/Proportional Term PP', 15),  # or 8 (softer)
    ('Position Control Parameter Set/Derivative Term PD', 10),  # or 14 (softer)
    ('Current Control Parameter Set/Continuous Current Limit', 500),  # mA
    ('Current Control Parameter Set/Peak Current Limit', 1640),  # mA
    ('Current Control Parameter Set/Integral Term CI', 3),
    ('Max Profile Velocity', 1000),  # milli
    ('Profile Acceleration', 1000),  # milli
    ('Profile Deceleration', 1000),  # milli
    ('Software Position Limit/Minimum Position Limit', -1e7),
    ('Software Position Limit/Maximum Position Limit', 1e7),
])


MAXON_EC_45_DEFAULT_SETTINGS = collections.OrderedDict([
    ('Motor type', MaxonMotorType.SINUSOIDAL_PM_BL_MOTOR),
    ('Motor data/Number of pole pairs', 8),
    ('Axis configuration/Sensors configuration', MaxonSensorsConfiguration().to_int()),
    ('Axis configuration/Control structure', MaxonControlStructure().to_int()),
    ('Axis configuration/Commutation sensors', 0x31),
    ('Store parameters', 0),
    ('Digital incremental encoder 1/Digital incremental encoder 1 number of pulses', 2048),
    ('Digital incremental encoder 1/Digital incremental encoder 1 type', 0),
    ('Interpolation time period/Interpolation time period value', INTERVAL / MILLI),
    ('Digital input properties/Digital inputs polarity', MAXON_INPUT_LOW_ACTIVE),
    ('Following error window', MAXON_FOLLOWING_ERROR_WINDOW_DISABLED),
    ('Motor data/Nominal current', 3210),  # mA
    ('Motor data/Output current limit', 2 * 3210),  # mA
    ('Motor data/Thermal time constant winding', 29.6),
    ('Motor data/Torque constant', 36900),
    ('Motor rated torque', 128000),
])


MAXON_DC_22_DEFAULT_SETTINGS = collections.OrderedDict([
    ('Axis configuration/Commutation sensors', 0),
    ('Axis configuration/Control structure', MaxonControlStructure(gear=1).to_int()),
    ('Axis configuration/Sensors configuration', MaxonSensorsConfiguration(sensorType3=0, sensorType2=0, sensorType1=1).to_int()),
    ('Digital incremental encoder 1/Digital incremental encoder 1 number of pulses', 1024),
    ('Digital incremental encoder 1/Digital incremental encoder 1 type', 1),
    ('Digital input properties/Digital inputs polarity', MAXON_INPUT_LOW_ACTIVE),
    ('Disable operation option code', 0),  # Otherwise we loose to much time when disabling drive (timeout)
    ('Following error window', MAXON_FOLLOWING_ERROR_WINDOW_DISABLED),
    ('Gear configuration/Gear reduction denominator', 13),
    ('Gear configuration/Gear reduction numerator', 69),
    ('Gear configuration/Max gear input speed', 8000),  # RPM
    ('Interpolation time period/Interpolation time period value', INTERVAL / MILLI),
    ('Max motor speed', 9000),  # RPM
    ('Motor data/Nominal current', 379),  # mA
    ('Motor data/Output current limit', 2 * 379),  # mA
    ('Motor data/Thermal time constant winding', 143),
    ('Motor data/Torque constant', 30800),
    ('Motor rated torque', 12228),
    ('Motor type', MaxonMotorType.PHASE_MODULATED_DC_MOTOR),
    ('Store parameters', 0),
])


MOTORS = {
    'LM1247': Motor(
        'Faulhaber',
        'LM 1247',
        length=0.100,
        units=DeviceUnits(position=MICRO, velocity=MILLI, acceleration=MILLI),
        defaultSettings=FAULHABER_DEFAULT_SETTINGS,
    ),
    'LM0830': Motor(
        'Faulhaber',
        'LM 0830',
        length=0.040,
        units=DeviceUnits(position=MICRO, velocity=MILLI, acceleration=MILLI),
        defaultSettings=FAULHABER_DEFAULT_SETTINGS,
    ),
    'LM1483': Motor(
        'Faulhaber',
        'LM 1483',
        length=0.080,
        units=DeviceUnits(position=MICRO, velocity=MILLI, acceleration=MILLI),
        defaultSettings=FAULHABER_DEFAULT_SETTINGS,
    ),
    'LM2070': Motor(
        'Faulhaber',
        'LM 2070',
        length=0.220,
        units=DeviceUnits(position=MICRO, velocity=MILLI, acceleration=MILLI),
        defaultSettings=FAULHABER_DEFAULT_SETTINGS,
    ),
    'EC45': Motor(
        'Maxon',
        'EC 45',
        units=DeviceUnits(position=TAU / 4 / 2048),  # Todo: velocity and acceleration?
        defaultSettings=MAXON_EC_45_DEFAULT_SETTINGS,
    ),
    'DC22': Motor(
        'Maxon',
        'DC 22',
        units=DeviceUnits(position=TAU / 4 / 1024),  # Todo: velocity and acceleration?
        gear=Fraction(69, 13),
        defaultSettings=MAXON_DC_22_DEFAULT_SETTINGS,
    ),
}


def orify(things: Sequence) -> str:
    """Comma separate sequence with final 'or'.

    Example:
        >>> orify(['a', 'b', 'c'])
        'a, b or c'
    """
    *pre, last = things
    if len(pre) == 0:
        return str(last)

    return f'{", ".join(pre)} or {last}'


def get_motor(name: str) -> Motor:
    """Lookup motor by name.

    Args:
        name: Motor name. Can be lowercase and spaces get deleted for easy lookup.

    Returns:
        Motor informations.

    Raises:
        KeyError: If motor could not be found.

    Example:
        >>> motor = get_motor('LM 1247')
        ... motor.name
        'LM 1247'

        >>> get_motor('R2D2')
        KeyError: 'Unknown motor R2D2! Try one of LM1247, LM0830, LM1483, LM2070, EC45 or DC22'
    """
    key = name.replace(' ', '').upper()
    if key not in MOTORS:
        raise KeyError(f'Unknown motor {name}! Try one of {orify(MOTORS)}')

    return MOTORS[key]
