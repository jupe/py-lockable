""" lockable library """
import random
import json
import socket
import os
import logging
import time
import tempfile
from dataclasses import dataclass
from contextlib import contextmanager
from uuid import uuid1
from pydash import filter_, merge, count_by
from pid import PidFile, PidFileError

MODULE_LOGGER = logging.getLogger('lockable')


@dataclass
class Allocation:
    """
    Reservation dataclass
    """
    requirements: dict
    resource_info: dict
    release: callable
    pid_file: str
    alloc_id: str = str(uuid1())

    @property
    def resource_id(self):
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
    """
    Base class for Lockable. It handle low-level functionality.
    """
    def __init__(self, hostname=socket.gethostname(),
                 resource_list_file=None,
                 lock_folder=tempfile.gettempdir()):
        self._resources = dict()
        self.logger = logging.getLogger('lockable.Lockable')
        self.logger.debug('Initialized lockable')
        self._hostname = hostname
        self._lock_folder = lock_folder
        self._resource_list = None
        if resource_list_file:
            self.load_resources_list(resource_list_file)
        else:
            self.logger.warning('resource_list_file is not configured')

    def load_resources_list(self, filename: str):
        """ Load resources list """
        self._resource_list = self._read_resources_list(filename)
        self.logger.debug('Resources: ')
        for resource in self._resource_list:
            self.logger.debug(json.dumps(resource))
        self.logger.warning('Use resources from %s file', filename)

    @staticmethod
    def _read_resources_list(filename):
        """ Read resources json file """
        MODULE_LOGGER.debug('Read resource list file: %s', filename)
        with open(filename) as json_file:
            try:
                data = json.load(json_file)
                assert isinstance(data, list), 'data is not an list'
            except (json.decoder.JSONDecodeError, AssertionError) as error:
                raise ValueError(f'invalid resources json file: {error}') from error
            Lockable._validate_json(data)
        return data

    @staticmethod
    def _validate_json(data):
        """ Internal method to validate resources.json content """
        counts = count_by(data, lambda obj: obj.get('id'))
        no_ids = filter_(counts.keys(), lambda key: key is None)
        if no_ids:
            raise ValueError('Invalid json, id property is missing')

        duplicates = filter_(counts.keys(), lambda key: counts[key] > 1)
        if duplicates:
            MODULE_LOGGER.warning('Duplicates: %s', duplicates)
            raise ValueError(f"Invalid json, duplicate ids in {duplicates}")

    @staticmethod
    def parse_requirements(requirements_str: (str or dict)):
        """ Parse requirements """
        if not requirements_str:
            return dict()
        if isinstance(requirements_str, dict):
            return requirements_str
        try:
            return json.loads(requirements_str)
        except json.decoder.JSONDecodeError as error:
            if error.colno > 1:
                raise ValueError(str(error)) from error
        parts = requirements_str.split('&')
        requirements = dict()
        for part in parts:
            try:
                part.index("=")
            except ValueError as error:
                raise ValueError(f'Missing value ({part})') from error
            key, value = part.split('=')
            if not value:
                raise ValueError(f'Missing value ({part})')
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            requirements[key] = value
        return requirements

    def _try_lock(self, requirements, candidate):
        """ Function that tries to lock given candidate resource """
        resource_id = candidate.get("id")
        try:
            pid_file = os.path.join(self._lock_folder, f"{resource_id}.pid")
            self.logger.debug('Trying lock using: %s', pid_file)

            _lockable = PidFile(pidname=pid_file)
            _lockable.create()
            self.logger.info('Allocated: %s, lockfile: %s', resource_id, pid_file)

            def release():
                nonlocal self, resource_id, _lockable
                self.logger.info('Release resource: %s', resource_id)
                _lockable.close()
                del self._resources[resource_id]

            return Allocation(requirements=requirements,
                              resource_info=candidate,
                              release=release,
                              pid_file=pid_file)
        except PidFileError as error:
            raise AssertionError('no success') from error

    def _lock_some(self, requirements, candidates, timeout_s, retry_interval):
        """ Contextmanager that lock some candidate that is free and release it finally """
        self.logger.debug('Total match local resources: %d, timeout: %d',
                          len(candidates), timeout_s)
        abort_after = timeout_s
        start = time.time()

        while True:
            for candidate in candidates:
                try:
                    allocation = self._try_lock(requirements, candidate)
                    self.logger.debug('resource %s allocated (%s)',
                                      allocation.resource_id, json.dumps(allocation.resource_info))
                    return allocation
                except AssertionError:
                    pass
            # Check if timeout occurs. No need to be high resolution timeout.
            # in first loop we should first check before giving up.
            delta = time.time() - start
            if delta >= abort_after:
                self.logger.warning('Allocation timeout')
                raise TimeoutError(f'Allocation timeout ({timeout_s}s)')

            self.logger.debug('trying to lock after short period')
            time.sleep(retry_interval)

    def _lock(self, requirements, timeout_s, retry_interval=1):
        """ Lock resource """
        local_resources = filter_(self._resource_list, requirements)
        random.shuffle(local_resources)
        ResourceNotFound.invariant(local_resources, "Suitable resource not available")
        return self._lock_some(requirements, local_resources, timeout_s, retry_interval)

    @staticmethod
    def _get_requirements(requirements, hostname):
        """ Generate requirements"""
        MODULE_LOGGER.debug('hostname: %s', hostname)
        return merge(dict(hostname=hostname, online=True), requirements)

    def lock(self, requirements: (str or dict), timeout_s: int = 1000):
        """
        Lock resource
        :param requirements: resource requirements
        :param timeout_s: timeout while trying to lock
        :return:
        """
        assert isinstance(self._resource_list, list), 'resources list is not loaded'
        requirements = self.parse_requirements(requirements)
        predicate = self._get_requirements(requirements, self._hostname)
        self.logger.debug("Use lock folder: %s", self._lock_folder)
        self.logger.debug("Requirements: %s", json.dumps(predicate))
        self.logger.debug("Resource list: %s", json.dumps(self._resource_list))
        reservation = self._lock(predicate, timeout_s)
        self._resources[reservation.resource_id] = reservation
        return reservation

    def unlock(self, resource: dict):
        """
        Method to release resource
        :param resource: resource object. 'id' property required.
        :return: None
        """
        assert 'id' in resource, 'missing "id" -key'
        self.logger.info('Release: %s', resource)
        resource_id = resource['id']
        ResourceNotFound.invariant(resource_id in self._resources.keys(), 'resource not locked')
        reservation = self._resources[resource_id]
        reservation.release()

    @contextmanager
    def auto_lock(self, requirements: (str or dict), timeout_s: int = 0):
        """
        contextmanaged lock method. Resource is released automatically after context ends.
        :param requirements: requirements
        :param timeout_s: timeout while trying to lock suitable resource
        :return: return resource info object
        """
        allocator = self.lock(requirements=requirements, timeout_s=timeout_s)
        try:
            yield allocator.resource_info
        finally:
            allocator.release()
