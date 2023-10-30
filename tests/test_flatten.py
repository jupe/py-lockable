import unittest

from lockable.flatten import flatten_json, flatten_list


class TestFlattenJson(unittest.TestCase):

    def test_basic_flattening(self):
        data = {"a": {"b": 1}}
        result = flatten_json(data)
        self.assertEqual(result, {"a.b": 1})

    def test_multiple_level_flattening(self):
        data = {"a": {"b": {"c": 2}}}
        result = flatten_json(data)
        self.assertEqual(result, {"a.b.c": 2})

    def test_mixed_flattening(self):
        data = {"a": {"b": 1, "c": {"d": 2, "e": {"f": 3}}}, "g": 4}
        result = flatten_json(data)
        self.assertEqual(result, {'a.b': 1, 'a.c.d': 2, 'a.c.e.f': 3, 'g': 4})

    def test_empty_data(self):
        data = {}
        result = flatten_json(data)
        self.assertEqual(result, {})

    def test_non_nested_data(self):
        data = {"a": 1, "b": 2}
        result = flatten_json(data)
        self.assertEqual(result, data)

    def test_flatten_list_mixed(self):
        data = [{"a": 1, "b": 2}, {"a": {"b": {"c": 2}}}]
        result = flatten_list(data)
        self.assertEqual(result, [{'a': 1, 'b': 2}, {'a.b.c': 2}])

    def test_raise_if_overlapping_subfield(self):
        data = {"a": {"b": 1}, "a.b": 2}
        with self.assertRaises(AssertionError):
            flatten_json(data)
