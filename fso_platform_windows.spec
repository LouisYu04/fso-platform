# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for FSO Platform — Windows executable (onedir mode)

Usage (run on Windows):
    pyinstaller fso_platform_windows.spec
"""

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Project root.
# SPECPATH 由 PyInstaller 注入，指向 spec 文件所在目录。这样即使用户
# 从其他工作目录执行 pyinstaller，也能稳定定位项目文件。
ROOT = Path(SPECPATH)
UI_DIR = ROOT / "fso_platform" / "ui"

# Collect all .ui files as data files.
# UI 层使用 uic.loadUi() 在运行时读取 .ui 文件，PyInstaller 不会把它们
# 当作 import 自动收集，所以必须显式加入 datas。
ui_files = [(str(f), "fso_platform/ui") for f in UI_DIR.glob("*.ui")]

# Auto-collect data files for matplotlib and PyQt5.
# Matplotlib 的字体、样式和后端资源都在 mpl-data 中；PyQt5 的 Qt5/plugins
# 包含 platforms/qwindows.dll 等平台插件，缺失时应用通常会启动失败。
datas = ui_files
datas += collect_data_files("matplotlib", includes=["mpl-data/**"])
datas += collect_data_files("PyQt5", includes=["Qt5/plugins/**"])

# Auto-collect submodules.
# 项目内部模块数量不大，直接 collect_submodules("fso_platform") 可以避免
# 因动态导入、相对导入或 PyInstaller 静态分析遗漏而出现运行时 ImportError。
hiddenimports = collect_submodules("fso_platform")
hiddenimports += ["matplotlib.backends.backend_qt5agg"]

# Windows 采用 onedir 模式，便于查看依赖文件、替换 DLL 和排查 Qt 插件问题。
# 如果改成 onefile，需要额外关注启动解压目录和 Matplotlib/Qt 资源路径。
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

# Onedir EXE — only scripts, no binaries/datas.
# exclude_binaries=True 表示此阶段只生成启动器；DLL、zip、data 由 COLLECT
# 放进 dist/FSOPlatform/。Windows 上 UPX 压缩 Qt DLL 容易导致运行异常，
# 因此这里显式关闭 upx。
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

# Collect binaries and data into directory.
# 最终用户启动 dist/FSOPlatform/FSOPlatform.exe；同目录下会带有 Python
# 运行库、Qt 插件、Matplotlib 数据以及项目 .ui 文件。
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
