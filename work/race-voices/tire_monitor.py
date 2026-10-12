"""Conservative pit-updated tire checks; never present old readings as live."""
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parent
WHEELS=('LF','RF','LR','RR')
DEFAULTS=dict(pressure_kpa_min=110,pressure_kpa_max=350,
              temperature_c_min=40,temperature_c_max=130,
              wear_warning_remaining=.70,wear_critical_remaining=.40,
              settle_seconds=2,warmup_laps=2)
MESSAGES={
    ('cold_kpa','low'):'冷胎压设置低于当前检查下限，请检查胎压设置。',
    ('cold_kpa','high'):'冷胎压设置高于当前检查上限，请检查胎压设置。',
    ('pressure_kpa','low'):'进站更新的胎压低于当前检查下限，请检查轮胎和胎压设置。',
    ('pressure_kpa','high'):'进站更新的胎压高于当前检查上限，请检查胎压设置。',
    ('carcass_c','low'):'进站更新的胎温低于当前检查下限。若已经换上新胎，出站后先逐步热胎。',
    ('carcass_c','high'):'进站更新的胎温高于当前检查上限，请检查轮胎负荷和驾驶方式。',
    ('remaining','warning'):'进站更新的胎纹余量较低，请确认换胎安排。',
    ('remaining','critical'):'进站更新的胎纹余量已达到严重磨损提醒线，请确认已经换胎。',
}

def number(value,lo=None,hi=None):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        return None
    if lo is not None and value<lo or hi is not None and value>hi:
        return None
    return float(value)

def load_settings(car_path=''):
    path=ROOT/'tire_settings.json'
    if not path.exists():
        return DEFAULTS.copy()
    config=json.loads(path.read_text(encoding='utf-8'))
    result={**DEFAULTS,**config.get('defaults',{})}
    result.update(config.get('cars',{}).get(car_path,{}))
    return result

