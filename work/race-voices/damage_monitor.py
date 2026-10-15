"""Conservative damage advice from documented SDK warning/repair fields.

Incident points are not damage percentages. No body-part location is inferred.
"""
import math


def duration_phrase(seconds):
    from telemetry_announcer import chinese_number
    minutes, seconds = divmod(math.ceil(seconds), 60)
    return ((chinese_number(minutes) + '分') if minutes else '') + chinese_number(seconds) + '秒'


class DamageMonitor:
    def __init__(self):
        self.incidents = None
        self.contact_at = None
        self.contact_reported = -float('inf')
        self.candidate = None
        self.since = 0
        self.reported = set()
        self.repair_reported = False
        self.repair_seen = False
        self.completion_since = None
        self.completion_reported = False

    def update(self, sample, now):
        if not sample.get('active', False):
            self.incidents = sample.get('incidents', 0)
            self.contact_at = None
            self.candidate = None
            self.repair_seen = False
            self.completion_since = None
            self.completion_reported = False
            self.repair_reported = False
            return []
        incidents = sample.get('incidents', 0)
        if self.incidents is not None and incidents - self.incidents >= 4:
            self.contact_at = now
        self.incidents = incidents
        warnings = int(sample.get('warnings') or 0)
        flags = int(sample.get('flags') or 0)
        engine = warnings & 0x45 if sample.get('rpm', 0) > 1000 and sample.get('speed', 0) > 2 else 0
        level = 'required' if warnings & 0x80 or flags & 0x100000 else 'optional' if warnings & 0x100 else 'none'
        signature = (level, engine)
        if signature != self.candidate:
            self.candidate, self.since = signature, now
        # A confirmed clean state rearms alerts after repairs, without claiming
        # that every structural fault is repaired.
        if signature == ('none', 0) and now - self.since >= 2 and sample.get('in_stall'):
            self.reported.clear()
        messages = []
        if now - self.since >= 2 and signature not in self.reported and signature != ('none', 0):
            parts = []
            if level == 'required':
                parts.append('赛车需要强制维修，请尽快安全返回维修区。车辆无法控制时，在安全位置停车并呼叫拖车。')
            elif level == 'optional':
                parts.append('检测到车辆碰撞，请安全驾驶。方向、制动或动力异常时提前回站进行维修。')
            if engine & 4:
                parts.append('发动机机油压力告警，请减轻负荷，尽快安全回站检查。')
            if engine & 1:
                parts.append('发动机水温告警，请减轻负荷；持续不退时回站检查。')
            if engine & 64:
                parts.append('发动机机油温度告警，请减轻负荷；持续不退时回站检查。')
            messages.extend(parts)
            self.reported.add(signature)
            self.contact_at = None
        if self.contact_at is not None and now - self.contact_at >= 2:
            if signature == ('none', 0) and now - self.contact_reported >= 30:
                messages.append('检测到碰撞事故记录，尚未确认损伤。留意方向、制动和动力，出现异常时安全回站检查。')
                self.contact_reported = now
            self.contact_at = None
        if sample.get('in_stall'):
            required = float(sample.get('required') or 0)
            optional = float(sample.get('optional') or 0)
            if (math.isfinite(required) and required > 0) or (math.isfinite(optional) and optional > 0):
                self.repair_seen = True
            complete = (self.repair_seen and sample.get('required') is not None
                        and sample.get('optional') is not None
                        and required == 0 and optional == 0
                        and sample.get('service_status') == 2
                        and not warnings & 0x180 and not flags & 0x100000)
            if complete:
                if self.completion_since is None:
                    self.completion_since = now
                if not self.completion_reported:
                    messages.append('本次维修已完成。出站前留意维修区交通，回到赛道后先确认车辆状态。')
                    self.completion_reported = True
            else:
                self.completion_since = None
            if not self.repair_reported and (required > 0 or optional > 0):
                parts = []
                if math.isfinite(required) and required > 0:
                    parts.append('强制维修预计还需' + duration_phrase(required) + '。')
                if math.isfinite(optional) and optional > 0:
                    parts.append('可选维修预计还需' + duration_phrase(optional) + '。')
                if parts:
                    messages.append(''.join(parts))
                    self.repair_reported = True
        else:
            self.repair_reported = False
            self.repair_seen = False
            self.completion_since = None
            self.completion_reported = False
        return messages


def sdk_snapshot(ir):
    """Missing fields disable that signal; never guess unavailable damage data."""
    names = set(ir.var_headers_names or [])
    def get(name, default=0):
        value = ir[name] if name in names else None
        return default if value is None else value
    return dict(incidents=get('PlayerCarMyIncidentCount'), warnings=get('EngineWarnings'),
                flags=get('SessionFlags'), required=get('PitRepairLeft', None),
                optional=get('PitOptRepairLeft', None), service_status=get('PlayerCarPitSvStatus', None),
                rpm=get('RPM'), speed=get('Speed'),
                in_stall=bool(get('PlayerCarInPitStall')) if 'PlayerCarInPitStall' in names else get('PlayerTrackSurface', -1) == 1,
                active=bool(get('IsOnTrack', False)) and not get('IsReplayPlaying', False))
