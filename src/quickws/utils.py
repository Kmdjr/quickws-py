import json
import time
import random
import msgpack
from typing import Callable


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

def setup_server_params(starting_settings) -> object:
    from .user_data_class import userData as DataClass
    default_data = {
        "max_users":10,
        "custom_uid":False,
        "uid_len":16,
        "allowed_uid_chars":"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-",
        "uid_generation_tries":20,
        "reconnection_time":10,
    }
    data:DataClass = DataClass(default_data)
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
    


    