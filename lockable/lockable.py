""" lockable library """
import random
import json
import socket
import os
import time
import tempfile
from datetime import datetime
from contextlib import contextmanager
from pydash import filter_, merge
from pid import PidFile, PidFileError
from lockable.provider_helpers import create as create_provider
from lockable.logger import get_logger
from lockable.allocation import Allocation

MODULE_LOGGER = get_logger()


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
        self._allocations = {}
        MODULE_LOGGER.debug('Initialized lockable')
        self._hostname = hostname
        self._lock_folder = lock_folder
        assert not (isinstance(resource_list, list) and
                    resource_list_file), 'only one of resource_list or ' \
                                         'resource_list_file is accepted, not both'
        if resource_list is None and resource_list_file is None:
            self._provider = create_provider([])
        else:
            self._provider = create_provider(resource_list_file or resource_list)

    @property
    def resource_list(self) -> list:
        """ Return current resources list"""
        return self._provider.data

    @staticmethod
    def parse_requirements(requirements_str: (str or dict)) -> dict:
        """ Parse requirements """
        if not requirements_str:
            return {}
        if isinstance(requirements_str, dict):
            return requirements_str
        try:
            return json.loads(requirements_str)
        except json.decoder.JSONDecodeError as error:
            if error.colno > 1:
                raise ValueError(str(error)) from error
        parts = requirements_str.split('&')
        requirements = {}
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
            MODULE_LOGGER.debug('Trying lock using: %s', os.path.join(self._lock_folder, pid_file))

            _lockable = PidFile(pidname=pid_file, piddir=self._lock_folder)
            _lockable.create()
            MODULE_LOGGER.info('Allocated: %s, lockfile: %s', resource_id, pid_file)

            def release():
                nonlocal self, resource_id, _lockable
                MODULE_LOGGER.info('Release resource: %s', resource_id)
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
        MODULE_LOGGER.debug('Total match local resources: %d, timeout: %d',
                            len(candidates), timeout_s)
        abort_after = timeout_s
        start = time.time()

        while True:
            for candidate in candidates:
                try:
                    allocation = self._try_lock(requirements, candidate)
                    MODULE_LOGGER.debug('resource %s allocated (%s), alloc_id: (%s)',
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
                MODULE_LOGGER.warning('Allocation timeout')
                raise TimeoutError(f'Allocation timeout ({timeout_s}s)')

            MODULE_LOGGER.debug('trying to lock after short period')
            time.sleep(retry_interval)

    def _lock(self, requirements, timeout_s, retry_interval=1) -> Allocation:
        """ Lock resource """
        local_resources = filter_(self.resource_list, requirements)
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
        assert isinstance(self.resource_list, list), 'resources list is not loaded'
        requirements = self.parse_requirements(requirements)
        predicate = self._get_requirements(requirements, self._hostname)
        # Refresh resources data
        self._provider.reload()
        begin = datetime.now()
        MODULE_LOGGER.debug("Use lock folder: %s", self._lock_folder)
        MODULE_LOGGER.debug("Requirements: %s", json.dumps(predicate))
        MODULE_LOGGER.debug("Resource list: %s", json.dumps(self.resource_list))
        allocation = self._lock(predicate, timeout_s)
        self._allocations[allocation.resource_id] = allocation
        allocation.allocation_queue_time = datetime.now() - begin
        return allocation

    def unlock(self, allocation: Allocation) -> None:
        """
        Method to release resource
        :param allocation: Allocation object.
        :return: None
        """
        assert 'id' in allocation.resource_info, 'missing "id" -key'
        MODULE_LOGGER.info('Release: %s', allocation.resource_id)
        resource_id = allocation.resource_id
        ResourceNotFound.invariant(resource_id in self._allocations, 'resource not locked')
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
