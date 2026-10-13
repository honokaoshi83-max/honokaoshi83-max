"""Desktop adapter: read real state, select installation, execute owned tools."""
import json,sys,time,math
from pathlib import Path
import requests,irsdk

def atomic_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.desktop.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)

class Backend:
    def __init__(self,project,backend=None):
        self.project=Path(project).resolve();self.root=Path(backend).resolve() if backend else self.project/'work/race-voices'
        self.python=self.root/'venv/Scripts/python.exe'
        if not self.python.exists():self.python=self.project/'.runtime/python/python.exe'
        self.ir=irsdk.IRSDK();self.history=None
        sys.path.insert(0,str(self.root))
        try:
            from status_report import FuelHistory
            self.history=FuelHistory()
        except ImportError:pass

    def read(self,name,default=None):
        try:return self.ir[name]
        except (KeyError,TypeError,RuntimeError):return default

    @property
    def url(self):
        try:port=json.loads((self.project/'config/local.json').read_text(encoding='utf-8')).get('port',9881)
        except (OSError,ValueError):port=9881
        return f'http://127.0.0.1:{port}'

    def script(self,name):
        old=self.root/(name+'.ps1')
        return old if old.exists() else self.project/'scripts'/(name+'.ps1')

    def poll(self):
        state={'game':False,'health':{},'binding':{},'events':[],'fuel':None,'lap':None,'last':None,'range':None,'track':'暂无赛道数据','car':'等待驾驶会话','warnings':None}
        try:
            r=requests.get(self.url+'/health',timeout=.8);r.raise_for_status();state['health']=r.json()
        except (requests.RequestException,ValueError):pass
        try:
            for file,key in [('status_button_status.json','binding'),('status_button_settings.json','binding_config')]:
                path=self.root/file
                state[key]=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
            path=self.root/'telemetry_events.jsonl'
            if path.exists():
                with path.open('rb') as f:
                    f.seek(max(0,path.stat().st_size-40000));raw=f.read().decode('utf-8',errors='replace')
                for line in raw.splitlines():
                    try:row=json.loads(line)
                    except ValueError:continue
                    if row.get('event')=='played':state['events'].append(row)
                state['events']=state['events'][-8:][::-1]
            if not self.ir.is_initialized or not self.ir.is_connected:
                self.ir.shutdown();self.ir.startup()
            state['game']=bool(self.ir.is_initialized and self.ir.is_connected)
            if state['game']:
                state.update(fuel=self.read('FuelLevel'),lap=self.read('LapCompleted'),last=self.read('LapLastLapTime'),warnings=self.read('EngineWarnings'))
                weekend=self.read('WeekendInfo',{}) or {};state['track']=weekend.get('TrackDisplayName','暂无赛道数据')
                driver=self.read('DriverInfo',{}) or {};idx=driver.get('DriverCarIdx')
                car=next((x for x in driver.get('Drivers',[]) if x.get('CarIdx')==idx),{})
                state['car']=car.get('CarScreenName','当前车辆')
                if self.history and isinstance(state['lap'],int):
                    self.history.update(state['lap'],state['fuel'],state['last'],self.read('OnPitRoad',False))
                    if self.history.average and isinstance(state['fuel'],(float,int)):state['range']=max(0,math.floor(state['fuel']/self.history.average)-1)
        except (OSError,ValueError,RuntimeError,TypeError):pass
        return state
