import asyncio
from .utils import pack, unpack
import time

class Message:
    def __init__(self,raw_msg:bytes):
        self.raw_msg = raw_msg
        self.decoded = unpack(raw_msg)
        for part in ["event","data","sender","to","ack"]:
            setattr(self,part,self.decoded.get(part,None))
        self.rejected = False
        self.reject_reason = None

