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
    for k, v in data.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.update(flatten_json(v, new_key, sep=sep))
        else:
            items[new_key] = v
    return items

def flatten_list(array: list) -> list:
    return list(map(flatten_json, array))
