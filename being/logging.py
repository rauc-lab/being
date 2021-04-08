import logging


BEING_LOGGERS = set()
"""All being loggers. Workaround for messy logger hierarchy."""


def suppress_other_loggers():
    """Suppress log messages from some of the other common loggers."""
    for name in logging.root.manager.loggerDict:
        for part in ['parso', 'matplotlib', 'can', 'canopen']:
            if part in name:
                logging.getLogger(name).disabled = True


def get_logger(name=None):
    logger = logging.getLogger(name)
    BEING_LOGGERS.add(logger)
    return logger
