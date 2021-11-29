"""Being logging.

Resources:
  - https://stackoverflow.com/questions/7016056/python-logging-not-outputting-anything
"""
import logging
import logging.handlers
import os
from typing import Optional
from logging import Logger

from being.configuration import CONFIG
from being.constants import MB


LEVEL = CONFIG['Logging']['LEVEL']
DIRECTORY = CONFIG['Logging']['DIRECTORY']
FILENAME = CONFIG['Logging']['FILENAME']

BEING_LOGGER = logging.getLogger('being')
"""Being root logger."""

DEFAULT_EXCLUDES = ['parso', 'matplotlib', 'can', 'canopen', 'aiohttp',]


def get_logger(name: Optional[str] = None, parent: Optional[Logger] = BEING_LOGGER) -> Logger:
    """Get logger. Wrap for `logging.getLogger` in order to keep track of being
    loggers (via evil global variable BEING_LOGGERS).

    Args:
        name: Logger name. None for root logger if not parent logger.
        parent: Parent logger. BEING_LOGGER by default.
    """
    if name is None:
        return BEING_LOGGER

    if parent:
        return parent.getChild(name)

    return logging.getLogger(name)


def suppress_other_loggers(*excludes):
    """Suppress log messages from some of the other common loggers."""
    if len(excludes) == 0:
        excludes = DEFAULT_EXCLUDES

    for name in logging.root.manager.loggerDict:
        for part in excludes:
            if part in name:
                logging.getLogger(name).disabled = True


def setup_logging(level=LEVEL):
    """Setup being loggers."""
    # Note using logging.basicConfig(level=level) would route all the other
    # loggers to stdout
    logging.root.setLevel(level)

    formatter = logging.Formatter(
        fmt='%(asctime)s.%(msecs)03d - %(levelname)5s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    if DIRECTORY:
        os.makedirs(DIRECTORY, exist_ok=True)
        filename = os.path.join(DIRECTORY, FILENAME)
        print(f'Logging to {filename!r}')
        handler = logging.handlers.RotatingFileHandler(
            filename,
            maxBytes=100 * MB,
            backupCount=5,
        )
    else:
        handler = logging.StreamHandler()

    handler.setFormatter(formatter)
    #handler.setLevel(level)
    logging.root.addHandler(handler)
