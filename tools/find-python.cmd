@echo off
rem Export _CC_PY to the caller. The caller owns SETLOCAL.
set "_CC_PY="
if exist "%~dp0..\.venv-build\Scripts\python.exe" (
    set _CC_PY="%~dp0..\.venv-build\Scripts\python.exe"
    exit /b 0
)
py -3.13 -c "import sys, tkinter; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if not errorlevel 1 (
    set "_CC_PY=py -3.13"
    exit /b 0
)
py -3 -c "import sys, tkinter; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if not errorlevel 1 (
    set "_CC_PY=py -3"
    exit /b 0
)
python -c "import sys, tkinter; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if not errorlevel 1 (
    set "_CC_PY=python"
    exit /b 0
)
echo Python mit Tcl/Tk wurde nicht gefunden.
echo Installieren Sie Python 3.13 x64 von python.org, einschliesslich Tcl/Tk und Python Launcher.
echo Danach dieses Fenster schliessen und erneut starten.
exit /b 1
