""" resources Provider for HTTP """
import logging
import requests
from requests import HTTPError
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from requests.packages.urllib3.util import parse_url

from lockable.provider import Provider, ProviderError

MODULE_LOGGER = logging.getLogger('lockable')


class ProviderHttp(Provider):
    """ ProviderHttp interface"""

    def __init__(self, uri: str):
        """ ProviderHttp constructor """
        super().__init__(uri)
        self._configure_http_strategy()
        self._reload()

    def _configure_http_strategy(self):
        """ configure http Strategy """
        retry_strategy = Retry(
            total=5,
            redirect=5,
            status_forcelist=[
                429,  # Too Many Requests
                500,  # Internal Server Error
                502,  # Bad Gateway server error
                503,  # Service Unavailable
                504  # Gateway Timeout server error
            ],
            backoff_factor=0.5
        )

        #  create http adapter with retry strategy
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._http = requests.Session()

        # Assert in hook if not success response
        assert_status_hook = (lambda response, *args, **kwargs: response.raise_for_status())
        self._http.hooks["response"] = [assert_status_hook]

        url = parse_url(self._uri)
        self._http.mount(f'{url.scheme}://', adapter)

    def _reload(self) -> None:
        """ Reload resources list from web server """
        self.set_resources_list(self._get_http())

    def _get_http(self) -> list:
        """ Internal method to get http json data"""
        try:
            response = self._http.get(self._uri)

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
