import unittest
import collections

from being.params import IMPLEMENTATIONS, _TomlConfig


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


class TestConfig(unittest.TestCase):
    def test_initial_data_is_dict_like(self):
        for implType in IMPLEMENTATIONS.values():
            impl = implType()
            self.assertEqual(impl.data, {})

    def test_new_config_is_empty(self):
        for implType in IMPLEMENTATIONS.values():
            impl = implType()
            self.assertEqual(impl.data, {})

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

            self.assertIn('This', impl.data)
            self.assertIn('is', impl.data['This'])
            self.assertIn('it', impl.data['This']['is'])

    #def test_json_does_not_support_comments(self):
    #    pass

    def test_loading_and_dumping_leaves_data_untouched(self):
        a = _TomlConfig()
        a.loads(SOME_TOML)

        b = _TomlConfig()
        b.loads(a.dumps())

        self.assertEqual(a.data, b.data)


    #def test_yaml_preserves_comments(self):
    #    pass

    def test_toml_preserves_comments(self):
        config = _TomlConfig()
        config.loads(SOME_TOML)

        self.assertEqual(SOME_TOML, config.dumps())


if __name__ == '__main__':
    unittest.main()
