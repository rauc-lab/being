try:
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping

from canopen.pdo import Map, PDO, TPDO, RPDO
from canopen.pdo.base import Maps
from canopen.nmt import NmtMaster
from canopen.emcy import EmcyConsumer
from canopen import ObjectDictionary, RemoteNode

from being.backends import CanBackend
from being.can.nmt import OPERATIONAL
from being.can.definitions import TransmissionType
from being.logging import get_logger
from .cia402_definitions import *
from .cia_402 import CiA402Node


class MapsSimplified(Maps):
    def __init__(self):
        super(Mapping, self).__init__()
        self.maps: Dict[int, "Map"] = {}


class TPDOSimplified(TPDO):
    def __init__(self, node):
        super(TPDO, self).__init__(node)
        self.map = MapsSimplified()


class RPDOSimplified(RPDO):
    def __init__(self, node):
        super(RPDO, self).__init__(node)
        self.map = MapsSimplified()


class StepperCiA402Node(CiA402Node):
    # device constants:
    _max_current = 0.88  # [A]
    _vsense_current_ratio = 0.55  # [-]
    # as per reference manual of TMC2208, for best microstep performance,
    # cs for Irun should be between 16 and 31, so set 16 as threshold below
    # which vsense is set to 1 to still achieve higher cs for low current
    # limits
    _vsense_cs_switch_limit = 16  # [-]

    supported_operation_modes = {
        OperationMode.PROFILE_POSITION,
        OperationMode.PROFILE_VELOCITY,
        OperationMode.HOMING
    }

    def __init__(self, nodeId: int, objectDictionary: ObjectDictionary, network: CanBackend):
        # use only __init__() of BaseNode
        super(RemoteNode, self).__init__(nodeId, objectDictionary)

        self.logger = get_logger(str(self))

        self.sdo_channels = []
        self.sdo = self.add_sdo(0x600 + self.id, 0x580 + self.id)
        self.tpdo = TPDOSimplified(self)
        self.rpdo = RPDOSimplified(self)
        self.pdo = PDO(self, self.rpdo, self.tpdo)
        self.nmt = NmtMaster(self.id)
        self.emcy = EmcyConsumer()
        network.add_node(self, objectDictionary)
        self.associate_network(network)
        self.nmt.state = OPERATIONAL

        rx = Map(self.rpdo, self.sdo[0x1401], 0)
        rx.cob_id = 0x300 + nodeId
        rx.add_variable(CONTROLWORD)
        rx.add_variable(TARGET_POSITION)
        rx.enabled = True
        rx.trans_type = TransmissionType.SYNCHRONOUS_CYCLIC
        rx.subscribe()
        network.register_rpdo(rx)
        self.rpdo.map.maps[2] = rx

        tx = Map(self.tpdo, self.sdo[0x1800], 0)
        tx.cob_id = 0x180 + nodeId
        tx.add_variable(STATUSWORD)
        tx.enabled = True
        tx.trans_type = TransmissionType.ASYNCHRONOUS
        tx.subscribe()
        self.tpdo.map.maps[1] = tx

        # FIXME: motor-dependent
        ihold_delay = 1
        mres = 7
        polarity = 0
        tpower_down = 20

        self.sdo['Drive Settings']['i_hold_delay'].write(ihold_delay)
        self.sdo['Chop Settings']['chop_conf_mres'].write(mres)
        self.sdo['polarity'].write(polarity)
        self.sdo['Drive Settings']['t_power_down'].write(tpower_down)

        self.rad_per_full_step_ = 0.130899693899574718269

        self.pos_si2dev = (2.0 ** (8.0 - mres)) / self.rad_per_full_step_
        # vel and acc conversion factors are identical
        self.vel_si2dev = self.pos_si2dev
        self.acc_si2dev = self.pos_si2dev

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

        if op not in self.supported_operation_modes:
            raise RuntimeError(f'This drive does not support {op!r}!')

        self.sdo[MODES_OF_OPERATION].raw = op

    def set_target_position(self, pos):
        """Set target position in device units."""
        # FIXME
        self.rpdo[TARGET_POSITION].raw = pos * self.pos_si2dev
        self.rpdo[CONTROLWORD].write(Command.ENABLE_OPERATION | CW.NEW_SET_POINT)
        self.sdo[CONTROLWORD].write(Command.ENABLE_OPERATION)

    def get_actual_position(self):
        """Get actual position in device units."""
        return self.sdo[POSITION_ACTUAL_VALUE].raw / self.pos_si2dev

    def manufacturer_device_name(self):
        """Get manufacturer device name."""
        return 'PathosStepper'

    def set_currents(self, irun: float, ihold: float):
        """
        Sets current scalers for run and hold RMS current, automatically
        adjusting vsense to result in well-microstepping behavior according to
        TMC reference manual (CS >= 16 for good behavior).

        The method enforces a 0.2A lower limit on the run current as
        recommended by the TMC manual for use with internal sense resistors.

        Args:
            irun:
                run current in [A]. Min 0.2A enforced.
            ihold:
                hold current in [A].

        Raises:
            ValueError:
                - if irun > max. current

        Note:
            - CS run >= CS hold is enforced automatically
        """

        # enforce max current:
        if irun > self._max_current:
            raise ValueError('irun exceeds max current')

        # enforce min. run current:
        if irun < 0.2:
            irun = 0.2

        # first calculate the CS for vsense = 0:
        vsense = 0
        csrun = int(round((irun / self._max_current * 32.0))) - 1
        cshold = int(round((ihold / self._max_current * 32.0))) - 1

        if csrun < self._vsense_cs_switch_limit:
            vsense = 1
            csrun = int(
                round((irun / (self._max_current * self._vsense_current_ratio)
                       * 32.0))) - 1
            cshold = int(
                round((ihold / (self._max_current * self._vsense_current_ratio)
                       * 32.0))) - 1

        # enforce minimum of hold current
        if cshold < 0:
            cshold = 0

        # enforce cshold <= csrun
        if cshold > csrun:
            cshold = csrun

        # now set it all:
        self.sdo['Chop Settings']['chop_conf_vsense'].write(vsense)
        self.sdo['Drive Settings']['i_run'].write(csrun)
        self.sdo['Drive Settings']['i_hold'].write(cshold)
