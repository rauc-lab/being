"""CiA 402 definitions, state machine and CiA402Node class.

CiA402Node is a trimmed down version of canopen.BaseNode402. We favor SDO
communication during setup but synchronous acyclic PDO communication during
operation. Also added support for CYCLIC_SYNCHRONOUS_POSITION mode.
"""
import contextlib
from enum import auto, IntEnum, Enum
from typing import List, Dict, Set, Tuple, ForwardRef, Generator, Union, Optional
from collections import deque, defaultdict
import time

from canopen import RemoteNode

from being.bitmagic import check_bit
from being.can.cia_301 import MANUFACTURER_DEVICE_NAME
from being.can.definitions import TransmissionType
from being.can.nmt import OPERATIONAL, PRE_OPERATIONAL
from being.can.vendor import UNITS, Units
from being.logging import get_logger


# Mandatory (?) CiA 402 object dictionary entries
# (SJA): CiA 402 is still a Draft Specification Proposal (DSP).

CONTROLWORD = 0x6040
STATUSWORD = 0x6041
MODES_OF_OPERATION = 0x6060
MODES_OF_OPERATION_DISPLAY = 0x6061
POSITION_DEMAND_VALUE = 0x6062
POSITION_ACTUAL_VALUE = 0x6064
POSITION_WINDOW = 0x6067
POSITION_WINDOW_TIME = 0x6068
VELOCITY_DEMAND_VALUE = 0x606B
VELOCITY_ACTUAL_VALUE = 0x606C
TARGET_POSITION = 0x607A
POSITION_RANGE_LIMIT = 0x607B
SOFTWARE_POSITION_LIMIT = 0x607D
MIN_POSITION_LIMIT = 1
MAX_POSITION_LIMIT = 2
MAX_PROFILE_VELOCITY = 0x607F
PROFILE_VELOCITY = 0x6081
PROFILE_ACCELERATION = 0x6083
PROFILE_DECELERATION = 0x6084
QUICK_STOP_DECELERATION = 0x6085
HOMING_METHOD = 0x6098
HOMING_SPEED = 0x6099
HOMING_ACCELERATION = 0x609A
DIGITAL_INPUTS = 0x60FD
TARGET_VELOCITY = 0x60FF
SUPPORTED_DRIVE_MODES = 0x6502

State = ForwardRef('State')
Edge = Tuple[State, State]
CanOpenRegister = Union[int, str]


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


