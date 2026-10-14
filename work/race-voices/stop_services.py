"""Stop only processes whose parsed command points at this deployment."""
from watchdog import ROOT,STOP,processes
import psutil
def main():
    STOP.write_text('manual stop',encoding='utf-8')
    for script in ('watchdog.py','telemetry_announcer.py','bridge.py'):
        if script=='telemetry_announcer.py':
            from simulator_link import SimulatorLink
            result=SimulatorLink().stop()
            if result=='stop_failed':print('自动启动的 Simulator Controller 未能关闭，请手动退出组件。')
        for process in processes(script):
            try:
                if script=='watchdog.py':
                    # Let startup ownership be recorded and linked shutdown finish.
                    try:process.wait(timeout=8);continue
                    except psutil.TimeoutExpired:pass
                process.terminate();process.wait(timeout=5)
            except psutil.NoSuchProcess:pass
            except psutil.TimeoutExpired:process.kill();process.wait(timeout=5)
    (ROOT/'watchdog_status.json').write_text('{"services": {}, "state": "stopped"}',encoding='utf-8')
    print('本目录播报服务已停止。')
if __name__=='__main__':main()
