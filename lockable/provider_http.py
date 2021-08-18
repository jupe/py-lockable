""" resources Provider for HTTP """
import requests
from requests import HTTPError

from lockable.provider import Provider, ProviderError
from lockable.logger import get_logger

MODULE_LOGGER = get_logger()


class ProviderHttp(Provider):
    """ ProviderHttp interface"""

    def __init__(self, uri: str):
        """ ProviderHttp constructor """
        super().__init__(uri)

    def reload(self) -> None:
        """ Reload resources list from web server """
        self.set_resources_list(self._get_http(self._uri))

    @staticmethod
    def _get_http(uri: str) -> list:
        """ Internal method to get http json data"""
        try:
            response = requests.get(uri)
            response.raise_for_status()

            # could utilise ETag or Last-Modified headers to optimize performance
            # etag = response.headers.get("ETag")
            # last_modified = response.headers.get("Last-Modified")

            # access JSON content
            return response.json()
        except HTTPError as http_err:
            MODULE_LOGGER.error('HTTP error occurred %s', http_err)
            raise ProviderError(http_err.response.reason) from http_err
        except Exception as err:
            MODULE_LOGGER.error('Other error occurred: %s', err)
            raise ProviderError(err) from err
