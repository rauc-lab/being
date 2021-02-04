from being.config import INTERVAL
from being.utils import SingleInstanceCache


class Clock(SingleInstanceCache):
    def __init__(self, startTime=0):
        self.time = startTime

    def now(self):
        return self.time

    def step(self, dt=INTERVAL):
        self.time += dt