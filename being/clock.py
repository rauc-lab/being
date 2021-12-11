"""Being internal time giver. For a given main loop cycle the time should stay
constant and not depend on external factors (kind of rendering time).
"""
from being.configuration import CONFIG
from being.utils import SingleInstanceCache

# Look before you leap
INTERVAL = CONFIG['General']['INTERVAL']


class Clock(SingleInstanceCache):

    """Clock giver. Returns current timestamp and needs to be ticked during the
    main loop.

    Important:
        Needs to be ticked once (and only once) by the end of each cycle.

    Note:
        Uses an :obj:`int` internally to count up. Less jitter due to
        floating-point precision. Pure Python integers are unbounded so overflow
        is not an issue (see `Arbitrary-precision arithmetic <https://en.wikipedia.org/wiki/Arbitrary-precision_arithmetic>`_).
    """

    def __init__(self, interval: float = INTERVAL):
        """
        Args:
            interval (optional): Interval duration in seconds. Default is taken
                from :obj:`CONFIG` object from :mod:`being.configuration`.
        """
        self.interval = interval
        self.counter = 0

    def now(self) -> float:
        """Get current timestamp.

        Returns:
            Timestamp in seconds.
        """
        return self.counter * self.interval

    def step(self):
        """Step clock further by one step."""
        self.counter += 1
