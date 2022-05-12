import logging

from being.awakening import awake
from being.behavior import Behavior
from being.logging import suppress_other_loggers, setup_logging
from being.motion_player import MotionPlayer
from being.motors import DummyMotor
from being.resources import manage_resources
from being.sensors import DummySensor

#logging.basicConfig(level=logging.DEBUG)
#setup_logging(level=logging.DEBUG)


with manage_resources():
    sensor = DummySensor()
    behavior = Behavior.from_config('dummy_behavior.json')

    head = MotionPlayer(ndim=1, name='Head')
    head.positionOutputs[0].connect(DummyMotor(name='Neck').input)

    arm = MotionPlayer(ndim=2, name='Arm')
    arm.positionOutputs[0].connect(DummyMotor(name='Elbow').input)
    arm.positionOutputs[1].connect(DummyMotor(name='Wrist').input)

    awake(sensor | behavior | arm, head)
