# pylint: disable=missing-function-docstring,missing-class-docstring
""" Unit test for lockable pytest plugin """
import json
import unittest
import os
import socket
import time
from nose.tools import nottest
import multiprocessing as mp
from tempfile import mktemp
from contextlib import contextmanager
from lockable.plugin import read_resources_list, parse_requirements, lock, validate_json


HOSTNAME = socket.gethostname()


@contextmanager
def tmp_file(data):
    filename = mktemp()
    with open(filename, 'w') as file:
        file.write(data)
    yield filename
    os.unlink(filename)


@nottest
def run_test(index, req, devices, duration, timeout):
    print(f'waiting for test {index} resources')
    with lock(requirements=req, resource_list=devices, lock_folder='.', timeout_s=timeout, retry_interval=0.1):
        print(f'Run test {index}')
        time.sleep(duration)
        return index


class TestLockable(unittest.TestCase):

    def test_read_resources_list(self):
        data = []
        with tmp_file(json.dumps(data)) as filename:
            data = read_resources_list(filename)
            self.assertIsInstance(data, list)
            for obj in data:
                self.assertIsInstance(obj, dict)

    def test_parse_requirements(self):
        self.assertEqual(parse_requirements(""), dict())
        self.assertEqual(parse_requirements("a"), dict())
        self.assertEqual(parse_requirements("a=b"), dict(a='b'))
        self.assertEqual(parse_requirements("a=b&b=2&"), dict(a='b', b="2"))
        self.assertEqual(parse_requirements('{"a":"c"}'), dict(a='c'))
        self.assertEqual(parse_requirements('{"a":"c", "d":2}'), dict(a='c', d=2))

    def test_lock_success(self):
        requirements = dict(id=1)
        resource_list = [dict(hostame='12', id='1', online=True), dict(id=1, hostname=HOSTNAME, online=True)]
        with lock(requirements=requirements, resource_list=resource_list, lock_folder='.', timeout_s=1) as resource:
            self.assertTrue(os.path.exists('1.lock'))
            self.assertEqual(resource, resource_list[1])
        self.assertFalse(os.path.exists('1.lock'))

    def test_not_available(self):
        requirements = dict(id=1)
        resource_list = [dict(hostame='12', id='1', online=True)]
        try:
            with lock(requirements=requirements, resource_list=resource_list,
                      lock_folder='.', timeout_s=0.1):
                raise AssertionError('did not raise TimeoutError')
        except TimeoutError:
            pass
        self.assertFalse(os.path.exists('1.lock'))

    def test_not_online(self):
        requirements = dict(id=1)
        resource_list = [dict(hostame=HOSTNAME, id='1', online=False)]
        try:
            with lock(requirements=requirements, resource_list=resource_list,
                      lock_folder='.', timeout_s=0.1):
                raise AssertionError('did not raise TimeoutError')
        except TimeoutError:
            pass
        self.assertFalse(os.path.exists('1.lock'))

    def test_raise_pending_timeout(self):
        requirements = dict(id=1)
        resource_list = [dict(id=1, hostname=HOSTNAME, online=True)]
        with lock(requirements=requirements, resource_list=resource_list, lock_folder='.', timeout_s=1):
            self.assertTrue(os.path.exists('1.lock'))
            try:
                with lock(requirements=requirements, resource_list=resource_list, lock_folder='.',
                          timeout_s=0.1):
                    pass
            except TimeoutError:
                self.assertTrue(os.path.exists('1.lock'))
            else:
                raise AssertionError('did not raise TimeoutError')
        self.assertFalse(os.path.exists('1.lock'))

    def test_wait_pending_success(self):
        requirements = dict(id=1)
        resource_list = [dict(id=1, hostname=HOSTNAME, online=True)]
        parallel_count = 5
        pool = mp.Pool(parallel_count)

        results = []

        for index in range(parallel_count):
            results.append(pool.apply_async(run_test,
                                            args=(index,
                                                  requirements,
                                                  resource_list,
                                                  0.1,  # duration
                                                  5  # allocation timeout
                                                  )))

        pool.close()
        pool.join()

        results = [result.get() for result in results]
        results.sort()  # we don't care for now how was first - just that all got resolved

        expected = list(range(parallel_count))
        self.assertEqual(results, expected)

    def test_valid_json(self):
        data = [{"id": "12345"}]
        validate_json(data)

    def test_duplicate_id_in_json(self):
        data = [{"id": "1234"}, {"id": "12345"}, {"id": "12345"}]
        with self.assertRaises(AssertionError):
            validate_json(data)

    def test_missing_id_in_json(self):
        data = [{"a": "1234"}, {"id": "12345"}, {"id": "123456"}]
        with self.assertRaises(AssertionError):
            validate_json(data)
