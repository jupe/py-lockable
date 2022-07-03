""" Provider library """
from abc import ABC, abstractmethod
import json
import typing
from typing import List

from pydash import filter_, count_by

from lockable.logger import get_logger

MODULE_LOGGER = get_logger()


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
        MODULE_LOGGER.debug('Resources loaded: ')
        for resource in self._resources:
            MODULE_LOGGER.debug(json.dumps(resource))

    @staticmethod
    def _validate_json(data: List[dict]):
        """ Internal method to validate resources.json content """
        counts = count_by(data, lambda obj: obj.get('id'))
        no_ids = filter_(counts.keys(), lambda key: key is None)
        if no_ids:
            raise ValueError('Invalid json, id property is missing')

        duplicates = filter_(counts.keys(), lambda key: counts[key] > 1)
        if duplicates:
            MODULE_LOGGER.warning('Duplicates: %s', duplicates)
            raise ValueError(f"Invalid json, duplicate ids in {duplicates}")
