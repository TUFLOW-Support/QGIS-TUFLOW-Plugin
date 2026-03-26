from pathlib import Path


def cache_dir(sub_dir: str = '') -> Path:
    cachedir = Path.home() / '.tuflow_plugin'
    return cachedir / sub_dir if sub_dir else cachedir


def save_cached_content(path: Path | str, content: str | bytes):
    p = cache_dir(str(path))
    if not p.parent.exists():
        p.parent.mkdir(parents=True)
    mode = 'w' if isinstance(content, str) else 'wb'
    with p.open(mode) as f:
        f.write(content)


def get_cached_content(path: Path | str, data_type: type) -> str | bytes:
    p = cache_dir(str(path))
    if not p.exists():
        return '' if data_type is str else b''
    mode = 'r' if data_type is str else 'rb'
    with p.open(mode) as f:
        return f.read()
