# Build Guide

Build Atulya-All-File-Converter for all platforms from a single Python codebase.

## Prerequisites

```bash
pip install -e ".[all]"
```

Individual extras: `pip install atulya-convert[pdf]` or `[docx]` or `[all]`.

## Windows EXE & System Installer

### 1. Portable Standalone EXE (PyInstaller)
```batch
build_exe.bat
```
Produces `dist/atulya-convert.exe` — single-file, no Python required.

### 2. Windows System Installer (NSIS)
```batch
build_installer.bat
```
Produces `dist/atulya-convert-installer.exe`:
- Installs to `Program Files\Atulya File Converter`
- Adds **Desktop** and **Start Menu** shortcuts
- Adds **Windows File Explorer Context Menu** ("Convert with Atulya" on right-click)
- Sets up clean registry uninstaller and adds `atulya-convert` to system PATH.

## Android APK (Buildozer & GitHub Actions)

Requires Linux, WSL, or automated via GitHub Actions:
```bash
build_apk.sh
```
Uses `main.py` as entry point and compiles native Android APK (`bin/atulya_convert_*.apk`).
Works on Android 8+ devices with local offline conversion web studio.

## Linux (pip / .deb / AppImage)

### pip install (all distros)

```bash
pip install atulya-all-file-converter
```

### .deb package (Debian/Ubuntu)

```bash
fpm -s python -t deb .
```

### AppImage (portable Linux)

```bash
pip install pyinstaller
pyinstaller --onefile --name atulya-convert src/atulya_all_file_converter/cli.py
```

## Cross-platform notes

- All core operations are pure Python — no platform-specific code
- Android: uses `termux-open` for file access; clipboard via termux-clipboard-set
- Windows EXE includes all dependencies via PyInstaller hooks
- Linux AppImage works on any distro with FUSE
