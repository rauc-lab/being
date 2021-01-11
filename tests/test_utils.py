import unittest

from being.utils import SingleInstanceCache


class Foo(SingleInstanceCache):

    """Test class."""

    pass


class TestSingleInstanceCache(unittest.TestCase):
    def setUp(self):
        Foo.clear()

    def test_initializing_an_instance_does_not_add_it_to_the_cache(self):
        foo = Foo()

        self.assertNotIn(Foo, Foo.INSTANCES)

    def test_constructing_an_instance_via_default_puts_it_int_the_cache(self):
        foo = Foo.default()

        self.assertIn(Foo, Foo.INSTANCES)

    def test_same_reference_in_cache(self):
        a = Foo.default()
        b = Foo.default()

        self.assertIs(a, b)


if __name__ == '__main__':
    unittest.main()
