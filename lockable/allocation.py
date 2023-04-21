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
        # if there is {<field>: {$exists: true}} in requirements, filter out resources
        # that does not have the field. if value is false, filter out resources that have the field.
        def in_filter(resource):
            """ Check if resource matches requirements """
            for key, value in requirements.items():
                if isinstance(value, dict) and '$exists' in value:
                    if value['$exists'] and key not in resource:
                        return False
                    if not value['$exists'] and key in resource:
                        return False
                elif key not in resource or resource[key] != value:
                    return False
            return True
        return filter_(resource_list, in_filter)
