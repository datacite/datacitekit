import re
from collections import defaultdict


def camel_terms(value):
    """Split a string into its constituent terms based on camelCase and other patterns.

    This function breaks down strings into component terms using a complex regular expression
    that matches various patterns including:
    - Words starting with capital letters followed by lowercase letters (e.g., "Camel")
    - Groups of uppercase letters or numbers before a camelCase word (e.g., "XML" in "XMLParser")
    - Groups of 2 or more uppercase letters or numbers (e.g., "API", "123")
    - Groups of 2 or more lowercase letters or numbers (e.g., "api", "123")
    - Single alphanumeric characters

    Args:
        value (str): The input string to split into terms

    Returns:
        list: A list of strings, each representing a term found in the input
    """

    return re.findall(
        "[A-Z][a-z]+|[0-9A-Z]+(?=[A-Z][a-z])|[0-9A-Z]{2,}|[a-z0-9]{2,}|[a-zA-Z0-9]",
        value,
    )


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
