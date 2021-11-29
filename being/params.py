"""Parameter blocks which can be used to control values inside the block network
and to mirror their state inside a config file.
"""
from typing import Any, Optional

from being.block import Block
from being.configs import ConfigFile, split_name
from being.content import Content
from being.configuration import CONFIG
from being.math import clip
from being.utils import SingleInstanceCache, unique


PARAMETER_CONFIG_FILEPATH = CONFIG['General']['PARAMETER_CONFIG_FILEPATH']


class ParamsConfigFile(ConfigFile, SingleInstanceCache):

    """Slim ConfigFile subclass so that we can use it with
    SingleInstanceCache.
    """

    def __init__(self, filepath=PARAMETER_CONFIG_FILEPATH):
        super().__init__(filepath)


class Parameter(Block):

    """Parameter block base class.

    Attributes:
        fullname: Full name of config entry.
        configFile: Configuration file instance.
    """

    def __init__(self, fullname: str, configFile: Optional[ConfigFile] = None):
        """Args:
            fullname: Full name of config entry.
            configFile: Configuration file instance (DI). Default is
                ParamsConfigFile instance.
        """
        _, name = split_name(fullname)
        if configFile is None:
            configFile = ParamsConfigFile.single_instance_setdefault()

        super().__init__(name=name)
        self.add_value_output()
        self.fullname = fullname
        self.configFile = configFile

    def validate(self, value: Any) -> Any:
        """Validate value. Pass-through / no validation by default.

        Args:
            value: Value to validate.

        Returns:
            Validated value.
        """
        return value

    def load(self):
        """Load value from config file."""
        value = self.configFile.retrieve(self.fullname)
        validated = self.validate(value)
        if validated != value:
            self.configFile.store(self.fullname, validated)
            self.configFile.save()

        self.output.value = validated

    def loaddefault(self, default):
        """Load value from Configuration file with default value (setdefault).

        Args:
            default: Default value.
        """
        validated = self.validate(default)
        self.configFile.storedefault(self.fullname, validated)
        self.load()

    def change(self, value):
        """Change value and store it to Configuration file.

        Args:
            value: New value to set.
        """
        validated = self.validate(value)
        self.configFile.store(self.fullname, validated)
        self.configFile.save()
        self.output.value = validated

    def to_dict(self):
        dct = super().to_dict()
        dct['fullname'] = self.fullname
        dct['value'] = self.output.value
        return dct

    def __str__(self):
        return f'{type(self).__name__}({self.fullname!r}, value: {self.output.value}, {self.configFile})'


class Slider(Parameter):

    """Scalar value slider."""

    def __init__(self, fullname, default: Any = 0.0, minValue=0., maxValue=1., **kwargs):
        if maxValue < minValue:
            raise ValueError

        super().__init__(fullname, **kwargs)
        self.minValue = min(minValue, default)
        self.maxValue = max(maxValue, default)

        self.loaddefault(default)

    def validate(self, value):
        return clip(value, self.minValue, self.maxValue)

    def to_dict(self):
        dct = super().to_dict()
        dct['minValue'] = self.minValue
        dct['maxValue'] = self.maxValue
        return dct


class SingleSelection(Parameter):

    """Single selection out of multiple possibilities."""

    def __init__(self, fullname, possibilities, default=None, **kwargs):
        super().__init__(fullname, **kwargs)
        self.possibilities = list(unique(possibilities))
        if default is None:
            default = self.possibilities[0]

        self.loaddefault(default)

    def validate(self, value):
        assert value in self.possibilities, f'{value} not in {self.possibilities}'
        return value

    def to_dict(self):
        dct = super().to_dict()
        dct['possibilities'] = self.possibilities
        return dct


class MultiSelection(Parameter):

    """Multiple selection out of multiple possibilities."""

    def __init__(self, fullname, possibilities, default=None, **kwargs):
        super().__init__(fullname, **kwargs)
        if default is None:
            default = []

        self.possibilities = list(unique(possibilities))
        self.loaddefault(default)

    def validate(self, value):
        return list(set(self.possibilities).intersection(value))

    def to_dict(self):
        dct = super().to_dict()
        dct['possibilities'] = self.possibilities
        return dct


class MotionSelection(MultiSelection):

    """Multiple motion selection."""

    def __init__(self, fullname, default=None, content=None, **kwargs):
        if default is None:
            default = []

        if content is None:
            content = Content.single_instance_setdefault()

        possibilities = content.list_curve_names()
        super().__init__(fullname, possibilities, **kwargs)
        self.content = content
        self.loaddefault(default)

    def on_content_changed(self):
        """Callback function on contented changed."""
        self.possibilities = self.content.list_curve_names()
        self.load()
