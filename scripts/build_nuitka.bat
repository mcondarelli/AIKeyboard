@echo off
setlocal
set ENTRY=src\aikeyboard\AIKeyboard.py
set OUTDIR=build
set ICON=resources\icons\aikeyboard.ico

python -m nuitka ^
  --standalone ^
  --onefile ^
  --enable-plugin=pyside6 ^
  --windows-icon-from-ico=%ICON% ^
  --output-dir=%OUTDIR% ^
  %ENTRY%
