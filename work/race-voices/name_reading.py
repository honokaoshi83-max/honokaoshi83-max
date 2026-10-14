"""Catalog-backed name readings; model identifiers are spelled, quantities counted."""
import json,re
from functools import lru_cache
from runtime_settings import data_path
from speech_reading import DIGITS,cardinal
LETTERS=dict(zip('ABCDEFGHIJKLMNOPQRSTUVWXYZ',('诶','比','西','迪','伊','艾弗','吉','艾尺','艾','杰','开','艾勒','艾姆','恩','欧','皮','丘','阿尔','艾斯','提','优','维','达布留','艾克斯','歪','泽德')))

def spell_name(text):
    from speech_reading import normalize_reading
    text=normalize_reading(text)
    text=text.replace('iRacing','艾瑞星').replace('EVO II','第二代升级版').replace('升级版 II','第二代升级版')
    # Formula class names refer to classes, not four individual digits.
    text=re.sub(r'(?<=方程式)\s*2000','两千',text)
    text=text.replace('USF 2000','USF 两千').replace('Indy Pro 2000','Indy Pro 两千').replace('FF1600','FF一千六百')
    text=re.sub(r'(?<![A-Za-z0-9])(?:19|20)\d{2}(?=款|年|版|$|，)',lambda m:''.join(DIGITS[int(c)] for c in m.group()),text)
    text=re.sub(r'\d+(?:\.\d+)?',lambda m:''.join('点' if c=='.' else ('幺' if c=='1' else DIGITS[int(c)] ) for c in m.group()),text)
    text=re.sub(r'[A-Za-z]+',lambda m:''.join(LETTERS[c.upper()] for c in m.group()),text)
    text=re.sub(r'[()\[\]、，,；;]+','，',text)
    text=re.sub(r'[-—–]','',text)
    return re.sub(r'\s+','',text).strip('，')

@lru_cache(maxsize=1)
def aliases():
    mapping={name:"保时捷九幺幺" for name in ("保时捷911","保时捷 911","保时捷九一一","Porsche 911")}
    mapping.update({name:"保时捷七幺八" for name in ("保时捷718","保时捷 718","保时捷七一八","Porsche 718")})
    for file,field in (('tracks_zh.json','tracks'),('cars_zh.json','cars')):
        path=data_path(file)
        if not path.exists():continue
        for row in json.loads(path.read_text(encoding='utf-8'))[field]:
            reading=row.get('spoken')
            if not reading:continue
            for name in [row['zh'],row['en'],*row.get('aliases',[])]:
                # Conflicting same-name editions resolve only via explicit full name/path.
                if name in mapping and mapping[name]!=reading:continue
                mapping[name]=reading
            mapping.update(row.get('speech_aliases',{}))
            for current in [reading,*row.get('speech_aliases',{}).values()]:
                old=current.replace('幺','一')
                if old!=current:mapping[old]=current
    return sorted(mapping.items(),key=lambda row:-len(row[0]))

def normalize_names(text):
    rules={name.casefold():reading for name,reading in aliases()}
    if not rules:return text
    pattern='|'.join(r'(?<![A-Za-z0-9])'+re.escape(name)+r'(?![A-Za-z0-9])' for name in rules)
    return re.sub(pattern,lambda m:rules[m.group().casefold()],text,flags=re.I)


def resolve_car(path,display):
    key=re.sub(r'[\\/\s]+','/',path).strip('/').casefold()
    data=json.loads(data_path('cars_zh.json').read_text(encoding='utf-8'))
    for row in data['cars']:
        if key in [p.casefold() for p in [row['path'],*row.get('path_aliases',[])]]:return row['zh']
    return display
