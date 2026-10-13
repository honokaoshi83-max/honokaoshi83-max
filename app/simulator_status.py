"""Read Simulator Controller installation and integration without changing it."""
import ctypes
import json
import os
from pathlib import Path

ROLES = ('Race Engineer', 'Race Spotter', 'Race Strategist')
GUIDE_URL = 'https://github.com/SeriousOldMan/Simulator-Controller/wiki/Installation-%26-Configuration'

def inspect_simulator(project):
    project = Path(project)
    config = {}
    for name in ('default.json', 'local.json'):
        path = project / 'config' / name
        if path.exists():
            config.update(json.loads(path.read_text(encoding='utf-8-sig')))
    docs = Path.home() / 'Documents'
    if os.name == 'nt':
        buf = ctypes.create_unicode_buffer(32768)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0:
            docs = Path(buf.value)
    docs = Path(config.get('documents') or docs)
    root = Path(config.get('simulator_controller') or Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Simulator Controller')
    ini = docs / 'Simulator Controller/Config/Simulator Configuration.ini'
    installed = (root / 'Binaries/Simulator Startup.exe').is_file()
    configured = ini.is_file()
    integrated = False
    if configured:
        raw = ini.read_bytes()
        text = raw.decode('utf-16' if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8-sig')
        section = ''; plugins = {}
        for line in text.splitlines():
            line = line.strip()
            if line.startswith('['): section = line.strip('[]')
            elif section == 'Plugins' and '=' in line:
                key, value = line.split('=', 1); plugins[key.strip()] = value
        url = 'http://127.0.0.1:' + str(config.get('port', 9881))
        integrated = all(plugins.get(role, '').startswith('true|') and
                         'language: zh' in plugins[role] and 'listener: Off' in plugins[role] and
                         'speaker: gpt-sovits/' in plugins[role] and
                         'synthesizer: OpenAI|' + url + '|local' in plugins[role]
                         for role in ROLES)
        integrated = integrated and plugins.get('IRC', '').startswith('true|') and all((docs / 'Simulator Controller/Grammars' / (role + '.grammars.zh')).is_file() for role in ROLES)
    return dict(root=root, documents=docs, ini=ini, installed=installed,
                configured=configured, integrated=integrated)
