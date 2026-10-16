"""Manual button delivery independent of SDK reads, review generation and model jobs."""
import threading,time

class StatusSnapshot:
    def __init__(self):self.lock=threading.Lock();self.value=None
    def update(self,text,connected,now=None):
        with self.lock:self.value=(text,bool(connected),time.monotonic() if now is None else now)
    def read(self,now=None):
        from status_report import DISCONNECTED
        with self.lock:value=self.value
        if value is None:return DISCONNECTED
        text,connected,created=value;now=time.monotonic() if now is None else now
        if connected and now-created>5:return '赛车数据暂未更新，请稍后再试。'
        return text

class StatusDispatcher:
    def __init__(self,button,snapshot,submit,log=lambda *args,**kwargs:None):
        self.button=button;self.snapshot=snapshot;self.submit=submit;self.log=log
    def step(self):
        if not self.button.requested():return False
        text=self.snapshot.read();accepted=self.submit(text)
        self.log('status_dispatch',accepted=bool(accepted),text=text)
        return bool(accepted)
    def run(self):
        while True:
            try:self.step()
            except Exception as error:self.log('status_dispatch_error',error=type(error).__name__,detail=str(error)[:150])
            time.sleep(.02)
    def start(self):
        threading.Thread(target=self.run,name='protected-status-dispatch',daemon=True).start()
