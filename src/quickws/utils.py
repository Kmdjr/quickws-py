import json
import time
import random
import asyncio
import msgpack
import inspect
from typing import Callable
from .data_class import Data
from copy import deepcopy


color_codes: dict[str, str] = {
    "reset":    "\033[0m",
    "bold":     "\033[1m",
    "dim":      "\033[2m",
    "underline":"\033[4m",
    "blink":    "\033[5m",
    "reverse":  "\033[7m",

    "black":    "\033[30m",
    "red":      "\033[31m",
    "green":    "\033[32m",
    "yellow":   "\033[33m",
    "blue":     "\033[34m",
    "magenta":  "\033[35m",
    "cyan":     "\033[36m",
    "white":    "\033[37m",

    "bright_black":   "\033[90m",
    "bright_red":     "\033[91m",
    "bright_green":   "\033[92m",
    "bright_yellow":  "\033[93m",
    "bright_blue":    "\033[94m",
    "bright_magenta": "\033[95m",
    "bright_cyan":    "\033[96m",
    "bright_white":   "\033[97m",

    "bg_black":    "\033[40m",
    "bg_red":      "\033[41m",
    "bg_green":    "\033[42m",
    "bg_yellow":   "\033[43m",
    "bg_blue":     "\033[44m",
    "bg_magenta":  "\033[45m",
    "bg_cyan":     "\033[46m",
    "bg_white":    "\033[47m",

    "bg_bright_black":   "\033[100m",
    "bg_bright_red":     "\033[101m",
    "bg_bright_green":   "\033[102m",
    "bg_bright_yellow":  "\033[103m",
    "bg_bright_blue":    "\033[104m",
    "bg_bright_magenta": "\033[105m",
    "bg_bright_cyan":    "\033[106m",
    "bg_bright_white":   "\033[107m"
}



class CancelProcessing(Exception):
    """Signal to abort processing the current message. Carries Structured Failure Info"""
    def __init__(self,*,raise_msg:str=None,reason:str=None,errcode:str="[Fail Error]",obj:object=None):
        self.raise_msg = raise_msg
        self.reason = reason
        self.errcode = errcode
        self.obj = obj
    
    def __str__(self):
        return f"{self.errcode} -> {f'From Object: {str(self.obj)} |' if self.obj else ""} {self.raise_msg} for reason: {self.reason}"

async def maybe_await(fn,*args,**kwargs):
    if inspect.iscoroutinefunction(fn):
        return await fn(*args,**kwargs)
    else:
        return fn(*args,**kwargs)

def pack(data:dict[str]) -> bytes:
    """Packs dict `data` using msgpack.packb() and returns as Binary Bytes """
    return msgpack.packb(data)

def unpack(data:bytes) -> dict:
    """Unpacks binary bytes `data` using msgpack.unpackdb() and returns as a dictionary."""
    return msgpack.unpackdb(data)

def check_for_pass(data,failure_marker = False,on_failure:Callable=None):
    for entry, result in data:
        if result == failure_marker:
            if isinstance(on_failure,Callable): on_failure()
            return False
    return True

def setup_server_params(starting_settings) -> Data:
    default_data = {
        "max_users":10,
        "custom_uid":True,
        "uid_len":16,
        "allowed_uid_chars":"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-",
        "uid_generation_tries":20,
        "reconnection_time":10,
    }
    data:Data = Data(default_data)
    data.sets(starting_settings)
    return data

async def resolve_uid(uid,hooks,current_users,custom_bool,uid_len,
                      allowed_chars,uid_generation_tries,
                      return_on_fail:str="__ERROR__") -> str:
    generated = False
    for _ in range(uid_generation_tries + 1):
        failed = False
        if not uid:
            uid = gen_id(uid_len,"",allowed_chars)
        if uid == return_on_fail:
            failed = True
        if uid in current_users:
            failed = True
        if len(uid) != uid_len:
            failed = True
        if not custom_bool and not generated:
            failed = True
        if not check_for_allowed_chars(uid,allowed_chars):
            failed = True
        result = await hooks.trigger_collect("uid_validation",None,uid)
        if not check_for_pass(result,False):
            failed = True
        if not failed:
            return uid
        uid = gen_id(uid_len,"",allowed_chars)
        generated = True
    
    return return_on_fail
    
def check_for_allowed_chars(text,allowed) -> bool:
    for i in range(len(text)):
        if i not in allowed:
            return False
    return True

def gen_id(length=21,kind:str="ack_id",chars_used:str="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") -> str:
    if length <1:
        length = 21
    id:str = kind + "-"
    for i in range(length):
        chars = chars_used
        id += chars[random.randint(0,len(chars)-1)]
    return id

def fail_operation_close_ws(ws,operation="",reason=""):
    if reason and operation:
        print(str(operation)+" Failed. Reason: "+str(reason))
    return

def build_msg(event,data,sender,to:object,ack_id:str,failed=False):
    msg={
        "event":event,
        "data":data,
        "sender":sender,
    }
    if to.__dict__.get("uid"):
        msg["to"] = to.uid
    else:
        return failed
    if isinstance(ack_id,str):
        msg['ack_id'] = ack_id
    return msg

def mergel(*args:list):
    """Merge multiple lists into a single flat list."""
    for arg in args:
        if not isinstance(arg,list): raise ValueError
    return [item for sub in args for item in sub]

def clean_values(full_list:list,sublist:list):
    if not isinstance(full_list,list) or not isinstance(sublist,list):
        raise ValueError
    cleaned = full_list
    for i in sublist:
        cleaned = clean_value(i,cleaned)
    return cleaned

def clean_value(val_to_remove,full_list:list):
    cleaned = []
    for item in full_list:
        if item != val_to_remove:
            cleaned.append(item)
    return cleaned

def in_and_not_in(val,allowed:list,not_allowed:list,case_sensitive:bool=True) -> bool:
    """
    Return True if `val` is in `allowed` and NOT in `not_allowed`.

    Args:
        val: The value to check.
        allowed: List of allowed values.
        not_allowed: List of disallowed values.
        case_sensitive: If False, comparison is case-insensitive.

    Returns:
        bool: True if `val` is in `allowed` and not in `not_allowed`, else False.
    """
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
    """Return a list of all string elements from `List`, converted to lowercase."""
    return [s.lower() for s in items if isinstance(s,str)]

def in_lower_list(val:str,List:list) -> bool:
    """
    Check if the lowercase of `val` exists among the lowercase string elements of `List`.

    Returns True only if `val` is a string and is found in the lowercase-transformed `List`.
    """
    if isinstance(val,str) and isinstance(List,list):
        return True if val.lower() in lower_list(List) else False

def merge_data(data1:Data,data2:Data,include_protected1:bool=False,include_protected2:bool=False) -> Data:
    """
    Merge two Data objects into a new Data instance.

    Args:
        data1: First Data object.
        data2: Second Data object.
        include_protected1: Whether to include protected keys from data1.
        include_protected2: Whether to include protected keys from data2.

    Returns:
        A new Data object combining both, without overwriting any shared keys.
    """
    if not isinstance(data1,Data) and not isinstance(data2,Data):
        raise ValueError
    new = {}
    a, b = data1.as_dict(include_protected1), data2.as_dict(include_protected2)
    new:dict = deepcopy(a)
    for key, val in b:
        if key not in new.keys():
            new[key] = val
    return Data(new)