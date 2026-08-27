"""Point the venv ``gunicorn`` launcher at gunicorn.conf.py.

Render keeps the start command from the dashboard even after render.yaml
changes. This rewrite is a no-op unless RENDER=true, so local runserver
and ``gunicorn`` on a laptop stay untouched.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / 'gunicorn.conf.py'


def patch_launcher(launcher: Path, config: Path = CONFIG) -> str:
    shebang = launcher.read_text(encoding='utf-8').splitlines()[0]
    if not shebang.startswith('#!'):
        shebang = '#!/usr/bin/env python'
    launcher.write_text(
        f'{shebang}\n'
        'import sys\n'
        'from gunicorn.app.wsgiapp import run\n'
        f'_config = {str(config)!r}\n'
        'if "-c" not in sys.argv and "--config" not in sys.argv:\n'
        '    sys.argv[1:1] = ["-c", _config]\n'
        'if "--threads" not in sys.argv:\n'
        '    sys.argv.extend([\n'
        '        "--workers", "1",\n'
        '        "--threads", "8",\n'
        '        "--timeout", "30",\n'
        '        "--keep-alive", "5",\n'
        '    ])\n'
        'sys.exit(run())\n',
        encoding='utf-8',
    )
    launcher.chmod(launcher.stat().st_mode | 0o111)
    return shebang


def main() -> int:
    if os.environ.get('RENDER') != 'true':
        print('skip gunicorn patch (not on Render)')
        return 0
    path = shutil.which('gunicorn')
    if not path:
        print('gunicorn not on PATH; skip', file=sys.stderr)
        return 0
    if not CONFIG.is_file():
        print(f'{CONFIG} missing', file=sys.stderr)
        return 1
    patch_launcher(Path(path), CONFIG)
    print(f'patched {path} to load {CONFIG}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
