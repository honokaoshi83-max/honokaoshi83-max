"""Repeatable two-voice speech latency probe, without audio playback."""
import json,time,requests,platform,io,argparse
import soundfile as sf
from pathlib import Path
from runtime_settings import service_url
def main():
    p=argparse.ArgumentParser();p.add_argument('--url',default=service_url());p.add_argument('--output',default='benchmark-result.json');args=p.parse_args()
    results=[]
    for voice in ('clorinde','furina'):
        for text in ('本圈一分四十二秒六。','当前状态。剩余燃油二十升，预计还能行驶六圈，建议在五圈内进站加油。'):
            for attempt in (1,2):
                start=time.perf_counter();r=requests.post(args.url+'/v1/audio/speech',json={'voice':voice,'input':text,'response_format':'wav','emotion':'calm'},timeout=240);r.raise_for_status()
                elapsed=time.perf_counter()-start
                with sf.SoundFile(io.BytesIO(r.content)) as w:duration=len(w)/w.samplerate
                row={'voice':voice,'text':text,'attempt':attempt,'request_seconds':round(elapsed,3),'audio_seconds':round(duration,3)};results.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
    Path(args.output).write_text(json.dumps({'machine':platform.platform(),'note':'首轮可能已有缓存；删除缓存需单独授权，勿据此推断首次合成速度。','results':results},ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
