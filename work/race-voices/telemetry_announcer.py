"""Read-only iRacing SDK lap/track announcements; standard spotter takes priority."""
import json
import queue
import re
import threading
import time
from functools import lru_cache
from itertools import count
from pathlib import Path

ROOT = Path(__file__).resolve().parent
from runtime_settings import documents, data_path, service_url
from opening_sequence import OpeningLine,opening_sequence,mark_opening,component_interrupts_opening
SC_TEMP = documents()/'Simulator Controller/Temp'

@lru_cache(maxsize=1)
def phrasebook():
    """Adapt already-loaded SC phrases until assistants reload user grammars.

    Match a complete known template. Never invent a missing telemetry value.
    """
    path = data_path('phrasebook.json')
    if not path.exists():
        return []
    rules, seen = [], set()
    token = r'%([A-Za-z][A-Za-z0-9_]*)%'
    for entry in json.loads(path.read_text(encoding='utf-8')):
        before, after = entry['before'].strip(), entry['after'].strip()
        names = re.findall(token, before)
        if not set(re.findall(token, after)) <= set(names):
            continue
        if (before, after) in seen:
            continue
        seen.add((before, after))
        parts, cursor, captured = [], 0, set()
        for match in re.finditer(token, before):
            parts.append(re.escape(before[cursor:match.start()]))
            name = match.group(1)
            parts.append(f'(?P={name})' if name in captured else f'(?P<{name}>.+?)')
            captured.add(name)
            cursor = match.end()
        parts.append(re.escape(before[cursor:]))
        rules.append((re.compile(''.join(parts)), after))
    return rules

def clean_phrase(text):
    # Recover only the known corrupted farewell, never synthesize INI keys.
    if ('Bye.2=' in text and 'Bye.3=' in text) or text.startswith('鏈椹'):
        return '本次比赛结束，期待下一次合作。'
    for pattern, replacement in phrasebook():
        match = pattern.fullmatch(text)
        if match:
            text = re.sub(r'%([A-Za-z][A-Za-z0-9_]*)%',
                          lambda m: match.group(m.group(1)), replacement)
            break
    text = re.sub(r'\s*(?:Jona|Elisa|Khato|Aiden)\s*', '芙宁娜', text)
    text = text.replace('我是芙宁娜，会帮你留意赛车状态和油量。', '赛车状态和油量监控已就绪。')
    text = text.replace('我是芙宁娜，会帮你留意进站策略。', '进站策略监控已就绪。')
    # Assistants may still hold an older grammar until their next session.
    for before, after in [('两侧都清了。', '两侧已无车。'),
                          ('左侧清了。', '左侧已无车。'),
                          ('右侧清了。', '右侧已无车。')]:
        text = text.replace(before, after)
    text = re.sub(r'(\d+)\s*分\s*(\d+(?:\.\d+)?)\s*秒',
                  lambda m: lap_phrase(int(m.group(1))*60+float(m.group(2)))[2:-1], text)
    prefix = r'赛道(?:是|抓地状态[：:])\s*'
    text = re.sub(prefix+r'(?:绿色|Green)[。.]?', '赛道橡胶较少，抓地力偏低。', text, flags=re.I)
    text=re.sub(prefix+r'Fast[。.]?', '赛道抓地状态良好。', text, flags=re.I)
    from driver_numbers import normalize_references
    return normalize_references(text)

def chinese_number(number):
    from speech_reading import cardinal
    return cardinal(number)

def lap_phrase(seconds):
    minutes, remainder = divmod(round(seconds*10), 600)
    whole, tenth = divmod(remainder, 10)
    whole_text = ('零' if whole < 10 else '')+chinese_number(whole)
    return f'本圈{chinese_number(minutes)}分{whole_text}秒{chinese_number(tenth)}。'

