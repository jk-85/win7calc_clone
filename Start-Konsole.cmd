@echo off
setlocal
pushd "%~dp0"
set "PYTHONUTF8=1"
call "%~dp0tools\find-python.cmd"
if errorlevel 1 goto :error
%_CC_PY% "%~dp0app.py" %*
set "_CC_RC=%ERRORLEVEL%"
popd
if not "%_CC_RC%"=="0" pause
exit /b %_CC_RC%
:error
popd
pause
exit /b 1
