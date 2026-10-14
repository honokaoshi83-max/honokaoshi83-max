"""Check every catalog reading with the installed GPT-SoVITS Chinese frontend.

Run with the bundled runtime Python from the GPT-SoVITS repository root.
"""
import csv
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'work' / 'race-voices'))
sys.path.insert(0, str(Path.cwd() / 'GPT_SoVITS'))

import jieba
import jieba.posseg
sys.modules['jieba_fast'] = jieba
sys.modules['jieba_fast.posseg'] = jieba.posseg

from text import chinese2
from speech_reading import install_overrides


def main():
    install_overrides()
    started = time.monotonic()
    results = []
    failures = []
    for file, kind in (('tracks_zh.json', 'tracks'), ('cars_zh.json', 'cars')):
        rows = json.loads((ROOT / 'data' / file).read_text(encoding='utf-8'))[kind]
        for row in rows:
            entries = [(row['path'], row['en'], row['zh'], row['spoken'])]
            entries.extend((row['path'] + '#alias', alias, alias, spoken)
                           for alias, spoken in row.get('speech_aliases', {}).items())
            for path, english, chinese, spoken in entries:
                try:
                    normalized = chinese2.text_normalize(spoken)
                    phones, word2ph = chinese2.g2p(normalized)
                    valid = bool(phones) and len(word2ph) == len(re.sub(r'\s', '', normalized))
                    valid &= sum(word2ph) == len(phones)
                    valid &= not re.search(r'[A-Za-z0-9]', normalized)
                    status = 'frontend_pass' if valid else 'frontend_fail'
                    result = {'kind': kind, 'path': path, 'en': english, 'zh': chinese,
                              'spoken': spoken, 'normalized': normalized,
                              'phones': phones, 'characters': len(word2ph), 'status': status}
                except Exception as exc:
                    result = {'kind': kind, 'path': path, 'en': english, 'zh': chinese,
                              'spoken': spoken, 'status': 'frontend_fail', 'error': repr(exc)}
                results.append(result)
                if result['status'] != 'frontend_pass':
                    failures.append(result)
    report = {'date': date.today().isoformat(),
              'method': 'actual GPT-SoVITS chinese2 text normalization and g2p, not acoustic acceptance',
              'records': len(results), 'failures': failures,
              'seconds': round(time.monotonic() - started, 2), 'results': results}
    docs = ROOT / 'docs'
    (docs / 'name-reading-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    with (docs / '名称读法核对表.csv').open('w', encoding='utf-8-sig', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['类别', '目录标识', '英文名', '中文名', '播报文本', '前端归一化', '音素', '结果'])
        for row in results:
            writer.writerow([row['kind'], row['path'], row['en'], row['zh'], row['spoken'],
                             row.get('normalized', ''), ' '.join(row.get('phones', [])), row['status']])
    print(json.dumps({key: report[key] for key in ('records', 'failures', 'seconds')}, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
