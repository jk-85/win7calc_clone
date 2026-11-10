"""Small OS boundary; no Windows libraries are imported on other platforms.

The arithmetic engine and classic layout are shared on Windows and Linux.
Windows uses system-DPI awareness intentionally: Tk's fixed-pixel controls do
not implement WM_DPICHANGED. --scale remains an absolute, user-selected zoom.
"""
from __future__ import annotations

import ctypes
import math
import os
from pathlib import Path
import sys
from typing import Mapping

APP_ID = "ClassicCalc.KlassischerRechner"


def settings_path(*, platform: str | None = None,
                  environ: Mapping[str, str] | None = None,
                  home: Path | None = None) -> Path:
    """Return a per-user, writable settings path without creating anything."""
    platform = sys.platform if platform is None else platform
    env = os.environ if environ is None else environ
    home = Path.home() if home is None else Path(home)
    if platform == "win32":
        base = Path(env["APPDATA"]) if env.get("APPDATA") else home / "AppData" / "Roaming"
        return base / "ClassicCalc" / "state.json"
    base = Path(env["XDG_CONFIG_HOME"]) if env.get("XDG_CONFIG_HOME") else home / ".config"
    return base / "classic-calc" / "state.json"


def log_path() -> Path:
    return settings_path().with_name("error.log")


def prepare_windows_process() -> None:
    """Call before creating any Tk window; older/missing APIs are harmless.

    A frozen executable declares system awareness in its manifest. These calls
    also cover the ordinary python/pythonw entry points. ACCESS_DENIED simply
    means the host process or manifest has already chosen a DPI context.
    """
    if sys.platform != "win32":
        return
    try:
        from ctypes import wintypes
        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        set_id = shell32.SetCurrentProcessExplicitAppUserModelID
        set_id.argtypes = [wintypes.LPCWSTR]
        set_id.restype = ctypes.c_long
        set_id(APP_ID)
    except (AttributeError, OSError):
        pass
    try:
        from ctypes import wintypes
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        set_context = user32.SetProcessDpiAwarenessContext
        set_context.argtypes = [ctypes.c_void_p]
        set_context.restype = wintypes.BOOL
        # DPI_AWARENESS_CONTEXT_SYSTEM_AWARE, NOT PerMonitorV2.
        if set_context(ctypes.c_void_p(-2)) or ctypes.get_last_error() == 5:
            return
    except (AttributeError, OSError):
        pass
    try:
        shcore = ctypes.WinDLL("shcore", use_last_error=True)
        set_awareness = shcore.SetProcessDpiAwareness
        set_awareness.argtypes = [ctypes.c_int]
        set_awareness.restype = ctypes.c_long
        result = set_awareness(1)  # PROCESS_SYSTEM_DPI_AWARE
        if result == 0 or (result & 0xFFFFFFFF) == 0x80070005:
            return
    except (AttributeError, OSError):
        pass
    try:
        from ctypes import wintypes
        set_aware = ctypes.WinDLL("user32", use_last_error=True).SetProcessDPIAware
        set_aware.argtypes = []
        set_aware.restype = wintypes.BOOL
        set_aware()
    except (AttributeError, OSError):
        pass


def scale_from_dpi(dpi: float) -> float:
    """Convert Windows logical DPI to the application's supported zoom range."""
    if not math.isfinite(dpi) or dpi <= 0:
        return 1.0
    return max(0.75, min(3.0, dpi / 96.0))


def initial_scale(root) -> float:
    """Use Windows system scaling at startup; leave the Linux default unchanged."""
    if sys.platform != "win32":
        return 1.0
    try:
        from ctypes import wintypes
        get_dpi = ctypes.WinDLL("user32", use_last_error=True).GetDpiForSystem
        get_dpi.argtypes = []
        get_dpi.restype = wintypes.UINT
        dpi = get_dpi()
        if dpi:
            return scale_from_dpi(float(dpi))
    except (AttributeError, OSError):
        pass
    try:
        return scale_from_dpi(float(root.winfo_fpixels("1i")))
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return 1.0


def tkinter_install_hint() -> str:
    if sys.platform == "win32":
        return ("Installieren oder ändern Sie Python (64 Bit) mit dem offiziellen "
                "Windows-Installer und aktivieren Sie 'tcl/tk and IDLE'. "
                "Prüfung: py -3 -m tkinter")
    return "Unter Linux Mint: sudo apt install python3-tk"
