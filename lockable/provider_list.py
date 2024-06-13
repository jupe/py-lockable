""" resources Provider for static list """
import logging

from lockable.provider import Provider

MODULE_LOGGER = logging.getLogger(__name__)


class ProviderList(Provider):
    """ ProviderList implementation """

    def __init__(self, uri: list):
        """ ProviderList constructor """
        MODULE_LOGGER.debug('Creating ProviderList')
        super().__init__(uri)
        self.set_resources_list(self._uri)

    def reload(self):
        """ Nothing to do """
