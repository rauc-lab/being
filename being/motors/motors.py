"""Motor definitions for the actual hardware motor types. Different motor
parameters / settings.
"""
from typing import NamedTuple


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
MAXON_PHASE_MODULATED_DC_MOTOR = 1
MAXON_SINUSOIDAL_PM_BL_MOTOR = 10
MAXON_TRAPEZOIDAL_PM_BL_MOTOR = 11
TODO = 0
MAXON_DC_22_S_DEFAULT_SETTINGS = {
    'Motor type': MAXON_PHASE_MODULATED_DC_MOTOR,
    'Motor data/Nominal current': 0.379,  # [Ampere]
    'Motor data/Output current limit': 2 * 0.379,  # [Ampere]
    'Motor data/Number of pole pairs': 1,
    'Motor data/Thermal time constant winding': 14.3,
    'Motor data/Torque constant': 0.0308,
    # TODO: Gear
    'Axis configuration/Sensors configuration': 1,
    'Axis configuration/Control structure': TODO,
    'Axis configuration/Commutation sensors': 0,
    'Axis configuration/Axis configuration miscellaneous': TODO,
}
MAXON_EC_45_DEFAULT_SETTINGS = {
    'Motor type': MAXON_SINUSOIDAL_PM_BL_MOTOR,
    'Motor data/Nominal current': 3.210,  # [Ampere]
    'Motor data/Output current limit': 2 * 3.210,  # [Ampere]
    'Motor data/Number of pole pairs': 8,
    'Motor data/Thermal time constant winding': 29.6,
    'Motor data/Torque constant': 0.0369,
    # TODO: Gear
    'Axis configuration/Sensors configuration': 0x100001,
    'Axis configuration/Control structure': TODO,
    'Axis configuration/Commutation sensors': 0x31,
    'Axis configuration/Axis configuration miscellaneous': TODO,
}


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

    brushed: bool = False  # To deprecate?
    """If is brushed motor."""

    defaultSettings: dict = {}
    """Default settings for this motor."""


MOTORS = {
    'LM0830': Motor('Faulhaber', 'LM 0830', length=0.040, defaultSettings=FAULHABER_DEFAULT_SETTINGS),
    'LM1247': Motor('Faulhaber', 'LM 1247', length=0.120, defaultSettings=FAULHABER_DEFAULT_SETTINGS),
    'LM1483': Motor('Faulhaber', 'LM 1483', length=0.080, defaultSettings=FAULHABER_DEFAULT_SETTINGS),
    'LM2070': Motor('Faulhaber', 'LM 2070', length=0.220, defaultSettings=FAULHABER_DEFAULT_SETTINGS),
    'DC22': Motor('Maxon', 'DC 22', brushed=True, defaultSettings=MAXON_DC_22_S_DEFAULT_SETTINGS),
    'EC45': Motor('Maxon', 'EC 45', defaultSettings=MAXON_EC_45_DEFAULT_SETTINGS),
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
