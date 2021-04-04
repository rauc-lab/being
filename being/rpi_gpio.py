try:
    import RPi.GPIO as GPIO
except ImportError:
    import logging


    LOGGER = logging.getLogger(__name__)


    class GPIO:

        """Dummy GPIO in order to mock missing RPI.GPIO if on non Raspberry PI
        platform.
        """

        BCM = 'BCM'
        IN = 'IN'
        OUT = 'OUT'

        PUD_UP = 'PUD_UP'
        PUD_DOWN = 'PUD_DOWN'
        PUD_OFF = 'PUD_OFF'

        RISING = 'RISING'
        FALLING = 'FALLING'
        BOTH = 'BOTH'

        @staticmethod
        def setup(*args, **kwargs):
            LOGGER.debug('setup(%s, %s)', args, kwargs)

        @staticmethod
        def add_event_detect(*args, **kwargs):
            LOGGER.debug('add_event_detect(%s, %s)', args, kwargs)

        @staticmethod
        def cleanup(*args, **kwargs):
            LOGGER.debug('cleanup(%s, %s)', args, kwargs)

        @staticmethod
        def setmode(*args, **kwargs):
            LOGGER.debug('setmode(%s, %s)', args, kwargs)
