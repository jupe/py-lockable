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

    def test_key_with_only_dot(self):
        data = {".": "a"}
        with self.assertRaises(ValueError):  # Assuming you want to raise an error for invalid keys
            unflatten(data)

    def test_key_ending_with_dot(self):
        data = {"key.": "a"}
        with self.assertRaises(ValueError):
            unflatten(data)

    def test_key_starting_with_dot(self):
        data = {".key": "a"}
        with self.assertRaises(ValueError):
            unflatten(data)

    def test_multiple_consecutive_dots(self):
        data = {"key1..key2": "a"}
        with self.assertRaises(ValueError):
            unflatten(data)

    def test_non_string_keys(self):
        data = {1: "a"}
        with self.assertRaises(ValueError):
            unflatten(data)

    def test_value_as_dict_without_dot_key(self):
        data = {"key": {"nested": "value"}}
        expected = {"key": {"nested": "value"}}
        self.assertEqual(unflatten(data), expected)

    def test_mixed_types(self):
        data = {"key1": "a", "key2.key3": [1, 2, 3], "key4.key5.key6": {"nested": True}}
        expected = {"key1": "a", "key2": {"key3": [1, 2, 3]}, "key4": {"key5": {"key6": {"nested": True}}}}
        self.assertEqual(unflatten(data), expected)
