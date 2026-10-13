import sys,requests,winsound
from pathlib import Path
from wav_playback import finalize_wav
url=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:9881'
voice=sys.argv[2] if len(sys.argv)>2 else 'clorinde'
text='当前车辆状态正常，剩余燃油二十升。'
r=requests.post(url+'/v1/audio/speech',json={'voice':voice,'input':text,'response_format':'wav'},timeout=120);r.raise_for_status()
path=Path(__file__).resolve().parent/'desktop-test.wav';path.write_bytes(finalize_wav(r.content));winsound.PlaySound(str(path),winsound.SND_FILENAME|winsound.SND_NODEFAULT)
print('试听完成。')
