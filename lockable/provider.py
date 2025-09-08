""" Provider library """
from abc import ABC, abstractmethod
import json
import logging
import typing
from typing import List

from lockable.lockable import log_with_group
from collections import Counter

MODULE_LOGGER = logging.getLogger(__name__)


class ProviderError(Exception):
    """ Provider error """


class Provider(ABC):
    """ Abstract Provider """
    def __init__(self, uri: typing.Union[str, list]):
        """ Provider constructor """
        self._uri = uri
        self._resources = []
        self.reload()

    @property
    def data(self) -> list:
        """ Get resources list """
        return self._resources

    @abstractmethod
    def reload(self) -> None:  # pragma: no cover
        """ Reload resources data"""

    def set_resources_list(self, resources_list: list):
        """ Load resources list """
        assert isinstance(resources_list, list), 'resources_list is not an list'
        Provider._validate_json(resources_list)
        self._resources = resources_list
        
        log_with_group(MODULE_LOGGER, 'Resources loaded:', json.dumps(self._resources, indent=2))

    @staticmethod
    def _validate_json(data: List[dict]):
        """ Internal method to validate resources.json content """
        counts = Counter(obj.get('id') for obj in data)
        no_ids = [key for key in counts.keys() if key is None]
        if no_ids:
            raise ValueError('Invalid json, id property is missing')

        duplicates = [key for key, value in counts.items() if value > 1]
        if duplicates:
            log_with_group(MODULE_LOGGER, f'Duplicates: {duplicates}')
            raise ValueError(f"Invalid json, duplicate ids in {duplicates}")
