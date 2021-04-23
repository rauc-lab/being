import logging
import logging.handlers
import os
from typing import Optional

from being.config import CONFIG
from being.constants import MB

BEING_LOGGERS = set()
"""All being loggers. Workaround for messy logger hierarchy."""

DEFAULT_EXCLUDES = [
    'parso',
    'matplotlib',
    'can',
    'canopen',
    'aiohttp',
]


LEVEL = CONFIG['Logging']['LEVEL']
DIRECTORY = CONFIG['Logging']['DIRECTORY']
FILENAME = CONFIG['Logging']['FILENAME']


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
        name: Logger name. None for root logger.
    """
    logger = logging.getLogger(name)
    BEING_LOGGERS.add(logger)
    return logger


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
