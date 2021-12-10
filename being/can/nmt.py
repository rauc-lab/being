"""NMT states. String constants for the canopen NMT commands."""


OPERATIONAL: str = 'OPERATIONAL'
"""All CANopen services can be used."""

STOPPED: str = 'STOPPED'
"""No CANopen services can be used, except NMT and Heartbeat."""

SLEEP: str = 'SLEEP'
"""Newer CiA 320 NMT state?"""

STANDBY: str = 'STANDBY'  # TODO: Not sure what this does...

PRE_OPERATIONAL: str = 'PRE-OPERATIONAL'
"""All CANopen services can be used, except PDO services."""

INITIALISING: str = 'INITIALISING'
"""Node is initialising."""

RESET: str = 'RESET'
"""Reset."""

RESET_COMMUNICATION: str = 'RESET COMMUNICATION'
"""Reset communication. Can be used to resolve PDO communication errors."""
