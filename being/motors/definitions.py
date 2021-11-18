"""Abstract motor interface."""
import abc
import enum
from typing import NamedTuple, Optional

from being.motors.homing import HomingState
from being.pubsub import PubSub
from being.serialization import register_enum


class MotorEvent(enum.Enum):

    """Motor / controller events."""

    STATE_CHANGED = enum.auto()
    HOMING_CHANGED = enum.auto()
    ERROR = enum.auto()


register_enum(MotorEvent)


class MotorState(enum.Enum):

    """Simplified motor state."""

    FAULT = 0
    DISABLED = 1
    ENABLED = 2


register_enum(MotorState)


class PositionProfile(NamedTuple):

    """Position profile segment.

    Units are assumed to be SI. Controller has to convert to device units.
    """
    position: float
    velocity: Optional[float] = None
    acceleration: Optional[float] = None


class VelocityProfile(NamedTuple):

    """Velocity profile segment.

    Units are assumed to be SI. Controller has to convert to device units.
    """
    velocity: float
    acceleration: Optional[float] = None


class MotorInterface(PubSub, abc.ABC):

    """Base class for motor like things and what they have to provide."""

    def __init__(self):
        super().__init__(events=MotorEvent)

    @abc.abstractmethod
    def disable(self, publish: bool = True):
        """Disable motor (no power).

        Args:
            publish: If to publish motor changes.
        """
        if publish:
            self.publish(MotorEvent.STATE_CHANGED)

    @abc.abstractmethod
    def enable(self, publish: bool = True):
        """Enable motor (power on).

        Args:
            publish: If to publish motor changes.
        """
        if publish:
            self.publish(MotorEvent.STATE_CHANGED)

    @abc.abstractmethod
    def motor_state(self) -> MotorState:
        """Return current motor state."""
        raise NotImplementedError

    @abc.abstractmethod
    def home(self):
        """Start homing routine for this motor. Has then to be driven via the
        update() method.
        """
        self.publish(MotorEvent.HOMING_CHANGED)

    @abc.abstractmethod
    def homing_state(self) -> HomingState:
        """Return current homing state."""
        raise NotImplementedError
