"""Different config formats. Currently supported are:
    - JSON
    - INI
    - YAML
    - TOML

Round-trip preservation for preserving comments in config files (depending on
third-party libraries). Internally all config formats get mapped on a
:class:`being.utils.NestedDict` data structure which can be accessed through a
`path-like` syntax.

Example:
    >>> c = Config()
    ... c.store('this/is/it', 1234)
    ... print(c.data)
    {'this': {'is': {'it': 1234}}}
"""
import collections
import io
import json
import os
from typing import Tuple, Any, Optional

import ruamel.yaml
import tomlkit
import configobj

from being.utils import NestedDict


SEP: str = '/'
"""Separator character for name <-> key path conversion."""

ROOT_NAME: str = ''
"""Empty string denoting the root config entry."""


def split_name(name: str) -> Tuple[str, str]:
    """Split name into (head, tail) where tail is everything after the finals
    separator (like splitting a filepath in the directory vs. filename part).

    Args:
        name: Name to split.

    Returns:
        head and tail tuple

    Example:
        >>> split_name('this/is/it')
        ('this/is', 'it')
    """
    if SEP not in name:
        return '', name

    return name.rsplit('/', maxsplit=1)


def guess_config_format(filepath: str) -> str:
    """Guess config format from file extension.

    Args:
        filepath: Path to guess from.

    Returns:
        Config format.

    Example:
        >>> guess_config_format('this/is/it.json')
        'json'
    """
    _, ext = os.path.splitext(filepath)
    return ext[1:].lower()


class _ConfigImpl(NestedDict):

    """Base class for private implementations of different config formats.

    Holds the dict-like data object from the various third-party libraries.
    Contains the default_factory() for intermediate levels. Allows for path like
    `name` syntax to access nested dicts with string keys.

    Attributes:
        data: Original dict-like config data object.
        default_factory: Associated default_factory for creating intermediate
            elements

    Example:
        >>> c = _ConfigImpl()
        ... c.store('this/is/it', 'Hello, world!')
        ... c.storedefault('this/is/it', 42)
        'Hello, world!'
    """

    def retrieve(self, name: str = ROOT_NAME) -> Any:
        """Retrieve config entry of a given name. Root object by default."""
        if name == ROOT_NAME:
            return self.data

        keys = tuple(name.split(SEP))
        return self[keys]

    def store(self, name: str, value: Any):
        """Store config entry under a given name."""
        keys = tuple(name.split(SEP))
        self[keys] = value

    def erase(self, name: str):
        """Erase config entry."""
        keys = tuple(name.split(SEP))
        del self[keys]

    def storedefault(self, name: str, default: Any = None) -> Any:
        """Store config entry under name if it does not exist."""
        keys = tuple(name.split(SEP))
        return self.setdefault(keys, default)

    def loads(self, string):
        """Load from string..."""
        raise NotImplementedError

    def load(self, stream):
        """Load from stream..."""
        raise NotImplementedError

    def dumps(self) -> str:
        """Dumps config to string."""
        raise NotImplementedError

    def dump(self, stream) -> str:
        """Dumps to stream..."""
        raise NotImplementedError


class _TomlConfig(_ConfigImpl):

    """Config implementation for TOML format."""

    def __init__(self, data=None):
        if data is None:
            data = tomlkit.document()  # Differs from default_factory=tomlkit.table

        super().__init__(data, default_factory=tomlkit.table)

    def loads(self, string):
        self.data = tomlkit.loads(string)

    def load(self, stream):
        self.data = tomlkit.loads(stream.read())

    def dumps(self):
        return tomlkit.dumps(self.data)

    def dump(self, stream):
        stream.write(tomlkit.dumps(self.data))


class _YamlConfig(_ConfigImpl):

    """Config implementation for YAML format."""

    def __init__(self, data=None):
        super().__init__(data,  default_factory=ruamel.yaml.CommentedMap)
        self.yaml = ruamel.yaml.YAML()

    def loads(self, string):
        data = self.yaml.load(string)
        if data is None:
            data = ruamel.yaml.CommentedMap()

        self.data = data

    def load(self, stream):
        data = self.yaml.load(stream)
        if data is None:
            data = ruamel.yaml.CommentedMap()

        self.data = data

    def dumps(self):
        out = io.StringIO()
        self.yaml.dump(self.data, stream=out)
        out.seek(0)
        return out.read()

    def dump(self, stream):
        self.yaml.dump(self.data, stream)


class _JsonConfig(_ConfigImpl):

    """Config implementation for JSON format. JSON does not support comments!
    Getting or setting comments will result in RuntimeError errors.
    """

    def __init__(self, data=None):
        super().__init__(data, default_factory=dict)

    def loads(self, string):
        self.data = json.loads(string)

    def load(self, stream):
        self.data = json.load(stream)

    def dumps(self):
        return json.dumps(self.data, indent=4)

    def dump(self, stream):
        return json.dump(self.data, stream, indent=4)


class _IniConfig(_ConfigImpl):

    """Config implementation for INI format. Also supports round trip
    preservation. Comments should be possible as well but not implemented right
    now.
    """

    def __init__(self, data=None):
        super().__init__(data, default_factory=configobj.ConfigObj)

    def loads(self, string):
        buf = io.StringIO(string)
        self.data = configobj.ConfigObj(buf)

    def load(self, stream):
        self.data = configobj.ConfigObj(stream)

    def dumps(self):
        buf = io.BytesIO()
        self.data.write(buf)
        buf.seek(0)
        return buf.read().decode()

    def dump(self, stream):
        return self.data.write(stream)


IMPLEMENTATIONS = {
    None: _ConfigImpl,
    'toml': _TomlConfig,
    'yaml': _YamlConfig,
    'json': _JsonConfig,
    'ini': _IniConfig,
}


class Config(_ConfigImpl, collections.abc.MutableMapping):

    """Configuration object. Proxy for _ConfigImpl (depending on config format)."""

    def __init__(self, data: Optional[dict] = None, configFormat: Optional[str] = None):
        """Args:
            data: Initial / internal data.
            configFormat: Config format (if any).
        """
        if configFormat not in IMPLEMENTATIONS:
            raise ValueError(f'No config implementation for {configFormat}!')

        implType = IMPLEMENTATIONS[configFormat]
        self.impl: _ConfigImpl = implType(data)

    @property
    def data(self):
        return self.impl.data

    def __getitem__(self, key):
        return self.impl[key]

    def __setitem__(self, key, value):
        self.impl[key] = value

    def __delitem__(self, key):
        del self.impl[key]

    def __iter__(self):
        return iter(self.impl)

    def __len__(self):
        return len(self.impl)

    def store(self, name, value):
        self.impl.store(name, value)

    def retrieve(self, name=ROOT_NAME) -> Any:
        return self.impl.retrieve(name)

    def erase(self, name):
        return self.impl.erase(name)

    def storedefault(self, name, default=None):
        return self.impl.storedefault(name, default)

    def loads(self, string):
        self.impl.loads(string)

    def load(self, stream):
        self.impl.load(stream)

    def dumps(self):
        return self.impl.dumps()

    def dump(self, stream):
        return self.impl.dump(stream)


class ConfigFile(Config):
    def __init__(self, filepath):
        super().__init__(configFormat=guess_config_format(filepath))
        self.filepath = filepath
        if os.path.exists(self.filepath):
            self.reload()

    def save(self):
        with open(self.filepath, 'w') as fp:
            self.impl.dump(fp)

    def reload(self):
        with open(self.filepath) as fp:
            self.impl.load(fp)

    def __str__(self):
        return f'{type(self).__name__}({self.filepath!r})'
