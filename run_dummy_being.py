import time
import logging

from being.being import awake
from being.behavior import Behavior, Params
from being.motion_player import MotionPlayer
from being.motor import DummyMotor, Motor
from being.block import Block
from being.logging import suppress_other_loggers



MOTIONS = [
    'Untitled 1', 'Untitled', 'deep_uncertainty', 'peaceful_blue',
    'prove_pumped', 'pumped_highway', 'serious_peaceful',
    'uncertainty_uncertainty', 'unequaled_folklore', 'unequaled_serious',
    'uninterested_unequaled', 'unknown_deep',
]


logging.basicConfig(level=0)
suppress_other_loggers()


class DummySensor(Block):
    def __init__(self):
        super().__init__()
        self.add_message_output()
        self.interval = 10;
        self.nextUpd = -1

    def update(self):
        now = time.perf_counter()
        if now < self.nextUpd:
            return

        self.nextUpd = now + self.interval
        self.output.send('But hey')


sensor = DummySensor()
params = Params(2.5, MOTIONS, MOTIONS, MOTIONS)
behavior = Behavior(params)
mp = MotionPlayer()
behavior.associate(mp)
mp | DummyMotor()

#behavior.input.push('asdf')
sensor | behavior

awake(behavior)
