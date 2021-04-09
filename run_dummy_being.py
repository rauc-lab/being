import time
import logging

from being.behavior import Behavior
from being.being import awake
from being.logging import suppress_other_loggers
from being.motion_player import MotionPlayer
from being.motor import DummyMotor
from being.sensors import Sensor


logging.basicConfig(level=0)
suppress_other_loggers()


class DummySensor(Sensor):
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
behavior = Behavior.from_config('behavior.json')
mp = MotionPlayer()
behavior.associate(mp)
mp | DummyMotor()
sensor | behavior
awake(behavior)
