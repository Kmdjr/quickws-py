def mergel(*args:list):
    """Merge multiple lists into one flat list. Returns merged list."""
    for arg in args:
        if not isinstance(arg,list): raise ValueError
    return [item for sub in args for item in sub]

def clean_values(full_list:list,sublist:list):
    """Remove all values in `sublist` from `full_list`. Returns cleaned list."""
    if not isinstance(full_list,list) or not isinstance(sublist,list):
        raise ValueError
    cleaned = full_list
    for i in sublist:
        cleaned = clean_value(i,cleaned)
    return cleaned

def clean_value(val_to_remove,full_list:list):
    """Remove all instances of `val_to_remove` from `full_list`. Returns cleaned list."""
    cleaned = []
    for item in full_list:
        if item != val_to_remove:
            cleaned.append(item)
    return cleaned

def in_and_not_in(val,allowed:list,not_allowed:list,case_sensitive:bool=True) -> bool:
    """Return True if `val` is in `allowed` and not in `not_allowed`. Case-sensitive by default."""
    if not case_sensitive:
        val = val.lower()
        allowed = lower_list(allowed)
        not_allowed = lower_list(not_allowed)
    if val not in allowed:
        return False
    if val in not_allowed:
        return False
    return True

def lower_list(items:list) -> list[str]:
    """Return lowercase version of all string items in `items`."""
    return [s.lower() for s in items if isinstance(s,str)]

def in_lower_list(val:str,List:list) -> bool:
    """Return True if lowercase `val` is found in lowercase of `List`."""
    if isinstance(val,str) and isinstance(List,list):
        return True if val.lower() in lower_list(List) else False

def biggest_list(*args):
    """Return a `tuple` of (list of longest lists, their length). Ignores non-list inputs."""
    biggest = []
    largest_seen:int = 0
    for l in args:
        if isinstance(l,list):
            length = len(l)
            if length > largest_seen:
                biggest = [l]
                largest_seen = length
            elif length == largest_seen:
                biggest.append(l)
    return (list(biggest),largest_seen)

