from dataclasses import dataclass, field
import asyncio
import inspect
from collections import defaultdict
from typing import Callable, Optional, Tuple, List, Any
import math

ninf:float = -math.inf

@dataclass(order=True)
class HookEntry:
    priority:int
    hook_type:str   # the name to trigger it
    name:Optional[str] = field(compare=False) # event name or loop (optional)
    callback:Callable = field(compare=False) #
    interval:Optional[float] = field(default=None,compare=False) #only for loop hooks
    oneshot:bool = field(default=False,compare=False) #for one shots

class HookManager:
    def __init__(self):
        self._hooks = defaultdict(list) # hook_type ==> list[HookEntry]
        self.builtin_hook_types = ["loop","oneshot","pre_on","pre_send","on_event","raw_incoming"]
    
    def register(self, *, hook_type:str,name:Optional[str]=None,priority:int=0,interval:Optional[float]=None,oneshot:bool=False):
        if not self._register_check(hook_type=hook_type,name=name,interval=interval,oneshot=oneshot):
            return
        def wrapper(fn:Callable):
            entry = HookEntry(priority=priority,hook_type=hook_type,name=name,callback=fn,interval=interval,oneshot=oneshot)
            self._hooks[hook_type].append(entry)
            self._hooks[hook_type].sort()
            return fn
        return wrapper
    
    async def trigger(
            self,
            hook_type: str,
            name: Optional[str] = None,
            *args: Any,
            **kwargs: Any
        ):
            """
            Call all matching hooks, dropping extra args/kwargs, logging if
            required args are missing, and auto‐removing one-shots.
            """
            entries = list(self._hooks[hook_type])
            for entry in entries:
                if name is not None and entry.name != name:
                    continue

                # prepare filtered args/kwargs
                sig = inspect.signature(entry.callback)
                params = sig.parameters

                # count how many positional slots (exclude VAR_POSITIONAL)
                pos_kinds = (inspect.Parameter.POSITIONAL_ONLY,
                            inspect.Parameter.POSITIONAL_OR_KEYWORD)
                max_pos = sum(1 for p in params.values() if p.kind in pos_kinds)
                f_args = args[:max_pos]

                # only pass kwargs that the function actually declares
                kw_kinds = (inspect.Parameter.POSITIONAL_OR_KEYWORD,
                            inspect.Parameter.KEYWORD_ONLY)
                f_kwargs = {
                    k: v for k, v in kwargs.items()
                    if k in params and params[k].kind in kw_kinds
                }

                # call & await if needed, with error handling
                try:
                    result = entry.callback(*f_args, **f_kwargs)
                    if inspect.iscoroutine(result):
                        await result
                except TypeError as te:
                    # missing required arg or other signature mismatch
                    print(f"[Hook ERROR] {entry.callback.__name__} signature mismatch: {te}")
                    continue
                except Exception as e:
                    # error inside the hook itself
                    print(f"[Hook CRASH] {entry.callback.__name__} raised: {e}")
                    continue

                # clean up one-shots
                if entry.oneshot:
                    self._hooks[hook_type].remove(entry)


    async def trigger_collect(
        self,
        hook_type: str,
        name: Optional[str] = None,
        *args: Any,
        **kwargs: Any
    ) -> List[Tuple[HookEntry, Any]]:
        """
        Like trigger(), but returns a list of (entry, return_value) tuples.
        Extra args/kwargs are dropped, missing params are logged.
        """
        results: List[Tuple[HookEntry, Any]] = []
        entries = list(self._hooks[hook_type])

        for entry in entries:
            if name is not None and entry.name != name:
                continue

            # filter args/kwargs exactly as above
            sig = inspect.signature(entry.callback)
            params = sig.parameters
            pos_kinds = (inspect.Parameter.POSITIONAL_ONLY,
                        inspect.Parameter.POSITIONAL_OR_KEYWORD)
            max_pos = sum(1 for p in params.values() if p.kind in pos_kinds)
            f_args = args[:max_pos]
            kw_kinds = (inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        inspect.Parameter.KEYWORD_ONLY)
            f_kwargs = {
                k: v for k, v in kwargs.items()
                if k in params and params[k].kind in kw_kinds
            }

            # call & capture return or log error
            try:
                res = entry.callback(*f_args, **f_kwargs)
                if inspect.iscoroutine(res):
                    res = await res
            except TypeError as te:
                print(f"[Hook ERROR] {entry.callback.__name__} signature mismatch: {te}")
                res = None
            except Exception as e:
                print(f"[Hook CRASH] {entry.callback.__name__} raised: {e}")
                res = None

            results.append((entry, res))

            # clean up one-shots 
            if entry.oneshot:
                self._hooks[hook_type].remove(entry)

        return results
    
    def get_loop_hooks(self):
        """Returns List of all loop hooks."""
        return [e for e in self._hooks["loop"]]

    def _register_check(self,hook_type,name,interval,oneshot):
        if hook_type == "loop" and (interval is None or oneshot):
            print(f"Loop hooks must have a positive interval and oneshot must be False")
            return False
        if hook_type == "oneshot" and interval is not None:
            print("Oneshot hooks can not have an interval.")
            return False
        return True