class TrackCatalog:
    def __init__(self, path):
        self.rows = json.loads(Path(path).read_text(encoding='utf-8'))['tracks']
        self.paths = {self.key(path): r['zh'] for r in self.rows for path in [r['path'],*r.get('path_aliases',[])]}
        self.names = {r['en'].casefold(): r['zh'] for r in self.rows}

    @staticmethod
    def key(value):
        return re.sub(r'[\\/\s]+', '/', str(value).strip()).strip('/').casefold()

    def resolve(self, identifier, display, layout=''):
        key = self.key(identifier)
        # Never discard an unknown layout by silently returning the base track.
        if key in self.paths and ('/' in key or not layout):
            return self.paths[key]
        combined = (display + ' - ' + layout).casefold()
        if combined in self.names:
            return self.names[combined]
        if layout and self.key(str(identifier)+'/'+layout) in self.paths:
            return self.paths[self.key(str(identifier)+'/'+layout)]
        base = self.names.get(display.casefold(), self.paths.get(key, display))
        return base + (' — '+layout if layout else '')

def lap_reporting_allowed(session_type,session_state):
    return session_type != "Race" or session_state in (4,5,6)

class LapIncidents:
    """Keep incident evidence against SDK current lap, not score delivery time."""
    def __init__(self):
        self.lap=None
        self.count=None
        self.invalid=set()
        self.current_time=None

    def update(self, lap, incidents, completed=None, current_time=None, last_score=None):
        if self.lap is not None and (lap<self.lap or incidents<self.count):
            self.invalid.clear()
        reset=(completed==0 and (last_score is None or last_score<=0)
               and current_time is not None and self.current_time is not None
               and self.current_time>1 and current_time+1<self.current_time)
        if self.count is not None and incidents>self.count:
            # A crossing sample belongs to the lap just completed.
            target=self.lap if self.lap is not None and lap>self.lap else lap
            self.invalid.add(target)
        if reset:
            # Some sessions keep the same Lap value while leaving the outlap.
            self.invalid.discard(lap)
        self.lap,self.count,self.current_time=lap,incidents,current_time
        self.invalid={n for n in self.invalid if n>=lap-3}

    def valid(self, completed):
        return completed not in self.invalid


def play_with_priority(play, stop, speaking, duration, created, limit, opening=False,
                       is_status=False, on_interrupt=lambda:None, now=None,
                       sleep=None,cancelled=lambda:False):
    now=now or time.monotonic
    sleep=sleep or time.sleep
    attempts=40 if opening else 2
    for attempt in range(attempts):
        quiet_since=now()
        while now()-created<limit:
            if cancelled():stop();return False
            if speaking():quiet_since=now()
            elif not opening or now()-quiet_since>=2:break
            sleep(.1)
        if cancelled() or now()-created>=limit:return False
        play()
        until=now()+duration
        interrupted=False
        speaking_since=None
        while now()<until:
            if cancelled():stop();return False
            if speaking():
                if speaking_since is None:speaking_since=now()
                if not opening or now()-speaking_since>=.35:
                    stop();interrupted=True;on_interrupt();break
            else:speaking_since=None
            sleep(.1)
        if not interrupted:return True
        if is_status:return False
    return False

class LapTracker:
    def __init__(self):
        self.completed = None
        self.last_time = 0
        self.pending = None
        self.best = None

    def update(self, completed, seconds, now, valid=True, current_lap=None):
        if self.completed is None or completed < self.completed:
            self.completed, self.last_time, self.pending = completed, seconds, None
            self.best = seconds if seconds > 0 else None
            return None
        if completed > self.completed:
            self.pending = (completed, now, valid)
            self.completed = completed
        if not self.pending:
            self.last_time=seconds
            return None
        if now-self.pending[1]>5:
            self.pending=None
            self.last_time=seconds
            return None
        if seconds <= 0:
            return None
        lap, started, valid = self.pending
        # SDK lap number and last-time variables can update on different ticks.
        # A timer reset proves a crossing, not publication of the new score.
        # Identical values have no freshness evidence; expire instead of guessing.
        if seconds == self.last_time:
            return None
        self.pending = None
        self.last_time = seconds
        message = lap_phrase(seconds)
        if not valid:
            message += '本圈有事故记录。'
        else:
            if self.best is not None:
                delta = seconds-self.best
                if delta < -.05:
                    message += f'刷新最快圈，快{-delta:.1f}秒。'
                elif delta > .05:
                    message += f'比最快圈慢{delta:.1f}秒。'
            self.best = seconds if self.best is None else min(self.best, seconds)
        return message

