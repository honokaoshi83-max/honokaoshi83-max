"""Portable paths and local-only service configuration."""
import ctypes,hashlib,json,os,shutil
from pathlib import Path

def project_root():return Path(__file__).resolve().parents[2]

def settings():
    root=project_root(); result=json.loads((root/'config/default.json').read_text(encoding='utf-8'))
    local=root/'config/local.json'
    if local.exists():result.update(json.loads(local.read_text(encoding='utf-8')))
    if 'IRACING_ASSISTANT_PORT' in os.environ:result['port']=int(os.environ['IRACING_ASSISTANT_PORT'])
    if result['engine'] not in ('system','gpt-sovits'):raise ValueError('Invalid speech engine')
    if not isinstance(result['port'],int) or not 1024<=result['port']<=65535:raise ValueError('Invalid local port')
    return result

def service_url(config=None):return 'http://127.0.0.1:'+str((config or settings())['port'])

def instance_id():return hashlib.sha256(str(project_root().resolve()).casefold().encode()).hexdigest()[:16]

def documents():
    override=settings().get('documents')
    if override:return Path(override)
    if os.name=='nt':
        buf=ctypes.create_unicode_buffer(32768)
        if ctypes.windll.shell32.SHGetFolderPathW(None,5,None,0,buf)==0:return Path(buf.value)
    return Path.home()/'Documents'

def simulator_root():
    config=settings()
    return Path(config['simulator_controller']) if config.get('simulator_controller') else Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Simulator Controller'

def ffmpeg_path():
    configured=os.environ.get('IRACING_ASSISTANT_FFMPEG') or settings().get('ffmpeg')
    if configured:return Path(configured)
    try:
        import imageio_ffmpeg
        return Path(imageio_ffmpeg.get_ffmpeg_exe())
    except ImportError:
        installed=shutil.which('ffmpeg')
        if installed:return Path(installed)
        return simulator_root()/'Binaries/Audio Capture/ffmpeg.exe'

def data_path(name):return project_root()/'data'/name
