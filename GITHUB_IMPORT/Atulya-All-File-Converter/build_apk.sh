#!/usr/bin/env bash
# Build Android APK with Buildozer
# Requires: Ubuntu/Debian, Python 3, buildozer
# Run: chmod +x build_apk.sh && ./build_apk.sh

set -e

echo "Installing build dependencies..."
pip install buildozer cython

echo "Initializing Buildozer spec..."
cat > buildozer.spec << 'SPEC'
[app]
title = Atulya Converter
package.name = atulyaconvert
package.domain = com.atulya
source.dir = atulya_all_file_converter
source.include_exts = py,png,jpg,jpeg,gif,svg
version = 0.1.0
requirements = python3,click,rich,pandas,openpyxl,xlsxwriter,pillow,pyyaml,tomli,tomli-w,chardet
orientation = portrait
osx.python_version = 3
osx.kivy_version = 2.1.0
fullscreen = 0

[buildozer]
log_level = 2
warn_on_root = 1
SPEC

echo "Building APK..."
buildozer android debug

echo "Done! APK at bin/"
