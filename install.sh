#!/bin/sh
# Per-user install: no sudo and no automatic downloads.
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if ! python3 -c 'import sys, tkinter; assert sys.version_info >= (3,10)' 2>/dev/null; then
    printf '%s\n' 'Python 3.10 oder neuer mit Tk ist erforderlich.' 'Unter Linux Mint: sudo apt install python3 python3-tk' >&2
    exit 1
fi
DATA_HOME=${XDG_DATA_HOME:-"$HOME/.local/share"}
APP_DIR="$DATA_HOME/classic-calc"
BIN_DIR="$HOME/.local/bin"
mkdir -p "$APP_DIR" "$BIN_DIR" "$DATA_HOME/applications" "$DATA_HOME/icons/hicolor/128x128/apps" "$DATA_HOME/icons/hicolor/scalable/apps"
cp -R "$HERE/classiccalc" "$APP_DIR/"
cp "$HERE/app.py" "$HERE/README.md" "$HERE/LICENSE" "$APP_DIR/"
cp "$HERE/assets/classic-calc.png" "$DATA_HOME/icons/hicolor/128x128/apps/"
cp "$HERE/assets/classic-calc.svg" "$DATA_HOME/icons/hicolor/scalable/apps/"
python3 - "$APP_DIR" "$BIN_DIR" "$DATA_HOME" "$HERE" <<'PY'
from pathlib import Path
import shlex,sys
app,bin_dir,data,here=map(Path,sys.argv[1:])
launcher=bin_dir/'classic-calc'
launcher.write_text('#!/bin/sh\nexec python3 '+shlex.quote(str(app/'app.py'))+' "$@"\n',encoding='utf-8')
launcher.chmod(0o755)
def desktop_quote(value):
    return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$').replace('%','%%')+'"'
text=(here/'classic-calc.desktop').read_text(encoding='utf-8')
text=text.replace('Exec=classic-calc','Exec='+desktop_quote(launcher))
text=text.replace('Icon=classic-calc','Icon='+str(data/'icons/hicolor/128x128/apps/classic-calc.png'))
(data/'applications/classic-calc.desktop').write_text(text,encoding='utf-8')
PY
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DATA_HOME/applications" >/dev/null 2>&1 || true
fi
printf 'Installiert. Öffnen Sie „Klassischer Rechner“ im Anwendungsmenü.\nAlternativ ausführen: %s/classic-calc\n' "$BIN_DIR"
