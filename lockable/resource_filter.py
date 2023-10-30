""" Resource filter module """

import re

from pydash import filter_


def get_matching_resources(resource_list: [{}], requirements: {}) -> [{}]:
    """ Get matching resources from resource list """
    def in_filter(resource: dict):
        """ Check if resource matches requirements """
        for key, value in requirements.items():
            if isinstance(value, dict):
                # check that dictionary contains only accepted keys
                accepted_keys = ['$exists', '$in', '$nin', '$regex']
                for k in value.keys():
                    assert k in accepted_keys, f'Unsupported key: {k} in {value}'

                if '$exists' in value:
                    exists = value['$exists']
                    assert isinstance(exists, bool), f'Unsupported value: {exists} in {value}'
                    # if exists is true, filter out resources that does not have the field
                    # if exists is false, filter out resources that have the field
                    return exists == (key in resource)
                if '$in' in value:
                    value_in = value['$in']
                    assert isinstance(value_in, list), f'Unsupported $in value: {value_in}'
                    if resource[key] not in value_in:
                        return False
                if '$nin' in value:
                    value_nin = value['$nin']
                    assert isinstance(value_nin, list), f'Unsupported $nin value: {value_nin}'
                    if resource[key] in value_nin:
                        return False
                if '$regex' in value:
                    value_regex = value['$regex']
                    assert isinstance(value_regex, str), f'Unsupported $regex value: {value_regex}'
                    if not re.search(value_regex, resource[key]):
                        return False
            elif key not in resource or resource[key] != value:
                return False
        return True
    return filter_(resource_list, in_filter)
