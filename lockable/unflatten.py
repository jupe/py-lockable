""" Convert a flat dictionary with dot-separated keys into a nested dictionary.
"""

from typing import Any, Dict


def unflatten(input_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a flat dictionary with dot-separated keys into a nested dictionary.

    Args:
        input_dict (Dict[str, Any]): A dictionary with potentially dot-separated keys.

    Returns:
        Dict[str, Any]: A nested dictionary.

    Example:
        unflatten({"key": "a", "nested.key": "b"})
        => {'key': 'a', 'nested': {'key': 'b'}}
    """
    result = {}
    for key, value in input_dict.items():
        if not isinstance(key, str):
            raise ValueError(f"Invalid key type: {type(key)}")
        if key.startswith('.') or key.endswith('.') or '..' in key:
            raise ValueError(f"Invalid key format: {key}")
        keys = key.split(".")
        temp = result
        for k in keys[:-1]:
            temp = temp.setdefault(k, {})
        temp[keys[-1]] = value
    return result
