"""Cache deployed fixed Chinese phrases without playing audio; safe to resume."""
import json
from pathlib import Path
import time
import requests

ROOT=Path(__file__).resolve().parent
from runtime_settings import service_url

def fixed_phrases(base,user,role):
    entries={}
    for folder in (base,user):
        path=folder/(role+'.grammars.zh')
        if not path.exists():
            continue
        raw=path.read_bytes()
        text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
        section=''
        for line in text.splitlines():
            if line.startswith('['):
                section=line.strip()
            elif section in ('[Speaker Phrases]','[Spotter Phrases]') and '=' in line:
                key,value=line.split('=',1)
                entries[key]=value.strip()
    return sorted({v for v in entries.values() if v and '%' not in v})

def catalog():
    from runtime_settings import simulator_root, documents, data_path, project_root, service_url
    base=simulator_root()/'Resources/Grammars'
    user=data_path('grammars')
    rows=set()
    for role,voice in [('Race Spotter','furina'),('Race Strategist','furina'),('Race Engineer','clorinde')]:
        for text in fixed_phrases(base,user,role):
            rows.add((voice,text,'mp3'))
    from damage_monitor import DamageMonitor
    texts=['我是克洛琳德，负责赛车状态、油量和维修提醒。',
           '检测到碰撞事故记录，尚未确认损伤。留意方向、制动和动力，出现异常时安全回站检查。',
           '本次维修已完成。出站前留意维修区交通，回到赛道后先确认车辆状态。']
    for flag in (128,256,4,1,64):
        m=DamageMonitor(); sample=dict(active=True,warnings=flag,rpm=3000,speed=20)
        m.update(sample,0); texts+=m.update(sample,2.1)
    for text in texts:
        rows.add(('clorinde',text,'wav'))
    from tire_monitor import MESSAGES
    for text in MESSAGES.values():
        rows.add(('clorinde',text,'wav'))
    from status_report import DISCONNECTED
    rows.add(('clorinde',DISCONNECTED,'wav'))
    # Keep each voice together to avoid switching models for every phrase.
    return sorted(rows,key=lambda r:(r[0]!='furina',r[0],r[2],r[1]))

def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    rows=catalog()
    if args.dry_run:
        print(json.dumps({'total':len(rows),'furina':sum(r[0]=='furina' for r in rows),'clorinde':sum(r[0]=='clorinde' for r in rows)}))
        return
    report=[]
    target=ROOT/'cache_report.json'
    for i,(voice,text,fmt) in enumerate(rows,1):
        status=ROOT/'telemetry_status.json'
        if status.exists() and json.loads(status.read_text(encoding='utf-8')).get('state')!='waiting_for_iracing':
            print('Paused: iRacing connected. Run again after driving.',flush=True)
            break
        started=time.perf_counter()
        r=requests.post(service_url()+'/v1/audio/speech',json=dict(voice=voice,input=text,response_format=fmt,speed=1),timeout=180)
        r.raise_for_status()
        if len(r.content)<1000:
            raise RuntimeError('Empty/short cache audio')
        report.append(dict(voice=voice,text=text,format=fmt,seconds=round(time.perf_counter()-started,3),bytes=len(r.content)))
        target.write_text(json.dumps(dict(total=len(rows),completed=len(report),complete=len(report)==len(rows),items=report),ensure_ascii=False,indent=2),encoding='utf-8')
        print(f'{i}/{len(rows)} {voice} {fmt} {text}',flush=True)
    print('Cache run complete',flush=True)

if __name__=='__main__':
    main()
