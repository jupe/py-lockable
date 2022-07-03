""" resources Provider for HTTP """
import requests
from requests import HTTPError, ConnectionError as RequestConnectionError
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.util import parse_url
from urllib3.exceptions import MaxRetryError

from lockable.provider import Provider, ProviderError
from lockable.logger import get_logger

MODULE_LOGGER = get_logger()


class RetryWithLogging(Retry):
    """ urllib3.util.retry Retry overwrite to add logging """
    def increment(self, *args, **kwargs):
        try:
            error = kwargs['error']
            MODULE_LOGGER.warning('retried http resources GET due to %s', error)
        except KeyError:
            pass

        return super().increment(*args, **kwargs)


class ProviderHttp(Provider):
    """ ProviderHttp interface"""

    TOTAL_RETRIES = 9  # This should be enough even we update server with short service break
    REDIRECT = 5  # redirect max count
    BACKOFF_FACTOR = 1  # [0.0s, 1s, 2s, 4s, 8s, 16s, 32s, 1min4s, 2min8s]

    def __init__(self, uri: str):
        """ ProviderHttp constructor """
        MODULE_LOGGER.debug('Creating ProviderHTTP using %s', uri)
        self._configure_http_strategy(uri)
        super().__init__(uri)

    def _configure_http_strategy(self, uri):
        """ configure http Strategy """
        retry_strategy = RetryWithLogging(
            total=ProviderHttp.TOTAL_RETRIES,
            redirect=ProviderHttp.REDIRECT,
            connect=ProviderHttp.TOTAL_RETRIES,
            other=ProviderHttp.TOTAL_RETRIES,
            raise_on_status=False,
            status_forcelist=[
                429,  # Too Many Requests
                500,  # Internal Server Error
                502,  # Bad Gateway server error
                503,  # Service Unavailable
                504  # Gateway Timeout server error
            ],
            backoff_factor=ProviderHttp.BACKOFF_FACTOR
        )

        #  create http adapter with retry strategy
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._http = requests.Session()

        url = parse_url(uri)
        self._http.mount(f'{url.scheme}://', adapter)

    def reload(self) -> None:
        """ Reload resources list from web server """
        self.set_resources_list(self._get_list())

    def _get_list(self) -> list:
        """ Internal method to get http json data"""
        try:
            response = self._http.get(self._uri)

            # could utilise ETag or Last-Modified headers to optimize performance
            # etag = response.headers.get("ETag")
            # last_modified = response.headers.get("Last-Modified")

            # if we get non retry_strategy based response we still
            # have to check if response is success, e.g. not 404..
            response.raise_for_status()

            # access JSON content
            return response.json()
        except HTTPError as http_err:
            MODULE_LOGGER.error('HTTP error occurred %s', http_err)
            raise ProviderError(http_err.response.reason) from http_err
        except RequestConnectionError as error:
            MODULE_LOGGER.error('Connection error: %s', error)
            raise ProviderError(error) from error
        except MaxRetryError as error:
            MODULE_LOGGER.error('Max retries error: %s', error)
            raise ProviderError(error) from error
        except Exception as error:
            MODULE_LOGGER.error('Other error occurred: %s', error)
            raise ProviderError(error) from error
