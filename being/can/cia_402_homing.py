"""CiA 402 homing methods."""
from typing import NamedTuple, Dict

from being.constants import FORWARD, BACKWARD


POSITIVE = RISING = FORWARD
NEGATIVE = FALLING = BACKWARD
UNAVAILABLE = UNDEFINED = 0.0


class HomingParam(NamedTuple):

    """Homing parameters to describe different CiA402 homing methods."""

    endSwitch: int = UNAVAILABLE
    homeSwitch: int = UNAVAILABLE
    homeSwitchEdge: int = UNDEFINED
    indexPulse: bool = False

    direction: int = UNDEFINED
    hardStop: bool = False


HOMING_METHODS: Dict[HomingParam, int] = {
    HomingParam(indexPulse=True, direction=POSITIVE, hardStop=True, ): -1,
    HomingParam(indexPulse=True, direction=NEGATIVE, hardStop=True, ): -2,
    HomingParam(direction=POSITIVE, hardStop=True, ): -3,
    HomingParam(direction=NEGATIVE, hardStop=True, ): -4,
    HomingParam(indexPulse=True, endSwitch=NEGATIVE, ): 1,
    HomingParam(indexPulse=True, endSwitch=POSITIVE, ): 2,
    HomingParam(indexPulse=True, homeSwitch=POSITIVE, homeSwitchEdge=FALLING, ): 3,
    HomingParam(indexPulse=True, homeSwitch=POSITIVE, homeSwitchEdge=RISING, ): 4,
    HomingParam(indexPulse=True, homeSwitch=NEGATIVE, homeSwitchEdge=FALLING, ): 5,
    HomingParam(indexPulse=True, homeSwitch=NEGATIVE, homeSwitchEdge=RISING, ): 6,
    HomingParam(indexPulse=True, homeSwitch=NEGATIVE, homeSwitchEdge=FALLING, endSwitch=POSITIVE, ): 7,
    HomingParam(indexPulse=True, homeSwitch=NEGATIVE, homeSwitchEdge=RISING, endSwitch=POSITIVE, ): 8,
    HomingParam(indexPulse=True, homeSwitch=POSITIVE, homeSwitchEdge=RISING, endSwitch=POSITIVE, ): 9,
    HomingParam(indexPulse=True, homeSwitch=POSITIVE, homeSwitchEdge=FALLING, endSwitch=POSITIVE, ): 10,
    HomingParam(indexPulse=True, homeSwitch=POSITIVE, homeSwitchEdge=FALLING, endSwitch=NEGATIVE, ): 11,
    HomingParam(indexPulse=True, homeSwitch=POSITIVE, homeSwitchEdge=RISING, endSwitch=NEGATIVE, ): 12,
    HomingParam(indexPulse=True, homeSwitch=NEGATIVE, homeSwitchEdge=RISING, endSwitch=NEGATIVE, ): 13,
    HomingParam(indexPulse=True, homeSwitch=NEGATIVE, homeSwitchEdge=FALLING, endSwitch=NEGATIVE, ): 14,
    HomingParam(endSwitch=NEGATIVE, ): 17,
    HomingParam(endSwitch=POSITIVE, ): 18,
    HomingParam(homeSwitch=POSITIVE, homeSwitchEdge=FALLING, ): 19,
    HomingParam(homeSwitch=POSITIVE, homeSwitchEdge=RISING, ): 20,
    HomingParam(homeSwitch=NEGATIVE, homeSwitchEdge=FALLING, ): 21,
    HomingParam(homeSwitch=NEGATIVE, homeSwitchEdge=RISING, ): 22,
    HomingParam(homeSwitch=NEGATIVE, homeSwitchEdge=FALLING, endSwitch=POSITIVE, ): 23,
    HomingParam(homeSwitch=NEGATIVE, homeSwitchEdge=RISING, endSwitch=POSITIVE, ): 24,
    HomingParam(homeSwitch=POSITIVE, homeSwitchEdge=RISING, endSwitch=POSITIVE, ): 25,
    HomingParam(homeSwitch=POSITIVE, homeSwitchEdge=FALLING, endSwitch=POSITIVE, ): 26,
    HomingParam(homeSwitch=POSITIVE, homeSwitchEdge=FALLING, endSwitch=NEGATIVE, ): 27,
    HomingParam(homeSwitch=POSITIVE, homeSwitchEdge=RISING, endSwitch=NEGATIVE, ): 28,
    HomingParam(homeSwitch=NEGATIVE, homeSwitchEdge=RISING, endSwitch=NEGATIVE, ): 29,
    HomingParam(homeSwitch=NEGATIVE, homeSwitchEdge=FALLING, endSwitch=NEGATIVE, ): 30,
    HomingParam(indexPulse=True, direction=NEGATIVE,): 33,
    HomingParam(indexPulse=True, direction=POSITIVE,): 34,
    HomingParam(): 35,  # TODO(atheler): Got replaced with 37 in newer versions
}
"""CiA 402 homing method lookup."""

assert len(HOMING_METHODS) == 35, 'Something went wrong with HOMING_METHODS keys! Not enough homing methods anymore.'


def determine_homing_method(
        endSwitch: int = UNAVAILABLE,
        homeSwitch: int = UNAVAILABLE,
        homeSwitchEdge: int = UNDEFINED,
        indexPulse: bool = False,
        direction: int = UNDEFINED,
        hardStop: bool = False,
    ) -> int:
    """Determine homing method."""
    param = HomingParam(endSwitch, homeSwitch, homeSwitchEdge, indexPulse, direction, hardStop)
    return HOMING_METHODS[param]


assert determine_homing_method(hardStop=True, direction=FORWARD) == -3
assert determine_homing_method(hardStop=True, direction=BACKWARD) == -4
