import enum
import collections
from typing import (
    Dict,
    Iterator,
    List,
    Set,
    Tuple,
    Union,
    NamedTuple
)

from being.bitmagic import check_bit
from being.constants import FORWARD, BACKWARD

# Mandatory (?) CiA 402 object dictionary entries
# (SJA): CiA 402 is still a Draft Specification Proposal (DSP).
CONTROLWORD: int = 0x6040
"""Controlword. :hex:"""

STATUSWORD: int = 0x6041
"""Statusword. :hex:"""

MODES_OF_OPERATION: int = 0x6060
"""Selecting the active drive profile. :hex:"""

MODES_OF_OPERATION_DISPLAY: int = 0x6061
"""Get supported modes of operations for drive. :hex:"""

POSITION_DEMAND_VALUE: int = 0x6062
"""Target position in user units. :hex:"""

POSITION_ACTUAL_VALUE: int = 0x6064
"""Actual position in internal units. :hex:"""

POSITION_WINDOW: int = 0x6067
"""Target corridor around set-point value for target reached. :hex:"""

POSITION_WINDOW_TIME: int = 0x6068
"""Time needed in target corridor for target reached. :hex:"""

VELOCITY_DEMAND_VALUE: int = 0x606B
"""Target velocity in user units. :hex:"""

VELOCITY_ACTUAL_VALUE: int = 0x606C
"""Actual velocity in internal units. :hex:"""

TARGET_POSITION: int = 0x607A
"""Target position in internal units. :hex:"""

POSITION_RANGE_LIMIT: int = 0x607B
"""Min / max position range limit. :hex:"""

SOFTWARE_POSITION_LIMIT: int = 0x607D
"""Min / max software position range limit. :hex:"""

MIN_POSITION_LIMIT: int = 1
"""Subindex for lower position range limit."""

MAX_POSITION_LIMIT: int = 2
"""Subindex for upper position range limit."""

MAX_PROFILE_VELOCITY: int = 0x607F
"""Maximum velocity. Units vendor dependent. :hex:"""

PROFILE_VELOCITY: int = 0x6081
"""Maximum velocity. Units vendor dependent. :hex:"""

PROFILE_ACCELERATION: int = 0x6083
"""Maximum acceleration. :hex:"""

PROFILE_DECELERATION: int = 0x6084
"""Maximum deceleration. :hex:"""

QUICK_STOP_DECELERATION: int = 0x6085
"""Quick stop deceleration. :hex:"""

HOMING_METHOD: int = 0x6098
"""Homing method number. :hex:"""

HOMING_SPEEDS: int = 0x6099
"""Speed values of homing. :hex:"""

SPEED_FOR_SWITCH_SEARCH: int = 1
"""Homing speed for switch searching."""

SPEED_FOR_ZERO_SEARCH: int = 2
"""Homing speed for zero search."""

HOMING_ACCELERATION: int = 0x609A
"""Acceleration during homing. :hex:"""

DIGITAL_INPUTS: int = 0x60FD
"""Read state of digital inputs (read-only). :hex:"""

TARGET_VELOCITY: int = 0x60FF
"""Target velocity. :hex:"""

SUPPORTED_DRIVE_MODES: int = 0x6502
"""Supported operating modes for drive. :hex:"""


CanOpenRegister = Union[int, str]


class State(enum.Enum):

    """CANopen CiA 402 states."""

    START = enum.auto()
    NOT_READY_TO_SWITCH_ON = enum.auto()
    SWITCH_ON_DISABLED = enum.auto()
    READY_TO_SWITCH_ON = enum.auto()
    SWITCHED_ON = enum.auto()
    OPERATION_ENABLED = enum.auto()
    QUICK_STOP_ACTIVE = enum.auto()
    FAULT_REACTION_ACTIVE = enum.auto()
    FAULT = enum.auto()
    HALT = enum.auto()


StateSwitching = Iterator[State]
Edge = Tuple[State, State]


class CW(enum.IntEnum):

    """Controlword bits."""

    SWITCH_ON = (1 << 0)
    """:bin:"""
    ENABLE_VOLTAGE = (1 << 1)
    """:bin:"""
    QUICK_STOP = (1 << 2)
    """:bin:"""
    ENABLE_OPERATION = (1 << 3)
    """:bin:"""
    NEW_SET_POINT = (1 << 4)
    """:bin:"""
    START_HOMING_OPERATION = NEW_SET_POINT  # Alias
    """:bin:"""
    ENABLE_IP_MODE = NEW_SET_POINT  # Alias
    """:bin:"""
    CHANGE_SET_IMMEDIATELY = (1 << 5)
    """:bin:"""
    ABS_REL = (1 << 6)
    """:bin:"""
    FAULT_RESET = (1 << 7)
    """:bin:"""
    HALT = (1 << 8)
    """:bin:"""


