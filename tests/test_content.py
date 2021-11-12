import unittest

from being.content import Content


class TestContent(unittest.TestCase):
    def test_exists(self):
        data = {'asdf.json': 1234}
        content = Content(directory=None, data=data)

        self.assertTrue(content.curve_exists('asdf'))
        self.assertFalse(content.curve_exists('bsdf'))

    def test_loading_gets_it_from_data(self):
        data = {'asdf.json': 1234}
        content = Content(directory=None, data=data)

        with self.assertRaises(KeyError):
            content.load_curve('qwer')

        self.assertEqual(content.load_curve('asdf'), 1234)

    def test_saving_stores_it_in_data(self):
        data = {}
        content = Content(directory=None, data=data)
        content.save_curve('asdf', 1234)

        self.assertEqual(data, {'asdf.json': 1234})

    def test_renaming_updates_dict(self):
        data = {'asdf.json': 1234}
        content = Content(directory=None, data=data)
        content.rename_curve('asdf', 'qwer')

        self.assertEqual(data, {'qwer.json': 1234})

    def test_non_existing_can_not_be_renamed(self):
        content = Content(directory=None, data={})
        with self.assertRaises(KeyError):
            content.rename_curve('asdf', 'bsdf')

    def test_find_next_free_name(self):
        data = {
            'Untitled.json': 1234,
            'Untitled 1.json': 1234,
            'Untitled 3.json': 1234,
        }
        content = Content(directory=None, data=data)
        freename = content.find_free_name('Untitled')

        self.assertEqual(freename, 'Untitled 2')


if __name__ == '__main__':
    unittest.main()
