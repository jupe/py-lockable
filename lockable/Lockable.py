""" Lockable plugin for robot-framework """
import random
import json
import socket
import os
import logging
import time
from contextlib import contextmanager
from uuid import uuid1
import tempfile
from pydash import filter_, merge, count_by
from pid import PidFile, PidFileError
from dataclasses import dataclass

from opcode import HAVE_ARGUMENT
from inspect import currentframe
from dis import opmap
from contextlib import contextmanager


def callable_contextmanager(func):
    def wrapper(*args, **kwargs):

        caller = currentframe().f_back
        last_opcode = caller.f_code.co_code[caller.f_lasti]
        # Warning! The following might not cover all possible cases
        last_size = 3 if last_opcode > HAVE_ARGUMENT else 1
        calling_opcode = caller.f_code.co_code[caller.f_lasti + last_size]

        if calling_opcode == opmap["SETUP_WITH"]:
            # Called within a context manager
            return contextmanager(func)(args, kwargs)
        else:
            # Called as a regular function
            return func(args, kwargs).next()

    return wrapper


@dataclass
class Reservation:
    """
    Reservation dataclass
    """
    requirements: dict
    resource_info: dict
    release: callable
    alloc_id: str = str(uuid1())

    @property
    def id(self):
        """ resource id getter """
        return self.resource_info['id']


class ResourceNotFound(Exception):
    """ Exception raised when resource not found """

    @staticmethod
    def invariant(true, message):
        """ Raise ResourceNotFound if not true with given message"""
        if not true:
            raise ResourceNotFound(message)


class Lockable:

    logger: logging.Logger = logging.getLogger("lockable")

    """
    Base class for Lockable. It handle low-level functionality.
    """
    def __init__(self, hostname=socket.gethostname(),
                 resource_list_file="resources.json",
                 lock_folder=tempfile.gettempdir()):
        self._resources = dict()
        self._logger = None
        self.logger.debug('Initialized lockable')
        self._hostname = hostname
        self._resource_list = Lockable.read_resources_list(resource_list_file)
        self._lock_folder = lock_folder

    @property
    def logger(self):
        if not self._logger:
            self._logger = logging.getLogger("lockable")
            if not self._logger.handlers:
                self._logger.addHandler(logging.StreamHandler())
            Lockable.logger = self._logger
        return self._logger

    def set_logger(self, logger):
        self._logger = logger
        Lockable.logger = logger

    @staticmethod
    def read_resources_list(filename):
        """ Read resources json file """
        Lockable.logger.debug(f'Read resource list file: {filename}')
        with open(filename) as json_file:
            try:
                data = json.load(json_file)
                assert isinstance(data, list), 'data is not an list'
            except (json.decoder.JSONDecodeError, AssertionError) as error:
                raise ValueError(f'invalid resources json file: {error}')
            Lockable.validate_json(data)
        return data

    @staticmethod
    def validate_json(data):
        counts = count_by(data, lambda obj: obj.get('id'))
        no_ids = filter_(counts.keys(), lambda key: key is None)
        if no_ids:
            raise ValueError('Invalid json, id property is missing')

        duplicates = filter_(counts.keys(), lambda key: counts[key] > 1)
        if duplicates:
            Lockable.logger.warn(f'Duplicates: {duplicates}')
            raise ValueError(f"Invalid json, duplicate ids in {duplicates}")

    @staticmethod
    def parse_requirements(requirements_str):
        """ Parse requirements """
        if isinstance(requirements_str, dict):
            return requirements_str
        if not requirements_str:
            return dict()
        try:
            return json.loads(requirements_str)
        except json.decoder.JSONDecodeError as error:
            if error.colno > 1:
                raise ValueError(str(error))
        parts = requirements_str.split('&')
        if len(parts) == 0:
            raise ValueError('no requirements given')
        requirements = dict()
        for part in parts:
            try:
                part.index("=")
            except ValueError:
                continue
            key, value = part.split('=')
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            requirements[key] = value
        return requirements

    def _try_lock(self, candidate):
        """ Function that tries to lock given candidate resource """
        resource_id = candidate.get("id")
        try:
            lock_file = os.path.join(self._lock_folder, f"{resource_id}.pid")
            self.logger.debug(f"Trying lock using: {lock_file}")

            _lockable = PidFile(pidname=lock_file)
            _lockable.check()
            self.logger.info(f'Allocated: {resource_id}, lockfile: {lock_file})')

            def release():
                nonlocal _lockable, self
                self.logger.info(f'Release resource: {resource_id}')
                _lockable.close()

            return candidate, release
        except PidFileError:
            raise AssertionError('no success')

    def _lock_some(self, candidates, timeout_s, retry_interval):
        """ Contextmanager that lock some candidate that is free and release it finally """
        self.logger.debug(f'Total match local resources: {len(candidates)}, timeout: {timeout_s}')
        abort_after = timeout_s
        start = time.time()

        while True:
            for candidate in candidates:
                try:
                    return self._try_lock(candidate)
                except AssertionError:
                    pass

            # Check if timeout occurs. No need to be high resolution timeout.
            # in first loop we should first check before giving up.
            delta = time.time() - start
            if delta >= abort_after:
                self.logger.warning(f'Allocation timeout')
                raise TimeoutError(f'Allocation timeout ({timeout_s}s)')

            self.logger.debug('trying to lock after short period')
            time.sleep(retry_interval)

        self.logger.debug(f'resource {resource["id"]} allocated ({json.dumps(resource)})')
        return resource, release

    def _lock(self, requirements: dict, timeout_s: int, retry_interval=1):
        """ Lock resource """
        local_resources = filter_(self._resource_list, requirements)
        random.shuffle(local_resources)
        ResourceNotFound.invariant(local_resources, "Suitable resource not available")
        resource, release = self._lock_some(local_resources, timeout_s, retry_interval)
        reservation = Reservation(requirements=requirements,
                                  resource_info=resource,
                                  release=release)
        return reservation

    @staticmethod
    def _get_requirements(requirements, hostname):
        """ Generate requirements"""
        Lockable.logger.debug(f'hostname: {hostname}')
        return merge(dict(hostname=hostname, online=True), requirements)

    def lock(self, requirements, timeout_s=1000, alloc_time_s=10):
        requirements = self.parse_requirements(requirements)
        predicate = self._get_requirements(requirements, self._hostname)
        self.logger.debug(f"Use lock folder: {self._lock_folder}")
        self.logger.debug(f"Requirements: {json.dumps(predicate)}")
        self.logger.debug(f"Resource list: {json.dumps(self._resource_list)}")
        reservation = self._lock(predicate, timeout_s)
        self._resources[reservation.id] = reservation
        return reservation

    def unlock(self, resource):
        self.logger.info('Release:', resource)
        resource_id = resource['id']
        ResourceNotFound.invariant(resource_id in self._resources.keys(), 'resource not locked')
        reservation = self._resources[resource_id]
        del self._resources[resource_id]
        reservation.release()

    @contextmanager
    def auto_lock(self, requirements: str, timeout_s: int = 0, alloc_time_s: int = None):
        allocator = self.lock(requirements=requirements, timeout_s=timeout_s, alloc_time_s=alloc_time_s)
        try:
            yield allocator.resource_info
        finally:
            allocator.release()
