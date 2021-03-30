import collections
from typing import NamedTuple

from being.backends import Rpi
from being.block import Block
from being.clock import Clock
from being.resources import register_resource
from being.rpi_gpio import GPIO


class SensorEvent(NamedTuple):
    channel: int
    timestamp: float


class SensorGpio(Block):
    def __init__(self, channel, edge=GPIO.RISING, pull_up_down=GPIO.PUD_DOWN, bouncetime=.01, rpi=None):
        super().__init__()
        self.channel = channel
        if rpi is None:
            rpi = Rpi.single_instance_setdefault()
            register_resource(rpi, duplicates=False)

        self.clock = Clock.single_instance_setdefault()
        self.add_message_output()
        rpi.gpio.setup(self.channel, GPIO.IN, pull_up_down=pull_up_down)
        rpi.gpio.add_event_detect(self.channel, edge, callback=self.callback, bouncetime=1000*bouncetime)
        self.queue = collections.deque(maxlen=50)

    def callback(self, channel):
        now = self.clock.now()
        evt = SensorEvent(channel, now)
        self.queue.append(evt)

    def update(self):
        while self.queue:
            evt = self.queue.popleft()
            self.output.send(evt)

