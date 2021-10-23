""" Allocation context module """
from uuid import uuid1
from dataclasses import dataclass
from typing import Union
from datetime import datetime, timedelta


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
