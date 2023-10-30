""" resources Provider for file """
import json
import os
from typing import List

from lockable.provider import Provider
from lockable.logger import get_logger

MODULE_LOGGER = get_logger()


class ProviderFile(Provider):
    """ ProviderFile interface """

    def __init__(self, uri: str):
        """
        ProviderFile constructor
        :param uri: file path
        """
        MODULE_LOGGER.debug('Creating ProviderFile using %s', uri)
        self._resource_list_file_mtime = None
        super().__init__(uri)

    def reload(self):
        """ Load resources list file"""
        self.reload_resource_list_file()
        MODULE_LOGGER.warning('Use resources from %s file', self._uri)

    def reload_resource_list_file(self):
        """ Reload resources from file if file has been modified """
        mtime = os.path.getmtime(self._uri)
        if self._resource_list_file_mtime != mtime:
            self._resource_list_file_mtime = mtime
            data = self._read_resources_list_file(self._uri)
            self.set_resources_list(data)

    @staticmethod
    def _read_resources_list_file(filename: str) -> List[dict]:
        """ Read resources json file """
        MODULE_LOGGER.debug('Read resource list file: %s', filename)
        with open(filename, encoding="utf-8") as json_file:
            try:
                data = json.load(json_file)
                assert isinstance(data, list), 'data is not an list'
            except (json.decoder.JSONDecodeError, AssertionError) as error:
                raise ValueError(f'invalid resources json file: {error}') from error
        return data
