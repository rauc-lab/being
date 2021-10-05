import io
import unittest

from being.configs import Config
from being.math import clip
from being.params import Parameter


class DummyConfigFile(Config):
    def __init__(self, configFormat=None):
        super().__init__(configFormat=configFormat)
        self.stream = io.StringIO()

    def save(self):
        self.stream = io.StringIO()
        self.impl.dump(self.stream)

    def reload(self):
        self.stream.seek(0)
        self.impl.load(self.stream)


class DummyParamter(Parameter):
    def __init__(self, fullname, default=0.0, minValue=0., maxValue=1., **kwargs):
        if maxValue < minValue:
            raise ValueError

        super().__init__(fullname, **kwargs)
        self.minValue = minValue
        self.maxValue = maxValue
        self.loaddefault(default)

    def validate(self, value):
        return clip(value, self.minValue, self.maxValue)


class TestParameter(unittest.TestCase):
    def test_block_name_is_last_part_of_fullname(self):
        c = DummyConfigFile()
        param = Parameter('this/is/it', configFile=c)

        self.assertEqual(param.fullname, 'this/is/it')
        self.assertEqual(param.name, 'it')

    def test_stored_value_is_on_output(self):
        c = DummyConfigFile('json')
        c.store('this/is/it', 42)
        c.save()
        param = Parameter('this/is/it', configFile=c)
        param.loaddefault(None)

        self.assertEqual(param.output.value, 42)

    def test_changed_value_is_on_output(self):
        c = DummyConfigFile('json')
        param = Parameter('this/is/it', configFile=c)
        param.loaddefault(None)
        param.change(value='hello, world!')

        self.assertEqual(param.output.value, 'hello, world!')

    def test_default_value_gets_validated_and_stored_in_config_file(self):
        c = DummyConfigFile('json')
        param = DummyParamter('this/is/it', default=1234, minValue=0, maxValue=10, configFile=c)

        self.assertEqual(c.retrieve('this/is/it'), 10)
        self.assertEqual(param.output.value, 10)

    def test_default_does_not_overwrite_existing_value_in_config_file(self):
        c = DummyConfigFile('json')
        c.store('this/is/it', 8)
        param = DummyParamter('this/is/it', default=0, minValue=0, maxValue=10, configFile=c)

        self.assertEqual(c.retrieve('this/is/it'), 8)
        self.assertEqual(param.output.value, 8)

    def test_retrieved_values_get_validated(self):
        c = DummyConfigFile('json')
        c.store('this/is/it', 42)
        param = DummyParamter('this/is/it', minValue=0, maxValue=10, configFile=c)

        self.assertEqual(c.retrieve('this/is/it'), 10)
        self.assertEqual(param.output.value, 10)

    def test_changing_validation_overwrites_value_in_config_file(self):
        c = DummyConfigFile('json')
        c.store('this/is/it', 42)
        self.assertEqual(c.retrieve('this/is/it'), 42)
        param = DummyParamter('this/is/it', minValue=0, maxValue=10, configFile=c)

        self.assertEqual(c.retrieve('this/is/it'), 10)

        param = DummyParamter('this/is/it', minValue=0, maxValue=5, configFile=c)

        self.assertEqual(c.retrieve('this/is/it'), 5)


if __name__ == '__main__':
    unittest.main()
