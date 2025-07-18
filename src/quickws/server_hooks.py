from .server import Server
from .hook_manager import ninf
from .msg_context import Message

def register_hooks(server:Server):
    @server.hook(hook_type="uid_validation",name=None,priority=ninf)
    async def builtin_uid_validation(msg_ctx,uid):
        current_users:list = server.users
        gen_tries:int = server.settings.uid_generation_tries
        allows_chars:str = server.settings.allowed_uid_chars
        uidlen:int = server.settings.uid_len
        custom_ok:bool = server.settings.custom_uids

        from .utils import gen_id
        generated = False
        if not uid:
            uid = None
            # Finish UID validation hook
    pass