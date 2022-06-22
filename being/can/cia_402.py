"""CiA 402 object dictionary addresses, definitions, state machine and
CiA402Node class.

CiA402Node is a trimmed down version of canopen.BaseNode402. We favor SDO
communication during setup but synchronous acyclic PDO communication during
operation. Also added support for
:class:`being.can.cia_402.OperationMode.CYCLIC_SYNCHRONOUS_POSITION`.
"""
import contextlib
import time
from typing import (
    Any,
    Optional,
)

from canopen import RemoteNode, ObjectDictionary

from being.backends import CanBackend
from being.can.cia_301 import MANUFACTURER_DEVICE_NAME
from being.can.definitions import TransmissionType
from being.logging import get_logger
from being.can.cia402_definitions import *


class CiA402Node(RemoteNode):

    """Remote CiA 402 node. Communicates with and controls remote drive. Default
    PDO configuration. State switching helpers. Controlword & statusword
    communication can happen via SDO or PDO (how argument, ``'sdo'`` and
    ``'pdo'``).

    Caution:
        Using SDO and PDO for state switching at the same time can lead to
        problems. E.g. only sending a command via SDO but not setting the same
        command in the PDO. The outdated PDO value will then interfere when send
        the next time.

    Hint:
        If the node is constantly in :attr:`State.NOT_READY_TO_SWITCH_ON`, this
        could indicate deactivated PDO communication. (Default statusword value
        in PDO is zero which maps to :attr:`State.NOT_READY_TO_SWITCH_ON`).

    Note:
        :mod:`canopen` also has a CiA 402 node implementation
        (:class:`canopen.profiles.p402.BaseNode402`).
        Implemented our own because we wanted more control over SDO / PDO
        communication and at the time of writing
        :attr:`OperationMode.CYCLIC_SYNCHRONOUS_POSITION` was not fully
        supported.
    """

    def __init__(self, nodeId: int, objectDictionary: ObjectDictionary, network: CanBackend):
        """
        Args:
            nodeId: CAN node id to connect to.
            objectDictionary: Object dictionary for the remote drive.
            network: Connected network. Mandatory for configuring PDOs during
                initialization.
        """

        super().__init__(nodeId, objectDictionary, load_od=False)
        self.logger = get_logger(str(self))

        network.add_node(self, objectDictionary)

        # Configure PDOs
        self.tpdo.read()
        self.rpdo.read()

        # Note: Default PDO mapping of some motors includes the Control- /
        # Statusword in multiple PDOs. This can lead to unexpected behavior with
        # our CANopen stack since for example:
        #
        #     node.rpdo['Controlword'] = Command.ENABLE_OPERATION
        #
        # will only set the value in the first PDO with the Controlword but not
        # for the others following. In these, the Controlword will stay zero and
        # subsequently shut down the motor.
        #
        # -> We clear all of them and have the Controlword only in the first RxPDO1.

        # EPOS4 has no PDO mapping for Error Register,
        # thus re-register later txpdo1 if available

        # FIXME: use unique COB-IDs which depend on the nodeID from the objectDictionary
        # (pdo.read() loads values from the nodes which by default are all same and conflict if n(nodes) > 1)

        self.setup_txpdo(1, STATUSWORD)
        self.setup_txpdo(2, POSITION_ACTUAL_VALUE, VELOCITY_ACTUAL_VALUE)
        self.setup_txpdo(3, enabled=False)
        self.setup_txpdo(4, enabled=False)

        self.setup_rxpdo(1, enabled=False)
        self.setup_rxpdo(2, TARGET_POSITION, TARGET_VELOCITY)
        self.setup_rxpdo(3, enabled=False)
        self.setup_rxpdo(4, enabled=False)

        network.register_rpdo(self.rpdo[2])

    def setup_txpdo(self,
            nr: int,
            *variables: CanOpenRegister,
            overwrite: bool = True,
            enabled: bool = True,
            trans_type: TransmissionType = TransmissionType.SYNCHRONOUS_CYCLIC,
            event_timer: Optional[int] = None,  # TODO: set to 100 or so for FH motors to reduce bus load
        ):
        """Setup single transmission PDO of node (receiving PDO messages from
        remote node). Note: Sending / receiving direction always from the remote
        nodes perspective. Setting `event_timer` to 0 can lead to KeyErrors on
        some controllers.

        Args:
            nr: TxPDO number (1-4).
            *variables: CANopen variables to register to receive from remote
                node via TxPDO.
            enabled: Enable or disable TxPDO.
            overwrite: Overwrite TxPDO.
            trans_type: Event based or synchronized transmission
            event_timer: Update period [ms]
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
            *variables: CANopen variables to register to send to remote node via
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
            how (optional): Which communication channel to use. Either via
                ``'sdo'`` or ``'pdo'``.  ``'sdo'`` by default.

        Returns:
            Current CiA 402 state.
        """
        if how == 'pdo':
            return which_state(self.tpdo[STATUSWORD].raw)  # This takes approx. 0.027 ms
        elif how == 'sdo':
            return which_state(self.sdo[STATUSWORD].raw)  # This takes approx. 2.713 ms
        else:
            raise ValueError(f'Unknown how {how!r}')

    def set_state(self, target: State, how: str = 'sdo'):
        """Set node to a new target state. Target state has to be reachable from
        node's current state. RuntimeError otherwise.

        Args:
            target: Target state to switch to.
            how (optional): Communication channel. ``'sdo'`` (default) or ``'pdo'``.
        """
        self.logger.debug('set_state(%s (how=%r))', target, how)
        if target in {State.NOT_READY_TO_SWITCH_ON, State.FAULT, State.FAULT_REACTION_ACTIVE}:
            self.logger.warning(f'Can not change to state {target}')
            return

        current = self.get_state(how)
        if current == target:
            return current

        edge = (current, target)
        if edge not in TRANSITION_COMMANDS:
            self.logger.warning(f'Invalid state transition from {current!r} to {target!r}!')
            return current

        cw = TRANSITION_COMMANDS[edge]
        if how == 'pdo':
            self.rpdo[CONTROLWORD].raw = cw
        elif how == 'sdo':
            self.sdo[CONTROLWORD].raw = cw
        else:
            raise ValueError(f'Unknown how {how!r}')

        return

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
            how (optional): Communication channel. ``'sdo'`` (default) or ``'pdo'``.
            timeout (optional): Optional timeout value in seconds. 1.0 second by default.

        Yields:
            Current states.
        """
        self.logger.debug('state_switching_job(%s, how=%r, timeout=%s)', target, how, timeout)
        endTime = time.perf_counter() + timeout
        initial = current = self.get_state(how)
        #self.logger.debug('initial: %s', initial)
        lastPlanned = None
        while True:
            yield current

            if current == target:
                self.logger.debug('Reached target %s', target)
                return

            #self.logger.debug('Still in %s (not in %s)', current.name, target.name)

            if time.perf_counter() > endTime:
                raise TimeoutError(f'Could not transition from {initial.name} to {target.name} in {timeout:.3f} sec!')

            if current != lastPlanned:
                lastPlanned = current
                intermediate = WHERE_TO_GO_NEXT[(current, target)]
                current = self.set_state(intermediate, how)
                if current is not None:
                    continue

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
            how (optional): Communication channel. ``'sdo'`` (default) or ``'pdo'``.
            timeout (optional): Optional timeout value in seconds. 1.0 second by default.

        Returns:
            Final state.
        """
        self.logger.debug('change_state(%s, how=%r, timeout=%s)', target, how, timeout)
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
        if current == op:
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
            how (optional): Communication channel. ``'sdo'`` (default) or ``'pdo'``.
            timeout (optional): Timeout duration.

        Example:
            >>> with node.restore_states_and_operation_mode():
            ...     # Do something fancy with the states
            ...     pass

        Warning:
            Deprecated. Led to more problems than it solved...
        """
        oldOp = self.get_operation_mode()
        oldState = self.get_state(how)

        yield self

        self.set_operation_mode(oldOp)
        self.change_state(oldState, how=how, timeout=timeout)

    def reset_fault(self):
        """Perform fault reset to SWITCH_ON_DISABLED."""
        self.logger.warning('Resetting fault')
        self.sdo[CONTROLWORD].raw = 0
        self.sdo[CONTROLWORD].raw = CW.FAULT_RESET

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
        self.rpdo[TARGET_POSITION].raw = pos

    def get_actual_position(self):
        """Get actual position in device units."""
        return self.tpdo[POSITION_ACTUAL_VALUE].raw

    def set_target_velocity(self, vel):
        """Set target velocity in device units."""
        self.rpdo[TARGET_VELOCITY].raw = vel

    def get_actual_velocity(self):
        """Get actual velocity in device units."""
        return self.tpdo[VELOCITY_ACTUAL_VALUE].raw

    def move_to(self,
            position: int,
            velocity: Optional[int] = None,
            acceleration: Optional[int] = None,
            immediately: bool = True,
        ):
        """Move to position. For :attr:`OperationMode.PROFILED_POSITION`.

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
        """Move with velocity. For :attr:`OperationMode.PROFILE_VELOCITY`.

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
        """Get the current drive information."""
        return {
            'nmt': self.nmt.state,
            'state': self.get_state(),
            'op': self.get_operation_mode(),
        }

    def manufacturer_device_name(self):
        """Get manufacturer device name."""
        return self.sdo[MANUFACTURER_DEVICE_NAME].raw

    def apply_settings(self, settings: Dict[str, Any]):
        """Apply multiple settings to CANopen node. Path syntax for nested
        entries but it is also possible to use numbers, bin and hex notation for
        path entries. E.g. ``someName/0x00`` (see :func:`maybe_int`).

        Args:
            settings: Settings to apply. Addresses (path syntax) -> value entries.

        Example:
            >>> settings = {
            ...     'Software Position Limit/Minimum Position Limit': 0,
            ...     'Software Position Limit/Maximum Position Limit': 10000,
            ... }
            ... node.apply_settings(settings)
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
