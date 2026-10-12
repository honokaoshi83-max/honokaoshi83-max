"""Package tracked source only; never include runtimes, voices or user data."""
import hashlib,subprocess,zipfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]
git='git'
files=subprocess.check_output([git,'-C',str(root),'ls-files','-z']).decode('utf-8').split('\0')
forbidden={'.git','.runtime','models','cache','venv','__pycache__'}
output=root/'dist';output.mkdir(exist_ok=True)
archive=output/'iracing-chinese-assistant-v0.1.0-windows-x64.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for name in filter(None,files):
        path=Path(name)
        if forbidden.intersection(path.parts) or name=='config/local.json' or path.suffix in ('.wav','.mp3','.log','.jsonl','.bak','.pid'):
            raise ValueError('Private/runtime file tracked: '+name)
        source=root/path
        if source.stat().st_size>20*1024*1024:raise ValueError('Unexpected large source: '+name)
        z.write(source,'iracing-chinese-assistant/'+name)
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
archive.with_suffix('.sha256.txt').write_text(digest+'  '+archive.name+'\n',encoding='utf-8')
print(archive.name,archive.stat().st_size,digest)
