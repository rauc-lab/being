"""CiA 402 CANopen node.

Alternative to canopen.BaseNode402. Simpler. Statusword & controlword always via
SDO, rest via PDO. Proper support for CYCLIC_SYNCHRONOUS_POSITION.
"""
from enum import auto, IntEnum, Enum
from typing import List, Dict, Set
from collections import deque, defaultdict

from canopen import RemoteNode
from being.bitmagic import check_bit
from being.can.definitions import (
    CONTROLWORD, OPERATION_MODE, OPERATION_MODE_DISPLAY, STATUSWORD,
    SUPPORTED_DRIVE_MODES,
)


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


class Command(IntEnum):

    """CANopen CiA 402 controlword commands for state transitions."""

    SHUT_DOWN = 0b0110
    SWITCH_ON = 0b0111
    DISABLE_VOLTAGE = 0b0000
    QUICK_STOP = 0b0010
    DISABLE_OPERATION = 0b0111
    ENABLE_OPERATION = 0b1111
    FAULT_RESET = 0b10000000


TRANSITIONS = {
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
"""Possible state transitions and the corresponding controlword command."""


POSSIBLE_TRANSITIONS: Dict[State, Set[State]] = defaultdict(set)
for edge in TRANSITIONS:
    src, dst = edge
    POSSIBLE_TRANSITIONS[src].add(dst)
"""Reachable states for a given state."""


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


VALID_OP_MODE_CHANGE_STATES = {
    State.SWITCH_ON_DISABLED,
    State.READY_TO_SWITCH_ON,
    State.SWITCHED_ON,
}
"""set: Not every state support switching of operation mode."""


def which_state(statusword: int) -> State:
    """Extract state from statusword."""
    stuff = [
        (0b1001111, 0b0000000, State.NOT_READY_TO_SWITCH_ON),
        (0b1001111, 0b1000000, State.SWITCH_ON_DISABLED),
        (0b1101111, 0b0100001, State.READY_TO_SWITCH_ON),
        (0b1101111, 0b0100011, State.SWITCHED_ON),
        (0b1101111, 0b0100111, State.OPERATION_ENABLE),
        (0b1101111, 0b0000111, State.QUICK_STOP_ACTIVE),
        (0b1001111, 0b0001111, State.FAULT_REACTION_ACTIVE),
        (0b1001111, 0b0001000, State.FAULT),
    ]
    for mask, value, state in stuff:
        if (statusword & mask) == value:
            return state

    raise ValueError('Unknown state for statusword {statusword}!')


def supported_operation_modes(supportedDriveModes: int) -> List[OperationMode]:
    """Determine supported operation modes for value of SUPPORTED_DRIVE_MODES
    0x6502.
    """
    stuff = [
        (0, OperationMode.PROFILED_POSITION),
        (2, OperationMode.PROFILED_VELOCITY),
        (5, OperationMode.HOMING),
        (7, OperationMode.CYCLIC_SYNCHRONOUS_POSITION),
        # TODO: Add additional modes for different manufacturer
    ]
    supported = []
    for bit, op in stuff:
        if check_bit(supportedDriveModes, bit):
            supported.append(op)

    return supported


def find_shortest_state_path(start: State, end: State) -> List[State]:
    """Find shortest path from start to end state. Start node is also included
    in returned path.
    """
    # BFS
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

    def __init__(self, node_id, object_dictionary):
        super().__init__(node_id, object_dictionary)

        #self.tpdo_values = dict() # { index: TPDO_value }
        #self.rpdo_pointers = dict() # { index: RPDO_pointer }

    def get_state(self) -> State:
        """Get current node state."""
        sw = self.sdo[STATUSWORD].raw
        return which_state(sw)

    def set_state(self, target: State):
        """Set node state."""
        current = self.get_state()
        if target is current:
            return

        if not target in POSSIBLE_TRANSITIONS[current]:
            msg = f'Invalid state transition from {current!r} to {target!r}!'
            raise RuntimeError(msg)

        edge = (current, target)
        cmd = TRANSITIONS[edge]
        print('  Controlword:', cmd, int(cmd))
        self.sdo[CONTROLWORD].raw = int(cmd)

    def change_state(self, target: State):
        """Change to a specific state. Will traverse all necessary states in
        between to get there.
        """
        current = self.get_state()
        if target is current:
            return

        path = find_shortest_state_path(current, target)
        for state in path[1:]:
            self.set_state(state)

    def get_operation_mode(self) -> OperationMode:
        """Get current operation mode."""
        return OperationMode(self.sdo[OPERATION_MODE_DISPLAY].raw)

    def set_operation_mode(self, op: OperationMode):
        """Set operation mode."""
        state = self.get_state()
        if state not in VALID_OP_MODE_CHANGE_STATES:
            msg = f'Can not change operation mode when in {state!r}'
            raise RuntimeError(msg)

        sdm = self.sdo[SUPPORTED_DRIVE_MODES].raw
        if op not in supported_operation_modes(sdm):
            msg = f'This drive does not support {op!r}!'
            raise RuntimeError(msg)

        self.sdo[OPERATION_MODE].raw = op
