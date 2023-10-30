from unittest import TestCase
from lockable.resource_filter import get_matching_resources


class TestResourceFilter(TestCase):
    def test_resource_filter_empty_list(self):
        candidates = get_matching_resources([], {})
        self.assertEqual(candidates, [])

    def test_all_pass(self):
        options = [{"id": 1}, {"id": 2}]
        candidates = get_matching_resources(options, {})
        self.assertEqual(candidates, options)

    def test_one_pass(self):
        options = [{"id": 1}, {"id": 2}]
        candidates = get_matching_resources(options, {"id": 1})
        self.assertEqual(candidates, [{"id": 1}])

    def test_get_matching_resources_without_has_field(self):
        resource_list = [{'id': 1, 'name': 'resource1'},
                         {'id': 2, 'name': 'resource2'}]
        requirements = {'id': 1}
        self.assertEqual(get_matching_resources(resource_list, requirements),
                         [resource_list[0]])

    def test_get_matching_resources_with_has_field_true(self):
        resource_list = [{'id': 1, 'name': 'resource1'},
                         {'id': 2, 'name': 'resource2', 'field': '1'}]
        requirements = {'field': {"$exists": True}}
        self.assertEqual([resource_list[1]],
                         get_matching_resources(resource_list, requirements))

    def test_get_matching_resources_with_has_field_false(self):
        resource_list = [{'id': 1, 'name': 'resource1', 'field': '1'},
                         {'id': 2, 'name': 'resource2'}]
        requirements = {'field': {"$exists": False}}
        self.assertEqual([resource_list[1]],
                         get_matching_resources(resource_list, requirements))

    def test_get_matching_resources_with_in(self):
        resource_list = [{'id': 1, 'name': 'resource1', 'field': '1'},
                         {'id': 2, 'name': 'resource2', 'field': '2'},
                         {'id': 3, 'name': 'resource3', 'field': '3'}]
        requirements = {'field': {"$in": ['1', '3']}}
        self.assertEqual([resource_list[0], resource_list[2]],
                         get_matching_resources(resource_list, requirements))

    def test_get_matching_resources_without_in(self):
        resource_list = [{'id': 1, 'name': 'resource1', 'field': '1'},
                         {'id': 2, 'name': 'resource2', 'field': '2'},
                         {'id': 3, 'name': 'resource3', 'field': '3'}]
        requirements = {'field': {"$in": []}}
        self.assertEqual([],
                         get_matching_resources(resource_list, requirements))

    def test_get_matching_resources_with_nin(self):
        resource_list = [{'id': 1, 'name': 'resource1', 'field': '1'},
                         {'id': 2, 'name': 'resource2', 'field': '2'},
                         {'id': 3, 'name': 'resource3', 'field': '3'}]
        requirements = {'field': {"$nin": ['1', '3']}}
        self.assertEqual([resource_list[1]],
                         get_matching_resources(resource_list, requirements))

    def test_get_matching_resources_without_nin(self):
        resource_list = [{'id': 1, 'name': 'resource1', 'field': '1'},
                         {'id': 2, 'name': 'resource2', 'field': '2'},
                         {'id': 3, 'name': 'resource3', 'field': '3'}]
        requirements = {'field': {"$nin": []}}
        self.assertEqual(resource_list,
                         get_matching_resources(resource_list, requirements))

    def test_get_matching_raises_invalid_exists(self):
        resource_list = [{'id': 1, 'name': 'resource1', 'field': '1'}]
        requirements = {'field': {"$exists": 1}}
        with self.assertRaises(AssertionError):
            get_matching_resources(resource_list, requirements)

    def test_get_matching_raises_invalid_in(self):
        resource_list = [{'id': 1, 'name': 'resource1', 'field': '1'}]
        requirements = {'field': {"$in": 1}}
        with self.assertRaises(AssertionError):
            get_matching_resources(resource_list, requirements)

    def test_get_matching_raises_invalid_nin(self):
        resource_list = [{'id': 1, 'name': 'resource1', 'field': '1'}]
        requirements = {'field': {"$nin": 1}}
        with self.assertRaises(AssertionError):
            get_matching_resources(resource_list, requirements)

    def test_get_matching_resources_with_regex(self):
        resource_list = [{'id': 1, 'name': 'resource1', 'field': '1'},
                         {'id': 2, 'name': 'resource2', 'field': '2'},
                         {'id': 3, 'name': 'resource3', 'field': '3'}]
        requirements = {'name': {"$regex": 'ce3'}}
        self.assertEqual([resource_list[2]],
                         get_matching_resources(resource_list, requirements))
