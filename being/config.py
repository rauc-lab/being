"""Loading configurations and default configuration values."""
import configparser
import json
import logging
import os
from typing import Union


CONFIG = {
    'General': {
        'INTERVAL': .010,  # Main loop interval in seconds.
        'CONTENT_DIRECTORY': 'content',  # Default directory for motions / splines
    },
    'Can': {
        'DEFAULT_CAN_BITRATE': 1000000,  # Default bitrate (bit / sec) for CAN interface.
        'SI_2_FAULHABER': 1e6,  # Unit conversion for Lineare DC-Servomotoren Serie LM 0830 ... 01.
    },
    'Web': {
        'HOST': None,  # Host name of web server
        'PORT': 8080,  # Port number of web server
        'API_PREFIX': '/api',  # API route prefix.
        'WEB_SOCKET_ADDRESS': '/stream',  # Web socket URL.
    },
    'Logging': {
        'LEVEL': logging.WARNING,
        'DIRECTORY': None,
        'FILENAME': 'being.log',
    }
}
"""Global configuration object."""


def parse_string(string: str) -> Union[str, object]:
    """Try to parse some JSON data from string."""
    for ctor in [int, float]:
        try:
            return ctor(string)
        except ValueError:
            pass

    try:
        return json.loads(string)
    except json.JSONDecodeError:
        pass

    return string


def parse_config(content: str) -> dict:
    """Parse INI string to dictionary (recursive sub-dictionaries for sections).

    Args:
        string: String to parse.

    Returns:
        Parsed configuration dictionary.
    """
    config = {}
    parser = configparser.ConfigParser(
        inline_comment_prefixes=('#',),
        default_section='DEFAULT',
    )
    parser.optionxform = str  # Case sensitive parsing
    parser.read_string(content)
    for key, s in parser['DEFAULT'].items():
        config[key] = parse_string(s)

    for section in parser.sections():
        subconfig = config.setdefault(section, {})
        for key, s in parser[section].items():
            subconfig[key] = parse_string(s)

    return config


def _update_recursively(dct: dict, **kwargs):
    """Update dictionary recursively.

    Args:
        dct: Dictionary to update.

    Kwargs:
        key / values
    """
    for key, value in kwargs.items():
        if isinstance(dct.get(key), dict):
            _update_recursively(dct[key], **value)
        else:
            dct[key] = value


for fp in [
    os.path.join(os.getcwd(), 'being.ini'),
]:
    if os.path.exists(fp):
        with open(fp) as f:
            _update_recursively(CONFIG, **parse_config(f.read()))
