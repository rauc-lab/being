"""Sensor blocks."""
import collections
import time
from typing import NamedTuple, Optional, Union

import numpy as np

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

    """Listens to audio and emits sound event messages.

    Example:
        >>> from being.awakening import awake
        ... from being.block import Block
        ... from being.resources import manage_resources
        ... from being.sensors import Mic
        ... 
        ... 
        ... class MessagePrinter(Block):
        ...     def __init__(self):
        ...         super().__init__()
        ...         self.add_message_input()
        ... 
        ...     def update(self):
        ...         for msg in self.input.receive():
        ...             print(msg)
        ... 
        ... 
        ... with manage_resources():
        ...     awake(Mic() | MessagePrinter())
        ...     # Clap your hands
    """

    def __init__(self,
            threshold=0.01,
            bouncetime=0.1,
            input_device_index: Optional[int] = None,
            frames_per_buffer: int = 1024,
            dtype: Union[str, type, np.dtype] = np.uint8,
            audio: Optional[AudioBackend] = None,
            clock: Optional[Clock] = None,
            **kwargs,
        ):
        """
        Args:
            threshold: Spectral flux difference threshold.
            bouncetime: Blocked duration after emitted sound event.
            input_device_index: Input device index for given host api.
                Unspecified (or None) uses default input device.
            frames_per_buffer: Audio buffer size.
            dtype: Data type for samples. Not all data types are supported for
                audio. uint8, int16, int32 and float32 should works.
            audio: Audio backend instance (DI).
            clock: Clock instance (DI).
        """
        if audio is None:
            self.audio = AudioBackend.single_instance_setdefault(
                input_device_index=input_device_index,
                frames_per_buffer=frames_per_buffer,
                dtype=dtype,
            )
            register_resource(self.audio, duplicates=False)

        if clock is None:
            clock = Clock.single_instance_setdefault()

        super().__init__(**kwargs)
        self.add_message_output()
        self.threshold = threshold
        self.bouncetime = bouncetime
        self.clock = clock

        self.prevSf = 0.0
        self.blockedUntil = -1

        self.audio.subscribe_microphone(self)

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
            'deviceName': self.audio.deviceName,
        })
        self.output.send(evt)
        # TODO: Additional message queue between threads?
