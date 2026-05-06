# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for FSO Platform — Windows executable (onedir mode)

Usage (run on Windows):
    pyinstaller fso_platform_windows.spec
"""

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Project root
ROOT = Path(SPECPATH)
UI_DIR = ROOT / "fso_platform" / "ui"

# Collect all .ui files as data files
ui_files = [(str(f), "fso_platform/ui") for f in UI_DIR.glob("*.ui")]

# Auto-collect data files for matplotlib and PyQt5
datas = ui_files
datas += collect_data_files("matplotlib", includes=["mpl-data/**"])
datas += collect_data_files("PyQt5", includes=["Qt5/plugins/**"])

# Auto-collect submodules
hiddenimports = collect_submodules("fso_platform")
hiddenimports += ["matplotlib.backends.backend_qt5agg"]

a = Analysis(
    ["main.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={"matplotlib": {"backends": ["Qt5Agg"]}},
    runtime_hooks=[],
    excludes=["PySide2", "PySide6", "PyQt6"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Onedir EXE — only scripts, no binaries/datas
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FSOPlatform",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX can corrupt Qt DLLs on Windows
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# Collect binaries and data into directory
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="FSOPlatform",
)
