# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Weasel Entertainment System.

Build with:
    pyinstaller wes.spec

This creates a single-folder distribution in dist/wes/
Run with: dist/wes/wes (Linux) or dist/wes/wes.exe (Windows)
"""

import sys
import os

block_cipher = None

# Collect data files
datas = [
    ('media', 'media'),
    ('sounds', 'sounds'),
    ('games', 'games'),
]

# Add optional directories if they exist
for optional_dir in ['demos', 'docs']:
    if os.path.isdir(optional_dir):
        datas.append((optional_dir, optional_dir))

a = Analysis(
    ['game_launcher.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['pygame'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='wes',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add 'media/icon.ico' if you have an icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='wes',
)
