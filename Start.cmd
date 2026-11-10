@echo off
setlocal
pushd "%~dp0"
set "PYTHONUTF8=1"
call "%~dp0tools\find-python.cmd"
if errorlevel 1 goto :error
%_CC_PY% "%~dp0tools\start_windows.py" %*
if errorlevel 1 goto :error
popd
exit /b 0
:error
popd
echo.
pause
exit /b 1
