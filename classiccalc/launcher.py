"""Console-free Windows entry point with local diagnostics instead of lost errors."""
from __future__ import annotations

from contextlib import ExitStack
import os
import sys
import traceback

from .platform_support import log_path


def _error_dialog(message: str) -> None:
    """Use the OS error dialog even when Tk itself failed to import."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            show = ctypes.WinDLL("user32", use_last_error=True).MessageBoxW
            show.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]
            show.restype = ctypes.c_int
            show(None, message, "Klassischer Rechner", 0x10)
            return
        except (AttributeError, OSError):
            pass
    if sys.stderr is not None:
        print(message, file=sys.stderr)


def gui_main() -> int:
    """pythonw and PyInstaller --windowed have no stdout/stderr on Windows."""
    old_out, old_err = sys.stdout, sys.stderr
    error_file = None
    with ExitStack() as stack:
        try:
            if old_out is None or old_err is None:
                try:
                    error_file = log_path()
                    error_file.parent.mkdir(parents=True, exist_ok=True)
                    stream = stack.enter_context(error_file.open("a", encoding="utf-8", buffering=1))
                except OSError:
                    error_file = None
                    stream = stack.enter_context(open(os.devnull, "w", encoding="utf-8"))
                if old_out is None:
                    sys.stdout = stream
                if old_err is None:
                    sys.stderr = stream
            from .__main__ import main
            try:
                result = main()
            except Exception:
                traceback.print_exc()
                result = 1
            if result:
                detail = f"\n\nDetails: {error_file}" if error_file else "\n\nStarten Sie zur Diagnose Start-Konsole.cmd."
                _error_dialog("Der Rechner konnte nicht gestartet werden." + detail)
            return result
        finally:
            sys.stdout, sys.stderr = old_out, old_err
