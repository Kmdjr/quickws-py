import websockets
import asyncio
import msgpack
from typing import Callable, Optional, Union
import inspect
from .server_user import ConnectedUser as User
from .logger import Logger
from .utils import build_msg, fail_operation_close_ws as op_fail, check_for_pass as check_pass, setup_server_params, resolve_uid
from .hook_manager import HookManager, ninf
from .pluginsmanager import PluginManager
from .server_hooks import register_hooks
from .msg_context import Message as msgctx
from .user_data_class import userData as DataClass
from .ack_handler import AckInstance

class Server:
    def __init__(self, 
                 uri:str,
                 port:int,
                 plugin_dirs:Optional[list[str]] = None,
                 starting_logger_level:int=5,
                 starting_server_settings:dict = {}
                 ):
        self._serve = None
        self.host:str = uri
        self.port:int|str = port
        self.settings:DataClass = setup_server_params(starting_settings=starting_server_settings)
        
        # Connected Clients and Handlers for them

        self.users:list[User] = []
        self._log:Logger = Logger(starting_logger_level)
        self._connect_lock = asyncio.Lock()

        # Hook Manager
        self.hooks:HookManager = HookManager()
        
        #ack handlers:
        self._acks:dict[str,AckInstance] = {}

        register_hooks(self)
        if plugin_dirs:
            pm:PluginManager = PluginManager(plugindirs=plugin_dirs)
            pm.load(self)

        


    def hook(self,*,hook_type:str,name:Optional[str]=None,priority:int=0,interval:Optional[float]=None,once:bool=False):
        return self.hooks.register(hook_type=hook_type,name=name,priority=priority,interval=interval,once=once)

    def getuser(self, uid: str = None, ws=None, default=None):
        """Gets a user from provided uid and/or ws.
        Returns user if both match (if both are provided), or either one if only one is.
        Returns `default` if no match."""
        for user in self.users:
            uid_match = uid is None or user.uid == uid
            ws_match = ws is None or user.ws == ws
            if uid_match and ws_match:
                return user
        return default

    def log(self,msg:str,log_lvl:int=-1):
        self._log.log(msg,log_lvl)
    
    def set_log_lvl(self,new_log_lvl:int=0):
        self._log.set(new_log_lvl)
    
    def set_log_codes(self,log_codes:dict={}):
        if isinstance(log_codes,dict):
            self._log.log_codes = log_codes
            return
        print("Failed to Update Log Codes. Reason: log_codes not of type dict.")
    
    def set_setting(self,setting:str,new_val:any):
        self.settings.set(setting,new_val,True)
    
    def get_settings(self,settings:list|str):
        settings_array:list = [settings] if isinstance(settings,str) else settings
        settings_dict:dict = {}
        for i in settings_array:
            val = self.settings.get(i,None)
            settings_dict[i] = val
        return self.settings.get(settings) if len(settings_dict) == 1 else settings_dict

    def get_uids(self):
        return list(i.uid for i in self.users)

    def on(self,event_name:str):
        return self.hooks.register(
            hook_type="on_event",
            name=event_name,
            priority=0
        )

    async def send(
            self,
            event_name:str,
            data:dict,
            to:str|list[str],
            sender:str="SERVER",
            ack:bool=False,
            timeout:float=10.0
        ):
        
        targets = to if isinstance(to,list) else [to]
        
        if not ack:
            for uid in targets:
                user = self.getuser(uid=uid)
                msg = build_msg(event=event_name,data=data,sender=sender,to=user)
                if user and msg: 
                    await user.send(msg)
            return None

        ack_map:dict[str,AckInstance] = {}
        for uid in targets:
            user = self.getuser(uid=uid)
            if not user:
                continue
            inst = AckInstance(uid,timeout=timeout)
            self._acks[inst.ack_id] = inst
            inst.start_timeout(self._acks)
            from copy import deepcopy
            payload = build_msg(event=event_name,data=data,sender=sender,to=user,ack_id=inst.ack_id)
            if not payload:
                continue
            ack_map[uid] = inst
            user.send(built_msg=payload)
        
        results:dict[str,any] = {}
        for uid, inst in ack_map.items():
            res = await inst.future
            results[uid] = res
        return results

    async def _user_connecting_handler(self,msg,ws):
        data = msg.data
        uid = data.get("uid")
        if uid:
            ## Reconnection Logic ##
            pass
        async with self._connect_lock:
        #max_client_check:
            if self.settings.max_users > 0 and len(self.users) >= self.settings.max_users:
                print("Max Users Reached!")
                return ## DO RESPONSE FOR MAX SERVER LOGIC HERE ##
            uid = resolve_uid(uid,self.hooks,self.get_uids(),
                self.settings.custom_uid, self.settings.uid_len,self.settings.allowed_uid_chars,self.settings.uid_generation_tries
            )
            if uid == "__ERROR__":
                return #DO RESPONSE FOR FAILED GENERATION OF UID
            user = User(uid,ws)
            await self.hooks.trigger("user_creation",None,user)
            self.users.append(user)
            print(f"[+] Client Registered: {user.uid}")
            await self.hooks.trigger("user_connected",None,user)

    async def _message_handler(self,uid:str|None,raw:str,ws):
        ip, port = ws.remote_address 
        raw_on_results = await self.hooks.trigger_collect("raw_incoming",None,raw,ws,ip,port,uid)
        if check_pass(raw_on_results,False,lambda: print(f"raw_incoming hook rejected message.")):return
        try:
            msg:msgctx = msgctx(raw)
            if msg.event == "_UserConnected" and "uid" in msg.data.keys():
                try:
                    uid = await self._user_connecting_handler(msg,ws)
                except:
                    print("Failed User Registration")
                    return
        except:
            print("Failed to parse or construct msgctx class from raw msg.")
            return
        await self.hooks.trigger("pre_on",None,msg)
        if msg.rejected:
            print(f"Message was Rejected from pre_on hook. Reason: {msg.reject_reason}")
            return
        if msg.event in ["_UserConnected"]:
            await self.hooks.trigger(msg.event,None,msg)
            if msg.rejected:
                print(f"Message was Rejected from pre_on hook. Reason: {msg.reject_reason}")
                return
        else:
            await self.hooks.trigger("on_event",msg.event,msg)
        
        pass
    
    async def _disconnected_user_handler(self,uid,ws,user):
        user.connected = False
        self.users.remove(user)
        print("User Disconnected")

    async def _running(self,ws):
        try:
            raw = await asyncio.wait_for(ws.recv(),timeout=10)
        except asyncio.TimeoutError:
            return op_fail(ws,"TIMEOUT ERROR")
        await self._message_handler(uid=None,raw=raw,ws=ws)
        
        user = self.getuser(ws=ws)
        if not user:
            return op_fail(ws,"USER GET","No User with "+str(ws))
        uid = user.uid
        if not uid:
            return op_fail(ws,"UID GET",f"User: {str(user)} has no assigned UID")
        
        try:
            async for raw in ws:
                await self._message_handler(uid=uid,raw=raw,ws=ws)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            user.connected = False
            self.users
            

    async def shutdown(self):
        #shutdown logic
        await asyncio.sleep(1)
        self._serve.close()
        await self._serve.wait_closed()

    async def start(self):
        self._serve = await websockets.serve(self._running,self.host,self.port)
        print(f"Server Listening on {self.host}:{self.port}")
        print("Setting up Loop hooks and Hook System now...")
        for entry in self.hooks.get_loop_hooks():
            async def runner(e=entry):
                while True:
                    try:
                        await e.callback()
                    except Exception as err:
                        print(f"[loop:{e.name}] crashed: {err}")
                    await asyncio.sleep(e.interval)
            asyncio.create_task(runner())
        return self._serve

