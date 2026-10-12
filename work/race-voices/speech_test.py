import requests,winsound
from pathlib import Path
from runtime_settings import service_url
r=requests.post(service_url()+'/v1/audio/speech',json={'voice':'clorinde','input':'中文播报测试，当前声音正常。','response_format':'wav'},timeout=180)
r.raise_for_status()
p=Path(__file__).with_name('speech_test.wav');p.write_bytes(r.content)
winsound.PlaySound(str(p),winsound.SND_FILENAME)
print('已播放中文测试音。')
