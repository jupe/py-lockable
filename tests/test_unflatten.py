import unittest
from lockable.unflatten import unflatten


class TestUnflatten(unittest.TestCase):

    def test_simple_keys(self):
        data = {"key": "a"}
        expected = {"key": "a"}
        self.assertEqual(unflatten(data), expected)

    def test_nested_keys(self):
        data = {"key": "a", "nested.key": "b"}
        expected = {'key': 'a', 'nested': {'key': 'b'}}
        self.assertEqual(unflatten(data), expected)

    def test_multiple_nested_keys(self):
        data = {"key": "a", "nested.key1": "b", "nested.key2": "c"}
        expected = {'key': 'a', 'nested': {'key1': 'b', 'key2': 'c'}}
        self.assertEqual(unflatten(data), expected)

    def test_deeply_nested_keys(self):
        data = {"key": "a", "nested.level1.level2": "b"}
        expected = {'key': 'a', 'nested': {'level1': {'level2': 'b'}}}
        self.assertEqual(unflatten(data), expected)

    def test_empty_dict(self):
        data = {}
        expected = {}
        self.assertEqual(unflatten(data), expected)
