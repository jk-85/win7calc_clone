#!/bin/sh
# Removes only the per-user installation created by install.sh.
set -eu
DATA_HOME=${XDG_DATA_HOME:-"$HOME/.local/share"}
rm -rf -- "$DATA_HOME/classic-calc"
rm -f -- "$HOME/.local/bin/classic-calc" "$DATA_HOME/applications/classic-calc.desktop" \
    "$DATA_HOME/icons/hicolor/128x128/apps/classic-calc.png" "$DATA_HOME/icons/hicolor/scalable/apps/classic-calc.svg"
printf '%s\n' 'Benutzerinstallation entfernt. Einstellungen und Verlauf bleiben erhalten.'
