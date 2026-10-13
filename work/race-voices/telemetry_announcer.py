"""Read-only iRacing SDK lap/track announcements; standard spotter takes priority."""
import json
import queue
import re
import threading
import time
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent
from runtime_settings import documents, data_path, service_url
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
    return re.sub(prefix+r'Fast[。.]?', '赛道抓地状态良好。', text, flags=re.I)

def chinese_number(number):
    digits = '零一二三四五六七八九'
    if number < 10:
        return digits[number]
    if number < 100:
        tens, ones = divmod(number, 10)
        return (digits[tens] if tens > 1 else '')+'十'+(digits[ones] if ones else '')
    return str(number)

def lap_phrase(seconds):
    minutes, remainder = divmod(round(seconds*10), 600)
    whole, tenth = divmod(remainder, 10)
    whole_text = ('零' if whole < 10 else '')+chinese_number(whole)
    return f'本圈{chinese_number(minutes)}分{whole_text}秒{chinese_number(tenth)}。'

class TrackCatalog:
    def __init__(self, path):
        self.rows = json.loads(Path(path).read_text(encoding='utf-8'))['tracks']
        self.paths = {self.key(r['path']): r['zh'] for r in self.rows}
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

class LapTracker:
    def __init__(self):
        self.completed = None
        self.last_time = 0
        self.pending = None
        self.best = None

    def update(self, completed, seconds, now, valid=True):
        if self.completed is None or completed < self.completed:
            self.completed, self.last_time, self.pending = completed, seconds, None
            self.best = seconds if seconds > 0 else None
            return None
        if completed > self.completed:
            self.pending = (completed, now, valid)
            self.completed = completed
        if not self.pending or seconds <= 0:
            return None
        lap, started, valid = self.pending
        # SDK lap number and last-time variables can update on different ticks.
        if seconds == self.last_time and now-started < .5:
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
        self.items = queue.Queue(maxsize=8)
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
            self.items.put_nowait((time.monotonic(), text, False))
            log('queued', text=text)
        except queue.Full:
            log('queue_full', text=text)

    def submit_status(self,text):
        with self.status_lock:
            if self.status_pending:
                log('status_request_busy')
                return False
            try:
                self.items.put_nowait((time.monotonic(),text,True))
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
            created, text, is_status = self.items.get()
            # A long requested summary may require uncached CPU synthesis.
            limit=120 if is_status else 25
            try:
                if is_status:
                    # Submission holds this lock until local acknowledgement starts.
                    with self.status_lock:ack_until=self.status_ack_until
                else:ack_until=0
                while (SC_TEMP/'Speaking.status').exists() and time.monotonic()-created < limit-5:
                    time.sleep(.1)
                if time.monotonic()-created >= limit-5:
                    log('expired', text=text)
                    continue
                response = requests.post(service_url()+'/v1/audio/speech', json={
                    'voice':'clorinde', 'input':text, 'speed':1.0, 'response_format':'wav'}, timeout=90)
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
                    time.sleep(.1)
                if time.monotonic()-created >= limit:
                    log('expired_after_synthesis', text=text)
                    continue
                for attempt in range(2):
                    winsound.PlaySound(str(audio), winsound.SND_FILENAME|winsound.SND_ASYNC)
                    until = time.monotonic()+duration
                    interrupted = False
                    while time.monotonic() < until:
                        if (SC_TEMP/'Speaking.status').exists():
                            winsound.PlaySound(None, winsound.SND_PURGE)
                            interrupted = True
                            break
                        time.sleep(.1)
                    if not interrupted:
                        log('played', text=text, duration=round(duration,2))
                        break
                    log('yield_to_spotter', text=text)
                    if is_status:
                        # Do not restart an entire long report after a hazard.
                        break
                    while (SC_TEMP/'Speaking.status').exists() and time.monotonic()-created < limit:
                        time.sleep(.1)
                    if time.monotonic()-created >= limit:
                        break
            except Exception as e:
                self.audio_state(e)
            finally:
                if is_status:
                    with self.status_lock:
                        self.status_pending=False
                self.items.task_done()

def run():
    import irsdk
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
    invalid = False
    last_incidents = 0
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
                session = None
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
                session, tracker, invalid, last_incidents = key, LapTracker(), False, incidents
                damage = DamageMonitor()
                fuel_history = FuelHistory()
                driver_info = ir['DriverInfo'] or {}
                driver = next((d for d in driver_info.get('Drivers',[]) if d.get('CarIdx')==driver_info.get('DriverCarIdx')), {})
                car_path = driver.get('CarPath','')
                try:
                    tires = TireMonitor(load_settings(car_path))
                except (ValueError, TypeError, OSError):
                    log('tire_config_invalid', car_path=car_path)
                    tires = TireMonitor()
                name = catalog.resolve(weekend.get('TrackName',''), weekend.get('TrackDisplayName',''), weekend.get('TrackConfigName',''))
                log('session', track=name, identifier=weekend.get('TrackName'), layout=weekend.get('TrackConfigName'), completed=completed)
                announcer.submit('当前赛道是'+name+'。')
            report_sample=report_snapshot(ir)
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
            if incidents > last_incidents:
                invalid = True
            message = tracker.update(completed, seconds, time.monotonic(), valid=not invalid)
            if message:
                log('lap_detected', lap=completed, seconds=seconds, text=message)
                announcer.submit(message)
                invalid = False
            last_incidents = incidents
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
