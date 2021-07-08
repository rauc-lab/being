#!/usr/local/python3
"""Slow Sine movement on the motors."""
from being.being import awake
from being.blocks import Sine, Trafo
from being.motors import LinearMotor
from being.resources import manage_resources


# Params
MOTOR_IDS = [8, 9]
ROD_LENGTH = .1
FREQUENCY = .05


with manage_resources():
    sine = Sine(FREQUENCY)
    trafo = Trafo.from_ranges(inRange=[-1, 1.], outRange=[0, ROD_LENGTH])
    sine | trafo
    trafo.scale /= 2
    for nodeId in MOTOR_IDS:
        mot = LinearMotor(nodeId, length=ROD_LENGTH)
        trafo | mot

    awake(sine)
