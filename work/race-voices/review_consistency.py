"""Shared descriptive consistency rules, not an official racing score."""
import math,statistics

RULE_ID='cv-075-200-v1'
RULE_TEXT=('评价规则：圈速波动率＝计时圈用时的总体标准差÷平均圈速×100%。'
           '不超过0.75%为稳定，超过0.75%且不超过2%为有一定波动，超过2%为不稳定；'
           '不足五个计时圈不评级。全部计时圈统计包含有用时的犯规无效圈；'
           '没有用时的无效圈只计入犯规比例。百分比显示保留两位小数，评级使用未舍入数值。以上为助手的评价参数。')

def timed(value):
    return type(value) in (int,float) and math.isfinite(value) and 10<=value<=3600

def grade(ratio,count):
    if ratio is None or count<5:return 'insufficient'
    return 'good' if ratio<=.0075 else 'medium' if ratio<=.02 else 'poor'

def pace_trend(valid):
    if len(valid)<4:return 'insufficient',None
    half=len(valid)//2
    delta=statistics.mean(valid[-half:])-statistics.mean(valid[:half])
    threshold=max(.1,statistics.mean(valid)*.002)
    return ('faster' if delta<=-threshold else 'slower' if delta>=threshold else 'steady'),delta

def measure(rows):
    times=[r['seconds'] for r in rows if timed(r.get('seconds'))]
    valid=[r['seconds'] for r in rows if r.get('valid') and timed(r.get('seconds'))]
    def metrics(values):
        average=statistics.mean(values) if values else None
        sd=statistics.pstdev(values) if len(values)>=2 else None
        ratio=sd/average if sd is not None else None
        return sd,ratio,grade(ratio,len(values))
    sd,ratio,stability=metrics(times)
    valid_sd,valid_ratio,valid_stability=metrics(valid)
    slow=0;mad=None;median=None
    if len(valid)>=5:
        median=statistics.median(valid)
        mad=statistics.median(abs(t-median) for t in valid)
        # Potential slow outliers only: no cause inferred and no data deleted.
        # A floor handles MAD=0 without classifying tiny timing noise as outliers.
        boundary=max(3.5*mad/.6745,.1,median*.0075)
        slow=sum(t-median>boundary for t in valid)
    return dict(standard_deviation=sd,valid_standard_deviation=valid_sd,
                all_timed_count=len(times),valid_timed_count=len(valid),
                timed_average=statistics.mean(times) if times else None,
                variation_ratio=ratio,valid_variation_ratio=valid_ratio,
                stability=stability,valid_stability=valid_stability,
                slow_outliers=slow,valid_median=median,valid_mad=mad,
                consistency_rule=RULE_ID,evaluation_rule=RULE_TEXT)

def description(stats,inline_rules=False):
    labels={'good':'圈速稳定','medium':'圈速有一定波动','poor':'圈速不稳定'}
    lines=[]
    for key,prefix,rating in [('variation_ratio','全部计时圈','stability'),
                              ('valid_variation_ratio','有效计时圈','valid_stability')]:
        if key=='variation_ratio' and stats['all_timed_count']==stats['valid_timed_count']:continue
        value=stats[key];level=stats[rating]
        if value is None:
            lines.append(prefix+'数据不足，暂不计算圈速波动率。')
        else:
            detail=(labels[level] if level in labels else '不足五个计时圈，暂不评级')
            note='（0.75%内为稳定；0.75%至2%为有一定波动；超过2%为不稳定）' if inline_rules else ''
            lines.append(f'{prefix}的圈速波动率为{value*100:.2f}%，'+detail+'。'+note)
    return lines
