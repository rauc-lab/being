"""Parameter blocks which can be used to control values inside the block network
and to mirror their state inside a config file.
"""
from being.block import Block
from being.configs import ConfigFile, split_name
from being.constants import INF
from being.content import Content
from being.math import clip
from being.utils import SingleInstanceCache
from typing import Any, Optional


class ParamsConfigFile(ConfigFile, SingleInstanceCache):

    """Slim ConfigFile subclass so that we can use it with
    SingleInstanceCache.
    """

    def __init__(self, filepath='being_params.yaml'):
        super().__init__(filepath)


class Parameter(Block):

    """Parameter block base class.

    Attributes:
        fullname: TODO.
        default: Default value.
        configFile: TODO:
    """

    def __init__(self, fullname: str, default: Any = 0.0, configFile: Optional[ConfigFile] = None):
        if configFile is None:
            configFile = ParamsConfigFile.single_instance_setdefault()

        _, name = split_name(fullname)
        super().__init__(name=name)
        self.add_value_output()
        self.fullname = fullname
        self.default = default
        self.configFile = configFile

    def reload(self):
        """Reload value from config file."""
        value = self.configFile.storedefault(self.fullname, self.default)
        validated = self.validate(value)
        changes = (validated != value)
        if changes:
            self.configFile.store(self.name, validated)
            self.configFile.save()

        self.output.value = validated

    def validate(self, value: Any) -> Any:
        """Validate value. Pass-through / no validation by default."""
        return value

    def change(self, value):
        """Change value of output and config entry."""
        validated = self.validate(value)
        self.configFile.store(self.fullname, validated)
        self.output.value = validated
        self.configFile.save()

    def __str__(self):
        return (
            f'{type(self).__name__}('
            f'fullname: {self.fullname!r}, '
            f'value: {self.output.value}, '
            f'configFile: {self.configFile}'
            ')'
        )


class Slider(Parameter):
    def __init__(self, fullname, minValue=0., maxValue=INF, **kwargs):
        assert minValue < maxValue
        super().__init__(fullname, **kwargs)
        self.minValue = minValue
        self.maxValue = maxValue

        self.reload()

    def validate(self, value):
        return clip(value, self.minValue, self.maxValue)


class SingleSelection(Parameter):
    def __init__(self, fullname, possibilities, default=None, **kwargs):
        if default is None:
            default = []

        super().__init__(fullname, default=default, **kwargs)
        self.possibilities = set(possibilities)

        self.reload()

    def validate(self, value):
        assert value in self.possibilities
        return value


class MultiSelection(Parameter):
    def __init__(self, fullname, possibilities, default=None, **kwargs):
        if default is None:
            default = []

        super().__init__(fullname, default=default, **kwargs)
        self.possibilities = set(possibilities)

        self.reload()

    def validate(self, value):
        return list(set(value) - self.possibilities)


class MotionSelection(Parameter):
    def __init__(self, fullname, default=None, content=None, **kwargs):
        if content is None:
            content = Content.single_instance_setdefault()

        super().__init__(fullname, default=default, **kwargs)
        self.content = content

        self.reload()

    def validate(self, motions):
        if isinstance(motions, str):
            motions = [motions]

        repertoire = set(self.content._sorted_names())
        return list(repertoire.intersection(motions))

    #def on_content_changed(self):
    #    self.possibilities = set(self.content._sorted_names())
