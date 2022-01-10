"""Sensor blocks."""
import collections
import time
from typing import NamedTuple, Optional

from being.backends import Rpi, AudioBackend
from being.block import Block
from being.clock import Clock
from being.resources import register_resource
from being.rpi_gpio import GPIO


class SensorEvent(NamedTuple):

    """Sensor event message."""

    timestamp: float
    """Timestamp of sensor event."""

    meta: dict
    """Additional informations."""


class Sensor(Block):

    """Sensor block base class."""


class DummySensor(Sensor):

    """Dummy sensor block for testing and standalone usage. Sends a dummy
    SensorEvent every `interval` seconds.
    """

    def __init__(self, interval: float = 5.0, **kwargs):
        """
        Args:
            interval: Message send interval in seconds.
            **kwargs: Arbitrary block keyword arguments.
        """
        super().__init__(**kwargs)
        self.add_message_output()
        self.interval: float = interval
        self.nextUpd = -1

    def update(self):
        now = time.perf_counter()
        if now < self.nextUpd:
            return

        self.nextUpd = now + self.interval
        evt = SensorEvent(timestamp=now, meta={
            'type': 'DummySensor',
        })
        self.output.send(evt)


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
        evt = SensorEvent(timestamp=now, meta={
            'type': 'RPi.GPIO',
            'channel': channel,
        })
        self.queue.append(evt)

    def update(self):
        while self.queue:
            evt = self.queue.popleft()
            self.output.send(evt)


class Mic(Sensor):

    """Listens to audio and emits sound event messages."""

    def __init__(self,
             threshold=0.01,
             bouncetime=0.1,
             audio: Optional[AudioBackend] = None,
             clock: Optional[Clock] = None,
             **kwargs,
        ):
        """
        Args:
            threshold: Spectral flux difference threshold.
            bouncetime: Blocked duration after emitted sound event.
            audio: Audio backend instance (DI).
            audio: Clock instance (DI).
        """
        if audio is None:
            audio = AudioBackend.single_instance_setdefault()
            register_resource(audio, duplicates=False)

        if clock is None:
            clock = Clock.single_instance_setdefault()

        super().__init__(**kwargs)
        self.add_message_output()
        self.threshold = threshold
        self.bouncetime = bouncetime
        self.clock = clock

        self.prevSf = 0.0
        self.blockedUntil = -1

        audio.subscribe_microphone(self)

    def new_spectral_flux_value(self, sf: float):
        """Process new spectral flux value and emit SoundEvent if necessary.

        Args:
            sf: Scalar spectral flux value.
        """
        diff = sf - self.prevSf
        self.prevSf = sf
        if diff < self.threshold:
            return

        now = self.clock.now()
        if now < self.blockedUntil:
            return

        self.blockedUntil = now + self.bouncetime
        evt = SensorEvent(timestamp=now, meta={
            'type': 'Mic Sound',
            'level': sf,
        })
        self.output.send(evt)
        # TODO: Additional message queue between threads?
