@echo off
cd /d "%~dp0"
set "NODE=%~dp0.tools\node-v26.13.1\node.exe"
if not exist "%NODE%" (
  echo [ERREUR] Node introuvable : %NODE%
  pause
  exit /b 1
)
echo SUNNAVOK dashboard - http://127.0.0.1:5100/
echo Appuyez sur Ctrl+C pour arreter le serveur.
"%NODE%" api\server.mjs
if errorlevel 1 (
  echo [ERREUR] Le serveur s'est arrete anormalement.
  pause
)
