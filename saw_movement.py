#!/usr/local/python3
"""Slow Sine movement on the motors."""
from being.awakening import awake
from being.blocks import Sawtooth, Trafo
from being.motors import RotaryMotor
from being.resources import manage_resources
from being.constants import TAU
from being.logging import setup_logging
from being.constants import BACKWARD, FORWARD
import logging


# Params
MOTOR_IDS = [1]
FREQUENCY = 0.5

setup_logging(level=logging.WARNING)

with manage_resources():
    saw = Sawtooth(FREQUENCY)

    for nodeId in MOTOR_IDS:
        mot = RotaryMotor(nodeId, gearNumerator=69, gearDenumerator=13, direction=FORWARD)
        saw | mot

    awake(saw)
