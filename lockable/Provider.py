from abc import ABC, abstractmethod
import json
import os
import logging
import requests
from urllib.parse import urlparse
from requests.exceptions import HTTPError
from pydash import filter_, count_by

MODULE_LOGGER = logging.getLogger('lockable')


class ProviderError(Exception):
    pass


class Provider(ABC):
    def __init__(self, uri: (str, list)):
        self._uri = uri
        self._resources = list()

    @property
    def data(self):
        self._reload()
        return self._resources

    @staticmethod
    def create(uri):
        """
        Create provider instance from uri
        :param uri: list of string for provider
        :return: Provider object
        :rtype: Provider
        """
        if Provider.is_http_url(uri):
            return ProviderHttp(uri)
        elif isinstance(uri, str):
            return ProviderFile(uri)
        elif isinstance(uri, list):
            return ProviderList(uri)
        raise AssertionError('uri should be list or string')

    @staticmethod
    def is_http_url(uri):
        try:
            result = urlparse(uri)
            return all([result.scheme, result.netloc])
        except:
            return False

    @abstractmethod
    def _reload(self):
        pass

    def set_resources_list(self, resources_list: list):
        """ Load resources list """
        assert isinstance(resources_list, list), 'resources_list is not an list'
        self._validate_json(resources_list)
        self._resources = resources_list
        MODULE_LOGGER.debug('Resources loaded: ')
        for resource in self._resources:
            MODULE_LOGGER.debug(json.dumps(resource))

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


class ProviderList(Provider):
    def __init__(self, uri):
        super().__init__(uri)
        self.set_resources_list(self._uri)

    def _reload(self): pass


class ProviderFile(Provider):

    def __init__(self, uri):
        super().__init__(uri)
        self._resource_list_file_mtime = None
        self._reload()

    def _reload(self):
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
    def _read_resources_list_file(filename):
        """ Read resources json file """
        MODULE_LOGGER.debug('Read resource list file: %s', filename)
        with open(filename) as json_file:
            try:
                data = json.load(json_file)
                assert isinstance(data, list), 'data is not an list'
            except (json.decoder.JSONDecodeError, AssertionError) as error:
                raise ValueError(f'invalid resources json file: {error}') from error
        return data


class ProviderHttp(Provider):

    def __init__(self, uri):
        super().__init__(uri)
        self._reload()

    def _reload(self):
        self.set_resources_list(self._reload_http(self._uri))

    @staticmethod
    def _reload_http(uri):
        try:
            response = requests.get(uri)
            response.raise_for_status()

            # could utilise ETag or Last-Modified headers to optimize performance
            # etag = response.headers.get("ETag")
            # last_modified = response.headers.get("Last-Modified")

            # access JSON content
            return response.json()
        except HTTPError as http_err:
            MODULE_LOGGER.error(f'HTTP error occurred: {http_err}')
            raise ProviderError(http_err.response.reason) from http_err
        except Exception as err:
            MODULE_LOGGER.error(f'Other error occurred: {err}')
            raise ProviderError(err) from err
