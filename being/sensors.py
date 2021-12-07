"""All things sensor."""
import collections
from typing import NamedTuple, Optional

from being.backends import Rpi
from being.block import Block
from being.clock import Clock
from being.resources import register_resource
from being.rpi_gpio import GPIO


class SensorEvent(NamedTuple):

    """Sensor event message."""

    channel: int
    """Channel over witch event was detected."""

    timestamp: float
    """Timestamp of sensor event."""


class Sensor(Block):

    """Sensor block base class."""


class SensorGpio(Sensor):

    """Raspberry Pi GPIO sensor block."""

    def __init__(self,
            channel: int,
            edge=GPIO.RISING,
            pull_up_down=GPIO.PUD_DOWN,
            bouncetime: float = 0.01,
            rpi: Optional[Rpi] = None,
            **kwargs,
        ):
        """Arguments according to RPi.GPIO.

        Args:
            channel: Raspberry PI GPIO number.
            edge (optional): Rising or falling edge.
            pull_up_down (optional): Pull up termination or not.
            bouncetime (optional): Edge detection bounce time in seconds.
            rpi (optional): Raspberry PI backend (DI).
            **kwargs: Arbitrary block keyword arguments.
        """
        super().__init__(**kwargs)
        self.add_message_output()

        if rpi is None:
            rpi = Rpi.single_instance_setdefault()
            register_resource(rpi, duplicates=False)

        self.channel = channel
        self.clock = Clock.single_instance_setdefault()
        rpi.gpio.setup(self.channel, GPIO.IN, pull_up_down=pull_up_down)
        rpi.gpio.add_event_detect(
            self.channel,
            edge,
            callback=self.callback,
            bouncetime=int(1000 * bouncetime),
        )
        self.queue = collections.deque(maxlen=50)

    def callback(self, channel):
        now = self.clock.now()
        evt = SensorEvent(channel, now)
        self.queue.append(evt)

    def update(self):
        while self.queue:
            evt = self.queue.popleft()
            self.output.send(evt)
