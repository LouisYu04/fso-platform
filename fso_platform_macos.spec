# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for FSO Platform — macOS .app bundle (onedir mode)

Usage:
    pyinstaller fso_platform_macos.spec

Output:
    dist/FSOPlatform.app
"""

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
        "PyQt5.sip",
        "PyQt5.QtCore",
        "PyQt5.QtGui",
        "PyQt5.QtWidgets",
        "matplotlib.backends.backend_qt5agg",
        "matplotlib.backends.backend_qt5",
        "scipy.special",
        "scipy.integrate",
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
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Collect binaries and data into app bundle directory
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="FSOPlatform",
)

# macOS app bundle
app = BUNDLE(
    coll,
    name="FSOPlatform.app",
    icon=None,
    bundle_identifier="com.fso.platform",
    info_plist={
        "CFBundleName": "FSO Platform",
        "CFBundleDisplayName": "无线光通信系统链路特性可视化平台",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1.0.0",
        "NSHighResolutionCapable": True,
    },
)
