"""Read-only installation diagnostics; no model loads or cloud requests."""
import json,platform,subprocess,sys
from pathlib import Path
from runtime_settings import project_root,settings,simulator_root,documents,ffmpeg_path,service_url

def check_assets(config):
    if config['engine']=='system':return []
    root=project_root();voice_root=root/'work/race-voices'
    manifest=json.loads((root/'config/assets.json').read_text(encoding='utf-8'))
    missing=[j['path'] for j in manifest if not (voice_root/j['path']).is_file()]
    for name in ('GPT-SoVITS/GPT_SoVITS/TTS_infer_pack/TTS.py','GPT-SoVITS/GPT_SoVITS/text/G2PWModel/g2pW.onnx','models/furina/reference.wav','models/clorinde/reference.wav'):
        if not (voice_root/name).is_file():missing.append(name)
    return missing

def main():
    config=settings();issues=[]
    if sys.platform!='win32' or platform.machine().lower() not in ('amd64','x86_64'):issues.append('仅支持 Windows x64')
    if not ffmpeg_path().is_file():issues.append('未找到 FFmpeg，请重新安装依赖')
    missing=check_assets(config)
    if missing:issues.append('角色资源缺失：'+str(len(missing))+'项，请安装角色音色组件')
    if config['engine']=='system':
        p=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(project_root()/'scripts/system_speech.ps1'),'-ListVoices'],capture_output=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if p.returncode or p.stdout.strip() in (b'',b'[]',b'null'):issues.append('没有 Windows 中文桌面语音，请在语言设置中安装中文语音')
    cfg=documents()/'Simulator Controller/Config/Simulator Configuration.ini'
    sc=(simulator_root()/'Binaries/Simulator Startup.exe').exists()
    print(json.dumps({'引擎':config['engine'],'语音地址':service_url(),'Simulator Controller已安装':sc,'基础配置已存在':cfg.is_file(),'角色资源缺失':missing,'安装问题':issues},ensure_ascii=False,indent=2))
    return 1 if issues else 0

if __name__=='__main__':sys.exit(main())
