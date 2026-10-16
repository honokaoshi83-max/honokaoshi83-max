"""Durable UTF-8 reviews and bounded read-only history listing."""
import hashlib,json,os,re,tempfile
from pathlib import Path

def atomic(path,text):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.review-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8-sig',newline='') as stream:
            stream.write(text);stream.flush();os.fsync(stream.fileno())
        os.replace(tmp,path)
    finally:Path(tmp).unlink(missing_ok=True)

def duration(seconds):
    if not isinstance(seconds,(int,float)) or seconds<0:return '未知'
    seconds=round(seconds);h,seconds=divmod(seconds,3600);m,s=divmod(seconds,60)
    return (f'{h}小时' if h else '')+f'{m}分{s:02d}秒'

def lap_duration(seconds):
    if seconds is None:return '未知'
    minutes,ms=divmod(round(seconds*1000),60000)
    return f'{minutes}分{ms/1000:06.3f}秒'

def format_review(row):
    lines=['iRacing 赛后复盘','',f"比赛模式：{'正赛' if row['mode']=='race' else 'Time Trial'}",
        f"赛道：{row.get('track') or '未知'}",f"赛道布局：{row.get('layout') or '未知'}",f"车辆：{row.get('car') or '未知'}",
        f"比赛日期与时间：{row.get('started_at','未知')} 至 {row.get('ended_at','未知')}（本机记录时段，含时区）",
        f"比赛开始时间：{row.get('race_started_at') or '未知（中途接入或未观测到起点）'}",
        f"比赛总用时：{duration(row.get('total_seconds'))}"+('（SDK计时）' if row.get('total_seconds') is not None else '（未完整观测起止边界）'),
        f"已记录用时：{duration(row.get('observed_seconds'))}",f"结束原因：{row.get('reason','会话结束')}",
        f"完成圈数：{row.get('completed','未知')}（SDK圈数）"]
    if row.get('left_early'):
        lines+=['提前退出：是','预计赛事结束时间：'+(row.get('expected_end_at') or '未知'),
                '复盘生成时间：'+row.get('saved_at','未知'),
                '结束时间依据：退出前最后一次SDK剩余时间估算；仅分析退出前已记录数据。' if row.get('expected_end_at') else '结束时间依据：缺少可用剩余时间，无法确认赛事实际结束时刻。']
    if row['mode']=='race':
        lines+=['',f"总排名：{row.get('position') or '未知'}",f"组别排名：{row.get('class_position') or '未知'}",
                f"参赛车辆数：{row.get('cars') or '未知'}",f"发车名次：{row.get('grid') or '未知'}",
                f"名次变化：{row['grid']-row['position']:+d}" if row.get('grid') and row.get('position') else '名次变化：未知',
                '排名来源：'+row.get('position_source','SDK最后观测值，最终结果未确认')]
    stats=row.get('stats',{})
    if stats:
        sd=stats.get('standard_deviation')
        lines+=['',f"记录完成圈数：{stats['observed_laps']}",f"有计时数据的圈数：{stats['timed_laps']}",f"有效圈数：{stats['valid_laps']}",f"犯规无效圈数：{stats['invalid_laps']}",
                f"最快有效圈：{lap_duration(stats.get('best_valid'))}",f"有效平均圈速：{lap_duration(stats.get('valid_average'))}",
                ('稳定性标准差：未知（没有可用圈速）' if sd is None else f"稳定性标准差：{sd:.3f}秒（包含犯规无效计时圈）"),
                (f"无效圈占比：{stats['invalid_laps']/stats['observed_laps']:.1%}" if stats.get('observed_laps') else '无效圈占比：未知（没有已采集完成圈）'),
                '无效圈没有可用用时时仍计入犯规比例，不为其编造圈速。']
        if stats.get('consistency_rule'):
            variation=stats.get('variation_ratio');valid_variation=stats.get('valid_variation_ratio')
            lines+=[f"全部计时圈平均圈速：{lap_duration(stats.get('timed_average'))}",
                    f"全部计时圈波动率：{variation:.2%}" if variation is not None else '全部计时圈波动率：未知',
                    f"有效计时圈波动率：{valid_variation:.2%}" if valid_variation is not None else '有效计时圈波动率：未知',
                    '评价规则版本：'+stats['consistency_rule']]
    lines+=['','评价内容',*row.get('summary',[]),'','数据说明：仅依据已记录数据；不包含燃油或轮胎分析。']
    if row.get('incomplete'):lines.append('注意：复盘语音生成曾中断，本文保留已收到的评价段落。')
    return '\r\n'.join(lines)+'\r\n'

def save_review(project,row):
    root=Path(project).resolve();folder=root/'复盘'
    if folder.resolve().parent!=root:raise ValueError('复盘目录不能链接到应用目录之外')
    folder.mkdir(parents=True,exist_ok=True)
    date=re.sub(r'[^0-9T-]','',row.get('ended_at',row.get('saved_at','未知'))[:19]).replace('T','_')
    track=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',row.get('track','未知'))[:45].strip(' .') or '未知'
    stamp=hashlib.sha256(row['id'].encode()).hexdigest()[:16]
    stem=f"{date}_{'正赛' if row['mode']=='race' else 'TimeTrial'}_{track}_{stamp}"
    txt=folder/(stem+'.txt');meta=folder/(stem+'.json')
    if meta.exists() and txt.exists():
        existing=json.loads(meta.read_text(encoding='utf-8-sig'))
        if existing.get('id')==row['id']:return dict(existing,path=str(txt),new=False)
        raise ValueError('复盘文件标识冲突')
    payload=dict(row,file=txt.name)
    atomic(txt,format_review(row));atomic(meta,json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    return dict(payload,path=str(txt),new=True)

def recent_reviews(project,limit=5):
    folder=Path(project).resolve()/'复盘';result=[]
    if not folder.exists() or folder.resolve().parent!=Path(project).resolve():return []
    for meta in folder.glob('*.json'):
        try:
            row=json.loads(meta.read_text(encoding='utf-8-sig'));name=row['file'];path=(folder/name).resolve()
            if path.parent!=folder.resolve() or path.suffix.lower()!='.txt' or not path.is_file() or Path(name).name!=name:continue
            result.append(dict(row,path=str(path)))
        except (OSError,ValueError,KeyError,TypeError):continue
    return sorted(result,key=lambda r:r.get('saved_at',''),reverse=True)[:limit]
