#!/usr/local/python3
"""Slow Sine movement on the motors."""
from being.awakening import awake
from being.blocks import Sawtooth, Trafo
from being.motors import RotaryMotor
from being.resources import manage_resources
from being.constants import TAU
from being.logging import setup_logging
from being.motion_player import MotionPlayer
from being.constants import BACKWARD, FORWARD
import logging


# Params
MOTOR_IDS = [1]
FREQUENCY = 0.5

setup_logging(level=logging.WARNING)

def look_for_motors():
    """Look which motors for NODE_IDS are available."""
    for nodeId in MOTOR_IDS:
        try:
            yield RotaryMotor(nodeId, gearNumerator=69, gearDenumerator=13, direction=FORWARD)
        except RuntimeError:
            pass


with manage_resources():
    saw = Sawtooth(FREQUENCY)

    motors = list(look_for_motors())
    mp = MotionPlayer(ndim=len(motors))
    # for mot in motors:
        # saw | mot

    for output, motor in zip(mp.positionOutputs, motors):
        output.connect(motor.input)

    awake(mp)
