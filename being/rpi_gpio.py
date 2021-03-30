try:
    import RPi.GPIO as GPIO
except ImportError:
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
            print(f'setup({args}, {kwargs})')

        @staticmethod
        def add_event_detect(*args, **kwargs):
            print(f'add_event_detect({args}, {kwargs})')

        @staticmethod
        def cleanup(*args, **kwargs):
            print(f'cleanup({args}, {kwargs})')

        @staticmethod
        def setmode(*args, **kwargs):
            print(f'setmode({args}, {kwargs})')
