"""Loading configurations and default configuration values."""
import logging
import os

from being.configs import ConfigFile
from being.utils import update_dict_recursively


CONFIG: dict = {
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
"""Global being configuration.

Note:
    - Not a :class:`being.configs.Config` instance because read-only
    - Not a :class:`being.utils.NestedDict` instance in order to catch :ref:`KeyError` pre-runtime.
"""

for fp in [
    os.path.join(os.getcwd(), 'being.ini'),
]:
    if os.path.exists(fp):
        update_dict_recursively(CONFIG, ConfigFile(fp))
