import os
import logging
import json
from tempfile import TemporaryDirectory
from unittest import TestCase
from lockable.lockable import Lockable, ResourceNotFound


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
            Lockable(hostname='myhost', resource_list_file=list_file, lock_folder=tmpdirname)

    def test_lock_require_resources_json_loaded(self):
        lockable = Lockable()
        with self.assertRaises(AssertionError) as error:
            lockable.lock({})
        self.assertEqual(str(error.exception), 'resources list is not loaded')

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
            Lockable.parse_requirements('a')
        with self.assertRaises(ValueError):
            Lockable.parse_requirements('a=')
        with self.assertRaises(ValueError):
            Lockable.parse_requirements('{"a":"b","c":"d}')

    def test_lock_resource_not_found(self):
        with TemporaryDirectory() as tmpdirname:
            list_file = os.path.join(tmpdirname, 'test.json')
            with open(list_file, 'w') as fp:
                fp.write('[]')
            lockable = Lockable(hostname='myhost', resource_list_file=list_file, lock_folder=tmpdirname)
            with self.assertRaises(ResourceNotFound):
                lockable.lock({})

    def test_lock_timeout_0(self):
        with TemporaryDirectory() as tmpdirname:
            list_file = os.path.join(tmpdirname, 'test.json')
            with open(list_file, 'w') as fp:
                fp.write('[{"id": 1, "hostname": "myhost", "online": true}]')
            lock_file = os.path.join(tmpdirname, "1.pid")
            with open(lock_file, 'w') as fp:
                fp.write(f'{os.getpid()}')
            lockable = Lockable(hostname='myhost', resource_list_file=list_file, lock_folder=tmpdirname)
            with self.assertRaises(TimeoutError):
                lockable.lock({}, timeout_s=0)
            os.unlink(lock_file)

    def test_lock_timeout_0_success(self):
        with TemporaryDirectory() as tmpdirname:
            list_file = os.path.join(tmpdirname, 'test.json')
            with open(list_file, 'w') as fp:
                fp.write('[{"id": 1, "hostname": "myhost", "online": true}]')
            lock_file = os.path.join(tmpdirname, '1.pid')
            lockable = Lockable(hostname='myhost', resource_list_file=list_file, lock_folder=tmpdirname)
            object = lockable.lock({}, timeout_s=0)
            self.assertTrue(os.path.exists(lock_file))
            object.release()
            self.assertFalse(os.path.exists(lock_file))

    def test_lock_timeout_1(self):
        with TemporaryDirectory() as tmpdirname:
            list_file = os.path.join(tmpdirname, 'test.json')
            with open(list_file, 'w') as fp:
                fp.write('[{"id": 1, "hostname": "myhost", "online": true}]')
            lock_file = os.path.join(tmpdirname, "1.pid")
            with open(lock_file, 'w') as fp:
                fp.write(f'{os.getpid()}')
            lockable = Lockable(hostname='myhost', resource_list_file=list_file, lock_folder=tmpdirname)
            with self.assertRaises(TimeoutError):
                lockable.lock({}, timeout_s=1)
            os.unlink(lock_file)

    def test_unlock(self):
        with TemporaryDirectory() as tmpdirname:
            list_file = os.path.join(tmpdirname, 'test.json')
            with open(list_file, 'w') as fp:
                fp.write('[{"id": 1, "hostname": "myhost", "online": true}]')
            lock_file = os.path.join(tmpdirname, '1.pid')
            lockable = Lockable(hostname='myhost', resource_list_file=list_file, lock_folder=tmpdirname)

            with self.assertRaises(AssertionError):
                lockable.unlock({'a': 2})

            with self.assertRaises(ResourceNotFound):
                lockable.unlock({'id': 2})

            allocation = lockable.lock({}, timeout_s=0)
            self.assertTrue(os.path.exists(lock_file))
            lockable.unlock(allocation.resource_info)
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
            with lockable.auto_lock({}) as resource:
                self.assertEqual(resource, resource_info)
                self.assertTrue(os.path.exists(lock_file))
            self.assertFalse(os.path.exists(lock_file))
