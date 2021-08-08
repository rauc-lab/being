"""Config data / file access for ini, json, yaml and toml. Round trip
preservation.
"""
import abc
import io
import json
import os
from typing import Tuple, Any

import ruamel.yaml
import tomlkit
import configobj

from being.utils import NestedDict


"""
Commenting stuff:
- INI
  - EOL
      >>> head, tail = split_name(name)
      ... parent = self.retrieve(head)
      ... parent.inline_comments[tail] = eol
  - Before
      Same as EOL but with parent.comments[key] = []
  - After
      ?

- JSON
    Not supported

- YAML
  - EOL
      >>> head, tail = split_name(name)
      ... parent = self.retrieve(head)
      ... parent.yaml_add_eol_comment(eol, key=tail)
  - Before / After
      >>> head, tail = split_name(name)
config.data.yaml_set_comment_before_after_key
      ... parent = self.retrieve(head)
      ... parent.yaml_set_comment_before_after_key(tail, before=before, after=after, indent=?)

- TOML
  - EOL
      >>> entry = self.retrieve(name)
      ... entry.comment(eol)

  - Before
      ?
  - After
      ?
"""


SEP: str = '/'
"""Separator for name <-> key path conversion."""

COMMENT_PREFIX: str = '#'
"""Comment prefix character."""

ROOT_NAME: str = ''
"""Empty string denoting the root config entry."""


def strip_comment_prefix(comment: str) -> str:
    """Strip away comment prefix from string."""
    comment = comment.lstrip()
    if COMMENT_PREFIX in comment:
        _, comment = comment.split(COMMENT_PREFIX, maxsplit=1)

    return comment.strip()


def split_name(name: str) -> Tuple[str, str]:
    """Split name into (head, tail) where tail is everything after the finals
    separator.

    Args:
        name: Name to split.

    Returns:
        head and tail tuple

    Usage:
        >>> split_name('this/is/it')
        ('this/is', 'it')
    """
    if SEP in name:
        return name.rsplit('/', maxsplit=1)

    return '', name


def guess_format(filepath):
    """Guess config format from file extension."""
    _, ext = os.path.splitext(filepath)
    return ext[1:].lower()


class _ConfigImpl(NestedDict, abc.ABC):

    """Semi abstract base class for all configuration implementations. Holds the
    dict-like data object from the various third-party libraries. Contains the
    default_factory() for intermediate levels.

    Attributes:
        data: Original dict-like config data object.
        default_factory: Associated default_factory for creating intermediate
            elements
    """

    def store(self, name: str, value: Any):
        """Store config entry under a given name."""
        keys = tuple(name.split(SEP))
        self[keys] = value

    def retrieve(self, name: str = ROOT_NAME) -> Any:
        """Retrieve config entry of a given name. Root object by default."""
        if name == ROOT_NAME:
            return self.data

        keys = tuple(name.split(SEP))
        return self[keys]

    def erase(self, name: str):
        """Erase config entry."""
        keys = tuple(name.split(SEP))
        del self[keys]

    def storedefault(self, name: str, default: Any = None):
        """Store config entry under name if it does not exist."""
        keys = tuple(name.split(SEP))
        return self.setdefault(keys, default)

    @abc.abstractmethod
    def loads(self, string):
        """Load from string..."""

    @abc.abstractmethod
    def load(self, stream):
        """Load from stream..."""

    @abc.abstractmethod
    def dumps(self) -> str:
        """Dumps config to string."""

    @abc.abstractmethod
    def dump(self, stream) -> str:
        """Dumps to stream..."""


class _TomlConfig(_ConfigImpl):

    """Config implementation for TOML format."""

    def __init__(self):
        super().__init__(data=tomlkit.document(), default_factory=tomlkit.table)

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

    def __init__(self):
        super().__init__(data=ruamel.yaml.CommentedMap(), default_factory=ruamel.yaml.CommentedMap)
        self.yaml = ruamel.yaml.YAML()

    def loads(self, string):
        self.data = self.yaml.load(string)

    def load(self, stream):
        self.data = self.yaml.load(stream)

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
    def __init__(self):
        super().__init__(data=dict(), default_factory=dict)

    def loads(self, string):
        self.data = json.loads(string)

    def load(self, stream):
        self.data = json.load(stream)

    def dumps(self, indent=4):
        return json.dumps(self.data, indent=indent)

    def dump(self, stream, indent=4):
        return json.dump(self.data, stream, indent=indent)


class _IniConfig(_ConfigImpl):

    """Config implementation for INI format. Also supports round trip
    preservation. Comments should be possible as well but not implemented right
    now.
    """

    def __init__(self):
        super().__init__(data=configobj.ConfigObj(), default_factory=configobj.ConfigObj)

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
    'toml': _TomlConfig,
    'yaml': _YamlConfig,
    'json': _JsonConfig,
    'ini': _IniConfig,
}


class Config():
    def __init__(self, configFormat):
        if configFormat not in IMPLEMENTATIONS:
            raise ValueError(f'No config implementation for {configFormat}!')

        implType = IMPLEMENTATIONS[configFormat]
        self.impl: _ConfigImpl = implType()

    def store(self, name, value):
        self.impl.store(name, value)

    def storedefault(self, name, default):
        self.impl.storedefault(name, default)

    def retrieve(self, name):
        return self.impl.retrieve(name)

    def erase(self, name):
        return self.impl.erase(name)

    def loads(self, string):
        self.impl.loads(string)

    def dumps(self):
        return self.impl.dumps()


class ConfigFile(Config):
    def __init__(self, filepath):
        super().__init__(configFormat=guess_format(filepath))
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
