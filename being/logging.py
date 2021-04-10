import logging
from typing import Optional


BEING_LOGGERS = set()
"""All being loggers. Workaround for messy logger hierarchy."""

DEFAULT_EXCLUDES = [
    'parso',
    'matplotlib',
    'can',
    'canopen',
]


def suppress_other_loggers(*excludes):
    """Suppress log messages from some of the other common loggers."""
    if len(excludes) == 0:
        excludes = DEFAULT_EXCLUDES

    for name in logging.root.manager.loggerDict:
        for part in excludes:
            if part in name:
                logging.getLogger(name).disabled = True


def get_logger(name: Optional[str] = None):
    """Get logger. Wrap for `logging.getLogger` in order to keep track of being
    loggers (via evil global variable BEING_LOGGERS).

    Args:
        name: Looger name. None for root logger.
    """
    logger = logging.getLogger(name)
    BEING_LOGGERS.add(logger)
    return logger
