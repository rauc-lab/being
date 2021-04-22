#!/usr/local/python3
"""Being for ECAL workshop May 2021."""
from being.behavior import Behavior
from being.being import awake
from being.motion_player import MotionPlayer
from being.motor import Motor
from being.resources import manage_resources
from being.sensors import SensorGpio


NODE_IDS = [1, 2]
"""Motor ids to use."""


def add_motor(mp, motor):
    """Connect motor to free position output from motion player. Create new
    position output if necessary.
    """
    for output in mp.positionOutputs:
        if not output.connected:
            output.connect(motor.input)
            return

    mp.add_position_output()
    mp.positionOutputs[-1].connect(motor.input)


with manage_resources():
    # Initialize being blocks
    sensor = SensorGpio(channel=6)
    behavior = Behavior.from_config('behavior.json')
    mp = MotionPlayer()
    motors = []
    for nodeId in NODE_IDS:
        try:
            mot = Motor(nodeId, length=0.100)
            motors.append(mot)
        except RuntimeError:
            pass

    if len(motors) == 0:
        raise RuntimeError('Found no motors!')

    # Make block connections
    sensor.output.connect(behavior.input)
    behavior.associate(mp)

    for mot in motors:
        add_motor(mp, mot)

    awake(behavior)