class Command(enum.IntEnum):

    """CANopen CiA 402 controlword commands for state transitions."""

    SHUT_DOWN = CW.QUICK_STOP | CW.ENABLE_VOLTAGE
    """:bin:"""
    SWITCH_ON = CW.QUICK_STOP | CW.ENABLE_VOLTAGE | CW.SWITCH_ON
    """:bin:"""
    DISABLE_VOLTAGE = 0
    """:bin:"""
    QUICK_STOP = CW.ENABLE_VOLTAGE
    """:bin:"""
    DISABLE_OPERATION = CW.QUICK_STOP | CW.ENABLE_VOLTAGE | CW.SWITCH_ON
    """:bin:"""
    ENABLE_OPERATION = CW.ENABLE_OPERATION | CW.QUICK_STOP | CW.ENABLE_VOLTAGE | CW.SWITCH_ON
    """:bin:"""
    FAULT_RESET = CW.FAULT_RESET
    """:bin:"""


class SW(enum.IntEnum):

    """Statusword bits."""

    READY_TO_SWITCH_ON = (1 << 0)
    """:bin:"""
    SWITCHED_ON = (1 << 1)
    """:bin:"""
    OPERATION_ENABLED = (1 << 2)
    """:bin:"""
    FAULT = (1 << 3)
    """:bin:"""
    VOLTAGE_ENABLED = (1 << 4)
    """:bin:"""
    QUICK_STOP = (1 << 5)
    """:bin:"""
    SWITCH_ON_DISABLED = (1 << 6)
    """:bin:"""
    WARNING = (1 << 7)
    """:bin:"""
    #alwayszero = (1 << 8)
    REMOTE = (1 << 9)
    """:bin:"""
    TARGET_REACHED = (1 << 10)
    """:bin:"""
    INTERNAL_LIMIT_ACTIVE = (1 << 11)
    """:bin:"""
    ACKNOWLEDGE = (1 << 12)
    """:bin:"""
    HOMING_ATTAINED = ACKNOWLEDGE  # Alias
    """:bin:"""
    HOMING_ERROR = (1 << 13)
    """:bin:"""
    DEVIATION_ERROR = HOMING_ERROR  # Alias
    """:bin:"""
    #NOT_IN_USE_0 = (1 << 14)
    #NOT_IN_USE_1 = (1 << 15)


class OperationMode(enum.IntEnum):

    """Modes of Operation (0x6060 / 0x6061)."""

    NO_MODE = 0
    PROFILE_POSITION = 1
    VELOCITY = 2
    PROFILE_VELOCITY = 3
    PROFILE_TORQUE = 4
    HOMING = 6
    INTERPOLATED_POSITION = 7
    CYCLIC_SYNCHRONOUS_POSITION = 8
    CYCLIC_SYNCHRONOUS_VELOCITY = 9
    CYCLIC_SYNCHRONOUS_TORQUE = 10
    OPEN_LOOP_SCALAR_MODE = -1
    OPEN_LOOP_VECTOR_MODE = -2


TRANSITION_COMMANDS: Dict[Edge, Command] = {
    # Shut down: 2, 6, 8
    (State.SWITCH_ON_DISABLED, State.READY_TO_SWITCH_ON):     Command.SHUT_DOWN,
    (State.SWITCHED_ON, State.READY_TO_SWITCH_ON):            Command.SHUT_DOWN,
    (State.OPERATION_ENABLED, State.READY_TO_SWITCH_ON):      Command.SHUT_DOWN,
    # Switch On: 3
    (State.READY_TO_SWITCH_ON, State.SWITCHED_ON):            Command.SWITCH_ON,
    # Disable Voltage: 7, 9, 10, 12
    (State.READY_TO_SWITCH_ON, State.SWITCH_ON_DISABLED):     Command.DISABLE_VOLTAGE,
    (State.OPERATION_ENABLED, State.SWITCH_ON_DISABLED):      Command.DISABLE_VOLTAGE,
    (State.SWITCHED_ON, State.SWITCH_ON_DISABLED):            Command.DISABLE_VOLTAGE,
    (State.QUICK_STOP_ACTIVE, State.SWITCH_ON_DISABLED):      Command.DISABLE_VOLTAGE,
    # Quick Stop: 7, 10, 11
    (State.READY_TO_SWITCH_ON, State.SWITCH_ON_DISABLED):     Command.QUICK_STOP,
    (State.SWITCHED_ON, State.SWITCH_ON_DISABLED):            Command.QUICK_STOP,
    (State.OPERATION_ENABLED, State.QUICK_STOP_ACTIVE):       Command.QUICK_STOP,
    # Disable Operation: 5
    (State.OPERATION_ENABLED, State.SWITCHED_ON):             Command.DISABLE_OPERATION,
    # Enable Operation: 4, 16
    (State.SWITCHED_ON, State.OPERATION_ENABLED):             Command.ENABLE_OPERATION,
    (State.QUICK_STOP_ACTIVE, State.OPERATION_ENABLED):       Command.ENABLE_OPERATION,
    # Fault Reset: 15
    (State.FAULT, State.SWITCH_ON_DISABLED):                  Command.FAULT_RESET,
    # Automatic: 0, 1, 14
    (State.START, State.NOT_READY_TO_SWITCH_ON):              Command.DISABLE_VOLTAGE,  # 0x0
    (State.NOT_READY_TO_SWITCH_ON, State.SWITCH_ON_DISABLED): Command.DISABLE_VOLTAGE,  # 0x0
    (State.FAULT_REACTION_ACTIVE, State.FAULT):               Command.DISABLE_VOLTAGE,  # 0x0
}
"""Possible state transitions edges and the corresponding controlword
command.

:meta hide-value:
"""

