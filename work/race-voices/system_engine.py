"""Windows speech fallback. Voice identifiers are roles, not cloned voices."""
import base64,hashlib,json,subprocess,tempfile
from pathlib import Path
from runtime_settings import project_root,settings,ffmpeg_path

class SystemEngine:
    def __init__(self):
        self.profiles={};self.config=settings();self.fingerprint=hashlib.sha256(json.dumps(self.config.get('system_voices',{}),sort_keys=True).encode()).hexdigest()

    def __call__(self,voice,text,speed,fmt):
        selected=self.config.get('system_voices',{}).get(voice,'')
        with tempfile.TemporaryDirectory() as tmp:
            wav=Path(tmp)/'speech.wav'
            subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',
                str(project_root()/'scripts/system_speech.ps1'),'-TextBase64',base64.b64encode(text.encode('utf-8')).decode(),
                '-VoiceName',selected,'-OutputFile',str(wav)],check=True,capture_output=True,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),timeout=60)
            data=wav.read_bytes()
        if fmt=='mp3':
            data=subprocess.run([str(ffmpeg_path()),'-hide_banner','-loglevel','error','-i','pipe:0','-f','mp3','-codec:a','libmp3lame','pipe:1'],input=data,capture_output=True,check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).stdout
        if speed!=1:
            from bridge import adjust_delivery
            data=adjust_delivery(data,speed)
        return data
