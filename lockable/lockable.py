""" lockable library """
import random
import json
import socket
import os
import logging
import time
import tempfile
from datetime import datetime
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
    _release: callable
    pid_file: str
    allocation_time: datetime = datetime.now()
    alloc_id: str = str(uuid1())

    @property
    def resource_id(self):
        """ resource id getter """
        return self.resource_info['id']

    def release(self, alloc_id):
        """ Release resource """
        assert self.alloc_id == alloc_id, 'Allocation id mismatch'
        self._release()
        self.alloc_id = None


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
                 resource_list=None,
                 lock_folder=tempfile.gettempdir()):
        self._allocations = dict()
        self.logger = logging.getLogger('lockable.Lockable')
        self.logger.debug('Initialized lockable')
        self._hostname = hostname
        self._lock_folder = lock_folder
        self._resource_list = None
        self._resource_list_file_mtime = None
        self._resource_list_file = resource_list_file
        assert not (isinstance(resource_list, list) and
                    resource_list_file), 'only one of resource_list or ' \
                                         'resource_list_file is accepted, not both'
        if isinstance(self._resource_list_file, str):
            self._resource_list_file_mtime = os.path.getmtime(resource_list_file)
            self.load_resources_list_file(self._resource_list_file)
        elif isinstance(resource_list, list):
            self.load_resources_list(resource_list)
        else:
            self.logger.warning('resource_list_file or resource_list is not configured')

    def load_resources_list_file(self, filename: str):
        """ Load resources list file"""
        self.load_resources_list(self._read_resources_list(filename))
        self.logger.warning('Use resources from %s file', filename)

    def load_resources_list(self, resources_list: list):
        """ Load resources list """
        assert isinstance(resources_list, list), 'resources_list is not an list'
        self._resource_list = resources_list
        self.logger.debug('Resources loaded: ')
        for resource in self._resource_list:
            self.logger.debug(json.dumps(resource))

    def reload_resource_list_file(self):
        """ Reload resources from file if file has been modified """
        if self._resource_list_file_mtime is None:
            return

        mtime = os.path.getmtime(self._resource_list_file)
        if self._resource_list_file_mtime != mtime:
            self._resource_list_file_mtime = mtime
            self.load_resources_list_file(self._resource_list_file)

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
    def parse_requirements(requirements_str: (str or dict)) -> dict:
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
            pid_file = f"{resource_id}.pid"
            self.logger.debug('Trying lock using: %s', os.path.join(self._lock_folder, pid_file))

            _lockable = PidFile(pidname=pid_file, piddir=self._lock_folder)
            _lockable.create()
            self.logger.info('Allocated: %s, lockfile: %s', resource_id, pid_file)

            def release():
                nonlocal self, resource_id, _lockable
                self.logger.info('Release resource: %s', resource_id)
                _lockable.close()
                del self._allocations[resource_id]

            return Allocation(requirements=requirements,
                              resource_info=candidate,
                              _release=release,
                              pid_file=_lockable.filename)
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
                    self.logger.debug('resource %s allocated (%s), alloc_id: (%s)',
                                      allocation.resource_id,
                                      json.dumps(allocation.resource_info),
                                      allocation.alloc_id)
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

    def lock(self, requirements: (str or dict), timeout_s: int = 1000) -> Allocation:
        """
        Lock resource
        :param requirements: resource requirements
        :param timeout_s: timeout while trying to lock
        :return: Allocation context
        """
        assert isinstance(self._resource_list, list), 'resources list is not loaded'
        self.reload_resource_list_file()
        requirements = self.parse_requirements(requirements)
        predicate = self._get_requirements(requirements, self._hostname)
        self.logger.debug("Use lock folder: %s", self._lock_folder)
        self.logger.debug("Requirements: %s", json.dumps(predicate))
        self.logger.debug("Resource list: %s", json.dumps(self._resource_list))
        allocation = self._lock(predicate, timeout_s)
        self._allocations[allocation.resource_id] = allocation
        return allocation

    def unlock(self, allocation: Allocation) -> None:
        """
        Method to release resource
        :param allocation: Allocation object.
        :return: None
        """
        assert 'id' in allocation.resource_info, 'missing "id" -key'
        self.logger.info('Release: %s', allocation.resource_id)
        resource_id = allocation.resource_id
        ResourceNotFound.invariant(resource_id in self._allocations.keys(), 'resource not locked')
        reservation = self._allocations[resource_id]
        reservation.release(allocation.alloc_id)

    @contextmanager
    def auto_lock(self, requirements: (str or dict), timeout_s: int = 0) -> Allocation:
        """
        contextmanaged lock method. Resource is released automatically after context ends.
        :param requirements: requirements
        :param timeout_s: timeout while trying to lock suitable resource
        :return: return Allocation object
        """
        allocator = self.lock(requirements=requirements, timeout_s=timeout_s)
        try:
            yield allocator
        finally:
            allocator.release(allocator.alloc_id)
