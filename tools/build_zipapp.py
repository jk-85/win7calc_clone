#!/usr/bin/env python3
"""Build the pure-Python single-file app. Tk remains a system dependency."""
from pathlib import Path
import shutil
import sys
import tempfile
import zipapp
root=Path(__file__).resolve().parents[1]
out=Path(sys.argv[1] if len(sys.argv)>1 else root/'dist/classic-calc.pyz').resolve()
out.parent.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory() as temporary:
    stage=Path(temporary)
    shutil.copytree(root/'classiccalc',stage/'classiccalc',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in ('LICENSE','README.md','RECREATION_NOTES.md','TEST_REPORT.md','CHANGELOG.md'):
        shutil.copy2(root/name,stage/name)
    zipapp.create_archive(stage,out,interpreter='/usr/bin/env python3',main='classiccalc.__main__:main',compressed=True)
    out.chmod(0o755)
print(out)
