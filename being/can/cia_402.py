"""CiA 402 CANopen node.

Trimmed down version of canopen.BaseNode402. Statusword & controlword always via
SDO, rest via PDO. Support for CYCLIC_SYNCHRONOUS_POSITION.
"""
import contextlib
from enum import auto, IntEnum, Enum
from typing import List, Dict, Set, Tuple, ForwardRef, Generator
from collections import deque, defaultdict

from canopen import RemoteNode

from being.bitmagic import check_bit
from being.can.definitions import (
    CONTROLWORD,
    MODES_OF_OPERATION,
    MODES_OF_OPERATION_DISPLAY,
    POSITION_ACTUAL_VALUE,
    STATUSWORD,
    SUPPORTED_DRIVE_MODES,
)
from being.can.nmt import OPERATIONAL, PRE_OPERATIONAL
from being.config import CONFIG
from being.logging import get_logger


State = ForwardRef('State')
Edge = Tuple[State, State]
SI_2_FAULHABER = CONFIG['Can']['SI_2_FAULHABER']


class State(Enum):

    """CANopen CiA 402 states."""

    START = auto()
    NOT_READY_TO_SWITCH_ON = auto()
    SWITCH_ON_DISABLED = auto()
    READY_TO_SWITCH_ON = auto()
    SWITCHED_ON = auto()
    OPERATION_ENABLE = auto()
    QUICK_STOP_ACTIVE = auto()
    FAULT_REACTION_ACTIVE = auto()
    FAULT = auto()
    HALT = auto()


class CW(IntEnum):

    """Controlword bits."""

    SWITCH_ON = (1 << 0)
    ENABLE_VOLTAGE = (1 << 1)
    QUICK_STOP = (1 << 2)
    ENABLE_OPERATION = (1 << 3)
    NEW_SET_POINT = (1 << 4)
    START_HOMING_OPERATION = NEW_SET_POINT  # Alias
    ENABLE_IP_MODE = NEW_SET_POINT  # Alias
    CHANGE_SET_IMMEDIATELY = (1 << 5)
    ABS_REL = (1 << 6)
    FAULT_RESET = (1 << 7)
    HALT = (1 << 8)


'''
class SW(IntEnum):

    """Statusword bits."""

    READY_TO_SWITCH_ON = (1 << 0)
    SWITCHED_ON = (1 << 1)
    OPERATION_ENABLED = (1 << 2)
    FAULT = (1 << 3)
    VOLTAGE_ENABLED = (1 << 4)
    QUICK_STOP = (1 << 5)
    SWITCH_ON_DISABLED = (1 << 6)
    WARNING = (1 << 7)
    #alwayszero = (1 << 8)
    REMOTE = (1 << 9)
    TARGET_REACHED = (1 << 10)
    INTERNAL_LIMIT_ACTIVE = (1 << 11)
    ACKNOWLEDGE = (1 << 12)
    DEVIATION_ERROR = (1 << 13)
    #NOT_IN_USE_0 = (1 << 14)
    #NOT_IN_USE_1 = 15
'''


class Command(IntEnum):

    """CANopen CiA 402 controlword commands for state transitions."""

    SHUT_DOWN = CW.ENABLE_VOLTAGE | CW.QUICK_STOP
    SWITCH_ON = CW.SWITCH_ON | CW.ENABLE_VOLTAGE | CW.QUICK_STOP
    DISABLE_VOLTAGE = 0
    QUICK_STOP = CW.ENABLE_VOLTAGE
    DISABLE_OPERATION = CW.ENABLE_VOLTAGE | CW.QUICK_STOP | CW.ENABLE_OPERATION
    ENABLE_OPERATION = CW.SWITCH_ON | CW.ENABLE_VOLTAGE | CW.QUICK_STOP | CW.ENABLE_OPERATION
    FAULT_RESET = CW.FAULT_RESET


class OperationMode(IntEnum):

    """Modes of Operation (0x6060 / 0x6061)."""

    NO_MODE = 0
    PROFILED_POSITION = 1
    VELOCITY = 2
    PROFILED_VELOCITY = 3
    PROFILED_TORQUE = 4
    HOMING = 6
    INTERPOLATED_POSITION = 7
    CYCLIC_SYNCHRONOUS_POSITION = 8
    CYCLIC_SYNCHRONOUS_VELOCITY = 9
    CYCLIC_SYNCHRONOUS_TORQUE = 10
    OPEN_LOOP_SCALAR_MODE = -1
    OPEN_LOOP_VECTOR_MODE = -2


