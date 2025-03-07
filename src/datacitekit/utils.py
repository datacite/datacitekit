import re
from collections import defaultdict


def camel_to_hyphen_case(camel_case_str):
    """Convert a camelCase string to hyphen-case format.

    Args:
        camel_case_str (str): String in camelCase format

    Returns:
        str: String converted to hyphen-case format
    """
    return re.sub(r"(?<!^)(?=[A-Z])", "-", camel_case_str).lower()


def merge_list_dicts(dict1, dict2):
    """Merge two dictionaries with list values.

    This function combines two dictionaries where the values are lists.
    For each key present in either dictionary, the resulting dictionary
    will contain a list that combines the values from both input dictionaries.

    Args:
        dict1 (dict): First dictionary with string keys and list values
        dict2 (dict): Second dictionary with string keys and list values

    Returns:
        dict: A new dictionary containing all keys from both input dictionaries,
              with their list values combined
    """

    result = defaultdict(list)
    # Update with first dict
    for key, value in dict1.items():
        result[key].extend(value)
    # Update with second dict
    for key, value in dict2.items():
        result[key].extend(value)

    return dict(result)


def group_by(items, key):
    """Group a list of dictionaries by a specified key or function.

    This function takes a list of dictionaries and groups them based on either
    a dictionary key or a function that determines the grouping value.

    Args:
        items (list): List of dictionaries to group
        key (Union[str, callable]): Either a string key to group by,
            or a function that takes a dictionary and returns the grouping value

    Returns:
        dict: A dictionary where keys are the grouping values and values are
              lists of dictionaries that share that grouping value

    """
    from collections import defaultdict

    groups = defaultdict(list)

    key_func = key if callable(key) else lambda x: x[key]
    for item in items:
        groups[key_func(item)].append(item)

    return dict(groups)
