import abc
import collections.abc
import io
import os
import json
from typing import Tuple

import ruamel.yaml
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
import tomlkit
import configobj

from being.utils import (
    NestedDict,
    SingleInstanceCache,
    read_file,
    write_file,
)


SEP: str = '/'
"""Separator for name <-> key path conversion."""

COMMENT_PREFIX: str = '#'
"""Comment prefix character."""


def strip_comment_prefix(comment: str) -> str:
    """Strip away comment prefix from string."""
    _, comment = comment.split(COMMENT_PREFIX, maxsplit=1)
    return comment.strip()


def name_to_keys(name: str) -> tuple:
    """Map name with separators to key path tuple."""
    return tuple(name.split(SEP))


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


class _ConfigImpl(abc.ABC):

    """Semi abstract base class for all configuration implementations.

    Attributes:
        nested (NestedDict): Nested dict instance for storing the configuration
            data.
    """

    def __init__(self):
        self.nested = NestedDict()

    def retrieve(self, name: str = '') -> object:
        """Retrieve config entry for a given name. Root object by default."""
        if name == '':
            return self.nested.data

        return self.nested.get(name_to_keys(name))

    def store(self, name: str, value: object) -> object:
        """Store value in config under a given name."""
        return self.nested.setdefault(name_to_keys(name), value)

    @abc.abstractmethod
    def loads(self, string):
        """Load from string..."""

    @abc.abstractmethod
    def dumps(self) -> str:
        """Dumps config to string."""

    @abc.abstractmethod
    def get_comment(self, name):
        """Get comment for config entry."""

    @abc.abstractmethod
    def set_comment(self, name, comment):
        """Set comment for config entry."""


class _TomlConfig(_ConfigImpl):

    """Config implementation for TOML format."""

    def __init__(self):
        self.nested = NestedDict(tomlkit.document(), default_factory=tomlkit.table)

    def loads(self, string):
        self.nested = NestedDict(tomlkit.loads(string), default_factory=tomlkit.table)

    def dumps(self):
        return tomlkit.dumps(self.nested.data)

    def get_comment(self, name):
        entry = self.retrieve(name)
        comment = entry.trivia.comment
        return strip_comment_prefix(comment)

    def set_comment(self, name, comment):
        entry = self.retrieve(name)
        entry.comment(comment)


class _YamlConfig(_ConfigImpl):

    """Config implementation for YAML format."""

    def __init__(self):
        self.yaml = YAML()
        self.nested = NestedDict(CommentedMap(), default_factory=CommentedMap)

    def loads(self, string):
        dct = self.yaml.load(string)
        self.nested = NestedDict(dct, default_factory=CommentedMap)

    def dumps(self):
        buf = io.StringIO()
        self.yaml.dump(self.nested.data, buf)
        buf.seek(0)
        return buf.read()

    @staticmethod
    def _fetch_comment(ele, key):
        comment = ele.ca.items[key][2].value
        return strip_comment_prefix(comment)

    def get_comment(self, name):
        head, tail = split_name(name)
        e = self.retrieve(head)
        return self._fetch_comment(e, key=tail)

    def set_comment(self, name, comment):
        head, tail = split_name(name)
        e = self.retrieve(head)
        e.yaml_add_eol_comment(comment, key=tail)

class _JsonConfig(_ConfigImpl):

    """Config implementation for JSON format. JSON does not support comments!
    Getting or setting comments will result in RuntimeError errors.
    """

    def loads(self, string):
        self.nested = NestedDict(json.loads(string))

    def dumps(self, indent=4):
        return json.dumps(self.nested.data, indent=indent)

    def get_comment(self, name):
        raise RuntimeError('JSON does not support comments!')

    def set_comment(self, name, comment):
        raise RuntimeError('JSON does not support comments!')


class _IniConfig(_ConfigImpl):

    """Config implementation for INI format. Also supports roundtrip
    preservation. Comments should be possible as well but not implemented right
    now.
    """

    def __init__(self):
        self.nested = NestedDict(configobj.ConfigObj())

    def loads(self, string):
        buf = io.StringIO(string)
        self.nested = NestedDict(configobj.ConfigObj(buf))

    def dumps(self):
        buf = io.BytesIO()
        self.nested.data.write(buf)
        buf.seek(0)
        return buf.read().decode()

    def get_comment(self, name):
        head, tail = split_name(name)
        e = self.retrieve(head)
        return e.inline_comments[tail]

    def set_comment(self, name, comment):
        # Note: Prepending comment can be done with the c.comments[key] = []
        head, tail = split_name(name)
        e = self.retrieve(head)
        e.inline_comments[tail] = comment



IMPLEMENTATIONS = {
    'TOML': _TomlConfig,
    'YAML': _YamlConfig,
    'JSON': _JsonConfig,
    'INI': _IniConfig,
}


class Config(_ConfigImpl):
    def __init__(self, configFormat):
        configFormat = configFormat.upper()
        if configFormat not in IMPLEMENTATIONS:
            raise ValueError(f'No config implementation for {configFormat}!')

        implType = IMPLEMENTATIONS[configFormat]
        self.impl: _ConfigImpl = implType()

    def retrieve(self, name) -> object:
        return self.impl.retrieve(name)

    def store(self, name, value):
        self.impl.store(name, value)

    def loads(self, string):
        self.impl.loads(string)

    def dumps(self):
        return self.impl.dumps()

    def get_comment(self, name):
        return self.impl.get_comment(name)

    def set_comment(self, name, comment):
        self.impl.set_comment(name, comment)


def guess_format(filepath):
    """Guess config format from file extension."""
    _, ext = os.path.splitext(filepath)
    return ext[1:].upper()


class ConfigFile(Config):
    def __init__(self, filepath):
        super().__init__(configFormat=guess_format(filepath))
        self.filepath = filepath
        self.load()

    def save(self):
        write_file(self.filepath, self.impl.dumps())

    def load(self):
        if not os.path.exists(self.filepath):
            return

        string = read_file(self.filepath)
        self.impl.loads(string)

    def __str__(self):
        return f'{type(self).__name__}({self.filepath!r})'
