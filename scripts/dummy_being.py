"""Two motor dummy being."""
from being.awakening import awake
from being.behavior import Behavior
from being.motion_player import MotionPlayer
from being.motors import DummyMotor
from being.resources import manage_resources
from being.sensors import DummySensor


with manage_resources():
    sensor = DummySensor()
    behavior = Behavior()
    motionPlayer = MotionPlayer(ndim=2)

    motionPlayer.positionOutputs[0].connect(DummyMotor(name='Motor 1').input)
    motionPlayer.positionOutputs[1].connect(DummyMotor(name='Motor 2').input)

    awake(sensor | behavior | motionPlayer)
