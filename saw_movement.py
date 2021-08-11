#!/usr/local/python3
"""Slow Sine movement on the motors."""
import logging

from being.awakening import awake
from being.blocks import Sawtooth, Trafo
from being.motors import RotaryMotor
from being.resources import manage_resources
from being.constants import TAU
from being.logging import setup_logging
from being.constants import BACKWARD, FORWARD
from being.motors.motor_paramters import DCmax22S_GB_KL_12V as DCmax22
from being.motors.motor_paramters import EC45_469292_24V as EC45


# Params
MOTOR_IDS = [1]
FREQUENCY = 0.5

setup_logging(level=logging.WARNING)

with manage_resources():
    saw = Sawtooth(FREQUENCY)

    for nodeId in MOTOR_IDS:
        mot = RotaryMotor(nodeId,  direction=FORWARD, motor=EC45, maxSpeed=500)
        mot.configure_node(encoderNumberOfPulses=2048, encoderHasIndex=False)
        saw | mot

    awake(saw)
