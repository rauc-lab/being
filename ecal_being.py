#!/usr/local/python3
"""Being for ECAL workshop May 2021."""
from being.behavior import Behavior
from being.awakening import awake
from being.logging import setup_logging, suppress_other_loggers
from being.motion_player import MotionPlayer
from being.motors import LinearMotor, RotaryMotor
from being.resources import manage_resources
from being.sensors import SensorGpio


NODE_IDS = [1, 2]
"""Motor ids to use."""


def look_for_motors():
    """Look which motors for NODE_IDS are available."""
    for nodeId in NODE_IDS:
        try:
            yield LinearMotor(nodeId, length=0.100)
        except RuntimeError:
            pass


#setup_logging()
#suppress_other_loggers()
#logging.basicConfig(level=0)


with manage_resources():
    # Initialize being blocks
    motors = list(look_for_motors())
    if not motors:
        raise RuntimeError('Found no motors!')

    sensor = SensorGpio(channel=6)
    behavior = Behavior.from_config('behavior.json')
    motionPlayer = MotionPlayer(ndim=len(motors))

    # Make block connections
    sensor | behavior | motionPlayer

    for output, motor in zip(motionPlayer.positionOutputs, motors):
        output.connect(motor.input)

    awake(behavior)
