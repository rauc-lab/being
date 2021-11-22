import unittest
import logging

from being.can.cia_402 import (
    Command, State, find_shortest_state_path, CiA402Node, STATUSWORD_2_STATE,
    STATUSWORD, CONTROLWORD, TRANSITION_COMMANDS
)


STATE_2_STATUSWORD = {
    state: mask & value
    for mask, value, state in STATUSWORD_2_STATE
}


def which_statusword(state: State) -> int:
    """Produce statusword value for a given state."""
    return STATE_2_STATUSWORD[state]


class DummyVariable:

    """Placeholder proxy for canopen Variable."""
    def __init__(self, node):
        self.node = node

    @property
    def raw(self):
        return self.node.read_callback(self)

    @raw.setter
    def raw(self, value):
        self.node.write_callback(self, value)


class DummyNode(CiA402Node):

    """Dummy node for testing state switching logic."""

    def __init__(self, initialState=State.SWITCH_ON_DISABLED, cyclesNeeded=0):
        self.cyclesNeeded = cyclesNeeded
        self._statusword = DummyVariable(node=self)
        self._controlword = DummyVariable(node=self)
        self.state = initialState
        self._stateSwitching = None
        self.logger = logging.getLogger('dummy')


    def read_callback(self, who):
        if who is self._statusword:
            self.tick()
            return which_statusword(self.state)

    def write_callback(self, who, value):
        if who is self._controlword:
            for (src, dst), command in TRANSITION_COMMANDS.items():
                if src == self.state and command == value:
                    break
            else:
                raise RuntimeError

            if src is dst:
                return

            n = max(0, self.cyclesNeeded - 1)
            self._stateSwitching = iter( n * [self.state] + [dst])

    def tick(self):
        if self._stateSwitching:
            try:
                self.state = next(self._stateSwitching)
            except StopIteration:
                self._stateSwitching = None

    def __getattr__(self, name):
        if name in ('sdo', 'pdo'):
            return self

    def __getitem__(self, item):
        if item == STATUSWORD:
            return self._statusword

        if item == CONTROLWORD:
            return self._controlword


class TestCommand(unittest.TestCase):
    def test_well_known_commands_are_valid(self):
        self.assertEqual(Command.SHUT_DOWN, 0b110)
        self.assertEqual(Command.SWITCH_ON, 0b111)
        self.assertEqual(Command.DISABLE_VOLTAGE, 0)
        self.assertEqual(Command.QUICK_STOP, 0b10)
        self.assertEqual(Command.DISABLE_OPERATION, 0b111)
        self.assertEqual(Command.ENABLE_OPERATION, 0b1111)
        self.assertEqual(Command.FAULT_RESET, (1 << 7))


class TestStateSwitching(unittest.TestCase):
    def test_shortest_path_from_state_to_itself_is_empty(self):
        for state in State:
            self.assertEqual(find_shortest_state_path(start=state, end=state), [])

    def test_enabling_traverses_all_intermediate_states(self):
        path = find_shortest_state_path(State.SWITCH_ON_DISABLED, State.OPERATION_ENABLED)

        self.assertEqual(path, [
            State.SWITCH_ON_DISABLED, State.READY_TO_SWITCH_ON, State.SWITCHED_ON, State.OPERATION_ENABLED,
        ])

    def test_disabling_can_happend_in_one_step(self):
        path = find_shortest_state_path(State.OPERATION_ENABLED, State.SWITCH_ON_DISABLED)

        self.assertEqual(path, [
            State.OPERATION_ENABLED, State.SWITCH_ON_DISABLED
        ])


class TestCiA402Node(unittest.TestCase):
    def test_get_state_returns_correct_states_for_sdo_and_pdo(self):
        node = DummyNode()
        states = [
            #State.START,
            State.NOT_READY_TO_SWITCH_ON,
            State.SWITCH_ON_DISABLED,
            State.READY_TO_SWITCH_ON,
            State.SWITCHED_ON,
            State.OPERATION_ENABLED,
            State.QUICK_STOP_ACTIVE,
            State.FAULT_REACTION_ACTIVE,
            State.FAULT,
            #State.HALT,
        ]
        for state in states:
            node.state = state
            for how in ['sdo', 'pdo']:
                self.assertEqual(node.get_state(how), state)

    def test_impossible_state_transitions_error(self):
        node = DummyNode(State.SWITCH_ON_DISABLED)

        with self.assertRaises(RuntimeError):
            node.set_state(State.OPERATION_ENABLED)

    def test_current_is_target_yields_only_once(self):
        node = DummyNode(State.SWITCH_ON_DISABLED, cyclesNeeded=3)

        alreadyThere = node.change_state(State.SWITCH_ON_DISABLED)

        self.assertEqual(alreadyThere, State.SWITCH_ON_DISABLED)

        job = node.state_switching_job(State.SWITCH_ON_DISABLED)

        self.assertEqual(list(job), [State.SWITCH_ON_DISABLED])

    def test_transitioning_to_neighboring_state(self):
        node = DummyNode(State.SWITCH_ON_DISABLED, cyclesNeeded=3)
        job = node.state_switching_job(State.READY_TO_SWITCH_ON)

        self.assertEqual(list(job), 3*[State.SWITCH_ON_DISABLED] + [State.READY_TO_SWITCH_ON])

    def test_longer_path(self):
        node = DummyNode(State.SWITCH_ON_DISABLED, cyclesNeeded=3)
        job = node.state_switching_job(State.OPERATION_ENABLED)

        self.assertEqual(list(job),
            3 * [State.SWITCH_ON_DISABLED]
            + 3 * [State.READY_TO_SWITCH_ON]
            + 3 * [State.SWITCHED_ON]
            + [State.OPERATION_ENABLED]
        )


if __name__ == '__main__':
    unittest.main()
