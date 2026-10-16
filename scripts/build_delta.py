"""Build a version-specific patch from two clean offline payloads."""
import argparse,hashlib,json,shutil,zipfile
from pathlib import Path
import apply_update

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def build(base,target,out):
    base=Path(base);target=Path(target);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    old=json.loads((base/'config/offline-bundle.json').read_text(encoding='utf-8'))
    new=json.loads((target/'config/offline-bundle.json').read_text(encoding='utf-8'))
    for key in ('python','torch','voices'):
        if old.get(key)!=new.get(key):raise ValueError('运行环境或默认模型变化，需要完整安装包')
    for name in ('config/assets.json','config/upstream.json','requirements.txt','requirements-roles.txt'):
        if sha(base/name)!=sha(target/name):raise ValueError('推理依赖变化，需要完整安装包：'+name)
    listing=json.loads((target/'config/release-files.json').read_text(encoding='utf-8'))['files']
    names={r['path'] for r in listing};names.add('config/release-files.json')
    names.update(p.relative_to(target).as_posix() for p in (target/'_internal').rglob('*') if p.is_file())
    rows=[]
    for name in sorted(names):
        try:apply_update.target_path(target.resolve(),name)
        except ValueError:continue
        current=target/name;previous=base/name
        if previous.is_file() and sha(previous)==sha(current):continue
        rows.append(dict(path=name,sha256=sha(current),base_sha256=sha(previous) if previous.is_file() else None,size=current.stat().st_size))
    controls={name:sorted({sha(base/name),sha(target/name)}) for name in ('work/race-voices/stop_services.py','work/race-voices/watchdog.py','scripts/start.ps1')}
    manifest=dict(from_version=old['version'],to_version=new['version'],files=rows,controls=controls)
    with zipfile.ZipFile(out/'patch.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        for row in rows:z.write(target/row['path'],'files/'+row['path'])
    shutil.copy2(Path(__file__).with_name('apply_update.py'),out/'apply_update.py')
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return dict(from_version=old['version'],to_version=new['version'],files=len(rows),bytes=(out/'patch.zip').stat().st_size)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('base');p.add_argument('target');p.add_argument('out');a=p.parse_args()
    print(json.dumps(build(a.base,a.target,a.out)))
