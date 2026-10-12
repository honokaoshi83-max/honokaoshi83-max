"""Conservative racing delivery profiles; emotion requires real reference audio."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
STYLES=('calm','warning','encouraging')
DEFAULTS={'calm':{'speed':1.0}, 'warning':{'speed':1.04}, 'encouraging':{'speed':1.02}, 'voices':{}}

def classify(text):
    # Remove clear/status text before looking for an active hazard.
    hazard=text.replace('黄旗解除','').replace('黄旗已解除','')
    if any(x in hazard for x in ('有车','还有车','三车并排','黄旗','红旗','黑旗','碰撞','前方事故','严重磨损','胎纹余量较低','当前检查上限','当前检查下限','告警','动力异常','油压过低','水温过高','油量只够','油量不够','必须维修','强制维修')):
        return 'warning'
    # Other drivers' best laps are information, not a congratulation.
    if not any(x in text for x in ('前一名','后一名','领跑车','号车','前车','后车')) and any(x in text for x in ('刷新最快圈','刷新个人最佳','刷新最佳圈','干得漂亮','做得很好','比赛获胜')):
        return 'encouraging'
    return 'calm'

def load_config():
    path=ROOT/'emotion_settings.json'
    cfg=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    result={**DEFAULTS,**cfg}
    for style in STYLES:
        speed=result[style].get('speed',1)
        if not isinstance(speed,(float,int)) or not .95 <= speed <= 1.08:
            raise ValueError('Emotion speed must be within 0.95–1.08')
    return result

def resolve(voice,style,base,config,root=ROOT):
    if style not in STYLES:
        raise ValueError('Unknown emotion; use auto, calm, warning or encouraging')
    settings=config.get('voices',{}).get(voice,{}).get(style,{})
    candidate=root/settings.get('reference','')
    ready=bool(settings.get('reference') and settings.get('reference_text') and candidate.is_file())
    profile={**base,**settings} if ready else dict(base)
    speed=float(config.get(style,{}).get('speed',1))
    identity=[style,speed]
    if ready:
        identity += [str(candidate.resolve()),settings['reference_text'],hashlib.sha256(candidate.read_bytes()).hexdigest()]
    return {'profile':profile,'speed':speed,'reference_ready':ready,
            'identity':hashlib.sha256(json.dumps(identity,ensure_ascii=False).encode()).hexdigest()}
