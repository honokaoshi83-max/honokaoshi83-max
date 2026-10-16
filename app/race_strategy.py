"""Offline fuel plan; no game controls or live strategy execution."""
import json,math,os,tempfile
from pathlib import Path

def calculate_plan(plan):
    def number(key,minimum,maximum):
        x=plan.get(key)
        if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or not minimum<=x<=maximum:
            raise ValueError('请填写有效的'+{'initial_fuel':'初始燃油','capacity':'本场油量上限','burn':'单圈油耗','lap_seconds':'预计圈速','reserve_laps':'安全储备','race_laps':'比赛圈数','duration_minutes':'比赛时长'}[key])
        return x
    fuel=number('initial_fuel',.1,500);capacity=number('capacity',.1,500)
    burn=number('burn',.01,100);seconds=number('lap_seconds',10,3600)
    reserve=number('reserve_laps',0,10)*burn
    if fuel>capacity:raise ValueError('初始燃油不能超过本场油量上限。')
    if capacity<reserve+burn or fuel<reserve+burn:raise ValueError('初始燃油及油量上限需要覆盖至少一圈和安全储备。')
    mode=plan.get('mode')
    if mode=='time':
        minutes=number('duration_minutes',1,1440)
        laps=math.ceil(minutes*60/seconds)+1
    elif mode=='laps':
        laps=number('race_laps',1,20000)
        if int(laps)!=laps:raise ValueError('比赛圈数必须是整数。')
        laps=int(laps)
    else:raise ValueError('请选择限时或限圈比赛。')
    schedule=[];completed=0;remaining=laps
    while remaining>0:
        reach=math.floor((fuel-reserve)/burn+1e-9)
        if remaining<=reach:break
        if reach<1:raise ValueError('油量不足以完成下一赛段，请增加油量或降低安全储备。')
        fuel-=reach*burn;completed+=reach;remaining-=reach
        add=min(capacity-fuel,remaining*burn+reserve-fuel)
        fuel+=add
        schedule.append(dict(number=len(schedule)+1,lap=completed,minutes=completed*seconds/60,add=round(add,2),after=round(fuel,2)))
    return dict(race_laps=laps,stops=len(schedule),first_stop=schedule[0]['lap'] if schedule else None,
                total_fuel=round(laps*burn+reserve,2),reserve=round(reserve,2),schedule=schedule)

def save_plan(path,plan):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    data=json.dumps(dict(schema_version=1,plan=plan),ensure_ascii=False,indent=2,allow_nan=False)
    fd,tmp=tempfile.mkstemp(prefix='.strategy-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:stream.write(data+'\n')
        os.replace(tmp,path)
    finally:Path(tmp).unlink(missing_ok=True)

def load_plan(path):
    path=Path(path)
    if not path.exists():return None
    try:
        data=json.loads(path.read_text(encoding='utf-8'))
        if data.get('schema_version')!=1 or not isinstance(data.get('plan'),dict):raise ValueError()
        return data['plan']
    except (ValueError,TypeError,AttributeError) as error:raise ValueError('保存的策略文件无法读取，原文件已保留。') from error
