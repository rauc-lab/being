#!/usr/local/python3
"""Being for ECAL workshop May 2021."""
from being.behavior import Behavior
from being.being import awake
from being.logging import setup_logging
from being.motion_player import MotionPlayer
from being.motor import LinearMotor
from being.resources import manage_resources
from being.sensors import SensorGpio


NODE_IDS = [23, 24]
"""Motor ids to use."""


def look_for_motors():
    """Look which motors for NODE_IDS are available."""
    for nodeId in NODE_IDS:
        try:
            yield LinearMotor(nodeId, length=0.100)
        except RuntimeError:
            pass


setup_logging()


with manage_resources():
    # Initialize being blocks
    motors = list(look_for_motors())
    if not motors:
        raise RuntimeError('Found no motors!')

    sensor = SensorGpio(channel=6)
    behavior = Behavior.from_config('behavior.json')
    mp = MotionPlayer(ndim=len(motors))

    # Make block connections
    sensor.output.connect(behavior.input)
    behavior.associate(mp)

    for output, motor in zip(mp.positionOutputs, motors):
        output.connect(motor.input)

    awake(behavior)
