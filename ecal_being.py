#!/usr/local/python3
"""Being for ECAL workshop May 2021."""
from being.behavior import Behavior
from being.being import awake
from being.motion_player import MotionPlayer
from being.motor import Motor
from being.resources import manage_resources
from being.sensors import SensorGpio


with manage_resources():
    # Initialize being blocks
    sensor = SensorGpio(channel=6)
    behavior = Behavior.from_config('behavior.json')
    mp = MotionPlayer()
    motor0 = Motor(nodeId=9, length=0.100)
    motor1 = Motor(nodeId=8, length=0.100)

    # Make block connections
    sensor.output.connect(behavior.input)
    behavior.associate(mp)
    mp.output.connect(motor0.input)
    mp.output.connect(motor1.input)
    awake(behavior)
