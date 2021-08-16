""" resources Provider helper """
from lockable.provider import Provider
from lockable.provider_list import ProviderList
from lockable.provider_file import ProviderFile
from lockable.provider_http import ProviderHttp


def create(uri):
    """
    Create provider instance from uri
    :param uri: list of string for provider
    :return: Provider object
    :rtype: Provider
    """
    if Provider.is_http_url(uri):
        return ProviderHttp(uri)
    if isinstance(uri, str):
        return ProviderFile(uri)
    if isinstance(uri, list):
        return ProviderList(uri)
    raise AssertionError('uri should be list or string')
