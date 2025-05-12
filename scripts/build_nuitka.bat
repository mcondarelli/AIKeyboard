@echo off
@echo off
REM Set Python path for module resolution
set PYTHONPATH=src

REM Optional: force Clang + caching
REM set CXX=clang++
REM set CCACHE_DIR=%LOCALAPPDATA%\ccache

REM Cleanup old build
if exist build (
    rmdir /s /q build
)
	
REM Run Nuitka with cache and optimizations
.venv\Scripts\python -m nuitka ^
    --standalone ^
    --onefile ^
    --enable-plugin=pyside6 ^
    --windows-icon-from-ico=resources\icons\aikeyboard.ico ^
    --output-dir=build ^
    --clang ^
    --lto=yes ^
    --remove-output ^
    --noinclude-unittest-mode=nofollow ^
    --jobs=4 ^
    src\aikeyboard\AIKeyboard.py
