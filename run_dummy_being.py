import time
import logging

from being.behavior import Behavior
from being.awakening import awake
from being.logging import setup_logging
from being.logging import suppress_other_loggers
from being.motion_player import MotionPlayer
from being.motors import DummyMotor
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
    #sensor = DummySensor()
    #behavior = Behavior.from_config('behavior.json')
    #sensor | behavior

    head = MotionPlayer(ndim=1, name='Head')
    head.positionOutputs[0].connect(DummyMotor(name='Head Motor').input)
    arm = MotionPlayer(ndim=2, name='Arm')
    arm.positionOutputs[0].connect(DummyMotor(name='Elbow').input)
    arm.positionOutputs[1].connect(DummyMotor(name='Wrist').input)
    awake(head, arm)
