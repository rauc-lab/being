"""Parameter blocks can be used to control values inside the block network.
Their value are mirrored in a dedicated config file. All Parameter blocks appear
in the web UI and can be tweaked by the end user.

Example:
    >>> # !This will create / add to the config file in your current working directory!
    >>> slider = Slider('some/value', default=0.0, minValue=0.0, maxValue=10.0)
    ... slider.change(15.0)  # Will get clipped to `maxValue`
    ... print(slider.output.value)
    10.0
"""
from typing import Any, Optional, Iterable, List

from being.block import Block
from being.configs import ConfigFile, split_name
from being.content import Content
from being.configuration import CONFIG
from being.math import clip
from being.utils import SingleInstanceCache, unique


PARAMETER_CONFIG_FILEPATH = CONFIG['General']['PARAMETER_CONFIG_FILEPATH']


class ParamsConfigFile(ConfigFile, SingleInstanceCache):

    """Slim :class:`being.configs.ConfigFile` subclass so that we can use it
    with :class:`being.utils.SingleInstanceCache`.
    """

    def __init__(self, filepath=PARAMETER_CONFIG_FILEPATH):
        super().__init__(filepath)


class Parameter(Block):

    """Parameter block base class."""

    def __init__(self, fullname: str, configFile: Optional[ConfigFile] = None):
        """
        Args:
            fullname: Full name of config entry.
            configFile: Configuration file instance (DI). Default is
                :attr:`being.params.ParamsConfigFile` instance.
        """
        _, name = split_name(fullname)
        if configFile is None:
            configFile = ParamsConfigFile.single_instance_setdefault()

        super().__init__(name=name)
        self.add_value_output()
        self.fullname: str = fullname
        """Full name of config entry."""

        self.configFile: ConfigFile = configFile
        """Configuration file instance."""

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
        """Load value from Configuration file with default value (similar
        :meth:`dict.setdefault`).

        Args:
            default: Default value.
        """
        validated = self.validate(default)
        self.configFile.storedefault(self.fullname, validated)
        self.load()

    def change(self, value: Any):
        """Change value and store it to the config file.

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

    def __init__(self,
            fullname: str,
            default: Any = 0.0,
            minValue: float = 0.,
            maxValue: float = 1.,
            **kwargs,
        ):
        """
        Args:
            fullname: Full name of config entry.
            default (optional): Default value.
            minValue (optional): Minimum value.
            maxValue (optional): Maximum value.
            **kwargs: Arbitrary Parameter block keyword arguments.
        """
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

    def __init__(self,
            fullname: str,
            possibilities: Iterable,
            default: Optional[Any] = None,
            **kwargs,
        ):
        """
        Args:
            fullname: Full name of config entry.
            possibilities: All possibilities to choose from.
            default (optional): Default value. First entry of `possibilities` by
                default.
            **kwargs: Arbitrary Parameter block keyword arguments.
        """
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

    def __init__(self,
            fullname: str,
            possibilities: Iterable,
            default: Optional[List[Any]] = None,
            **kwargs,
        ):
        """
        Args:
            fullname: Full name of config entry.
            possibilities: All possibilities to choose from.
            default (optional): Default value(s). List of elements from
                `possibilities`. Nothing selected by default.
            **kwargs: Arbitrary Parameter block keyword arguments.
        """
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

    """Multiple motion selection. Similar to
    :class:`being.params.MultiSelection` but works with motions from
    :class:`being.content.Content` and can be updated.
    """

    def __init__(self,
            fullname: str,
            default: Optional[List[str]] = None,
            content: Optional[Content] = None,
            **kwargs,
        ):
        """
        Args:
            fullname: Full name of config entry.
            default (optional): Default motions. List of motion names. Nothing
                selected by default.
            content (optional): Content instance (DI).
            **kwargs: Arbitrary Parameter block keyword arguments.
        """
        if default is None:
            default = []

        if content is None:
            content = Content.single_instance_setdefault()

        possibilities = content.list_curve_names()
        super().__init__(fullname, possibilities, **kwargs)
        self.content = content
        self.loaddefault(default)

    def on_content_changed(self):
        """Callback function on content changed. Motion cleanup. Will reload
        possibilities from current motions.
        """
        self.possibilities = self.content.list_curve_names()
        self.load()
