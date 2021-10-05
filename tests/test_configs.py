import io
import unittest

from being.configs import (
    IMPLEMENTATIONS,
    _ConfigImpl,
    _IniConfig,
    _JsonConfig,
    _TomlConfig,
    _YamlConfig,
    Config,
)


SOME_TOML = """
# This is a TOML document.

title = "TOML Example"

[owner]
name = "Tom Preston-Werner"
dob = 1979-05-27T07:32:00-08:00 # First class dates

[database]
server = "192.168.1.1"
ports = [ 8000, 8001, 8002 ]
connection_max = 5000
enabled = true

[servers]

  # Indentation (tabs and/or spaces) is allowed but not required
  [servers.alpha]
  ip = "10.0.0.1"
  dc = "eqdc10"

  [servers.beta]
  ip = "10.0.0.2"
  dc = "eqdc10"

[clients]
data = [ ["gamma", "delta"], [1, 2] ]

# Line breaks are OK when inside arrays
hosts = [
  "alpha",
  "omega"
]
"""

SOME_YAML = """
---
 # Doe is a dear funny deer
 doe: "a deer, a female deer"
 ray: "a drop of golden sun"
 pi: 3.14159
 xmas: true  # xmas is not cancelled this year
 french-hens: 3
 calling-birds:
   - huey
   - dewey
   - louie
   - fred
 xmas-fifth-day:
   calling-birds: four
   french-hens: 3
   golden-rings: 5
   partridges:
     count: 1
     location: "a pear tree"
   turtle-doves: two
"""

INI_SAMPLE = """[General]
INTERVAL = 0.01# Single cycle interval duration
[Behavior]# Behavior related configurations
Attention Span = 1.234# Minimum duration inside State II. In [sec]
Motions for State I = Sleepy One, Sleepy Two# Motion repertoire for sleepy State I
Motions for State II = Chilled, blue swirl# Motion repertoire for chilled State II
Motions for State III = Excited v2, Fireworks# Motion repertoire for excited State III
"""


JSON_SAMPLE = """{
    "General": {
        "INTERVAL": 0.01
    },
    "Behavior": {
        "Attention Span": 1.234,
        "Motions for State I": [
            "Sleepy One",
            "Sleepy Two"
        ],
        "Motions for State II": [
            "Chilled",
            "blue swirl"
        ],
        "Motions for State III": [
            "Excited v2",
            "Fireworks"
        ]
    }
}"""

YAML_SAMPLE = """General:
  INTERVAL: 0.01  # Single cycle interval duration
Behavior:  # Behavior related configurations
  Attention Span: 1.234  # Minimum duration inside State II. In [sec]
  Motions for State I: # Motion repertoire for sleepy State I
  - Sleepy One
  - Sleepy Two
  Motions for State II: # Motion repertoire for chilled State II
  - Chilled
  - blue swirl
  Motions for State III: # Motion repertoire for excited State III
  - Excited v2
  - Fireworks
"""

TOML_SAMPLE = """[General]
INTERVAL = 0.01 # Single cycle interval duration

[Behavior] # Behavior related configurations
"Attention Span" = 1.234 # Minimum duration inside State II. In [sec]
"Motions for State I" = ["Sleepy One", "Sleepy Two"] # Motion repertoire for sleepy State I
"Motions for State II" = ["Chilled", "blue swirl"] # Motion repertoire for chilled State II
"Motions for State III" = ["Excited v2", "Fireworks"] # Motion repertoire for excited State III"""


