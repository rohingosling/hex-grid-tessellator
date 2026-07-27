# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for the HEX Grid Tessellator — one-file console executable (dist/hextessellator.exe).
#
# The application is self-contained: it has no bundled data files. docs/CHANGELOG.md is read at runtime only when
# running from source (to source the banner version); the frozen exe falls back to the version string stamped into
# src/main.py by scripts/build.py.
#
# Build with:  .venv/Scripts/python.exe scripts/build.py   (or: pyinstaller hextessellator.spec, run from the repo root)

import os

# Resolve the repo root from the spec's own location, falling back to the working directory.

try:
    root = os.path.abspath(SPECPATH)
except NameError:
    root = os.path.abspath(os.getcwd())


a = Analysis(
    [os.path.join(root, 'src', 'main.py')],
    pathex=[root],
    binaries=[],
    datas=[],
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
    name='hextessellator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
