import os
from tempfile import TemporaryDirectory
from unittest import TestCase
from lockable.Lockable import Lockable, ResourceNotFound


class LockableTests(TestCase):

    def setUp(self):
        Lockable.logger


    def test_constructor(self):
        with TemporaryDirectory() as tmpdirname:
            list_file = os.path.join(tmpdirname, 'test.json')
            with open(list_file, 'w') as fp:
                fp.write('[]')
            Lockable(hostname='myhost', resource_list_file=list_file, lock_folder=tmpdirname)

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
        self.assertEqual(Lockable.parse_requirements('{}'), {})
        self.assertEqual(Lockable.parse_requirements('a=b'), {"a": "b"})
        self.assertEqual(Lockable.parse_requirements('a=true'), {"a": True})
        self.assertEqual(Lockable.parse_requirements('a=False'), {"a": False})
        self.assertEqual(Lockable.parse_requirements('a=b&c=d'), {"a": "b", "c": "d"})
        self.assertEqual(Lockable.parse_requirements('{"a":"b","c":"d"}'), {"a": "b", "c": "d"})
        with self.assertRaises(ValueError):
            self.assertEqual(Lockable.parse_requirements('{"a":"b","c":"d}'), {"a": "b", "c": "d"})

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
            lockable = Lockable(hostname='myhost', resource_list_file=list_file, lock_folder=tmpdirname)
            object = lockable.lock({}, timeout_s=0)
            object.release()

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

    def test_lock_offline(self):
        with TemporaryDirectory() as tmpdirname:
            list_file = os.path.join(tmpdirname, 'test.json')
            with open(list_file, 'w') as fp:
                fp.write('[{"id": 1, "hostname": "myhost", "online": false}]')
            lockable = Lockable(hostname='myhost', resource_list_file=list_file, lock_folder=tmpdirname)
            with self.assertRaises(ResourceNotFound):
                lockable.lock({}, timeout_s=0)