def log(event, **data):
    with (ROOT/'telemetry_events.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps({'time':time.strftime('%Y-%m-%d %H:%M:%S'), 'event':event, **data}, ensure_ascii=False)+'\n')

class Announcer:
    def __init__(self):
        self.items = queue.PriorityQueue(maxsize=16)
        self._sequence=count()
        self.urgent_pending=threading.Event()
        self.opening_generation=0
        mark_opening(False)
        self.error_latched = False
        self.status_pending = False
        self.status_lock = threading.Lock()
        from status_prompt import LocalStatusPrompt, prompt_path
        self.status_prompt = LocalStatusPrompt(prompt_path(), SC_TEMP/'Speaking.status', ROOT)
        self.status_ack_until = 0
        threading.Thread(target=self.play, daemon=True).start()

    def audio_state(self, error=None):
        if error is None:
            if self.error_latched:
                log('audio_recovered')
            self.error_latched = False
        else:
            if not self.error_latched:
                log('audio_error', error=type(error).__name__, detail=str(error)[:250])
            self.error_latched = True

    def submit(self, text):
        try:
            urgent=getattr(text,'flag',False)
            sequence=self.__dict__.setdefault('_sequence',count())
            item=(0 if urgent else 1,(time.monotonic(),next(sequence)),text,False)
            self.items.put_nowait(item)
            if urgent:self.urgent_pending.set()
            log('queued', text=text,order=item[1][1])
        except queue.Full:
            log('queue_full', text=text)

    def cancel_opening(self):
        self.opening_generation+=1
        mark_opening(False)

    def submit_opening(self,lines):
        self.cancel_opening()
        mark_opening(True)
        for index,line in enumerate(lines):
            line.generation=self.opening_generation
            line.last=index==len(lines)-1
            self.submit(line)

    def submit_status(self,text):
        with self.status_lock:
            if self.status_pending:
                log('status_request_busy')
                return False
            try:
                sequence=self.__dict__.setdefault('_sequence',count())
                self.items.put_nowait((1,(time.monotonic(),next(sequence)),text,True))
                self.status_pending=True
                prompt=getattr(self,'status_prompt',None)
                self.status_ack_until=prompt.play() if prompt else 0
                log('status_acknowledged' if self.status_ack_until else 'status_ack_skipped')
                log('status_queued',text=text)
                return True
            except queue.Full:
                log('status_queue_full')
                return False

    def play(self):
        import requests, winsound, wave
        audio = ROOT/'telemetry_playback.wav'
        while True:
            item=self.items.get()
            if len(item)==3:priority=1;created,text,is_status=item
            else:priority,created,text,is_status=item
            if isinstance(created,tuple):created=created[0]
            if priority==0:self.urgent_pending.clear()
            # A long requested summary may require uncached CPU synthesis.
            opening=isinstance(text,OpeningLine) or text.startswith("当前赛道是")
            cancelled=lambda:isinstance(text,OpeningLine) and getattr(text,'generation',self.opening_generation)!=self.opening_generation
            urgent_event=getattr(self,'urgent_pending',None)
            preempted=lambda:priority>0 and urgent_event is not None and urgent_event.is_set()
            limit=120 if is_status else (180 if opening else 25)
            try:
                if cancelled():
                    log('opening_cancelled',text=text);continue
                if is_status:
                    # Submission holds this lock until local acknowledgement starts.
                    with self.status_lock:ack_until=self.status_ack_until
                else:ack_until=0
                while (SC_TEMP/'Speaking.status').exists() and time.monotonic()-created < limit-5:
                    if cancelled():break
                    time.sleep(.1)
                if cancelled():
                    log('opening_cancelled',text=text);continue
                if time.monotonic()-created >= limit-5:
                    log('expired', text=text)
                    continue
                response = requests.post(service_url()+'/v1/audio/speech', json={
                    'voice':'furina' if text.startswith('本圈') else getattr(text,'voice','clorinde'), 'input':text, 'speed':1.0,
                    'response_format':'wav','opening':opening,'flag':getattr(text,'flag',False)}, timeout=90)
                response.raise_for_status()
                self.audio_state()
                audio.write_bytes(response.content)
                with wave.open(str(audio)) as w:
                    # FFmpeg pipe WAVs use an unknown-length header; count the
                    # actual PCM bytes instead of trusting that sentinel.
                    pcm = w.readframes(min(w.getnframes(), w.getframerate()*300))
                    channels, width, rate = w.getnchannels(), w.getsampwidth(), w.getframerate()
                    duration = len(pcm)/(channels*width*rate)
                with wave.open(str(audio), 'wb') as w:
                    w.setnchannels(channels)
                    w.setsampwidth(width)
                    w.setframerate(rate)
                    w.writeframes(pcm)
                while time.monotonic()<ack_until and not (SC_TEMP/'Speaking.status').exists():
                    time.sleep(.02)
                while (SC_TEMP/'Speaking.status').exists() and time.monotonic()-created < limit:
                    if cancelled():break
                    time.sleep(.1)
                if time.monotonic()-created >= limit:
                    log('expired_after_synthesis', text=text)
                    continue
                played=play_with_priority(
                    lambda:winsound.PlaySound(str(audio),winsound.SND_FILENAME|winsound.SND_ASYNC),
                    lambda:winsound.PlaySound(None,winsound.SND_PURGE),
                    lambda:(SC_TEMP/'Speaking.status').exists() and (not opening or component_interrupts_opening()),duration,created,limit,
                    opening=opening,is_status=is_status,
                    on_interrupt=lambda:log('yield_to_spotter',text=text),cancelled=lambda:cancelled() or preempted())
                log('played' if played else 'playback_not_completed',text=text,duration=round(duration,2))
                if not played and preempted() and not is_status and not cancelled():
                    self.items.put_nowait((priority,created,text,is_status))
            except Exception as e:
                self.audio_state(e)
            finally:
                if isinstance(text,OpeningLine) and getattr(text,'last',False) and not cancelled() and not preempted():
                    mark_opening(False)
                if is_status:
                    with self.status_lock:
                        self.status_pending=False
                self.items.task_done()

def run():
    import irsdk
    from driver_numbers import write_snapshot,clear_snapshot
    from flag_monitor import FlagMonitor,mark_active
    flags_monitor=FlagMonitor()
    flags_status_at=0
    driver_numbers_at=0
    from damage_monitor import DamageMonitor, sdk_snapshot
    from tire_monitor import TireMonitor, tire_snapshot, load_settings
    from status_button import StatusButton
    from status_report import FuelHistory, snapshot as report_snapshot, status_phrase, DISCONNECTED
    ir = irsdk.IRSDK()
    catalog = TrackCatalog(data_path('tracks_zh.json'))
    announcer = Announcer()
    button = StatusButton()
    fuel_history = FuelHistory()
    session = None
    tracker = LapTracker()
    damage = DamageMonitor()
    try:
        tires = TireMonitor(load_settings())
    except (ValueError, TypeError, OSError):
        log('tire_config_invalid')
        tires = TireMonitor()
    tire_status_at = 0
    lap_incidents = LapIncidents()
    status = ROOT/'telemetry_status.json'
    log('started')
    while True:
        try:
            request_status=button.requested()
            if not ir.is_initialized:
                ir.startup()
            if not ir.is_initialized or not ir.is_connected:
                if request_status:
                    announcer.submit_status(DISCONNECTED)
                if session is not None:
                    log('disconnected')
                    announcer.cancel_opening()
                session = None
                clear_snapshot()
                mark_active(False)
                fuel_history = FuelHistory()
                status.write_text(json.dumps({'state':'waiting_for_iracing'}), encoding='utf-8')
                (ROOT/'tire_monitor_status.json').write_text(json.dumps({'state':'waiting_for_iracing','mode':'pit_update_inspection'},ensure_ascii=False),encoding='utf-8')
                ir.shutdown()
                time.sleep(2)
                continue
            ir.freeze_var_buffer_latest()
            weekend = ir['WeekendInfo'] or {}
            key = (weekend.get('SubSessionID'), weekend.get('TrackID'), ir['SessionNum'])
            completed = int(ir['LapCompleted'] or 0)
            seconds = float(ir['LapLastLapTime'] or 0)
            incidents = int(ir['PlayerCarMyIncidentCount'] or 0)
            if key != session:
                session, tracker, lap_incidents = key, LapTracker(), LapIncidents()
                damage = DamageMonitor()
                fuel_history = FuelHistory()
                driver_info = ir['DriverInfo'] or {}
                write_snapshot(driver_info,ir['CarIdxClassPosition'])
                driver_numbers_at=time.monotonic()
                flags_monitor=FlagMonitor()
                driver = next((d for d in driver_info.get('Drivers',[]) if d.get('CarIdx')==driver_info.get('DriverCarIdx')), {})
                car_path = driver.get('CarPath','')
                try:
                    tires = TireMonitor(load_settings(car_path))
                except (ValueError, TypeError, OSError):
                    log('tire_config_invalid', car_path=car_path)
                    tires = TireMonitor()
                name = catalog.resolve(weekend.get('TrackName',''), weekend.get('TrackDisplayName',''), weekend.get('TrackConfigName',''))
                log('session', track=name, identifier=weekend.get('TrackName'), layout=weekend.get('TrackConfigName'), completed=completed)
                announcer.submit_opening(opening_sequence(name,ir['AirTemp'],ir['TrackTempCrew'],ir['TrackWetness']))
            report_sample=report_snapshot(ir)
            if time.monotonic()-driver_numbers_at>=2:
                write_snapshot(ir['DriverInfo'] or {},ir['CarIdxClassPosition'])
                driver_numbers_at=time.monotonic()
            for flag in flags_monitor.update(int(ir['SessionFlags'] or 0),time.monotonic()):
                log('flag_detected',text=flag,flags=int(ir['SessionFlags'] or 0))
                announcer.submit(flag)
            if time.monotonic()-flags_status_at>=2:
                mark_active(True);flags_status_at=time.monotonic()
            if report_sample['active']:
                fuel_history.update(completed,report_sample['fuel'],seconds,report_sample['pit'])
            else:
                fuel_history=FuelHistory()
            if request_status:
                report=status_phrase(report_sample,fuel_history) if report_sample['active'] else DISCONNECTED
                log('status_requested',connected=report_sample['active'],fuel_samples=len(fuel_history.samples))
                announcer.submit_status(report)
            damage_sample = sdk_snapshot(ir)
            for warning in damage.update(damage_sample, time.monotonic()):
                log('damage_detected', text=warning, evidence=damage_sample)
                announcer.submit(warning)
            tire_sample = tire_snapshot(ir)
            now = time.monotonic()
            for warning in tires.update(tire_sample, now):
                log('tire_detected', text=warning, evidence=tires.last_events)
                announcer.submit(warning)
            if now-tire_status_at>=2:
                tire_status_at = now
                tire_state = {'state':'connected','car_path':car_path,**tires.status()}
                temporary = ROOT/'tire_monitor_status.tmp'
                temporary.write_text(json.dumps(tire_state,ensure_ascii=False),encoding='utf-8')
                temporary.replace(ROOT/'tire_monitor_status.json')
            sdk_lap=int(ir['Lap'] or 0)
            current_time=float(ir['LapCurrentLapTime'] or 0)
            lap_incidents.update(sdk_lap,incidents,completed,current_time,seconds)
            session_info=ir['SessionInfo'] or {}
            session_number=ir['SessionNum']
            kind=next((row.get('SessionType','') for row in session_info.get('Sessions',[]) if row.get('SessionNum')==session_number),'')
            # Official SDK SessionState: racing=4, checkered=5, cool_down=6.
            race_active=lap_reporting_allowed(kind,ir['SessionState'])
            if not race_active:
                tracker=LapTracker()
                tracker.update(completed,seconds,time.monotonic())
                message=None
            else:
                message = tracker.update(completed, seconds, time.monotonic(), valid=lap_incidents.valid(completed), current_lap=current_time)
            if message:
                log('lap_detected', lap=completed, sdk_lap=sdk_lap, incidents=incidents, invalid_laps=sorted(lap_incidents.invalid), seconds=seconds, text=message)
                announcer.submit(message)
            status.write_text(json.dumps({'state':'connected','completed_laps':completed,'last_lap_seconds':seconds,'track':name}, ensure_ascii=False), encoding='utf-8')
            time.sleep(.25)
        except Exception as e:
            log('telemetry_error', error=type(e).__name__, detail=str(e)[:200])
            time.sleep(2)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test-audio', action='store_true')
    if parser.parse_args().self_test_audio:
        announcer = Announcer()
        announcer.submit('我是芙宁娜。本圈一分零九秒七。当前赛道是奥尔顿公园赛道，福斯特布局。')
        announcer.items.join()
    else:
        run()
