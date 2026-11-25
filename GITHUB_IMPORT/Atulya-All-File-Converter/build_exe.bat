@echo off
REM Build Windows EXE with PyInstaller
REM Produces dist/atulya-convert.exe

echo Installing build dependencies...
pip install pyinstaller

echo Building EXE...
pyinstaller --onefile ^
  --name atulya-convert ^
  --hidden-import atulya_all_file_converter ^
  --hidden-import atulya_all_file_converter.cli ^
  --hidden-import atulya_all_file_converter.core ^
  --hidden-import atulya_all_file_converter.utils ^
  --add-data "atulya_all_file_converter;atulya_all_file_converter" ^
  --console ^
  atulya_all_file_converter/cli.py

echo Done! EXE at dist/atulya-convert.exe
