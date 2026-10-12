"""Read the existing 1Joy25 binding without consuming any game input."""
import ctypes
import json
import queue
import threading
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parent

class PressLatch:
    def __init__(self,cooldown=8):
        self.previous=None; self.last=-float('inf'); self.cooldown=cooldown

    def update(self,down,now):
        if down is None:
            self.previous=None
            return False
        rising=self.previous is False and down is True
        self.previous=down
        if rising and now-self.last>=self.cooldown:
            self.last=now
            return True
        return False

class JoyInfo(ctypes.Structure):
    _fields_=[(name,ctypes.c_uint32) for name in ('size','flags','x','y','z','r','u','v','buttons','button_number','pov','reserved1','reserved2')]

class JoyCaps(ctypes.Structure):
    _fields_=[('mid',ctypes.c_uint16),('pid',ctypes.c_uint16),('name',ctypes.c_wchar*32)]+[(n,ctypes.c_uint32) for n in ('xmin','xmax','ymin','ymax','zmin','zmax','buttons','period_min','period_max','rmin','rmax','umin','umax','vmin','vmax','caps','max_axes','axes','max_buttons')]+[('registry_key',ctypes.c_wchar*32),('oem',ctypes.c_wchar*260)]

class WinMMButton:
    def __init__(self,device=1,button=25):
        if not 1<=device<=16 or not 1<=button<=32:
            raise ValueError('Invalid WinMM joystick binding')
        self.device=device-1; self.button=button
        self.api=ctypes.WinDLL('winmm')
        self.api.joyGetPosEx.argtypes=[ctypes.c_uint,ctypes.POINTER(JoyInfo)]
        self.api.joyGetPosEx.restype=ctypes.c_uint
        self.api.joyGetDevCapsW.argtypes=[ctypes.c_size_t,ctypes.POINTER(JoyCaps),ctypes.c_uint]
        self.api.joyGetDevCapsW.restype=ctypes.c_uint

    def read(self):
        info=JoyInfo(); info.size=ctypes.sizeof(info); info.flags=0x80
        if self.api.joyGetPosEx(self.device,ctypes.byref(info))!=0:
            return None
        return bool(info.buttons & (1<<(self.button-1)))

    def describe(self):
        caps=JoyCaps()
        ok=self.api.joyGetDevCapsW(self.device,ctypes.byref(caps),ctypes.sizeof(caps))==0
        return dict(binding=f'{self.device+1}Joy{self.button}',device_name=caps.name if ok else None,
                    button_count=caps.buttons if ok else None,connected=self.read() is not None)

class StatusButton:
    def __init__(self):
        cfg=json.loads((ROOT/'status_button_settings.json').read_text(encoding='utf-8'))
        self.reader=WinMMButton(cfg['device'],cfg['button'])
        self.latch=PressLatch(cfg.get('cooldown_seconds',8))
        self.events=queue.Queue(maxsize=1)
        threading.Thread(target=self.watch,daemon=True).start()

    def watch(self):
        last_status=0
        while True:
            now=time.monotonic()
            down=self.reader.read()
            if self.latch.update(down,now):
                try: self.events.put_nowait(now)
                except queue.Full: pass
            if now-last_status>=2:
                state={**self.reader.describe(),'mode':'single_press','cooldown_seconds':self.latch.cooldown,'time':time.time()}
                temp=ROOT/'status_button_status.tmp'
                try:
                    temp.write_text(json.dumps(state,ensure_ascii=False),encoding='utf-8')
                    temp.replace(ROOT/'status_button_status.json')
                except OSError: pass
                last_status=now
            time.sleep(.02)

    def requested(self):
        try:
            created=self.events.get_nowait()
            return time.monotonic()-created<=5
        except queue.Empty:
            return False