POSSIBLE_TRANSITIONS: Dict[State, Set[State]] = collections.defaultdict(set)
"""Reachable states from a given start state."""

for _edge in TRANSITION_COMMANDS:
    _src, _dst = _edge
    POSSIBLE_TRANSITIONS[_src].add(_dst)


VALID_OP_MODE_CHANGE_STATES: Set[State] = {
    State.SWITCH_ON_DISABLED,
    State.READY_TO_SWITCH_ON,
    State.SWITCHED_ON,
}
"""Not every state support switching of operation mode."""

STATUSWORD_2_STATE: List[Tuple[int, int, State]] = [
    (0b1001111, 0b0000000, State.NOT_READY_TO_SWITCH_ON),
    (0b1001111, 0b1000000, State.SWITCH_ON_DISABLED),
    (0b1101111, 0b0100001, State.READY_TO_SWITCH_ON),
    (0b1101111, 0b0100011, State.SWITCHED_ON),
    (0b1101111, 0b0100111, State.OPERATION_ENABLED),
    (0b1101111, 0b0000111, State.QUICK_STOP_ACTIVE),
    (0b1001111, 0b0001111, State.FAULT_REACTION_ACTIVE),
    (0b1001111, 0b0001000, State.FAULT),
]
"""Statusword bit masks for state lookup.

:meta hide-value:
"""

def which_state(statusword: int) -> State:
    """Extract state from statusword number.

    Args:
        statusword: Statusword number.

    Returns:
        Current state.

    Raises:
        ValueError: If no valid state was found.
    """
    for mask, value, state in STATUSWORD_2_STATE:
        if (statusword & mask) == value:
            return state

    raise ValueError('Unknown state for statusword {statusword}!')


def supported_operation_modes(supportedDriveModes: int) -> Iterator[OperationMode]:
    """Which operation modes are supported? Extract information from value of
    SUPPORTED_DRIVE_MODES (0x6502).

    Args:
        supportedDriveModes: Received value from 0x6502.

    Yields:
        Supported drive operation modes for the node.
    """
    # Look-up is identical between Faulhaber / Maxon

    stuff = [
        (0, OperationMode.PROFILE_POSITION),
        (2, OperationMode.PROFILE_VELOCITY),
        (5, OperationMode.HOMING),
        (7, OperationMode.CYCLIC_SYNCHRONOUS_POSITION),
        (8, OperationMode.CYCLIC_SYNCHRONOUS_VELOCITY),
        (9, OperationMode.CYCLIC_SYNCHRONOUS_TORQUE),
    ]
    for bit, op in stuff:
        if check_bit(supportedDriveModes, bit):
            yield op


# There are 31 official and a couple unofficial CiA 402 homing methods. All have
# assigned some number. It is hard to keep track of the different effect and
# parameters. :class:`HomingParam` is an intermediate representation with some
# more human understandable representation. This can that get mapped to the
# integer homing method number.
# The function :func:`determine_homing_method` can than be used to determine the
# wanted homing method.
POSITIVE: float = FORWARD
"""Positive homing direction."""

RISING: float = FORWARD
"""Rising home switch edge."""

NEGATIVE: float = BACKWARD
"""Negative direction."""

FALLING: float = BACKWARD
"""Falling home switch edge."""

UNAVAILABLE: float = 0.0
"""Unavailable indicator."""

UNDEFINED: float = 0.0
"""Undefined indicator."""


