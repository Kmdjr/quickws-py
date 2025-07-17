import asyncio
from .utils import pack, unpack
from typing import Callable
import time
import inspect
from .utils import CancelProcessing, maybe_await
from .server import Server
from .client import Client
from .data_class import Data

class Message:
    def __init__(self,raw_msg:bytes,socket:Server|Client,ws,ip="NULL",port="NULL",uid:str=None):
        """Class to hold original `raw_msg` bytes and all message data after on_raw handler is ran using local `decode` method.\n
        `socket` property is a reference to server or client class. (`self.server` or `self.client` will be added as alias properties depending on which it is.)\n
        holds `event`,`sender`,`data`, `etc` as properties."""
        self.socket:Server|Client = socket
        setattr(self,"server" if isinstance(self.socket,Server) else "client",self.socket)
        self.raw_msg = raw_msg
        self.ip = ip
        self.port = port
        self.ws = ws
        self.uid = None
        self.decoded = None
        # for part in ["event","data","sender","to","ack"]:
        #     setattr(self,part,self.decoded.get(part,None))
        self.rejected = False
        self.reject_reason = None
    
    def decode(self):
        """Decodes raw message bytes from `self.raw_msg` using `msgpack` and populates the class with the `properties` of the payload."""
        raw = self.raw_msg
        self.decoded = unpack(raw)
        for key in self.decoded.keys():
            setattr(self,key,self.decoded.get(key))
        if isinstance(self.data,dict):
            self.data = Data(self.data)


    def reject(self, reason: str = None, on_fail: Callable = None, errcode="[Message Rejected]"):
        """Unconditionally abort processing after running `on_fail` (if any).
        \nEquivalent to using `server/client.fail()` but generates a `raise_msg` automatically using the classes properties in the form:
        \n f"Message for event: {self.event} from {self.sender} with WS of {self.ws} going to {self.to} with data of {str(self.data)} and metadata of {str(self.metadata)}" 
        \nwhere each are not empty/None."""
        self.rejected = True
        self.reject_reason = reason
        event = self.event if self.event else "[Unknown Event Name]"
        sender = self.sender if self.sender else "[Unknown UID]"
        websock = str(self.ws) if self.ws else "[Unknown Web Socket]"
        data = self.data if self.data else "[Unknown/Empty Data]"
        to = self.to if self.to else "[Unknown Recipient]"
        metadata = self.metadata if self.metadata else "[Unknown/Empty Metadata]" 
        raise_msg:str = f"Message for event: {event} from {sender} with WS of {websock} going to {to} with data of {str(data)} and metadata of {str(metadata)}"
        self.socket.fail(raise_msg=raise_msg,reason=reason,on_fail=on_fail,errcode=errcode,Object=self)