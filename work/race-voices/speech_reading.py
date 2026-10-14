"""Contextual spoken numbers and explicit Chinese pronunciation overrides."""
import re,json
from functools import lru_cache
DIGITS='零一二三四五六七八九'
# Only override complete phrases; unrelated uses of the same character remain intact.
LEXICON={
    '筑波':('zhu4','bo1'), '长滩':('chang2','tan1'),
    '长布局':('chang2','bu4','ju2'), '延长':('yan2','chang2'),
    '俱乐部':('ju4','le4','bu4'), '柏林':('bo2','lin2'),
    '还可以':('hai2','ke3','yi3'), '还能':('hai2','neng2'),
    '还有':('hai2','you3'), '剩余':('sheng4','yu2'),
    '重新':('chong2','xin1'), '重启':('chong2','qi3'),
    '重复':('chong2','fu4'), '重量':('zhong4','liang4'),
    '更换':('geng1','huan4'), '磨损':('mo2','sun3'),
    '强制':('qiang2','zhi4'), '降雨':('jiang4','yu3'),
}
VERSION='reading-v2'

@lru_cache(maxsize=1)
def lexicon():
    from runtime_settings import data_path
    path=data_path('name_pronunciations_zh.json')
    names=json.loads(path.read_text(encoding='utf-8'))['phrases'] if path.exists() else {}
    return {**names,**LEXICON}


def cardinal(number):
    number=int(number)
    if number<0:return '负'+cardinal(-number)
    if number<10:return DIGITS[number]
    for scale,label in ((100000000,'亿'),(10000,'万')):
        if number>=scale:
            high,low=divmod(number,scale)
            prefix='两' if high==2 else cardinal(high)
            return prefix+label+(('零' if low<scale//10 else '')+cardinal(low) if low else '')
    result='';zero=False
    for unit,label in ((1000,'千'),(100,'百'),(10,'十'),(1,'')):
        digit,number=divmod(number,unit)
        if digit:
            if zero:result+='零';zero=False
            result+=('两' if digit==2 and unit==1000 else DIGITS[digit])+label
        elif result and number:zero=True
    return result[1:] if result.startswith('一十') else result

def spoken_numeric(value):
    sign='负' if value.startswith('-') else ''
    value=value.lstrip('+-')
    integer,dot,fraction=value.partition('.')
    return sign+cardinal(int(integer))+('点'+''.join(DIGITS[int(d)] for d in fraction) if dot else '')

def normalize_reading(text):
    # Race bibs use cardinal readings; model identifiers keep their own rules.
    def bib(value):
        digits={c:str(i) for i,c in enumerate(DIGITS)}
        digits.update({'幺':'1','〇':'0','两':'2'})
        return cardinal(int(''.join(digits.get(c,c) for c in value)))
    text=re.sub(r'[零〇一幺二两三四五六七八九]+(?=号(?:赛车|车)(?!位))',lambda m:bib(m.group()),text)
    text=re.sub(r'(车号|赛车号码|车辆编号)(\s*[:：]?\s*)([零〇一幺二两三四五六七八九]+)',lambda m:m.group(1)+m.group(2)+bib(m.group(3)),text)
    text=re.sub(r'(?<![A-Za-z0-9.])\d+(?=号(?:赛车|车)(?!位))',lambda m:cardinal(int(m.group())),text)
    text=re.sub(r'(车号|赛车号码|车辆编号)(\s*[:：]?\s*)(\d+)',lambda m:m.group(1)+m.group(2)+cardinal(int(m.group(3))),text)
    text=re.sub(r'筑波\s*(1000|2000)(?!\d)',lambda m:'筑波'+cardinal(int(m.group(1))),text)
    text=re.sub(r'(?<![A-Za-z0-9.])(100|200|300|1000|2000)(?=布局)',lambda m:cardinal(int(m.group())),text)
    # Explicit year labels retain digit-by-digit reading.
    text=re.sub(r'(?:19|20)\d{2}(?=版|年|大奖赛|杯赛|方程式|至)',lambda m:''.join(DIGITS[int(d)] for d in m.group()),text)
    # Counts and physical quantities, not model numbers, car numbers or years.
    units=r'(?:公里每小时|千米每小时|摄氏度|千帕|公里|千米|小时|分钟|秒钟|百分比|圈|升|秒|分|度|米|位|辆|个|天|周)'
    text=re.sub(r'(?<![A-Za-z0-9.])[-+]?\d+(?:\.\d+)?(?=\s*'+units+r')',lambda m:spoken_numeric(m.group()),text)
    text=re.sub(r'(?<![A-Za-z0-9.])(\d+(?:\.\d+)?)%',lambda m:'百分之'+spoken_numeric(m.group(1)),text)
    return text

def correct_word(word,pinyins):
    corrected=list(pinyins)
    for phrase,reading in lexicon().items():
        for match in re.finditer(re.escape(phrase),word):
            if len(corrected)==len(word):corrected[match.start():match.end()]=reading
    return corrected

def pronunciation_signature(text):
    return VERSION if any(word in text for word in lexicon()) else ''

def install_overrides():
    from pypinyin import load_phrases_dict
    load_phrases_dict({word:[[p] for p in reading] for word,reading in lexicon().items()})
    import jieba
    for word in lexicon():jieba.add_word(word,freq=100000)
    import text.chinese2 as chinese
    if getattr(chinese,'_race_reading_installed',False):return
    original=chinese.correct_pronunciation
    def corrected(word,pinyins):return correct_word(word,original(word,pinyins))
    chinese.correct_pronunciation=corrected
    chinese._race_reading_installed=True
