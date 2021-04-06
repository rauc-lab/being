import time
import logging

from being.being import awake
from being.behavior import Behavior
from being.motion_player import MotionPlayer
from being.motor import DummyMotor, Motor
from being.block import Block
from being.logging import suppress_other_loggers


logging.basicConfig(level=0)
suppress_other_loggers()


class DummySensor(Block):
    def __init__(self):
        super().__init__()
        self.add_message_output()
        self.interval = 5;
        self.nextUpd = -1

    def update(self):
        now = time.perf_counter()
        if now < self.nextUpd:
            return

        self.nextUpd = now + self.interval
        self.output.send('But hey')


sensor = DummySensor()
behavior = Behavior()
mp = MotionPlayer()
behavior.associate(mp)
mp | DummyMotor()

#behavior.input.push('asdf')
sensor | behavior

awake(behavior)
