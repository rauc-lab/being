import unittest
import collections

from being.configuration import IMPLEMENTATIONS, _TomlConfig, _YamlConfig


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


class TestConfig(unittest.TestCase):
    def test_initial_data_is_dict_like(self):
        for implType in IMPLEMENTATIONS.values():
            impl = implType()
            self.assertEqual(impl.nested, {})

    def test_new_config_is_empty(self):
        for implType in IMPLEMENTATIONS.values():
            impl = implType()
            self.assertEqual(impl.nested, {})

    def test_stored_value_can_be_retrieved(self):
        name = 'This/is/it'
        value = 'Hello, world!'
        for implType in IMPLEMENTATIONS.values():
            impl = implType()
            impl.store(name, value)
            ret = impl.retrieve(name)

            self.assertEqual(ret, value)

    def test_storing_nested_value_results_in_intermediate_keys(self):
        name = 'This/is/it'
        value = 'Hello, world!'
        for implType in IMPLEMENTATIONS.values():
            impl = implType()
            impl.store(name, value)

            self.assertIn('This', impl.nested)
            self.assertIn('is', impl.nested['This'])
            self.assertIn('it', impl.nested['This']['is'])

    def test_loading_and_dumping_leaves_data_untouched(self):
        # TOML
        a = _TomlConfig()
        a.loads(SOME_TOML)

        b = _TomlConfig()
        b.loads(a.dumps())

        self.assertEqual(a.nested, b.nested)

        # YAML
        a = _YamlConfig()
        a.loads(SOME_YAML)

        b = _YamlConfig()
        b.loads(a.dumps())

        self.assertEqual(a.nested, b.nested)

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

    def test_commenting_toml(self):
        # First level key
        toml = _TomlConfig()
        name = 'singleKey'
        toml.store(name, 'Hello')
        toml.set_comment(name, 'This is a comment')

        self.assertEqual(toml.dumps(), 'singleKey = "Hello" # This is a comment\n')

        # Multi level key
        toml = _TomlConfig()
        name = 'This/is/it'
        toml.store(name, 'Hello')
        toml.set_comment(name,  'This is a comment')

        self.assertEqual(toml.dumps(), '[This]\n[This.is]\nit = "Hello" # This is a comment\n')

    def test_commenting_yaml(self):
        # First level key
        yaml = _YamlConfig()
        name = 'singleKey'
        yaml.store(name, 'Hello')
        yaml.set_comment(name, 'This is a comment')

        self.assertEqual(yaml.dumps(), 'singleKey: Hello  # This is a comment\n')

        # Multi level key
        yaml = _YamlConfig()
        name = 'This/is/it'
        yaml.store(name, 'Hello')
        yaml.set_comment(name,  'This is a comment')

        self.assertEqual(yaml.dumps(), 'This:\n  is:\n    it: Hello  # This is a comment\n')

    def test_getting_comments_toml(self):
        s = 'hallo = "world"  # And this is a comment'
        toml = _TomlConfig()
        toml.loads(s)

        self.assertEqual(toml.get_comment('hallo'), 'And this is a comment')

        s = """[Header]
        [Header.Section]
        name = "something"    # This is another comment"""
        toml = _TomlConfig()
        toml.loads(s)

        self.assertEqual(toml.get_comment('Header/Section/name'), 'This is another comment')

    def test_getting_comments_yaml(self):
        s = 'hallo: world  # And this is a comment'
        yaml = _YamlConfig()
        yaml.loads(s)

        self.assertEqual(yaml.get_comment('hallo'), 'And this is a comment')

        s = """this:
          is:
            it: Hello, world!    # Unbelievable, yet another comment!
        """
        yaml = _YamlConfig()
        yaml.loads(s)

        self.assertEqual(yaml.get_comment('this/is/it'), 'Unbelievable, yet another comment!')

    def test_clearing_config_does_not_alter_underlying_data_type(self):
        for implType in IMPLEMENTATIONS.values():
            impl = implType()
            typeAsItWas = type(impl.nested.data)
            impl.nested.clear()

            self.assertEqual(impl.nested, {})
            self.assertIs(type(impl.nested.data), typeAsItWas)

    # TODO: _IniConfig commenting test cases


if __name__ == '__main__':
    unittest.main()
