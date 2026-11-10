#!/bin/sh
# Reproducible, no compilation or pip packages needed.
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
OUT=${1:-"$HERE/dist"}
mkdir -p "$OUT"
OUT=$(CDPATH= cd -- "$OUT" && pwd)
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT HUP INT TERM
mkdir -p "$STAGE/DEBIAN" "$STAGE/usr/bin" "$STAGE/usr/share/classic-calc" \
    "$STAGE/usr/share/applications" "$STAGE/usr/share/icons/hicolor/128x128/apps" \
    "$STAGE/usr/share/icons/hicolor/scalable/apps" "$STAGE/usr/share/doc/classic-calc"
cp -R "$HERE/classiccalc" "$STAGE/usr/share/classic-calc/"
find "$STAGE" -type d -name __pycache__ -prune -exec rm -rf '{}' +
cp "$HERE/app.py" "$STAGE/usr/share/classic-calc/"
cp "$HERE/classic-calc.desktop" "$STAGE/usr/share/applications/"
cp "$HERE/assets/classic-calc.png" "$STAGE/usr/share/icons/hicolor/128x128/apps/"
cp "$HERE/assets/classic-calc.svg" "$STAGE/usr/share/icons/hicolor/scalable/apps/"
cp "$HERE/README.md" "$HERE/RECREATION_NOTES.md" "$HERE/TEST_REPORT.md" "$HERE/CHANGELOG.md" "$STAGE/usr/share/doc/classic-calc/"
cp "$HERE/LICENSE" "$STAGE/usr/share/doc/classic-calc/copyright"
cp -R "$HERE/screenshots" "$STAGE/usr/share/doc/classic-calc/"
cat > "$STAGE/usr/bin/classic-calc" <<'LAUNCHER'
#!/bin/sh
exec /usr/bin/python3 /usr/share/classic-calc/app.py "$@"
LAUNCHER
chmod 755 "$STAGE/usr/bin/classic-calc"
SIZE=$(du -sk "$STAGE/usr" | cut -f1)
cat > "$STAGE/DEBIAN/control" <<CONTROL
Package: classic-calc
Version: 1.3.0
Section: math
Priority: optional
Architecture: all
Maintainer: Classic Calc contributors
Depends: python3 (>= 3.10), python3-tk
Installed-Size: $SIZE
Description: Native classic-style scientific, programmer and statistics calculator
 Independently written calculator inspired by the classic Windows 7 interface.
 Includes standard, scientific, fixed-width programmer and statistics modes,
 97 units across 11 conversion categories, date arithmetic, mortgage,
 vehicle lease and fuel economy worksheets. No Wine or Windows files needed.
CONTROL
find "$STAGE" -type d -exec chmod 755 '{}' +
find "$STAGE/usr/share" -type f -exec chmod 644 '{}' +
# Stable ordering and timestamps when rebuilding this version.
export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-1794312000}
dpkg-deb --root-owner-group --build "$STAGE" "$OUT/classic-calc_1.3.0_all.deb"
