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
    """The motor state has changed."""

    HOMING_CHANGED = enum.auto()
    """The homing state has changed."""

    ERROR = enum.auto()
    """An error occurred."""


register_enum(MotorEvent)


class MotorState(enum.Enum):

    """Simplified motor state."""

    FAULT = 0
    """Motor in fault state."""

    DISABLED = 1
    """Motor is disabled."""

    ENABLED = 2
    """Motor is enabled and working normally."""


register_enum(MotorState)

# TODO: Rename velocity -> maxVelocity, acceleration -> maxAcceleration?

class PositionProfile(NamedTuple):

    """Position profile segment.

    Units are assumed to be SI. Controller has to convert to device units.
    """

    position: float
    """Profiled target position value."""

    velocity: Optional[float] = None
    """Maximum profile velocity value."""

    acceleration: Optional[float] = None
    """Maximum profile acceleration (and deceleration)."""


class VelocityProfile(NamedTuple):

    """Velocity profile segment.

    Units are assumed to be SI. Controller has to convert to device units.
    """

    velocity: float
    """Profiled target velocity."""

    acceleration: Optional[float] = None
    """Maximum profile acceleration (and deceleration)."""


class MotorInterface(PubSub, abc.ABC):

    """Base class for motor like things and what they have to provide."""

    def __init__(self):
        super().__init__(events=MotorEvent)

    @abc.abstractmethod
    def disable(self, publish: bool = True):
        """Disable motor (no power).

        Args:
            publish (optional): If to publish motor changes.
        """
        if publish:
            self.publish(MotorEvent.STATE_CHANGED)

    @abc.abstractmethod
    def enable(self, publish: bool = True):
        """Enable motor (power on).

        Args:
            publish (optional): If to publish motor changes.
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
