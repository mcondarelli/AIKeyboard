# AIKeyboard.spec
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller import __main__ as pyi
import os
from pathlib import Path

# Get Vosk package path
import vosk
vosk_path = Path(vosk.__file__).parent


block_cipher = None


a = Analysis(
    ['src/aikeyboard/AIKeyboard.py'],
    pathex=[],
    binaries=[
        (os.path.join(vosk_path, 'libvosk.so'), 'vosk'),
    ],
    datas=collect_data_files('PySide6', subdir='Qt') + collect_data_files('PySide6', subdir='plugins'),
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AIKeyboard',
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
