"""Being configuration and default values. Searches the *current working
directory* for a ``being.yaml`` configuration file. If present default
configuration values get updated.

Todo:
    Rename :obj:`CONFIG` to ``DEFAULT_CONFIG``? Should not overwrite defaults
    but instead update a copy.

Notes:
  - :attr:`being.configuration.CONFIG` not a :class:`being.configs.Config`
    instance because read-only
  - :attr:`being.configuration.CONFIG` not a :class:`being.utils.NestedDict`
    instance in order to catch :exc:`KeyError` pre-runtime.
"""
import logging
import os
from typing import Dict, Any

from being.configs import ConfigFile
from being.utils import update_dict_recursively


CONFIG: Dict[str, Any] = {
    'General': {
        'INTERVAL': .010,  # Main loop interval in seconds.
        'CONTENT_DIRECTORY': 'content',  # Default directory for motions / splines
        'PARAMETER_CONFIG_FILEPATH': 'being_params.yaml',  # Filepath for parameter config file
    },
    'Can': {
        'DEFAULT_CAN_BITRATE': 1000000,  # Default bitrate (bit / sec) for CAN interface.
    },
    'Web': {
        'HOST': None,  # Host name of web server
        'PORT': 8080,  # Port number of web server
        'API_PREFIX': '/api',  # API route prefix.
        'WEB_SOCKET_ADDRESS': '/stream',  # Web socket URL.
        'INTERVAL': .050,  # Web socket stream interval in seconds.
    },
    'Logging': {
        'LEVEL': logging.WARNING,
        'DIRECTORY': None,
        'FILENAME': 'being.log',
    }
}
"""Global being default configuration."""

for fp in [
    os.path.join(os.getcwd(), 'being.yaml'),
]:
    if os.path.exists(fp):
        update_dict_recursively(CONFIG, ConfigFile(fp))
