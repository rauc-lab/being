from being.awakening import awake
from being.motion_player import MotionPlayer
from being.motors import LinearMotor
from being.resources import manage_resources


ROD_LENGTH = 0.04


with manage_resources():
    motor = LinearMotor(nodeId=8, length=ROD_LENGTH)
    mp = MotionPlayer()
    awake(mp | motor)