TRANSITIONS: Dict[Edge, Command] = {
    # Shut down: 2, 6, 8
    (State.SWITCH_ON_DISABLED, State.READY_TO_SWITCH_ON):     Command.SHUT_DOWN,
    (State.SWITCHED_ON, State.READY_TO_SWITCH_ON):            Command.SHUT_DOWN,
    (State.OPERATION_ENABLE, State.READY_TO_SWITCH_ON):       Command.SHUT_DOWN,
    # Switch On: 3
    (State.READY_TO_SWITCH_ON, State.SWITCHED_ON):            Command.SWITCH_ON,
    # Disable Voltage: 7, 9, 10, 12
    (State.READY_TO_SWITCH_ON, State.SWITCH_ON_DISABLED):     Command.DISABLE_VOLTAGE,
    (State.OPERATION_ENABLE, State.SWITCH_ON_DISABLED):       Command.DISABLE_VOLTAGE,
    (State.SWITCHED_ON, State.SWITCH_ON_DISABLED):            Command.DISABLE_VOLTAGE,
    (State.QUICK_STOP_ACTIVE, State.SWITCH_ON_DISABLED):      Command.DISABLE_VOLTAGE,
    # Quick Stop: 7, 10, 11
    (State.READY_TO_SWITCH_ON, State.SWITCH_ON_DISABLED):     Command.QUICK_STOP,
    (State.SWITCHED_ON, State.SWITCH_ON_DISABLED):            Command.QUICK_STOP,
    (State.OPERATION_ENABLE, State.QUICK_STOP_ACTIVE):        Command.QUICK_STOP,
    # Disable Operation: 5
    (State.OPERATION_ENABLE, State.SWITCHED_ON):              Command.DISABLE_OPERATION,
    # Enable Operation: 4, 16
    (State.SWITCHED_ON, State.OPERATION_ENABLE):              Command.ENABLE_OPERATION,
    (State.QUICK_STOP_ACTIVE, State.OPERATION_ENABLE):        Command.ENABLE_OPERATION,
    # Fault Reset: 15
    (State.FAULT, State.SWITCH_ON_DISABLED):                  Command.FAULT_RESET,
    # Automatic: 0, 1, 14
    (State.START, State.NOT_READY_TO_SWITCH_ON):              0x0,
    (State.NOT_READY_TO_SWITCH_ON, State.SWITCH_ON_DISABLED): 0x0,
    (State.FAULT_REACTION_ACTIVE, State.FAULT):               0x0,
}
"""Possible state transitions and the corresponding controlword command. State
edge -> command.
"""

POSSIBLE_TRANSITIONS: Dict[State, Set[State]] = defaultdict(set)
for _src, _dst in TRANSITIONS:
    POSSIBLE_TRANSITIONS[_src].add(_dst)
"""Reachable states from a given state."""

VALID_OP_MODE_CHANGE_STATES: Set[State] = {
    State.SWITCH_ON_DISABLED,
    State.READY_TO_SWITCH_ON,
    State.SWITCHED_ON,
}
"""Not every state support switching of operation mode."""


def which_state(statusword: int) -> State:
    """Extract state from statusword."""
    considerations = [
        (0b1001111, 0b0000000, State.NOT_READY_TO_SWITCH_ON),
        (0b1001111, 0b1000000, State.SWITCH_ON_DISABLED),
        (0b1101111, 0b0100001, State.READY_TO_SWITCH_ON),
        (0b1101111, 0b0100011, State.SWITCHED_ON),
        (0b1101111, 0b0100111, State.OPERATION_ENABLE),
        (0b1101111, 0b0000111, State.QUICK_STOP_ACTIVE),
        (0b1001111, 0b0001111, State.FAULT_REACTION_ACTIVE),
        (0b1001111, 0b0001000, State.FAULT),
    ]
    for mask, value, state in considerations:
        if (statusword & mask) == value:
            return state

    raise ValueError('Unknown state for statusword {statusword}!')


