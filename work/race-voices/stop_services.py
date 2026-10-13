"""Stop only processes whose parsed command points at this deployment."""
from watchdog import ROOT,STOP,processes
import psutil
def main():
    STOP.write_text('manual stop',encoding='utf-8')
    for script in ('watchdog.py','telemetry_announcer.py','bridge.py'):
        for process in processes(script):
            try:process.terminate();process.wait(timeout=5)
            except psutil.NoSuchProcess:pass
            except psutil.TimeoutExpired:process.kill();process.wait(timeout=5)
    print('本目录播报服务已停止。')
if __name__=='__main__':main()
