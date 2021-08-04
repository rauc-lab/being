import abc
import collections.abc

import ruamel.yaml
import tomlkit

from being.utils import SingleInstanceCache, write_file, read_file, update_dict_recursively

SEP: str = '/'
"""Separator for name <-> key path conversion."""

yaml = ruamel.yaml.YAML(typ='safe')  # defaults to round-trip


class _ConfigImpl(abc.ABC):
    def __init__(self):
        self.data = {}

    @abc.abstractmethod
    def loads(self, string, overwrite=True):
        """Load from string..."""

    @abc.abstractmethod
    def dumps(self) -> str:
        """Dumps config to string."""

    @abc.abstractmethod
    def retrieve(self, name) -> object:
        """Retrieve config entry."""

    @abc.abstractmethod
    def store(self, name, value):
        """Store value in config."""

    @abc.abstractmethod
    def get_comment(self, name):
        """Get comment for config entry."""

    @abc.abstractmethod
    def set_comment(self, name, comment):
        """Set comment for config entry."""


class _TomlConfig(_ConfigImpl):
    def __init__(self):
        self.data = tomlkit.document()

    def loads(self, string, overwrite=True):
        doc = tomlkit.loads(string)
        if overwrite:
            self.data = doc
        else:
            update_dict_recursively(self.data, doc)

    def dumps(self):
        return tomlkit.dumps(self.data)

    def retrieve(self, name):
        entry = self.data
        for key in name.split(SEP):
            if key not in entry:
                return None

            entry = entry[key]

        return entry

    def store(self, name, value):
        *path, key = name.split(SEP)
        entry = self.data
        for k in path:
            entry = entry.setdefault(k, tomlkit.table())

        entry[key] = value

    def get_comment(self, name):
        entry = self.retrieve(name)
        return entry.trivia.comment

    def set_comment(self, name, comment):
        entry = self.retrieve(name)
        entry.comment(comment)


class _YamlConfig(_ConfigImpl):
    pass


class _JsonConfig(_ConfigImpl):
    pass


IMPLEMENTATIONS = {
    #'JSON': _JsonConfig,
    #'YAML': _YamlConfig,
    'TOML': _TomlConfig,
}


class Config(_ConfigImpl):
    def __init__(self, format='TOML'):
        if format not in IMPLEMENTATIONS:
            raise ValueError(f'No config implementation for {format}!')

        implType = IMPLEMENTATIONS[format]
        self.impl = implType()

    def loads(self, string, overwrite=True):
        self.impl.loads(string, overwrite)

    def dumps(self):
        return self.impl.dumps()

    def retrieve(self, name) -> object:
        return self.impl.retrieve(name)

    def store(self, name, value):
        self.impl.store(name, value)

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
        super().__init__(format=guess_format(filepath))
        self.filepath = filepath
        self.load()

    def save(self):
        write_file(self.filepath, self.impl.dumps())

    def load(self, overwrite=False):
        if not os.path.exists(self.filepath):
            return

        string = read_file(self.filepath)
        self.impl.loads(string, overwrite)
