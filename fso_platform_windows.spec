# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for FSO Platform — Windows executable

Usage (run on Windows):
    pyinstaller fso_platform_windows.spec
"""

import sys
from pathlib import Path

# Project root
ROOT = Path(SPECPATH)
UI_DIR = ROOT / "fso_platform" / "ui"

# Collect all .ui files as data files
ui_files = [(str(f), "fso_platform/ui") for f in UI_DIR.glob("*.ui")]

# Analysis configuration
a = Analysis(
    ["main.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=ui_files,
    hiddenimports=[
        # PyQt5 modules
        "PyQt5.sip",
        "PyQt5.QtCore",
        "PyQt5.QtGui",
        "PyQt5.QtWidgets",
        # Matplotlib backends
        "matplotlib.backends.backend_qt5agg",
        "matplotlib.backends.backend_qt5",
        # SciPy submodules
        "scipy.special",
        "scipy.integrate",
        # Package submodules
        "fso_platform.models",
        "fso_platform.ui",
        "fso_platform.utils",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Remove duplicate libraries
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Windows EXE configuration
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="FSOPlatform",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI app, no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