class TireMonitor:
    def __init__(self,settings=None):
        self.settings={**DEFAULTS,**(settings or {})}
        for low,high in [('pressure_kpa_min','pressure_kpa_max'),('temperature_c_min','temperature_c_max')]:
            if number(self.settings[low]) is None or number(self.settings[high]) is None or self.settings[low]>=self.settings[high]:
                raise ValueError('Invalid tire inspection bounds')
        if not 0<=self.settings['wear_critical_remaining']<self.settings['wear_warning_remaining']<=1:
            raise ValueError('Wear thresholds use fraction of tread remaining')
        if number(self.settings['settle_seconds'],.1,30) is None or number(self.settings['warmup_laps'],0,100) is None:
            raise ValueError('Invalid tire timing settings')
        self.previous={}
        self.pending={}
        self.reported={}
        self.latest={}
        self.last_events=[]
        self.initialized=False

    def values(self,tire,field):
        raw=tire.get(field)
        if field in ('cold_kpa','pressure_kpa'):
            v=number(raw, .01 if field=='cold_kpa' else 0,1000)
            return None if v is None else (round(v,2),)
        raw=raw if isinstance(raw,(tuple,list)) else []
        lo,hi=(1,300) if field=='carcass_c' else (0,1)
        values=[number(v,lo,hi) for v in raw]
        # Partial triplets cannot define the coolest/hottest/worst region.
        return tuple(round(v,4) for v in values) if len(values)==3 and all(v is not None for v in values) else None

    def level(self,field,values,sample,replaced=False):
        cfg=self.settings
        if field in ('cold_kpa','pressure_kpa'):
            return 'low' if values[0]<cfg['pressure_kpa_min'] else 'high' if values[0]>cfg['pressure_kpa_max'] else None
        if field=='carcass_c':
            if max(values)>cfg['temperature_c_max']:
                return 'high'
            if not replaced and sample.get('completed_laps',0)>=cfg['warmup_laps'] and max(values)<cfg['temperature_c_min']:
                return 'low'
            return None
        worst=min(values)
        return 'critical' if worst<=cfg['wear_critical_remaining'] else 'warning' if worst<=cfg['wear_warning_remaining'] else None

    def update(self,sample,now):
        self.latest=sample
        self.last_events=[]
        if not sample.get('active'):
            self.pending.clear()
            # Reattachment establishes a baseline instead of speaking old data.
            self.initialized=False
            self.previous.clear()
            return []
        near=bool(sample.get('in_stall') or sample.get('on_pit_road'))
        stationary=sample.get('speed',float('inf'))<=1
        current={}
        replaced=set()
        for wheel in WHEELS:
            tire=sample.get('tires',{}).get(wheel,{})
            wear=self.values(tire,'remaining')
            old=self.previous.get((wheel,'remaining'))
            if near and old and wear and min(wear)>=.98 and min(old)<=.85:
                replaced.add(wheel)
            for field in ('cold_kpa','pressure_kpa','carcass_c','remaining'):
                key=(wheel,field)
                values=self.values(tire,field)
                if field=='remaining' and values==(0,0,0) and self.values(tire,'carcass_c') is None:
                    # A zero-filled initialization/reset packet is not evidence
                    # that three tread regions wore out simultaneously.
                    values=None
                current[key]=values
                if values is None:
                    self.pending.pop(key,None)
                elif field=='cold_kpa':
                    # These are current setup values, not tire measurements.
                    if key not in self.pending or self.pending[key][0]!=values:
                        self.pending[key]=(values,now,False)
                elif near and self.initialized and self.previous.get(key) is not None and self.previous[key]!=values:
                    prior_replaced=self.pending.get(key,(None,None,False))[2]
                    self.pending[key]=(values,now,wheel in replaced or prior_replaced)
        self.previous=current
        self.initialized=True
        if not near:
            self.pending={k:v for k,v in self.pending.items() if k[1]=='cold_kpa'}
        groups={}
        for key,(values,since,replaced_flag) in list(self.pending.items()):
            wheel,field=key
            if now-since<self.settings['settle_seconds'] or (field!='cold_kpa' and (not near or not stationary)):
                continue
            level=self.level(field,values,sample,replaced_flag)
            if level is None:
                self.reported.pop(key,None)
            elif self.reported.get(key)!=level:
                groups.setdefault((field,level),[]).append(dict(wheel=wheel,values=values))
                self.reported[key]=level
            if field!='cold_kpa':
                self.pending.pop(key,None)
        # Combine corners for each condition. Wear escalation wins if mixed.
        if ('remaining','critical') in groups:
            groups[('remaining','critical')]+=groups.pop(('remaining','warning'),[])
        self.last_events=[dict(field=f,level=l,wheels=w,text=MESSAGES[(f,l)]) for (f,l),w in groups.items()]
        return [event['text'] for event in self.last_events]

    def status(self):
        tires=self.latest.get('tires',{})
        return dict(mode='pit_update_inspection',settings=self.settings,
                    capabilities=dict(cold_pressure_settings=any(self.values(v,'cold_kpa') is not None for v in tires.values()),
                                      measured_pressure=any(self.values(v,'pressure_kpa') is not None for v in tires.values()),
                                      carcass_temperature=any(self.values(v,'carcass_c') is not None for v in tires.values()),
                                      tread_remaining=any(self.values(v,'remaining') is not None for v in tires.values())),
                    last_readings=tires,available_fields=self.latest.get('available_fields',[]),
                    freshness='temperature/wear/measurement alerts require observed pit update; setup pressure is not live pressure')

def tire_snapshot(ir):
    names=set(ir.var_headers_names or [])
    headers=getattr(ir,'_var_headers_dict',{})
    def get(name,default=None):
        value=ir[name] if name in names else None
        return default if value is None else value
    def unit(name,default=''):
        return str(getattr(headers.get(name),'unit',default) or default).strip().lower()
    def pressure(name,documented=False):
        value=number(get(name),0,1000000)
        if value is None:
            return None
        units=unit(name,'kpa' if documented else '')
        return value/1000 if units=='pa' else value*6.894757 if units=='psi' else value if units=='kpa' else None
    def temp(name):
        value=number(get(name),-100,600)
        if value is None:
            return None
        units=unit(name,'c')
        return (value-32)*5/9 if units in ('f','degf') else value if units in ('c','degc') else None
    tires={w:dict(cold_kpa=pressure(w+'coldPressure',True),pressure_kpa=pressure(w+'pressure'),
                  carcass_c=[temp(w+'tempC'+s) for s in 'LMR'],
                  remaining=[number(get(w+'wear'+s),0,1) for s in 'LMR']) for w in WHEELS}
    return dict(active=bool(get('IsOnTrack',False)) and not get('IsReplayPlaying',False) and not get('IsInGarage',False),
                in_stall=bool(get('PlayerCarInPitStall',False)),on_pit_road=bool(get('OnPitRoad',False)),
                speed=get('Speed',float('inf')),completed_laps=get('LapCompleted',0),tires=tires,
                available_fields=sorted(n for n in names if n.startswith(WHEELS) and any(t in n for t in ('pressure','Pressure','tempC','wear'))))
