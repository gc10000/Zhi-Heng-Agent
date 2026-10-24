"""仅计逻辑调用，绝不记录prompt/端点/密钥；不冒充SDK HTTP计量。"""
import threading


class LogicalProviderCounts:
    def __init__(self):self.lock=threading.Lock();self.counts=dict(invoke_started=0,stream_started=0)
    def snapshot(self):
        with self.lock:return dict(self.counts)
    def wrap(self,client):
        counts=self
        class Counted:
            @property
            def extra_body(self):
                from app.infrastructure.providers.clients import PolicyChatClient
                underlying=client.client if isinstance(client,PolicyChatClient) else client
                return getattr(underlying,'extra_body',None)
            def invoke(self,*args,**kw):
                with counts.lock:counts.counts['invoke_started']+=1
                return client.invoke(*args,**kw)
            def stream(self,*args,**kw):
                with counts.lock:counts.counts['stream_started']+=1
                yield from client.stream(*args,**kw)
        return Counted()
