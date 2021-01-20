"""Sine movement on the Faulhaber demo script."""
from being.being import awake
from being.blocks import Sine, Trafo
from being.motor import Motor
from being.resources import manage_resources


ROD_LENGTH = 0.04
"""Rod length of Faulhaber linear drive in meter."""


with manage_resources():
    motor = Motor(nodeId=8)
    sine = Sine(frequency=.1)
    trafo = Trafo(scale=.5 * ROD_LENGTH, offset=.5 * ROD_LENGTH)
    sine | trafo | motor
    awake(motor)
