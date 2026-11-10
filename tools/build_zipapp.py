#!/usr/bin/env python3
"""Package the complete app into .pyz (console) or .pyzw (Windows GUI).

Python and Tcl/Tk remain runtime dependencies; this is NOT an EXE compiler.
"""
import argparse
from pathlib import Path
import shutil
import tempfile
import zipapp


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', nargs='?', default='dist/classic-calc.pyz')
    parser.add_argument('--windowed', action='store_true', help='use the pythonw-safe GUI entry point')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = Path(args.output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        stage = Path(temporary)
        shutil.copytree(root/'classiccalc', stage/'classiccalc', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        for name in ('LICENSE', 'README.md', 'PORTING_NOTES.md', 'TEST_REPORT.md', 'CHANGELOG.md'):
            shutil.copy2(root/name, stage/name)
        zipapp.create_archive(stage, out,
            interpreter=None if args.windowed else '/usr/bin/env python3',
            main='classiccalc.launcher:gui_main' if args.windowed else 'classiccalc.__main__:main',
            compressed=True)
    out.chmod(0o755)
    print(out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
