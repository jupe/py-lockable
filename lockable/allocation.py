""" Allocation context module """
from uuid import uuid1
from dataclasses import dataclass
from typing import Union
from datetime import datetime, timedelta

from pydash import filter_


@dataclass
class Allocation:
    """
    Reservation dataclass
    """
    requirements: dict
    resource_info: dict
    _release: callable
    pid_file: str
    allocation_queue_time: timedelta = None  # how long to wait before resource allocated
    allocation_start_time: datetime = datetime.now()
    release_time: Union[datetime, None] = None
    alloc_id: str = str(uuid1())

    def get(self, key):
        """ Get resource information by key """
        return self.resource_info.get(key)

    def __str__(self):
        info = ', '.join([f'{k}={v}' for k, v in self.resource_info.items()])
        return f'Allocation(queue_time: {self.allocation_queue_time}, resource_info: {info})'

    @property
    def resource_id(self):
        """ resource id getter """
        return self.resource_info['id']

    def release(self, alloc_id: str):
        """ Release resource when selecting alloc_id """
        assert self.alloc_id is not None, 'already released resource'
        assert self.alloc_id == alloc_id, 'Allocation id mismatch'
        self._release()
        self.alloc_id = None
        self.release_time = datetime.now()

    def unlock(self):
        """ Unlock/Release resource without alloc_id """
        self.release(self.alloc_id)

    @property
    def allocation_durations(self) -> timedelta:
        """
        Get allocation duration
        If allocation is not ended, returnallocation duration so far.
        """
        end_time = self.release_time or datetime.now()
        return end_time - self.allocation_start_time

    @staticmethod
    def get_matching_resources(resource_list: [{}], requirements: {}) -> [{}]:
        """ Get matching resources from resource list """
        # if there is requirement key "has_xx: <bool>",
        # make sure resource has that key if bool is True, or not if False
        # and remove that key from requirements
        for key, value in requirements.copy().items():
            if key.startswith('has_'):
                has_key = key.replace('has_', '')
                if value:
                    resource_list = [r for r in resource_list if has_key in r]
                else:
                    resource_list = [r for r in resource_list if has_key not in r]
                requirements.pop(key)

        return filter_(resource_list, requirements)
