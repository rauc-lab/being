from typing import Iterable
try:
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping
import canopen
from canopen.node.base import BaseNode
from canopen.pdo import PdoBase, Map
from canopen.nmt import NmtMaster
from canopen.emcy import EmcyConsumer
from canopen.sdo import SdoClient
from .cia_402 import *


class Maps(Mapping):
    def __init__(self):
        self.maps: Dict[int, "Map"] = {}

    def __getitem__(self, key: int) -> "Map":
        return self.maps[key]

    def __iter__(self) -> Iterable[int]:
        return iter(self.maps)

    def __len__(self) -> int:
        return len(self.maps)


class TPDONoMap(PdoBase):
    """Transmit PDO to broadcast data from the represented node to the network.

    Properties 0x1800 to 0x1803 | Mapping 0x1A00 to 0x1A03.
    :param object node: Parent node for this object.
    """

    def __init__(self, node):
        super(TPDONoMap, self).__init__(node)
        self.map = Maps()
        # self.map = Maps(0x1800, 0x1A00, self, 0x180)
        # logger.debug('TPDO Map as {0}'.format(len(self.map)))

    def stop(self):
        """Stop transmission of all TPDOs.

        :raise TypeError: Exception is thrown if the node associated with the PDO does not
        support this function.
        """
        if isinstance(self.node, canopen.LocalNode):
            for pdo in self.map.values():
                pdo.stop()
        else:
            raise TypeError('The node type does not support this function.')


class RPDONoMap(PdoBase):
    """Receive PDO to transfer data from somewhere to the represented node.

    Properties 0x1400 to 0x1403 | Mapping 0x1600 to 0x1603.
    :param object node: Parent node for this object.
    """

    def __init__(self, node):
        super(RPDONoMap, self).__init__(node)
        self.map = Maps()
        # self.map = Maps(0x1400, 0x1600, self, 0x200)
        # logger.debug('RPDO Map as {0}'.format(len(self.map)))

    def stop(self):
        """Stop transmission of all RPDOs.

        :raise TypeError: Exception is thrown if the node associated with the PDO does not
        support this function.
        """
        if isinstance(self.node, canopen.RemoteNode):
            for pdo in self.map.values():
                pdo.stop()
        else:
            raise TypeError('The node type does not support this function.')


class StepperCiA402Node(BaseNode):
    def __init__(self, nodeId: int, objectDictionary: ObjectDictionary, network: CanBackend):
        super().__init__(nodeId, objectDictionary)
        self.logger = get_logger(str(self))

        network.send_message(0, bytes([0x01, self.id]))

        self.sdo_channels = []
        self.sdo = self.add_sdo(0x600 + self.id, 0x580 + self.id)
        self.tpdo = TPDONoMap(self)
        self.rpdo = RPDONoMap(self)
        self.nmt = NmtMaster(self.id)
        self.emcy = EmcyConsumer()

        network.add_node(self, objectDictionary)

        rx = Map(self.rpdo, self.sdo[0x1401], 0)
        # rx.read()
        rx.cob_id = 0x200 + nodeId
        # rx.predefined_cob_id = 0x200 + nodeId
        rx.add_variable(CONTROLWORD)
        rx.add_variable(TARGET_POSITION)
        rx.enabled = True
        rx.trans_type = TransmissionType.SYNCHRONOUS_CYCLIC
        # rx.save()
        rx.subscribe()
        network.register_rpdo(rx)
        self.rpdo.map.maps[1] = rx

        tx = Map(self.tpdo, self.sdo[0x1800], 0)
        tx.cob_id = 0x180 + nodeId
        tx.add_variable(STATUSWORD)
        tx.enabled = True
        tx.trans_type = TransmissionType.ASYNCHRONOUS
        # tx.save()
        tx.subscribe()
        self.tpdo.map.maps[1] = tx

        self.associate_network(network)
        print(self._get_info())

    def associate_network(self, network):
        self.network = network
        self.sdo.network = network
        self.tpdo.network = network
        self.rpdo.network = network
        self.nmt.network = network
        for sdo in self.sdo_channels:
            network.subscribe(sdo.tx_cobid, sdo.on_response)
        network.subscribe(0x700 + self.id, self.nmt.on_heartbeat)
        network.subscribe(0x80 + self.id, self.emcy.on_emcy)
        network.subscribe(0, self.nmt.on_command)

    def add_sdo(self, rx_cobid, tx_cobid):
        """Add an additional SDO channel.

        The SDO client will be added to :attr:`sdo_channels`.

        :param int rx_cobid:
            COB-ID that the server receives on
        :param int tx_cobid:
            COB-ID that the server responds with

        :return: The SDO client created
        :rtype: canopen.sdo.SdoClient
        """
        client = SdoClient(rx_cobid, tx_cobid, self.object_dictionary)
        self.sdo_channels.append(client)
        if self.network is not None:
            self.network.subscribe(client.tx_cobid, client.on_response)
        return client

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
        return OperationMode(self.sdo[MODES_OF_OPERATION].raw)

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

        sdm = {OperationMode.PROFILE_POSITION,
               OperationMode.PROFILE_VELOCITY,
               OperationMode.HOMING}
        if op not in sdm:
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
        # print(pos)
        # print(self.tpdo[STATUSWORD].raw)
        # self.rpdo[TARGET_POSITION].raw = pos * 10
        # network.send_message(0, bytes([0x01, self.id]))
        self.sdo[CONTROLWORD].raw = Command.ENABLE_OPERATION | CW.NEW_SET_POINT
        self.sdo[TARGET_POSITION].raw = int(pos * 1000)
        # print(self.nmt.state)

    def get_actual_position(self):
        """Get actual position in device units."""
        return self.sdo[POSITION_ACTUAL_VALUE].raw

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
        return 'PathosStepper'

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