class HomingParam(NamedTuple):

    """Intermediate homing parameters representation to describe the different
    CiA 402 homing methods.
    """

    endSwitch: float = UNAVAILABLE
    """Do we have an end switch? If so at which end?"""

    homeSwitch: float = UNAVAILABLE
    """Do we have a home switch? If so at which end?"""

    homeSwitchEdge: float = UNDEFINED
    """Home switch edge."""

    indexPulse: bool = False
    """Do we have index pulses?"""

    direction: float = UNDEFINED
    """Which direction to home to."""

    hardStop: bool = False
    """Perform hard stop homing. End / home switch and index pulse do not have
    an effect then.
    """


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
    HomingParam(): 35,  # Todo(atheler): Got replaced with 37 in newer versions
}
"""CiA 402 homing method lookup.

:meta hide-value:
"""

assert len(HOMING_METHODS) == 35, 'Something went wrong with HOMING_METHODS keys! Not enough homing methods anymore.'


def determine_homing_method(
        endSwitch: float = UNAVAILABLE,
        homeSwitch: float = UNAVAILABLE,
        homeSwitchEdge: float = UNDEFINED,
        indexPulse: bool = False,
        direction: float = UNDEFINED,
        hardStop: bool = False,
    ) -> int:
    """Determine homing method number.

    Args:
        endSwitch (optional): Do we have an end switch? If so at which end?
            Default is :const:`UNAVAILABLE`.
        homeSwitch (optional): Do we have a home switch? If so at which end?
            Default is :const:`UNAVAILABLE`.
        homeSwitchEdge (optional): Home switch edge. Default is
            :const:`UNDEFINED`.
        indexPulse (optional): Do we have index pulses? Default is False.
        direction (optional): Which direction to home to. Default is
            :const:`UNDEFINED`.
        hardStop (optional): Perform hard stop homing. End / home switch and
            index pulse do not have an effect then. Default is False.

    Returns:
        Homing method number.

    Examples:
        >>> determine_homing_method()  # Home at current position without moving
        35

        >>> determine_homing_method(direction=1.0, hardStop=True)  # Forward hard stop homing
        -3

        >>> determine_homing_method(endSwitch=1.0)  # Forward homing until end switch
        18
    """
    param = HomingParam(endSwitch, homeSwitch, homeSwitchEdge, indexPulse, direction, hardStop)
    return HOMING_METHODS[param]


assert determine_homing_method(hardStop=True, direction=FORWARD) == -3
assert determine_homing_method(hardStop=True, direction=BACKWARD) == -4


def find_shortest_state_path(start: State, end: State) -> List[State]:
    """Find shortest path from `start` to `end` state. Start node is also
    included in returned path.

    Args:
        start: Start state.
        end: Target end state.

    Returns:
        Path from start to end. Empty list for impossible transitions.

    Examples:
        >>> find_shortest_state_path(State.SWITCH_ON_DISABLED, State.OPERATION_ENABLED)
        [<State.SWITCH_ON_DISABLED: 3>,
         <State.READY_TO_SWITCH_ON: 4>,
         <State.SWITCHED_ON: 5>,
         <State.OPERATION_ENABLED: 6>]

        >>> find_shortest_state_path(State.OPERATION_ENABLED, State.SWITCH_ON_DISABLED)
        [<State.OPERATION_ENABLED: 6>, <State.SWITCH_ON_DISABLED: 3>]

        >>> find_shortest_state_path(State.OPERATION_ENABLED, State.NOT_READY_TO_SWITCH_ON)
        []  # Not possible to get to NOT_READY_TO_SWITCH_ON!
    """
    if start == end:
        return []

    # Breadth-first search
    queue = collections.deque([[start]])
    paths = []
    while queue:
        path = queue.popleft()
        tail = path[-1]
        for suc in POSSIBLE_TRANSITIONS[tail]:
            if suc in path:
                continue  # Cycle detected

            if suc == end:
                paths.append(path + [end])
            else:
                queue.append(path + [suc])

    return min(paths, key=len, default=[])


def target_reached(statusword: int) -> bool:
    """Check if target has been reached from statusword.

    Args:
        statusword: Statusword value.

    Returns:
        If target has been reached.
    """
    return bool(statusword & SW.TARGET_REACHED)


def maybe_int(string: str) -> Union[int, str]:
    """Try to cast string to int.

    Args:
        string: Input string.

    Returns:
        Maybe an int. Pass on input string otherwise.

    Example:
        >>> maybe_int('123')
        123

        >>> maybe_int('  0x7b')
        123
    """
    string = string.strip()
    if string.isnumeric():
        return int(string)

    if string.startswith('0x'):
        return int(string, base=16)

    if string.startswith('0b'):
        return int(string, base=2)

    return string


WHERE_TO_GO_NEXT: Dict[Edge, State] = {}
"""Lookup for the next intermediate state for a given state transition."""

for _src in State:
    for _dst in State:
        _shortest = find_shortest_state_path(_src, _dst)
        if _shortest:
            WHERE_TO_GO_NEXT[(_src, _dst)] = _shortest[1]
