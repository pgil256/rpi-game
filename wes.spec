# -*- mode: python ; coding: utf-8 -*-
"""Only active runtime media; game modules are discovered through imports."""
from pathlib import Path

# pygame has a filesystem fallback when pkg_resources is unavailable.
# Excluding it avoids ambient setuptools hooks; no game uses numpy/surfarray.
root = Path(SPECPATH)
datas = [(str(root / "media" / name), "media") for name in
         ("ferret-long-sprite.png", "ferret-long-sprite.json", "soupbowl.png")]
datas += [(str(p), "sounds") for p in sorted((root / "sounds").glob("*.wav"))]
a = Analysis([str(root / "game_launcher.py")], pathex=[str(root)], binaries=[],
             datas=datas, hiddenimports=["pygame"], hookspath=[], hooksconfig={},
             runtime_hooks=[], excludes=["numpy", "pkg_resources"], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="wes", debug=False,
          bootloader_ignore_signals=False, strip=False, upx=False, console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="wes")
