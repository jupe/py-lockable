""" lockable library """
from contextlib import contextmanager
from datetime import datetime
import json
import logging
import os
import random
import socket
import time
import tempfile

from mongoquery import Query, QueryError
from pid import PidFile, PidFileError

from lockable.allocation import Allocation
from lockable.provider_helpers import create as create_provider
from lockable.unflatten import unflatten

MODULE_LOGGER = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 1000


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

    def __init__(self,
                 hostname=socket.gethostname(),
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
    def parse_str_requirements(requirements_str: str) -> dict:
        """ Parse string requirements """
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
        return unflatten(requirements)

    @staticmethod
    def parse_requirements(requirements_str: (str or dict)) -> dict:
        """ Parse requirements """
        if not requirements_str:
            return {}
        if isinstance(requirements_str, dict):
            return requirements_str
        assert isinstance(requirements_str, str), 'requirements must be string or dict'
        requirements_str = requirements_str.strip()  # remove leading and trailing spaces
        if requirements_str.startswith('{'):
            try:
                return json.loads(requirements_str)
            except json.decoder.JSONDecodeError as error:
                raise ValueError(str(error)) from error
        return Lockable.parse_str_requirements(requirements_str)

    @staticmethod
    def _filter_resources(resources, requirement):
        """Filter resources using mongoquery."""
        try:
            query = Query(requirement)
        except QueryError as error:
            raise ValueError(str(error)) from error
        return list(filter(query.match, resources))

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
        if not isinstance(requirements, list):
            requirements = [requirements]
        abort_after = timeout_s
        start = time.time()

        current_allocations = []
        fulfilled_requirement_indexes = []
        while True:
            for index, req in enumerate(requirements):
                if index in fulfilled_requirement_indexes:
                    continue
                for candidate in candidates:
                    # Skip resources that are already allocated by same lockable instance.
                    if candidate.get('id') in self._allocations:
                        continue

                    try:
                        allocation = self._try_lock(req, candidate)
                        MODULE_LOGGER.debug('resource %s allocated (%s), alloc_id: (%s)',
                                            allocation.resource_id,
                                            json.dumps(allocation.resource_info),
                                            allocation.alloc_id)
                        self._allocations[allocation.resource_id] = allocation
                        current_allocations.append(allocation)
                        fulfilled_requirement_indexes.append(index)
                        break
                    except AssertionError:
                        pass

            # All resources allocated
            if len(requirements) == len(current_allocations):
                break

            # Check if timeout occurs. No need to be high resolution timeout.
            # in first loop we should first check before giving up.
            delta = time.time() - start
            if delta >= abort_after:
                # Unlock all already done allocations
                # pylint: disable=expression-not-assigned
                [allocation.unlock() for allocation in current_allocations]
                MODULE_LOGGER.warning('Allocation timeout')
                raise TimeoutError(f'Allocation timeout ({timeout_s}s)')

            MODULE_LOGGER.debug('trying to lock after short period')
            time.sleep(retry_interval)

        return current_allocations

    def _lock(self, requirements, timeout_s, retry_interval=1) -> Allocation:
        """ Lock resource """
        local_resources = self._filter_resources(self.resource_list, requirements)
        random.shuffle(local_resources)
        ResourceNotFound.invariant(local_resources,
                                   f"Suitable resource not available, {requirements=}")
        return self._lock_some(requirements, local_resources, timeout_s, retry_interval)[0]

    def _lock_many(self, requirements, timeout_s, retry_interval=1) -> [Allocation]:
        """ Lock resource """
        local_resources = []
        for req in requirements:
            resources = self._filter_resources(self.resource_list, req)
            ResourceNotFound.invariant(resources,
                                       f"Suitable resource not available, {requirements=}")
            local_resources += resources
        # Unique resources by id
        local_resources = list({v['id']: v for v in local_resources}.values())
        ResourceNotFound.invariant(
            len(local_resources) >= len(requirements),
            f"Suitable resource not available, {requirements=}")
        random.shuffle(local_resources)
        return self._lock_some(requirements, local_resources, timeout_s, retry_interval)

    @staticmethod
    def _get_requirements(requirements, hostname):
        """ Generate requirements"""
        MODULE_LOGGER.debug('hostname: %s', hostname)
        merged = {'hostname': hostname, 'online': True}
        merged.update(requirements)
        allowed_to_del = ["online", "hostname"]
        for key in allowed_to_del:
            # allow to remove online requirement by set it to None
            if merged[key] is None:
                del merged[key]
        return merged

    def lock(self, requirements: (str or dict), timeout_s: int = DEFAULT_TIMEOUT) -> Allocation:
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
        allocation.allocation_queue_time = datetime.now() - begin
        return allocation

    def lock_many(self, requirements: list, timeout_s: int = DEFAULT_TIMEOUT) -> list:
        """
        Lock many resources
        :param requirements: resource requirements, list of string or dicts
        :param timeout_s: max duration to try to lock
        :return: List of allocation contexts
        """
        assert isinstance(self.resource_list, list), "resources list is not loaded"
        predicates = []
        for req in requirements:
            predicates.append(self._get_requirements(self.parse_requirements(req), self._hostname))
        self._provider.reload()
        begin = datetime.now()
        MODULE_LOGGER.debug("Use lock folder: %s", self._lock_folder)
        MODULE_LOGGER.debug("Requirements: %s", json.dumps(predicates))
        MODULE_LOGGER.debug("Resource list: %s", json.dumps(self.resource_list))

        allocations = self._lock_many(predicates, timeout_s)
        for allocation in allocations:
            allocation.allocation_queue_time = datetime.now() - begin
        return allocations

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
    def auto_lock(self,
                  requirements: (str or dict),
                  timeout_s: int = DEFAULT_TIMEOUT) -> Allocation:
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
