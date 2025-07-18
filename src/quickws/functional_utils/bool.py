

def all_bool(True_or_False:bool=True,*args) -> bool:
    """Return True if all `args` are truthy or falsy, matching the `True_or_False` flag."""
    all_true = all(args)
    return all_true == True_or_False