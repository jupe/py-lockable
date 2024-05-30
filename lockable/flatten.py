"""
Helper functions for flattening nested dictionaries.
"""


def flatten_json(data: dict, parent_key='', sep='.') -> dict:
    """
    Flatten a nested dictionary.

    Args:
    - data (dict): The dictionary to flatten.
    - parent_key (str, optional): The concatenated key from the parent(s). Defaults to ''.
    - sep (str, optional): The separator to use between keys. Defaults to '.'.

    Returns:
    - dict: The flattened dictionary.
    """
    items = {}
    for key, value in data.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, dict):
            items.update(flatten_json(value, new_key, sep=sep))
        else:
            # ensure that the key doesn't overwrite an existing key
            assert new_key not in items, f"Key {new_key} already exists in items"
            items[new_key] = value
    return items


def flatten_list(array: list) -> list:
    """ Flatten a list of dictionaries """
    return list(map(flatten_json, array))
