from being.being import awake
from being.motion_player import MotionPlayer
from being.motor import DummyMotor

blocks = [
    MotionPlayer() | DummyMotor(),
    MotionPlayer() | DummyMotor(),
]

awake(*blocks)
