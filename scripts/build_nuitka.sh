#!/usr/bin/env bash
set -e

# Location of your entry script
ENTRY=src/aikeyboard/AIKeyboard.py
ICON=resources/icons/aikeyboard.ico
OUTDIR=build
APPNAME=AIKeyboard

echo "Building $APPNAME with Nuitka..."

# Clean old build if needed
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

# Optional: set this if you're in a venv and want to use its Python
PYTHON=${PYTHON:-python}

$PYTHON -m nuitka \
  --standalone \
  --onefile \
  --output-dir="$OUTDIR" \
  --enable-plugin=pyside6 \
  --nofollow-import-to=ctypes.windll,ctypes.wintypes \
  --noinclude-default-mode=error \
  --show-progress \
  --show-memory \
  --jobs=4 \
  --enable-console \
  "$ENTRY"

echo "✅ Build finished. Binary is in $OUTDIR/"
