"""Being logging.

See Also:
    `Python Logging Not Outputting Anything <https://stackoverflow.com/questions/7016056/python-logging-not-outputting-anything>`_
"""
import logging
import logging.handlers
import coloredlogs
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

DEFAULT_EXCLUDES = ['parso', 'matplotlib', 'can.interfaces.socketcan.socketcan',
                    'can.interfaces.socketcan.socketcan.tx', 'aiohttp', 'canopen',
                    ]


def get_logger(name: Optional[str] = None, parent: Optional[Logger] = BEING_LOGGER) -> Logger:
    """Get being logger. Wraps :func:`logging.getLogger`. Keeps track of all
    created being loggers (child loggers of :data:`being.logging.BEING_LOGGER`).

    Args:
        name: Logger name. None for root logger if not parent logger.
        parent: Parent logger. BEING_LOGGER by default.

    Returns:
        Requested logger for given mame.
    """
    if name is None:
        return BEING_LOGGER

    if parent:
        return parent.getChild(name)

    return logging.getLogger(name)


def suppress_other_loggers(*excludes):
    """Suppress log messages from some other common loggers."""
    if len(excludes) == 0:
        excludes = DEFAULT_EXCLUDES

    for name in logging.root.manager.loggerDict:
        for part in excludes:
            if part in name:
                logging.getLogger(name).disabled = True

    # some loggers are not found in the dict above - suppress them this way:
    for e in excludes:
        logging.getLogger(e).disabled = True


def setup_logging(level: int = LEVEL):
    """Setup being loggers.

    Args:
        level: Logging level.
    """
    # Note using logging.basicConfig(level=level) would route all the other
    # loggers to stdout

    fmt = '%(asctime)s.%(msecs)03d - %(levelname)5s - %(name)s - %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    coloredlogs.install(level=level, logger=logging.root, fmt=fmt, datefmt=datefmt)

    if DIRECTORY:
        os.makedirs(DIRECTORY, exist_ok=True)
        filename = os.path.join(DIRECTORY, FILENAME)
        print(f'Logging to {filename!r}')
        handler = logging.handlers.RotatingFileHandler(
            filename,
            maxBytes=100 * MB,
            backupCount=5,
        )
        handler.setFormatter(formatter)
        logging.root.addHandler(handler)
