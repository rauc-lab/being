#!/usr/local/python3
"""Slow Sine movement on the motors."""
from being.awakening import awake
from being.blocks import Sawtooth, Trafo
from being.motors import RotaryMotor
from being.resources import manage_resources


# Params
MOTOR_IDS = [1]
FREQUENCY = .05


with manage_resources():
    saw = Sawtooth(FREQUENCY)
    for nodeId in MOTOR_IDS:
        mot = RotaryMotor(nodeId)
        saw | mot

    awake(saw)
