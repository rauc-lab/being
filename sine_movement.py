"""Sine movement on the Faulhaber demo script."""
import time
import math

from being.backends import CanBackend
from being.block import Block
from being.can.homing import home_drives
from being.connectables import ValueInput, ValueOutput
from being.constants import TAU
from being.kinematics import State
from being.motor import Motor, INTERVAL


ROD_LENGTH = 0.04
ERASE_LINE = '\33[2K'


def sleep_until_next_cycle():
    now = time.perf_counter()
    then = math.ceil(now / INTERVAL) * INTERVAL
    time.sleep(max(0, then - now))
    return then


def execute(execOrder):
    for block in execOrder:
        block.update()


class Sine(Block):
    def __init__(self, frequency=1., startPhase=0.):
        super().__init__()
        self.phase = startPhase
        self.frequency, = self.inputs = [ValueInput(owner=self)]
        self.outputs = [ValueOutput(owner=self)]
        self.frequency.value = frequency

    def update(self):
        self.output.value = math.sin(self.phase)
        self.phase += TAU * self.frequency.value * INTERVAL
        self.phase %= TAU


class Trafo(Block):
    def __init__(self, scale=1., offset=0.):
        super().__init__()
        self.scale = scale
        self.offset = offset
        self.inputs = [ValueInput(owner=self)]
        self.outputs = [ValueOutput(owner=self)]

    def update(self):
        self.output.value = self.scale * self.input.value + self.offset


if __name__ == '__main__':
    with CanBackend() as network:
        mot = Motor(8, network=network)
        sine = Sine(frequency=.1)
        trafo = Trafo(scale=.5*ROD_LENGTH, offset=.5*ROD_LENGTH)
        sine | trafo | mot

        with mot.node.restore_states_and_operation_mode():
            network.home_drives()
            network.enable_drives()
            execOrder = [sine, trafo, mot]

            mot.state = State(mot.node.position, 0, 0)

            try:
                print('Start running')
                network.send_sync()
                while True:
                    sleep_until_next_cycle()
                    execute(execOrder)
                    actualPos = mot.output.value
                    print('\r', ERASE_LINE, end='')
                    print('Actual Position: %.3f m' % actualPos, end='')
                    network.send_sync()

            except KeyboardInterrupt:
                pass
