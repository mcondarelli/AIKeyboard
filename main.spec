# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
import os

model_path = os.path.abspath("vosk-model-small-it-0.22")
libvosk_path = os.path.abspath(".venv/lib/python3.13/site-packages/vosk/libvosk.so")

a = Analysis(
    ['src/aikeyboard/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        (libvosk_path, "vosk"),
        (model_path, "vosk-model-small-it-0.22")
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
