#!/usr/local/python3
"""Slow Sine movement on the motors."""
from being.awakening import awake
from being.blocks import Sawtooth, Trafo
from being.motors import RotaryMotor
from being.resources import manage_resources
from being.constants import TAU
from being.logging import setup_logging


# Params
MOTOR_IDS = [1]
FREQUENCY = 0.5

setup_logging()

with manage_resources():
    saw = Sawtooth(FREQUENCY)
    trafo = Trafo.from_ranges(inRange=[0, TAU], outRange=[0, 5.3 * 2048])  # radians to increments
    saw | trafo
    for nodeId in MOTOR_IDS:
        mot = RotaryMotor(nodeId)
        trafo | mot

    awake(saw)
