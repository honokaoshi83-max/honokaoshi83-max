"""Initialize SC's local GUID before settings need an owner; keep existing IDs."""
from pathlib import Path
import uuid


def identity_value(raw):
    encoding='utf-16' if raw[:2] in (b'\xff\xfe',b'\xfe\xff') else 'utf-8-sig'
    value=raw.decode(encoding).strip()
    if not value or value=='0' or any(c in value for c in ';\r\n'):
        raise ValueError('Simulator Controller ID文件无效，请检查原文件后重试。')
    return value


def existing(path):
    try:raw=path.read_bytes()
    except FileNotFoundError:return None
    identity_value(raw)
    return raw


def create_missing(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    try:
        with path.open('xb') as stream:stream.write(raw)
    except FileExistsError:
        pass  # Another initializer's identity takes precedence; never replace it.
    return existing(path)


def ensure_identity(home):
    """Match SC's GUID/copy convention, also reusing a restored database ID."""
    home=Path(home);config_path=home/'Config/ID';database_path=home/'Database/ID'
    config=existing(config_path);database=existing(database_path)
    if config is None:
        config=create_missing(config_path,database if database is not None else str(uuid.uuid4()).upper().encode('ascii'))
    if database is None:create_missing(database_path,config)
    return identity_value(config)
