import asyncio
from .msg_context import Message as msgctx
from .utils import gen_id

class AckInstance:
    def __init__(self,msg:msgctx,timeout:float):
        self.uid = msg.to
        self.ack_id = gen_id(27,"ack_id")
        self.future = asyncio.get_event_loop().create_future()
        self._timeout = timeout
        self._timeout_handle = None
    
    def start_timeout(self,registry:dict[str,object]):
        def on_timeout():
            if not self.future.done():
                self.future.set_result({"error":"timeout"})
            registry.pop(self.ack_id,None)
        
        self._timeout_handle = asyncio.get_event_loop().call_later(
            self._timeout, on_timeout
        )
    
    def resolve(self,data:any):
        if not self.future.done():
            self.future.set_result({"ok":True,"data":data})
        if self._timeout_handle:
            self._timeout_handle.cancel()