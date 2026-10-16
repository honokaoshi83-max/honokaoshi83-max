"""Manual GitHub release checks and verified small-updater downloads."""
import hashlib,json,os,re
from pathlib import Path
from urllib.parse import urlparse
import requests

REPO='honokaoshi83-max/iracing-chinese-assistant'
API='https://api.github.com/repos/'+REPO+'/releases/latest'
PAGE='https://github.com/'+REPO+'/releases/latest'
MAX_DOWNLOAD=256*1024*1024

def version(text):
    if not re.fullmatch(r'v?\d+\.\d+\.\d+',str(text)):raise ValueError('版本格式无效')
    return tuple(map(int,text.lstrip('v').split('.')))

def current_version(project):
    try:return json.loads((Path(project)/'config/offline-bundle.json').read_text(encoding='utf-8-sig'))['version']
    except (OSError,ValueError,KeyError):return '0.0.0'

def trusted(url):
    p=urlparse(url)
    return p.scheme=='https' and p.netloc=='github.com' and p.path.startswith('/'+REPO+'/releases/download/')

def select_release(release,current):
    latest=release.get('tag_name','')
    if release.get('draft') or release.get('prerelease'):raise ValueError('不是正式发布版本')
    result=dict(state='current',current=current,latest=latest.lstrip('v'),notes=str(release.get('body','')),url=PAGE,asset=None)
    if version(latest)<=version(current):return result
    result['state']='available'
    name=f'iracing-chinese-assistant-{result["latest"]}-update-from-{current}.exe'
    for asset in release.get('assets',[]):
        if asset.get('name')!=name:continue
        if not trusted(asset.get('browser_download_url','')):raise ValueError('更新地址不属于本项目发布页')
        if not re.fullmatch(r'sha256:[0-9a-f]{64}',str(asset.get('digest'))):raise ValueError('更新文件缺少有效校验信息，请使用发布页')
        if type(asset.get('size')) is not int or not 0<asset['size']<=MAX_DOWNLOAD:raise ValueError('更新文件大小异常')
        result['asset']=asset;break
    return result

def check(project):
    response=requests.get(API,timeout=(5,15),headers={'Accept':'application/vnd.github+json','User-Agent':'iRacing-Chinese-Assistant'})
    response.raise_for_status()
    return select_release(response.json(),current_version(project))

def download(asset,folder,progress=lambda percent:None):
    if not trusted(asset['browser_download_url']) or not re.fullmatch(r'[A-Za-z0-9._-]+\.exe',asset['name']):raise ValueError('更新文件地址无效')
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    target=folder/asset['name'];temporary=target.with_suffix('.part')
    try:
        response=requests.get(asset['browser_download_url'],stream=True,timeout=(10,30));response.raise_for_status()
        host=urlparse(response.url)
        if host.scheme!='https' or host.netloc not in ('github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'):raise ValueError('更新下载被重定向到非官方地址')
        size=0;digest=hashlib.sha256()
        try:
            with temporary.open('wb') as stream:
                for block in response.iter_content(256*1024):
                    if not block:continue
                    size+=len(block)
                    if size>MAX_DOWNLOAD or size>asset['size']:raise ValueError('更新文件超过预期大小')
                    stream.write(block);digest.update(block);progress(min(99,int(size*100/asset['size'])))
        finally:response.close()
        if size!=asset['size'] or 'sha256:'+digest.hexdigest()!=asset['digest']:raise ValueError('更新文件校验失败，请重新下载')
        os.replace(temporary,target);progress(100);return target
    finally:temporary.unlink(missing_ok=True)
