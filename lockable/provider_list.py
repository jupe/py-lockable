""" resources Provider for static list """
from lockable.provider import Provider


class ProviderList(Provider):
    """ ProviderList implementation """

    def __init__(self, uri: list):
        """ ProviderList constructor """
        super().__init__(uri)
        self.set_resources_list(self._uri)

    def reload(self):
        """ Nothing to do """
