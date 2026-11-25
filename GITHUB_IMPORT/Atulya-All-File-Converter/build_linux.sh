#!/usr/bin/env bash
# Build Linux packages (.deb, .rpm, AppImage, pip)
set -e

echo "=== Building pip wheel ==="
python -m pip wheel --no-deps -w dist .
echo "Wheel at dist/"

echo "=== Building .deb (requires fpm) ==="
if command -v fpm &>/dev/null; then
  fpm -s python -t deb --python-package-name-prefix python3-atulya-convert .
  echo ".deb built"
else
  echo "fpm not found. Install: gem install fpm"
fi

echo "=== Building AppImage (requires pyinstaller) ==="
if command -v pyinstaller &>/dev/null; then
  pyinstaller --onefile --name atulya-convert atulya_all_file_converter/cli.py
  mv dist/atulya-convert dist/atulya-convert-x86_64.AppImage
  echo "AppImage at dist/"
else
  echo "pyinstaller not found. Run: pip install pyinstaller"
fi

echo "=== Done ==="
ls -la dist/ 2>/dev/null || true
