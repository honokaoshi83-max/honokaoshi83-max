"""Final output gain; cached speech stays at its original normalized level."""
import json,subprocess
from pathlib import Path

def load_volume(root):
    try:
        value=json.loads((Path(root)/'playback_settings.json').read_text(encoding='utf-8')).get('volume_percent',100)
        return max(0,min(100,float(value)))
    except (OSError,ValueError,TypeError):return 100

def apply_volume(data,fmt,root,ffmpeg):
    value=load_volume(root)
    if value==100:return data
    codec=['-codec:a','pcm_s16le'] if fmt=='wav' else ['-codec:a','libmp3lame','-b:a','128k']
    return subprocess.run([str(ffmpeg),'-hide_banner','-loglevel','error','-i','pipe:0','-af',f'volume={value/100}',
        *codec,'-f',fmt,'pipe:1'],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).stdout
