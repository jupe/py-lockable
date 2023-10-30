from unittest import TestCase
import logging
from lockable.allocation import Allocation, timedelta


class LockableTests(TestCase):

    def setUp(self) -> None:
        logger = logging.getLogger('lockable')
        logger.handlers.clear()
        logger.addHandler(logging.NullHandler())

    def test_allocation_object(self):
        alloc = Allocation(requirements={},
                           resource_info={'id': 1},
                           alloc_id=1,
                           pid_file=1,
                           _release=lambda: True)
        self.assertEqual(alloc.resource_id, 1)
        self.assertIsInstance(alloc.allocation_durations, timedelta)
        self.assertEqual(alloc.get('id'), 1)
        with self.assertRaises(AssertionError):
            alloc.release(2)
        alloc.release(1)
        with self.assertRaises(AssertionError):
            alloc.unlock()
        self.assertEqual(alloc.allocation_durations,
                         alloc.release_time - alloc.allocation_start_time)
        self.assertEqual(alloc.allocation_queue_time, None)
        self.assertEqual(str(alloc), 'Allocation(queue_time: None, resource_info: id=1)')
