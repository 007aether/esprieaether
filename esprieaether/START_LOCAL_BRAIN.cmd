@echo off
setlocal
cd /d "%~dp0"
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [ERREUR] venv introuvable: %PY%
  exit /b 1
)
echo Demarrage des cerveaux locaux (llama.cpp) sur http://127.0.0.1:31416 ...
echo Un seul modele GGUF actif a la fois (RAM limitee).
"%PY%" -m src.local_brain
endlocal
