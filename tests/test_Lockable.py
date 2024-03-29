import dataclasses
from datetime import timedelta
import json
import logging
import mock
import os
import time
from contextlib import contextmanager
from tempfile import TemporaryDirectory
from unittest import TestCase

from lockable.lockable import Lockable, ResourceNotFound, Allocation


@contextmanager
def create_lockable(data=[{"id": 1, "hostname": "myhost", "online": True}], lock_folder=None):
    with TemporaryDirectory() as tmpdirname:
        lock_folder = lock_folder or tmpdirname
        yield Lockable(hostname='myhost', resource_list=data, lock_folder=lock_folder)


class LockableTests(TestCase):

    def setUp(self) -> None:
        logger = logging.getLogger('lockable')
        logger.handlers.clear()
        logger.addHandler(logging.NullHandler())

    def test_constructor(self):
        with TemporaryDirectory() as tmpdirname:
            list_file = os.path.join(tmpdirname, 'test.json')
            with open(list_file, 'w') as fp:
                fp.write('[]')
            lockable = Lockable(hostname='myhost', resource_list_file=list_file, lock_folder=tmpdirname)
            self.assertFalse(lockable._provider._resource_list_file_mtime is None)

    def test_resource_list(self):
        with TemporaryDirectory() as tmpdirname:
            list_file = os.path.join(tmpdirname, 'test.json')
            with open(list_file, 'w') as fp:
                fp.write('[{"id": "123"}]')
            lockable = Lockable(hostname='myhost', resource_list_file=list_file, lock_folder=tmpdirname)
            self.assertEqual(lockable.resource_list, [{"id": "123"}])

    def test_get_requirements(self):
        reqs = Lockable._get_requirements(dict(a=1), "myhost")
        self.assertEqual(reqs, {"online": True, "a": 1, "hostname": "myhost" })

        reqs = Lockable._get_requirements(dict(a=1, online=False), "myhost")
        self.assertEqual(reqs, {"online": False, "a": 1, "hostname": "myhost"})

        reqs = Lockable._get_requirements(dict(a=1, online=None), "myhost")
        self.assertEqual(reqs, {"a": 1, "hostname": "myhost"})

        reqs = Lockable._get_requirements(dict(a=1, hostname=None), "myhost")
        self.assertEqual(reqs, {"a": 1, "online": True})

    def test_reload_resource_list_file(self):
        with TemporaryDirectory() as tmpdirname:
            list_file = os.path.join(tmpdirname, 'test.json')
            with open(list_file, 'w') as fp:
                fp.write('[]')
            # mtime has at worst 1 second precision
            time.sleep(1)
            lockable = Lockable(hostname='myhost', resource_list_file=list_file, lock_folder=tmpdirname)
            lockable._provider._read_resources_list_file = mock.MagicMock(return_value=[])
            self.assertEqual(lockable._provider._read_resources_list_file.call_count, 0)
            lockable._provider.reload()
            self.assertEqual(lockable._provider._read_resources_list_file.call_count, 0)
            with open(list_file, 'w') as fp:
                fp.write('[1]')
            lockable._provider.reload()
            self.assertEqual(lockable._provider._read_resources_list_file.call_count, 1)
            # Check that stored mtime value is updated
            lockable._provider.reload()
            self.assertEqual(lockable._provider._read_resources_list_file.call_count, 1)

    def test_invalid_constructor(self):
        with self.assertRaises(AssertionError):
            Lockable(hostname='myhost', resource_list_file='asdf',
                     resource_list=[], lock_folder='.')

    def test_lock_require_resources_json_loaded(self):
        lockable = Lockable()
        with self.assertRaises(ResourceNotFound) as error:
            lockable.lock({"hostname": "test"})
        self.assertEqual(str(error.exception), "Suitable resource not available, requirements={'hostname': 'test', 'online': True}")

    def test_constructor_file_not_found(self):
        with TemporaryDirectory() as tmpdirname:
            list_file = os.path.join(tmpdirname, 'test.json')
            with self.assertRaises(FileNotFoundError):
                Lockable(hostname='myhost', resource_list_file=list_file, lock_folder=tmpdirname)

    def test_invalid_file(self):
        with TemporaryDirectory() as tmpdirname:
            list_file = os.path.join(tmpdirname, 'test.json')
            with open(list_file, 'w') as fp:
                fp.write('[s]')
            with self.assertRaises(ValueError):
                Lockable(hostname='myhost', resource_list_file=list_file, lock_folder=tmpdirname)

    def test_missing_id(self):
        with TemporaryDirectory() as tmpdirname:
            list_file = os.path.join(tmpdirname, 'test.json')
            with open(list_file, 'w') as fp:
                fp.write('[{}]')
            with self.assertRaises(ValueError):
                Lockable(hostname='myhost', resource_list_file=list_file, lock_folder=tmpdirname)

    def test_duplicate_id(self):
        with TemporaryDirectory() as tmpdirname:
            list_file = os.path.join(tmpdirname, 'test.json')
            with open(list_file, 'w') as fp:
                fp.write('[{"id": "1"}, {"id":  "1"}]')
            with self.assertRaises(ValueError):
                Lockable(hostname='myhost', resource_list_file=list_file, lock_folder=tmpdirname)

    def test_parse_requirements(self):
        self.assertEqual(Lockable.parse_requirements(''), {})
        self.assertEqual(Lockable.parse_requirements('{}'), {})
        self.assertEqual(Lockable.parse_requirements({'a': 'b'}), {'a': 'b'})
        self.assertEqual(Lockable.parse_requirements('a=b'), {"a": "b"})
        self.assertEqual(Lockable.parse_requirements('a=true'), {"a": True})
        self.assertEqual(Lockable.parse_requirements('a=False'), {"a": False})
        self.assertEqual(Lockable.parse_requirements('a=b&c=d'), {"a": "b", "c": "d"})
        self.assertEqual(Lockable.parse_requirements('{"a":"b","c":"d"}'), {"a": "b", "c": "d"})
        with self.assertRaises(ValueError):
            Lockable.parse_requirements('{')
        with self.assertRaises(AssertionError):
            Lockable.parse_requirements(1)
        with self.assertRaises(ValueError):
            Lockable.parse_requirements('a')
        with self.assertRaises(ValueError):
            Lockable.parse_requirements('a=')
        with self.assertRaises(ValueError):
            Lockable.parse_requirements('{"a":"b","c":"d}')
        with self.assertRaises(ValueError):
            Lockable.parse_requirements('{\na=b}')

    def test_lock_resource_not_found(self):
        with create_lockable([]) as lockable:
            with self.assertRaises(ResourceNotFound):
                lockable.lock({})

    def test_lock_timeout_0(self):
        with create_lockable([{"id": 1, "hostname": "myhost", "online": True}]) as lockable:
            lock_file = os.path.join(lockable._lock_folder, "1.pid")
            with open(lock_file, 'w') as fp:
                fp.write(f'{os.getpid()}')
            with self.assertRaises(TimeoutError):
                lockable.lock({}, timeout_s=0)
            os.unlink(lock_file)

    def test_lock_timeout_0_success(self):
        with create_lockable([{"id": 1, "hostname": "myhost", "online": True}],
                             lock_folder='.') as lockable:
            lockable._provider._read_resources_list_file = mock.MagicMock(return_value=[])
            lock_file = os.path.join(".", "1.pid")
            object = lockable.lock({}, timeout_s=0)
            self.assertTrue(os.path.exists(lock_file))
            object.release(object.alloc_id)
            self.assertFalse(os.path.exists(lock_file))

    def test_lock_timeout_1(self):
        with create_lockable([{"id": 1, "hostname": "myhost", "online": True}]) as lockable:
            lock_file = os.path.join(lockable._lock_folder, "1.pid")
            with open(lock_file, 'w') as fp:
                fp.write(f'{os.getpid()}')
            with self.assertRaises(TimeoutError):
                lockable.lock({}, timeout_s=1)
            os.unlink(lock_file)

    def test_unlock(self):
        with create_lockable([{"id": 1, "hostname": "myhost", "online": True}]) as lockable:
            lock_file = os.path.join(lockable._lock_folder, "1.pid")

            allocation = lockable.lock({}, timeout_s=0)
            self.assertIsInstance(allocation, Allocation)
            self.assertTrue(os.path.exists(lock_file))

            with self.assertRaises(AssertionError):
                alloc = dataclasses.replace(allocation)
                alloc.alloc_id = '123'
                lockable.unlock(alloc)

            with self.assertRaises(ResourceNotFound):
                alloc = dataclasses.replace(allocation)
                alloc.resource_info = alloc.resource_info.copy()
                alloc.resource_info['id'] = '2'
                lockable.unlock(alloc)

            lockable.unlock(allocation)
            self.assertFalse(os.path.exists(lock_file))

    def test_lock_offline(self):
        with TemporaryDirectory() as tmpdirname:
            list_file = os.path.join(tmpdirname, 'test.json')
            with open(list_file, 'w') as fp:
                fp.write('[{"id": 1, "hostname": "myhost", "online": false}]')
            lock_file = os.path.join(tmpdirname, '1.pid')
            lockable = Lockable(hostname='myhost', resource_list_file=list_file, lock_folder=tmpdirname)
            self.assertFalse(os.path.exists(lock_file))
            with self.assertRaises(ResourceNotFound):
                self.assertFalse(os.path.exists(lock_file))
                lockable.lock({}, timeout_s=0)
            self.assertFalse(os.path.exists(lock_file))

    def test_auto_lock(self):
        with TemporaryDirectory() as tmpdirname:
            list_file = os.path.join(tmpdirname, 'test.json')
            resource_info = {"id": 1, "hostname": "myhost", "online": True}
            with open(list_file, 'w') as fp:
                fp.write(f'[{json.dumps(resource_info)}]')
            lockable = Lockable(hostname='myhost', resource_list_file=list_file, lock_folder=tmpdirname)
            lock_file = os.path.join(tmpdirname, '1.pid')
            self.assertFalse(os.path.exists(lock_file))
            with lockable.auto_lock({}) as context:
                resource = context.resource_info
                self.assertEqual(resource, resource_info)
                self.assertTrue(os.path.exists(lock_file))
            self.assertFalse(os.path.exists(lock_file))

    def test_lock_many(self):
        with TemporaryDirectory() as tmpdirname:
            resources = [
                {"id": "1", "hostname": "myhost", "online": True},
                {"id": "2", "hostname": "myhost", "online": True}
            ]
            lockable = Lockable(hostname='myhost', resource_list=resources, lock_folder=tmpdirname)
            self.assertFalse(os.path.exists(os.path.join(tmpdirname, '1.pid')))
            self.assertFalse(os.path.exists(os.path.join(tmpdirname, '2.pid')))
            allocations = lockable.lock_many(['id=1', 'id=2'], timeout_s=0)
            self.assertTrue(allocations[0].allocation_queue_time < timedelta(seconds=1))
            self.assertTrue(allocations[1].allocation_queue_time < timedelta(seconds=1))
            self.assertTrue(os.path.exists(os.path.join(tmpdirname, '1.pid')))
            self.assertTrue(os.path.exists(os.path.join(tmpdirname, '2.pid')))
            lockable.unlock(allocations[0])
            lockable.unlock(allocations[1])
            self.assertFalse(os.path.exists(os.path.join(tmpdirname, '1.pid')))
            self.assertFalse(os.path.exists(os.path.join(tmpdirname, '2.pid')))

    def test_lock_many_can_not_fulfill(self):
        with TemporaryDirectory() as tmpdirname:
            resources = [
                {"id": "a", "hostname": "myhost", "online": True},
                {"id": "b", "hostname": "myhost", "online": True},
                {"id": "c", "hostname": "myhost", "online": True},
                {"id": "d", "hostname": "myhost", "online": True},
                {"id": "e", "hostname": "myhost", "online": True}
            ]
            lockable = Lockable(hostname='myhost', resource_list=resources, lock_folder=tmpdirname)
            with self.assertRaises(ResourceNotFound):
                lockable.lock_many(['id=a', 'id=x'], timeout_s=0)
            self.assertFalse(os.path.exists(os.path.join(tmpdirname, 'a.pid')))
            self.assertFalse(os.path.exists(os.path.join(tmpdirname, 'x.pid')))

            with self.assertRaises(ResourceNotFound):
                lockable.lock_many(['id=a', 'id=a'], timeout_s=0)
            self.assertFalse(os.path.exists(os.path.join(tmpdirname, 'a.pid')))

    def test_lock_many_existing_allocation(self):
        with TemporaryDirectory() as tmpdirname:
            resources = [
                {"id": "a", "hostname": "myhost", "online": True},
                {"id": "b", "hostname": "myhost", "online": True},
                {"id": "c", "hostname": "myhost", "online": True},
                {"id": "d", "hostname": "myhost", "online": True},
                {"id": "e", "hostname": "myhost", "online": True}
            ]

            lockable = Lockable(hostname='myhost', resource_list=resources, lock_folder=tmpdirname)
            allocations = lockable.lock_many(['id=a'], timeout_s=0)
            self.assertTrue(os.path.exists(os.path.join(tmpdirname, 'a.pid')))

            start = time.time()
            with self.assertRaises(TimeoutError):
                lockable.lock_many(['id=a', 'id=b'], timeout_s=1)
            end = time.time()
            self.assertTrue(end - start < 2 and end - start > 1)
            self.assertTrue(os.path.exists(os.path.join(tmpdirname, 'a.pid')))
            self.assertFalse(os.path.exists(os.path.join(tmpdirname, 'b.pid')))