class TestConfig(unittest.TestCase):
    def test_none_config_format_is_ConfigImpl(self):
        config = Config(configFormat=None)

        self.assertIs(type(config.impl), _ConfigImpl)

    def test_initial_data_is_dict_like_and_empty(self):
        for implType in IMPLEMENTATIONS.values():
            impl = implType()
            self.assertEqual(impl, {})

    def test_config_impl_leaves_original_data_untouched(self):
        data = {}
        config = Config(data)

        self.assertIs(config.impl.data, data)

    def test_storing_nested_value_results_in_intermediate_keys(self):
        config = Config()
        name = 'This/is/it'
        value = 'Hello, world!'
        config.store(name, value)

        self.assertIn('This', config)
        self.assertIn('is', config['This'])
        self.assertIn('it', config['This']['is'])

    def test_stored_value_can_be_retrieved(self):
        config = Config()
        name = 'This/is/it'
        value = 'Hello, world!'
        config.store(name, value)

        self.assertEqual(config.retrieve(name), value)

    def test_storing_overwrites_values(self):
        config = Config()
        name = 'this/is/it'
        config.store(name, 42)
        config.store(name, 43)

        self.assertEqual(config.retrieve(name), 43)

    def test_storedefault_does_not_overwrite_existing_values(self):
        config = Config()
        name = 'this/is/it'
        config.storedefault(name, 42)
        config.storedefault(name, 43)

        self.assertEqual(config.retrieve(name), 42)

    def assert_round_trip_string(self, impl, string):
        """Assert round trip preservation with string (loads() / dumps())."""
        impl.loads(string)
        self.assertEqual(impl.dumps(), string)

    def assert_round_trip_stream(self, impl, string):
        """Assert round trip preservation with stream (load() / dump())."""
        in_ = io.StringIO(string)
        impl.load(io.StringIO(string))

        # Note: configobj.ConfigObj expects a byte stream for writing
        if type(impl) is _IniConfig:
            out = io.BytesIO()
        else:
            out = io.StringIO()

        impl.dump(out)
        out.seek(0)

        if type(impl) is _IniConfig:
            self.assertEqual(out.read(), string.encode())
        else:
            self.assertEqual(out.read(), string)

    def test_ini_preserves_round_trip(self):
        self.assert_round_trip_string(_IniConfig(), INI_SAMPLE)
        self.assert_round_trip_stream(_IniConfig(), INI_SAMPLE)

    def test_json_preserves_round_trip(self):
        self.assert_round_trip_string(_JsonConfig(), JSON_SAMPLE)
        self.assert_round_trip_stream(_JsonConfig(), JSON_SAMPLE)

    def test_yaml_preserves_round_trip(self):
        self.assert_round_trip_string(_YamlConfig(), YAML_SAMPLE)
        self.assert_round_trip_stream(_YamlConfig(), YAML_SAMPLE)

    def test_toml_preserves_round_trip(self):
        self.assert_round_trip_string(_TomlConfig(), TOML_SAMPLE)
        self.assert_round_trip_stream(_TomlConfig(), TOML_SAMPLE)

    def test_loading_and_dumping_leaves_data_untouched(self):
        # TOML
        a = _TomlConfig()
        a.loads(SOME_TOML)

        b = _TomlConfig()
        b.loads(a.dumps())

        self.assertEqual(a, b)

        # YAML
        a = _YamlConfig()
        a.loads(SOME_YAML)

        b = _YamlConfig()
        b.loads(a.dumps())

        self.assertEqual(a, b)

    def test_toml_preserves_comments(self):
        config = _TomlConfig()
        config.loads(SOME_TOML)

        self.assertEqual(config.dumps(), SOME_TOML)

    def test_yaml_preserves_comments(self):
        config = _YamlConfig()
        config.loads(SOME_YAML.strip())
        dump = config.dumps()

        self.assertIn('# Doe is a dear funny deer', dump)
        self.assertIn('# xmas is not cancelled this year', dump)

    #def test_json_does_not_support_comments(self):
    #    pass

    def test_clearing_config_does_not_alter_underlying_data_type(self):
        for implType in IMPLEMENTATIONS.values():
            impl = implType()
            typeAsItWas = type(impl.data)
            impl.clear()

            self.assertEqual(impl, {})
            self.assertIs(type(impl.data), typeAsItWas)

    # TODO: _IniConfig commenting test cases


if __name__ == '__main__':
    unittest.main()
