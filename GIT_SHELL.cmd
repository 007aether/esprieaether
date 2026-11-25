@echo off
set "PATH=%~dp0.tools\git\cmd;%~dp0.tools\git\bin;%PATH%"
cd /d "%~dp0"
echo Git pret dans ce terminal (version portable locale).
cmd /k
