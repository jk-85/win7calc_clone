@echo off
setlocal
pushd "%~dp0"
set "PYTHONUTF8=1"
call "%~dp0tools\find-python.cmd"
if errorlevel 1 goto :error
%_CC_PY% -m unittest discover -v
set "_CC_RC=%ERRORLEVEL%"
popd
pause
exit /b %_CC_RC%
:error
popd
pause
exit /b 1
