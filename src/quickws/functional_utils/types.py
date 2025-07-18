from _collections_abc import Iterable

def multi_isinstance(items: Iterable, valid_types: Iterable, raise_val_error: bool = False) -> bool:
    """
    Checks whether each item in `items` is an instance of the corresponding type in `valid_types`.

    If `valid_types` is shorter than `items`, the last type in `valid_types` is reused for remaining items.
    If a type in `valid_types` is a list or tuple, `isinstance` will check against all contained types.

    Args:
        items (Iterable): Items to check.
        valid_types (Iterable): Expected types, one per item (or one type reused if shorter).
        raise_val_error (bool): If True, raises ValueError on invalid inputs.

    Returns:
        bool: True if all items are valid instances, False otherwise.
    """
    from .nums import clamp
    if not isinstance(items, Iterable) or isinstance(items, dict):
        if raise_val_error:
            raise ValueError("`items` must be a non-dict iterable.")
        return False
    if not isinstance(valid_types, Iterable) or isinstance(valid_types, dict):
        if raise_val_error:
            raise ValueError("`valid_types` must be a non-dict iterable.")
        return False

    valid_types = list(valid_types)
    for index, val in enumerate(items):
        type_index = clamp(index, 0, len(valid_types) - 1)
        expected_type = valid_types[type_index]
        if isinstance(expected_type, (list, tuple)):
            if not isinstance(val, tuple(expected_type)):
                return False
        else:
            if not isinstance(val, expected_type):
                return False
    return True


def is_type_exclude(obj, types: tuple, exclusions: tuple) -> bool:
    """
    Returns True if `obj` is an instance of any type in `types`, but not in `exclusions`.

    Args:
        obj (Any): Object to check.
        types (tuple): Types to match.
        exclusions (tuple): Types to exclude.

    Returns:
        bool: True if `obj` matches types and not exclusions, False otherwise.
    """
    if isinstance(obj, types) and not isinstance(obj, exclusions):
        return True
    return False