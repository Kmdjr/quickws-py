import asyncio
from .user_data_class import userData as Data

class ConnectedUser:
    def __init__(self,uid:str,ws,user_data:dict={}):
        self.connected = True
        self.uid:str = uid
        self.ws = ws
        self.data = Data(user_data)
        self.data.ws = ws
        self.data.uid = uid
        self._protected_vals = ["uid","ws"]
    
    async def send(self,built_msg:dict):
        self.ws.send(built_msg)

    def _set_ws(self,new_ws):
        """Sets users WS to new_ws. will set user.data.ws as well."""
        self.ws = new_ws
        self.data.ws = new_ws
    
    def _set_uid(self,new_uid):
        """Sets users UID to new_uid. will set user.data.uid as well."""
        self.uid = new_uid
        self.data.uid = new_uid

    def force_set(self,**kwargs):
        """ [WARNING] Used to force set values in user class. \nOnly use if you know what you're doing.
        \nProtected Values (such as UID and WS) Will force set user.data attributes as well."""
        if isinstance(key,str):
            for key, val in kwargs.items():
                if key.lower() in self._protected_vals:
                    match key.lower():
                        case "uid":
                            self._set_uid(val)
                        case "ws":
                            self._set_ws(val)
                setattr(self,key,val)

    def __str__(self):
        msg:str = f"Client ==> UID: {self.uid}\nWS: {self.ws}"
        return msg