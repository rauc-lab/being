import time
import logging

from being.behavior import Behavior
from being.being import awake
from being.logging import setup_logging
from being.logging import suppress_other_loggers
from being.motion_player import MotionPlayer
from being.motor import DummyMotor
from being.resources import manage_resources
from being.sensors import Sensor


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


#setup_logging(level=logging.DEBUG)


with manage_resources():
    sensor = DummySensor()
    behavior = Behavior.from_config('behavior.json')
    sensor | behavior
    mp = MotionPlayer(ndim=2)
    behavior.associate(mp)
    mp.outputs[0] | DummyMotor()
    mp.outputs[1] | DummyMotor()
    awake(behavior)
