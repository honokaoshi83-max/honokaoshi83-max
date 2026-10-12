"""Versioned source downloads; models stay outside Git and release archives."""
import hashlib,json,os,shutil,urllib.request,zipfile
from pathlib import Path,PureWindowsPath
from runtime_settings import project_root,ffmpeg_path

def target_path(root,name):
    if Path(name).is_absolute() or PureWindowsPath(name).is_absolute() or '..' in Path(name.replace('\\','/')).parts:
        raise ValueError('Unsafe asset path')
    result=(Path(root)/name).resolve()
    if not result.is_relative_to(Path(root).resolve()):raise ValueError('Asset path escapes install root')
    return result

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while chunk:=f.read(1024*1024):h.update(chunk)
    return h.hexdigest()

def verified(path,job):
    return path.is_file() and path.stat().st_size==job['size'] and sha256(path)==job['sha256']

def download(job,root):
    path=target_path(root,job['path']);path.parent.mkdir(parents=True,exist_ok=True)
    if verified(path,job):return path
    if not job['url'].startswith('https://'):raise ValueError('HTTPS downloads required')
    temp=path.with_name(path.name+'.part')
    for attempt in range(3):
        try:
            with urllib.request.urlopen(job['url'],timeout=120) as response,temp.open('wb') as out:
                shutil.copyfileobj(response,out,1024*1024)
            if not verified(temp,job):raise ValueError('Asset integrity mismatch: '+path.name)
            temp.replace(path);return path
        except Exception:
            if attempt==2:raise
    return path

def safe_extract(archive,destination):
    root=Path(destination).resolve()
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            target_path(root,member.filename)
            if (member.external_attr>>16)&0o170000==0o120000:raise ValueError('Archive symlinks not accepted')
        z.extractall(root)

def install_roles():
    root=project_root(); engine=root/'work/race-voices'
    jobs=json.loads((root/'config/assets.json').read_text(encoding='utf-8'))
    source=json.loads((root/'config/upstream.json').read_text(encoding='utf-8'))
    archive=download(source['source'],root/'.runtime/downloads')
    unpack=root/'.runtime/unpack';safe_extract(archive,unpack)
    folders=[p for p in unpack.iterdir() if p.is_dir()]
    if len(folders)!=1:raise ValueError('Unexpected upstream archive layout')
    shutil.copytree(folders[0],engine/'GPT-SoVITS',dirs_exist_ok=True)
    for job in jobs:
        print('校验或下载：'+job['path'],flush=True);download(job,engine)
    g2pw=download(source['g2pw'],root/'.runtime/downloads')
    safe_extract(g2pw,engine/'GPT-SoVITS/GPT_SoVITS/text')
    import subprocess
    profiles=json.loads((engine/'voices.json').read_text(encoding='utf-8'))
    for voice in ('furina','clorinde'):
        matches=[j for j in jobs if j['path'].startswith('models/'+voice+'/') and j['path'].endswith(('.wav','.mp3'))]
        if len(matches)!=1:raise ValueError('Expected one known reference per voice')
        subprocess.run([str(ffmpeg_path()),'-y','-hide_banner','-loglevel','error','-i',str(engine/matches[0]['path']),
            '-ar','32000','-ac','1',str(engine/profiles[voice]['reference'])],check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    (engine/'asset_manifest.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2),encoding='utf-8')
    print('角色资源已下载并校验。')

if __name__=='__main__':install_roles()
