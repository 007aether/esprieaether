@echo off
REM Build Windows Standalone EXE and NSIS Installer
echo ====================================================
echo 1. Building Standalone EXE with PyInstaller...
echo ====================================================

call build_exe.bat

if not exist "dist\atulya-convert.exe" (
    echo [ERROR] EXE build failed!
    exit /b 1
)

echo.
echo ====================================================
echo 2. Packaging Windows System Installer with NSIS...
echo ====================================================

where makensis >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [NOTICE] makensis is not found in PATH.
    echo If you have NSIS installed, add it to PATH or compile installer.nsi manually.
    echo The standalone binary is ready at: dist\atulya-convert.exe
    exit /b 0
)

makensis installer.nsi
if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] Windows System Installer generated at: dist\atulya-convert-installer.exe
) else (
    echo [ERROR] NSIS installer generation failed.
)
