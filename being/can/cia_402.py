"""CiA 402 definitions, state machine and CiA402Node class.

CiA402Node is a trimmed down version of canopen.BaseNode402. We favor SDO
communication during setup but synchronous acyclic PDO communication during
operation. Also added support for CYCLIC_SYNCHRONOUS_POSITION mode.
"""
import collections
import contextlib
import enum
import time
from typing import (
    Any,
    Dict,
    ForwardRef,
    Generator,
    List,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Union,
)

from canopen import RemoteNode

from being.bitmagic import check_bit
from being.can.cia_301 import MANUFACTURER_DEVICE_NAME
from being.can.definitions import TransmissionType
from being.constants import FORWARD, BACKWARD
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
HOMING_SPEEDS = 0x6099
SPEED_FOR_SWITCH_SEARCH = 1
SPEED_FOR_ZERO_SEARCH = 2
HOMING_ACCELERATION = 0x609A
DIGITAL_INPUTS = 0x60FD
TARGET_VELOCITY = 0x60FF
SUPPORTED_DRIVE_MODES = 0x6502


State = ForwardRef('State')
StateSwitching = Generator[State, None, None]
Edge = Tuple[State, State]
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


class CW(enum.IntEnum):

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


class Command(enum.IntEnum):

    """CANopen CiA 402 controlword commands for state transitions."""

    SHUT_DOWN = CW.QUICK_STOP | CW.ENABLE_VOLTAGE
    SWITCH_ON = CW.QUICK_STOP | CW.ENABLE_VOLTAGE | CW.SWITCH_ON
    DISABLE_VOLTAGE = 0
    QUICK_STOP = CW.ENABLE_VOLTAGE
    DISABLE_OPERATION = CW.QUICK_STOP | CW.ENABLE_VOLTAGE | CW.SWITCH_ON
    ENABLE_OPERATION = CW.ENABLE_OPERATION | CW.QUICK_STOP | CW.ENABLE_VOLTAGE | CW.SWITCH_ON
    FAULT_RESET = CW.FAULT_RESET


class SW(enum.IntEnum):

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
    HOMING_ERROR = (1 << 13)
    DEVIATION_ERROR = HOMING_ERROR  # Alias
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
    (State.START, State.NOT_READY_TO_SWITCH_ON):              0x0,
    (State.NOT_READY_TO_SWITCH_ON, State.SWITCH_ON_DISABLED): 0x0,
    (State.FAULT_REACTION_ACTIVE, State.FAULT):               0x0,
}
"""Possible state transitions and the corresponding controlword command. State
edge -> command.
"""

POSSIBLE_TRANSITIONS: Dict[State, Set[State]] = collections.defaultdict(set)
"""Reachable states from a given state."""

for _edge in TRANSITION_COMMANDS:
    _src, _dst = _edge
    POSSIBLE_TRANSITIONS[_src].add(_dst)


VALID_OP_MODE_CHANGE_STATES: Set[State] = {
    State.SWITCH_ON_DISABLED,
    State.READY_TO_SWITCH_ON,
    State.SWITCHED_ON,
}
"""Not every state support switching of operation mode."""

STATUSWORD_2_STATE = [
    (0b1001111, 0b0000000, State.NOT_READY_TO_SWITCH_ON),
    (0b1001111, 0b1000000, State.SWITCH_ON_DISABLED),
    (0b1101111, 0b0100001, State.READY_TO_SWITCH_ON),
    (0b1101111, 0b0100011, State.SWITCHED_ON),
    (0b1101111, 0b0100111, State.OPERATION_ENABLED),
    (0b1101111, 0b0000111, State.QUICK_STOP_ACTIVE),
    (0b1001111, 0b0001111, State.FAULT_REACTION_ACTIVE),
    (0b1001111, 0b0001000, State.FAULT),
]
"""Statusword bit masks for state loopkup."""


def which_state(statusword: int) -> State:
    """Extract state from statusword."""
    for mask, value, state in STATUSWORD_2_STATE:
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


POSITIVE = FORWARD
RISING = FORWARD
NEGATIVE = BACKWARD
FALLING = BACKWARD
UNAVAILABLE = 0.0
UNDEFINED = 0.0


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
    HomingParam(): 35,  # Todo(atheler): Got replaced with 37 in newer versions
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
    if start is end:
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


