from being.configuration import CONFIG
from being.utils import SingleInstanceCache


INTERVAL = CONFIG['General']['INTERVAL']


class Clock(SingleInstanceCache):

    """Clock giver.

    Note that we count up an integer and multiply it with the interval duration.
    This is for better precision and less jitter due to floating point
    arithmetics. Pure Python integers are unbounded.
    """

    def __init__(self, interval: float = INTERVAL):
        """Kwargs:
            interval: Interval time.
        """
        self.interval = interval
        self.counter = 0

    def now(self) -> float:
        """Current timestamp."""
        return self.counter * self.interval

    def step(self):
        """Step clock further by one step."""
        self.counter += 1
