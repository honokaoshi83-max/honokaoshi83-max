"""Set assistant speech routing while preserving all other saved settings."""
from datetime import datetime
from pathlib import Path
import re
import shutil

ASSISTANTS = {'Race Engineer', 'Race Strategist', 'Race Spotter'}

def configure(text):
    section = ''
    output = []
    for line in text.splitlines(keepends=True):
        header = re.match(r'^\[([^\]]+)\]', line)
        if header:
            section = header[1]
        if section == 'Plugins' and '=' in line and line.split('=',1)[0] in ASSISTANTS:
            key, value = line.rstrip('\r\n').split('=',1)
            fields = value.split('|',2)
            if len(fields) != 3:
                raise ValueError(f'Unexpected plugin configuration format: {key}')
            args = [arg.strip() for arg in fields[2].split(';') if arg.strip()]
            args = [arg for arg in args if arg.split(':',1)[0].strip().lower() not in ('speaker','speakervocalics','synthesizer')]
            voice = 'clorinde' if key == 'Race Engineer' else 'furina'
            args += [f'speaker: gpt-sovits/{voice}', 'speakerVocalics: 100,0,0', 'synthesizer: OpenAI|http://127.0.0.1:9881|local']
            newline = '\r\n' if line.endswith('\r\n') else '\n' if line.endswith('\n') else ''
            line = key+'='+'|'.join(fields[:2])+'|'+'; '.join(args)+newline
        output.append(line)
    result = ''.join(output)
    if result.count('speaker: gpt-sovits/furina') != 2 or result.count('speaker: gpt-sovits/clorinde') != 1:
        raise ValueError('The saved configuration must contain the three assistants')
    return result

if __name__ == '__main__':
    target = Path.home()/'Documents/Simulator Controller/Config/Simulator Configuration.ini'
    raw = target.read_bytes()
    encoding = 'utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig'
    updated = configure(raw.decode(encoding)).encode(encoding)
    if updated != raw:
        backup = target.with_name(target.name+'.before-local-voice-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.bak')
        shutil.copy2(target, backup)
        temporary = target.with_name(target.name+'.voice.tmp')
        temporary.write_bytes(updated)
        temporary.replace(target)
        print('Backup:', backup)
    print('Configured engineer Clorinde; spotter and strategist Furina.')
