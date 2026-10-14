"""Local evidence-based snapshot, fuel range estimate and selected pit services."""
import math
from collections import deque

DISCONNECTED='未连接驾驶会话，状态暂不可用。'

def numeric(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)

def spoken(value):
    from telemetry_announcer import chinese_number
    rounded=round(value,1)
    whole=int(rounded); decimal=int(round((rounded-whole)*10))
    return chinese_number(whole)+('点'+chinese_number(decimal) if decimal else '')

class FuelHistory:
    def __init__(self):
        self.samples=deque(maxlen=5); self.times=deque(maxlen=5)
        self.lap=None; self.boundary=None; self.last=None; self.tainted=True

    @property
    def average(self):
        return sum(self.samples)/len(self.samples) if len(self.samples)>=2 else None

    def update(self,lap,fuel,lap_time,pit=False):
        if not numeric(fuel) or fuel<0:
            self.tainted=True
            return
        if self.lap is None or lap<self.lap or (self.last is not None and fuel>self.last+.5):
            self.samples.clear(); self.times.clear()
            self.lap=lap; self.boundary=fuel; self.last=fuel; self.tainted=True
            return
        if pit: self.tainted=True
        if lap>self.lap:
            burn=self.boundary-fuel if self.boundary is not None else 0
            if lap==self.lap+1 and not self.tainted and .01<burn<100:
                self.samples.append(burn)
                if numeric(lap_time) and 10<lap_time<3600: self.times.append(lap_time)
            self.boundary=fuel; self.lap=lap; self.tainted=bool(pit)
        self.last=fuel

def snapshot(ir):
    names=set(ir.var_headers_names or [])
    def get(name): return ir[name] if name in names else None
    infos=ir['SessionInfo'] or {}
    session=next((r for r in infos.get('Sessions',[]) if r.get('SessionNum')==get('SessionNum')), {})
    header=getattr(ir,'_var_headers_dict',{}).get('PitSvFuel')
    return dict(active=bool(get('IsOnTrack')) and not get('IsReplayPlaying') and not get('IsInGarage'),
        fuel=get('FuelLevel'),warnings=get('EngineWarnings'),flags=get('SessionFlags'),
        required=get('PitRepairLeft'),optional=get('PitOptRepairLeft'),
        in_stall=bool(get('PlayerCarInPitStall')),pit=bool(get('OnPitRoad')),
        pit_flags=get('PitSvFlags'),pit_fuel=get('PitSvFuel'),
        pit_fuel_unit=str(getattr(header,'unit','')).lower(),
        auto_fuel=bool(get('dpFuelAutoFillActive')),
        race=session.get('SessionType')=='Race',laps_left=get('SessionLapsRemain'),
        time_left=get('SessionTimeRemain'),completed=get('LapCompleted'),last_time=get('LapLastLapTime'))

def status_phrase(s,h):
    parts=[]
    warnings=s.get('warnings'); flags=s.get('flags')
    if warnings is None or flags is None:
        parts.append('车辆告警数据暂不可用。')
    else:
        issues=[]
        if warnings&0x80 or flags&0x100000: issues.append('需要强制维修，请安全进站。')
        elif warnings&0x100: issues.append('有可选维修项目，可在下次进站处理。')
        for mask,name in ((1,'发动机水温'),(4,'机油压力'),(64,'机油温度')):
            if warnings&mask: issues.append(name+'告警。')
        parts+=issues or ['车辆无告警。']
    for field,name in (('required','强制维修'),('optional','可选维修')):
        if s.get('in_stall') and numeric(s.get(field)) and s[field]>0:
            from damage_monitor import duration_phrase
            parts.append(name+'还需'+duration_phrase(s[field])+'。')
    fuel=s.get('fuel'); burn=h.average
    if numeric(fuel) and fuel>=0:
        parts.append('剩余油量'+spoken(fuel)+'升。')
    else:
        parts.append('油量数据暂不可用。')
    if numeric(fuel) and fuel>=0 and burn is not None:
        usable=max(0,math.floor(fuel/burn)-1)
        laps=s.get('laps_left'); seconds=s.get('time_left')
        need=laps+1 if s.get('race') and numeric(laps) and 0<laps<10000 else None
        if need is None and s.get('race') and numeric(seconds) and 0<seconds<86400 and len(h.times)>=2:
            need=math.ceil(seconds/(sum(h.times)/len(h.times)))+1
        if need is not None and fuel>=need*burn:
            parts.append('油量够到终点。')
        elif usable<=0:
            parts.append('建议本圈进站加油。')
        else:
            parts.append('建议'+spoken(usable)+'圈内进站加油。' if s.get('race') else '预计还能跑'+spoken(usable)+'圈。')
    pit_flags=s.get('pit_flags')
    if isinstance(pit_flags,int):
        services=[]
        if pit_flags&16:
            if s.get('auto_fuel'): services.append('自动加油')
            elif numeric(s.get('pit_fuel')) and s['pit_fuel']>=0 and s.get('pit_fuel_unit')=='l':
                services.append('加油'+spoken(s['pit_fuel'])+'升')
            else: services.append('加油')
        count=(pit_flags&15).bit_count()
        if count: services.append('更换'+spoken(count)+'条轮胎')
        if pit_flags&64: services.append('快速维修')
        if services:parts.append('当前进站服务：'+'、'.join(services)+'。')
    return ''.join(parts)
