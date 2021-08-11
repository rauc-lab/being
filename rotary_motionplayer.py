#!/usr/local/python3
"""Slow Sine movement on the motors."""
import logging

from being.awakening import awake
from being.blocks import Sawtooth, Trafo
from being.motors import RotaryMotor
from being.resources import manage_resources
from being.constants import TAU
from being.logging import setup_logging
from being.motion_player import MotionPlayer
from being.constants import BACKWARD, FORWARD
from being.motors.motor_paramters import EC45_469292_24V as EC45


# Params
MOTOR_IDS = [1]
FREQUENCY = 0.5

setup_logging(level=logging.WARNING)


def look_for_motors():
    """Look which motors for NODE_IDS are available."""
    for nodeId in MOTOR_IDS:
        try:
            yield RotaryMotor(nodeId,  direction=FORWARD, motor=EC45, maxSpeed=50, maxAcc=10)
        except RuntimeError:
            pass


with manage_resources():
    saw = Sawtooth(FREQUENCY)

    motors = list(look_for_motors())
    mp = MotionPlayer(ndim=len(motors))
    # for mot in motors:
        # saw | mot

    for output, motor in zip(mp.positionOutputs, motors):
        motor.configure_node(encoderNumberOfPulses=2048, encoderHasIndex=False)
        output.connect(motor.input)

    awake(mp)
