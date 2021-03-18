import logging


def suppress_other_loggers():
    """Suppress log messages from some of the other common loggers."""
    for name in logging.root.manager.loggerDict:
        for part in ['parso', 'matplotlib', 'can', 'canopen']:
            if part in name:
                logging.getLogger(name).disabled = True