def supported_operation_modes(supportedDriveModes: int) -> Generator[OperationMode, None, None]:
    """Which operation modes are supported? Extract information from value of
    SUPPORTED_DRIVE_MODES (0x6502).

    Args:
        supportedDriveModes: Received value from 0x6502.

    Yields:
        Supported drive operation modes for the node.
    """
    stuff = [
        (0, OperationMode.PROFILED_POSITION),
        (2, OperationMode.PROFILED_VELOCITY),
        (5, OperationMode.HOMING),
        (7, OperationMode.CYCLIC_SYNCHRONOUS_POSITION),
        # TODO: From the Faulhaber manual. Add additional modes for different
        # manufacturer. Which bits do they us?
    ]
    for bit, op in stuff:
        if check_bit(supportedDriveModes, bit):
            yield op


def find_shortest_state_path(start: State, end: State) -> List[State]:
    """Find shortest path from start to end state. Start node is also included
    in returned path.

    Args:
        start: Start state.
        end: Target end state.

    Returns:
        Path from start -> end. Empty list if the does not exist a path from
        start -> end.
    """
    # Breadth-first search
    queue = deque([[start]])
    paths = []
    while queue:
        path = queue.popleft()
        tail = path[-1]
        for suc in POSSIBLE_TRANSITIONS[tail]:
            if suc in path:
                continue  # Cycle
            elif suc is end:
                paths.append(path + [end])
            else:
                queue.append(path + [suc])

    return min(paths, key=len, default=[])


class CiA402Node(RemoteNode):

    """Alternative / simplified implementation of canopen.BaseNode402."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = get_logger(str(self))

    @property
    def position(self):
        """Current actual position value."""
        return self.sdo[POSITION_ACTUAL_VALUE].raw / SI_2_FAULHABER

    # TODO: Wording. Any English speakers in the house?

    def disengage(self):
        self.nmt.state = PRE_OPERATIONAL
        self.change_state(State.READY_TO_SWITCH_ON)

    def disable(self):
        self.disengage()

    def engage(self):
        self.nmt.state = OPERATIONAL
        self.change_state(State.SWITCHED_ON)

    def disenable(self):
        self.engage()

    def enable(self):
        self.nmt.state = OPERATIONAL
        self.change_state(State.OPERATION_ENABLE)

    def get_state(self) -> State:
        """Get current node state."""
        sw = self.sdo[STATUSWORD].raw
        return which_state(sw)

    def set_state(self, target: State):
        """Set node state. This method only works for possible transitions from
        current state (single step). For arbitrary transitions use
        CiA402Node.change_state.

        Args:
            target: New target state.
        """
        self.logger.info('Switching to state %r', target)
        current = self.get_state()
        if target is current:
            return

        if not target in POSSIBLE_TRANSITIONS[current]:
            raise RuntimeError(f'Invalid state transition from {current!r} to {target!r}!')

        edge = (current, target)
        cw = TRANSITIONS[edge]
        self.sdo[CONTROLWORD].raw = cw

    def change_state(self, target: State):
        """Change to a specific state. Will traverse all necessary states in
        between to get there.

        Args:
            target: New target state.
        """
        current = self.get_state()
        if target is current:
            return

        path = find_shortest_state_path(current, target)
        for state in path[1:]:
            self.set_state(state)

    def get_operation_mode(self) -> OperationMode:
        """Get current operation mode."""
        return OperationMode(self.sdo[MODES_OF_OPERATION_DISPLAY].raw)

    def set_operation_mode(self, op: OperationMode):
        """Set operation mode.

        Args:
            op: New target mode of operation.
        """
        self.logger.info('Switching to operation mode %r', op)
        state = self.get_state()
        if state not in VALID_OP_MODE_CHANGE_STATES:
            raise RuntimeError(f'Can not change to {op!r} when in {state!r}')

        sdm = self.sdo[SUPPORTED_DRIVE_MODES].raw
        if op not in supported_operation_modes(sdm):
            raise RuntimeError(f'This drive does not support {op!r}!')

        self.sdo[MODES_OF_OPERATION].raw = op

    @contextlib.contextmanager
    def restore_states_and_operation_mode(self):
        """Restore NMT state, CiA 402 state and operation mode. Implemented as
        context manager.

        Usage:
            >>> with node.restore_states_and_operation_mode():
            ...     # Do something fancy with the states
            ...     pass
        """
        nmt = self.nmt.state
        op = self.get_operation_mode()
        state = self.get_state()

        yield self

        self.change_state(state)
        self.set_operation_mode(op)
        self.nmt.state = nmt

    def __str__(self):
        return f'{type(self).__name__}(id={self.id})'