class Command(IntEnum):

    """CANopen CiA 402 controlword commands for state transitions."""

    SHUT_DOWN = CW.ENABLE_VOLTAGE | CW.QUICK_STOP
    SWITCH_ON = CW.SWITCH_ON | CW.ENABLE_VOLTAGE | CW.QUICK_STOP
    DISABLE_VOLTAGE = 0
    QUICK_STOP = CW.ENABLE_VOLTAGE
    DISABLE_OPERATION = CW.ENABLE_VOLTAGE | CW.QUICK_STOP | CW.ENABLE_OPERATION
    ENABLE_OPERATION = CW.SWITCH_ON | CW.ENABLE_VOLTAGE | CW.QUICK_STOP | CW.ENABLE_OPERATION
    FAULT_RESET = CW.FAULT_RESET


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
    HOMING_ATTAINED = ACKNOWLEDGE  # Alias
    DEVIATION_ERROR = (1 << 13)
    #NOT_IN_USE_0 = (1 << 14)
    #NOT_IN_USE_1 = 15


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
    State.OPERATION_ENABLE,  # (SJA): Should work no?!
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
    # Look-up is identical between Faulhaber / Maxon

    stuff = [
        (0, OperationMode.PROFILED_POSITION),
        (2, OperationMode.PROFILED_VELOCITY),
        (5, OperationMode.HOMING),
        (7, OperationMode.CYCLIC_SYNCHRONOUS_POSITION),
        (8, OperationMode.CYCLIC_SYNCHRONOUS_VELOCITY),
        (9, OperationMode.CYCLIC_SYNCHRONOUS_TORQUE),
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
                continue  # Cycle detected

            if suc is end:
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


class CiA402Node(RemoteNode):

    """Alternative / simplified implementation of canopen.BaseNode402.

    Since we want to configure the CanOpen node during init we make a connected
    CAN network mandatory.

    Attributes:
        units (Units): Manufacturer dependent device units.
        softwarePositionWidth (int): Current software position width from
            homing. Used for flipped operation.
        flipped (bool): Flipped operation (position and velocity).
    """

    def __init__(self, nodeId, objectDictionary, network):
        super().__init__(nodeId, objectDictionary, load_od=False)
        self.logger = get_logger(str(self))
        self.units: Units = None

        network.add_node(self, objectDictionary)

        # Configure PDOs
        self.pdo.read()  # Load both node.tpdo and node.rpdo

        # Note: Default PDO mapping of some motors includes the Control- /
        # Statusword in multiple PDOs. This can lead to unexpected behavior with
        # our CanOpen stack since for example:
        #
        #     node.pdo['Controlword'] = Command.ENABLE_OPERATION
        #
        # will only set the value in the first PDO with the Controlword but not
        # for the others following. In these, the Controlword will stay zero and
        # subsequently shut down the motor.
        #
        # -> We clear all of them and have the Controlword only in the first RxPDO1.

        # EPOS4 has no PDO mapping for Error Regiser,
        # thus re-register later txpdo1 if available
        self.setup_txpdo(1, STATUSWORD)
        self.setup_txpdo(2, POSITION_ACTUAL_VALUE)
        self.setup_txpdo(3, VELOCITY_ACTUAL_VALUE)
        self.setup_txpdo(4, enabled=False)

        self.setup_rxpdo(1, CONTROLWORD)
        self.setup_rxpdo(2, TARGET_POSITION)
        self.setup_rxpdo(3, TARGET_VELOCITY)
        self.setup_rxpdo(4, enabled=False)

        # Determine device units
        manu = self.sdo[MANUFACTURER_DEVICE_NAME].raw
        self.units = UNITS[manu]

    def setup_txpdo(self,
            nr: int,
            *variables: CanOpenRegister,
            overwrite: bool = True,
            enabled: bool = True,
            trans_type: TransmissionType = TransmissionType.SYNCHRONOUS_CYCLIC,
            # TODO: Is event_timer needed? Throws a KeyError if set to 0 with EPOS4
            event_timer: Optional[int] = None,
        ):
        """Setup single transmission PDO of node (receiving PDO messages from
        remote node). Note: Sending / receiving direction always from the remote
        nodes perspective.

        Args:
            nr: TxPDO number (1-4).
            *variables: CanOpen variables to register to receive from remote
                node via TxPDO.

        Kwargs:
            enabled: Enable or disable TxPDO.
            overwrite: Overwrite TxPDO.
            trans_type:
            event_timer:
        """
        tx = self.tpdo[nr]
        if overwrite:
            tx.clear()

        for var in variables:
            tx.add_variable(var)

        tx.enabled = enabled
        tx.trans_type = trans_type
        tx.event_timer = event_timer
        tx.save()

    def setup_rxpdo(self,
            nr: int,
            *variables: CanOpenRegister,
            overwrite: bool = True,
            enabled: bool = True,
        ):
        """Setup single receiving PDO of node (sending PDO messages to remote
        node). Note: Sending / receiving direction always from the remote nodes
        perspective.

        Args:
            nr: RxPDO number (1-4).
            *variables: CanOpen variables to register to send to remote node via
                RxPDO.

        Kwargs:
            enabled: Enable or disable RxPDO.
            overwrite: Overwrite RxPDO.
        """
        rx = self.rpdo[nr]
        if overwrite:
            rx.clear()

        for var in variables:
            rx.add_variable(var)

        rx.enabled = enabled
        rx.save()

    def get_state(self) -> State:
        """Get current node state."""
        sw = self.sdo[STATUSWORD].raw  # This takes approx. 2.713 ms
        #sw = self.pdo['Statusword'].raw  # This takes approx. 0.027 ms
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

        if target not in POSSIBLE_TRANSITIONS[current]:
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

            # EPOS is too slow while state switching.
            # set_state() will throw an exception otherwise
            startTime = time.perf_counter()
            endTime = startTime + 0.05

            while self.get_state() != state:
                if time.perf_counter() > endTime:
                    raise RuntimeError(f'Timeout while trying to transition from state {current!r} to {target!r}!')
                time.sleep(0.002)

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
        oldNmt = self.nmt.state
        oldOp = self.get_operation_mode()
        oldState = self.get_state()

        yield self

        # TODO: Should we do a d-tour via READY_TO_SWITCH_ON so that we can
        # restore the operation mode in any case?
        #self.change_state(State.READY_TO_SWITCH_ON)
        self.set_operation_mode(oldOp)
        self.change_state(oldState)
        self.nmt.state = oldNmt

    # TODO: Wording. Any English speakers in the house?

    def switch_off(self):
        """Switch off drive. Same state as on power-up."""
        self.nmt.state = PRE_OPERATIONAL
        self.change_state(State.READY_TO_SWITCH_ON)

    def disable(self):
        """Disable drive (no power)."""
        self.nmt.state = OPERATIONAL
        self.change_state(State.SWITCHED_ON)

    def enable(self):
        """Enable drive."""
        self.nmt.state = OPERATIONAL
        self.change_state(State.OPERATION_ENABLE)

    def set_target_position(self, pos):
        """Set target position in SI units"""
        self.pdo[TARGET_POSITION].raw = pos * self.units.length
        self.rpdo[2].transmit()

    def set_target_angle(self, angle):
        """Set target angle in radians"""
        self.pdo[TARGET_POSITION].raw = angle
        self.rpdo[2].transmit()

    def get_actual_position(self):
        """Get actual position in SI units"""
        return self.pdo[POSITION_ACTUAL_VALUE].raw / self.units.length

    def set_target_velocity(self, vel):
        """Set target velocity in SI units."""
        self.pdo[TARGET_VELOCITY].raw = vel * self.units.speed
        self.rpdo[3].transmit()

    def get_actual_velocity(self):
        """Get actual velocity in SI units."""
        return self.pdo[VELOCITY_ACTUAL_VALUE].raw / self.units.speed

    def _get_info(self) -> dict:
        """Get the current states."""
        return {
            'nmt': self.nmt.state,
            'state': self.get_state(),
            'op': self.get_operation_mode(),
        }

    def __str__(self):
        return f'{type(self).__name__}(id={self.id})'
