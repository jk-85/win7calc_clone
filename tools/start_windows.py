"""Start this checkout with the same interpreter's pythonw, not a file association."""
from pathlib import Path
import subprocess
import sys


def main() -> int:
    if sys.platform != "win32":
        print("Dieser Starter ist für Windows. Unter Linux: python3 app.py", file=sys.stderr)
        return 1
    if sys.version_info < (3, 10):
        print("Python 3.10 oder neuer wird benötigt; empfohlen ist Python 3.13 x64.", file=sys.stderr)
        return 1
    try:
        import tkinter  # noqa: F401; validate before starting without a console.
    except ImportError:
        print("Tcl/Tk fehlt. Python-Installation ändern und 'tcl/tk and IDLE' aktivieren.", file=sys.stderr)
        return 1
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.is_file():
        print("pythonw.exe fehlt. Verwenden Sie Start-Konsole.cmd oder eine vollständige Python-Installation.", file=sys.stderr)
        return 1
    root = Path(__file__).resolve().parents[1]
    try:
        subprocess.Popen([str(pythonw), str(root / "app.pyw"), *sys.argv[1:]], cwd=root)
    except OSError as exc:
        print(f"Start fehlgeschlagen: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