class CiA402Node(RemoteNode):

    """Alternative / simplified implementation of canopen.BaseNode402.

    Since CanOpen node should be configured during initialization connected CAN
    network instance is mandatory.
    """

    def __init__(self, nodeId, objectDictionary, network):
        super().__init__(nodeId, objectDictionary, load_od=False)
        self.logger = get_logger(str(self))

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

        # EPOS4 has no PDO mapping for Error Register,
        # thus re-register later txpdo1 if available
        self.setup_txpdo(1, STATUSWORD)
        self.setup_txpdo(2, POSITION_ACTUAL_VALUE)
        self.setup_txpdo(3, VELOCITY_ACTUAL_VALUE)
        self.setup_txpdo(4, enabled=False)

        self.setup_rxpdo(1, CONTROLWORD)
        self.setup_rxpdo(2, TARGET_POSITION)
        self.setup_rxpdo(3, TARGET_VELOCITY)
        self.setup_rxpdo(4, enabled=False)

        network.register_rpdo(self.rpdo[1])
        network.register_rpdo(self.rpdo[2])
        network.register_rpdo(self.rpdo[3])

    def setup_txpdo(self,
            nr: int,
            *variables: CanOpenRegister,
            overwrite: bool = True,
            enabled: bool = True,
            trans_type: TransmissionType = TransmissionType.SYNCHRONOUS_CYCLIC,
            event_timer: Optional[int] = None,
        ):
        """Setup single transmission PDO of node (receiving PDO messages from
        remote node). Note: Sending / receiving direction always from the remote
        nodes perspective. Setting `event_timer` to 0 can lead to KeyErrors on
        some controllers.

        Args:
            nr: TxPDO number (1-4).
            *variables: CanOpen variables to register to receive from remote
                node via TxPDO.
            enabled: Enable or disable TxPDO.
            overwrite: Overwrite TxPDO.
            trans_type: Event based or synchronized transmission
            event_timer:
        """
        tx = self.tpdo[nr]
        if overwrite:
            tx.clear()

        for var in variables:
            tx.add_variable(var)

        tx.enabled = enabled
        tx.trans_type = trans_type
        if event_timer is not None:
            tx.event_timer = event_timer

        tx.save()

    def setup_rxpdo(self,
            nr: int,
            *variables: CanOpenRegister,
            overwrite: bool = True,
            enabled: bool = True,
            trans_type: TransmissionType = TransmissionType.SYNCHRONOUS_CYCLIC,
        ):
        """Setup single receiving PDO of node (sending PDO messages to remote
        node). Note: Sending / receiving direction always from the remote nodes
        perspective.

        Args:
            nr: RxPDO number (1-4).
            *variables: CanOpen variables to register to send to remote node via
                RxPDO.
            enabled: Enable or disable RxPDO.
            overwrite: Overwrite RxPDO.
            trans_type: Event based or synchronized transmission
        """
        rx = self.rpdo[nr]
        if overwrite:
            rx.clear()

        for var in variables:
            rx.add_variable(var)

        rx.enabled = enabled
        rx.trans_type = trans_type
        rx.save()

    def get_state(self, how: str = 'sdo') -> State:
        """Get current node state.

        Args:
            how (optional): Which communication channel to use. Either via 'sdo'
                or 'pdo'.  'sdo' by default.

        Returns:
            Current CiA 402 state.
        """
        if how == 'pdo':
            return which_state(self.pdo[STATUSWORD].raw)  # This takes approx. 0.027 ms
        elif how == 'sdo':
            return which_state(self.sdo[STATUSWORD].raw)  # This takes approx. 2.713 ms
        else:
            raise ValueError(f'Unknown how {how!r}')

    def set_state(self, target: State, how: str = 'sdo'):
        """Set node to a new target state. Target state has to be reachable from
        node's current state. RuntimeError otherwise.

        Args:
            target: Target state to switch to.
            how (optional): Communication channel. 'sdo' (default) or 'pdo'.
        """
        self.logger.debug('Setting state to %s (%s)', target, how)
        current = self.get_state(how)
        if current is target:
            return

        edge = (current, target)
        if edge not in TRANSITION_COMMANDS:
            raise RuntimeError(f'Invalid state transition from {current!r} to {target!r}!')

        cw = TRANSITION_COMMANDS[edge]
        if how == 'pdo':
            self.pdo[CONTROLWORD].raw = cw
        elif how == 'sdo':
            self.sdo[CONTROLWORD].raw = cw
        else:
            raise ValueError(f'Unknown how {how!r}')

    def state_switching_job(self,
            target: State,
            how: str = 'sdo',
            timeout: float = 1.0,
        ) -> StateSwitching:
        """Create a state switching job generator. The generator will check the
        current state during each cycle and steer the state machine towards the
        desired target state (traversing necessary intermediate accordingly).
        Implemented as generator so that multiple nodes can be switched in
        parallel.

        Args:
            target: Target state to switch to.
            how (optional): Communication channel. 'sdo' (default) or 'pdo'.
            timeout (optional): Optional timeout value in seconds. 1.0 second by default.

        Yields:
            Current states.
        """
        self.logger.debug('state_switching_job(%s, %s, %s)', target, how, timeout)
        endTime = time.perf_counter() + timeout
        initial = current = self.get_state(how)
        lastPlanned = None
        while True:
            yield current

            if current is target:
                return

            #self.logger.debug('Still in %s (not in %s)', current.name, target.name)

            if time.perf_counter() > endTime:
                raise TimeoutError(f'Could not transition from {initial.name} to {target.name} in {timeout:.3f} sec!')

            if current is not lastPlanned:
                lastPlanned = current
                intermediate = WHERE_TO_GO_NEXT[(current, target)]
                self.set_state(intermediate, how)

            current = self.get_state(how)

    def change_state(self,
            target: State,
            how: str = 'sdo',
            timeout: float = 1.0,
        ) -> Union[State, StateSwitching]:
        """Change to a specific target state and traverse necessary intermediate
        states. Blocking.

        Args:
            target: Target state to switch to.
            how (optional): Communication channel. 'sdo' (default) or 'pdo'.
            timeout (optional): Optional timeout value in seconds. 1.0 second by default.

        Returns:
            Final state.
        """
        self.logger.debug('change_state(%s, %s, %s)', target, how, timeout)
        job = self.state_switching_job(target, how, timeout)
        state = None
        for state in job:
            time.sleep(0.050)

        return state

    def get_operation_mode(self) -> OperationMode:
        """Get current operation mode."""
        return OperationMode(self.sdo[MODES_OF_OPERATION_DISPLAY].raw)

    def set_operation_mode(self, op: OperationMode):
        """Set operation mode.

        Args:
            op: New target mode of operation.
        """
        self.logger.debug('Switching to %s', op)
        current = self.get_operation_mode()
        if current is op:
            self.logger.debug('Already %s', op)
            return

        state = self.get_state()
        if state not in VALID_OP_MODE_CHANGE_STATES:
            raise RuntimeError(f'Can not change to {op} when in {state}')

        sdm = self.sdo[SUPPORTED_DRIVE_MODES].raw
        if op not in supported_operation_modes(sdm):
            raise RuntimeError(f'This drive does not support {op!r}!')

        self.sdo[MODES_OF_OPERATION].raw = op

    @contextlib.contextmanager
    def restore_states_and_operation_mode(self, how='sdo', timeout: float = 2.0):
        """Restore NMT state, CiA 402 state and operation mode. Implemented as
        context manager.

        Args:
            how (optional): Which communication channel to use. Either via 'sdo'
                or 'pdo'.  'sdo' by default.
            timeout (optional): Timeout duration.

        Example:
            >>> with node.restore_states_and_operation_mode():
            ...     # Do something fancy with the states
            ...     pass
        """
        oldOp = self.get_operation_mode()
        oldState = self.get_state(how)

        yield self

        self.set_operation_mode(oldOp)
        self.change_state(oldState, how=how, timeout=timeout)

    def reset_fault(self):
        """Perform fault reset to SWITCH_ON_DISABLED."""
        self.logger.info('Resetting fault')
        self.sdo[CONTROLWORD].raw = 0
        self.sdo[CONTROLWORD].raw = CW.FAULT_RESET

    def switch_off(self, timeout: float = 1.0):
        """Switch off drive. Same state as on power-up.

        Args:
            timeout (optional): Timeout duration.
        """
        self.change_state(State.SWITCH_ON_DISABLED, timeout=timeout)

    def disable(self, timeout: float = 1.0):
        """Disable drive (no power).

        Args:
            timeout (optional): Timeout duration.
        """
        self.change_state(State.READY_TO_SWITCH_ON, timeout=timeout)

    def enable(self, timeout: float = 1.0):
        """Enable drive.

        Args:
            timeout (optional): Timeout duration.
        """
        self.change_state(State.OPERATION_ENABLED, timeout=timeout)

    def set_target_position(self, pos):
        """Set target position in device units."""
        self.pdo[TARGET_POSITION].raw = pos

    def get_actual_position(self):
        """Get actual position in device units."""
        return self.pdo[POSITION_ACTUAL_VALUE].raw

    def set_target_velocity(self, vel):
        """Set target velocity in device units."""
        self.pdo[TARGET_VELOCITY].raw = vel

    def get_actual_velocity(self):
        """Get actual velocity in device units."""
        return self.pdo[VELOCITY_ACTUAL_VALUE].raw

    def move_to(self,
            position: int,
            velocity: Optional[int] = None,
            acceleration: Optional[int] = None,
            immediately: bool = True,
        ):
        """Move to position. For OperationMode.PROFILED_POSITION.

        Args:
            position: Target position.
            velocity: Profile velocity (if any).
            acceleration: Profile acceleration / deceleration (if any).
            immediately: If True overwrite ongoing command.
        """
        self.logger.debug('move_to(%s, velocity=%s, acceleration=%s)', position, velocity, acceleration)
        self.sdo[CONTROLWORD].raw = Command.ENABLE_OPERATION
        self.sdo[TARGET_POSITION].raw = position
        if velocity is not None:
            self.sdo[PROFILE_VELOCITY].raw = velocity

        if acceleration is not None:
            self.sdo[PROFILE_ACCELERATION].raw = acceleration
            self.sdo[PROFILE_DECELERATION].raw = acceleration

        if immediately:
            self.sdo[CONTROLWORD].raw = Command.ENABLE_OPERATION | CW.NEW_SET_POINT | CW.CHANGE_SET_IMMEDIATELY
        else:
            self.sdo[CONTROLWORD].raw = Command.ENABLE_OPERATION | CW.NEW_SET_POINT

    def move_with(self,
            velocity: int,
            acceleration: Optional[int] = None,
            immediately: bool = True,
        ):
        """Move with velocity. For OperationMode.PROFILE_VELOCITY.

        Args:
            velocity: Target velocity.
            acceleration: Profile acceleration / deceleration (if any).
            immediately: If True overwrite ongoing command.
        """
        self.logger.debug('move_with(%s, acceleration=%s)', velocity, acceleration)
        self.sdo[CONTROLWORD].raw = Command.ENABLE_OPERATION
        self.sdo[PROFILE_VELOCITY].raw = velocity
        if acceleration is not None:
            self.sdo[PROFILE_ACCELERATION].raw = acceleration
            self.sdo[PROFILE_DECELERATION].raw = acceleration

        if immediately:
            self.sdo[CONTROLWORD].raw = Command.ENABLE_OPERATION | CW.NEW_SET_POINT | CW.CHANGE_SET_IMMEDIATELY
        else:
            self.sdo[CONTROLWORD].raw = Command.ENABLE_OPERATION | CW.NEW_SET_POINT

    def _get_info(self) -> dict:
        """Get the current states."""
        return {
            'nmt': self.nmt.state,
            'state': self.get_state(),
            'op': self.get_operation_mode(),
        }

    def manufacturer_device_name(self):
        """Get manufacturer device name."""
        return self.sdo[MANUFACTURER_DEVICE_NAME].raw

    def apply_settings(self, settings: Dict[str, Any]):
        """Apply settings to CANopen node.

        Args:
            settings: Settings to apply. Addresses (path syntax) -> value
                entries.
        """
        for name, value in settings.items():
            *path, last = map(maybe_int, name.split('/'))
            sdo = self.sdo
            for key in path:
                sdo = sdo[key]

            self.logger.debug('Applying %r = %s', name, value)
            sdo[last].raw = value

    def __str__(self):
        return f'{type(self).__name__}(id: {self.id})'
