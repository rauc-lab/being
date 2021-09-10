import enum


class MotorEvent(enum.Enum):

    """Motor / controller events."""

    STATE_CHANGED = enum.auto()
    HOMING_CHANGED = enum.auto()
    ERROR = enum.auto()
