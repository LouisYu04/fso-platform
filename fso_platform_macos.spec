# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for FSO Platform — macOS .app bundle (onedir mode)

Usage:
    pyinstaller fso_platform_macos.spec

Output:
    dist/FSOPlatform.app
"""

from pathlib import Path

# Project root.
# SPECPATH 是 PyInstaller 在执行 spec 文件时注入的变量，指向 spec
# 文件所在目录。用它而不是当前工作目录，可以保证从任意路径调用
# `pyinstaller fso_platform_macos.spec` 时资源定位都一致。
ROOT = Path(SPECPATH)
UI_DIR = ROOT / "fso_platform" / "ui"

# Collect all .ui files as data files.
# 应用运行时通过 PyQt5.uic.loadUi() 动态加载这些 XML 文件，因此它们
# 不是 Python import 图能自动发现的模块，必须显式放入 datas。
ui_files = [(str(f), "fso_platform/ui") for f in UI_DIR.glob("*.ui")]

# Analysis configuration.
# Analysis 是 PyInstaller 的依赖扫描阶段：
#   - scripts: 程序入口，这里使用兼容旧启动方式的 main.py。
#   - pathex: 让扫描器能找到本地 fso_platform 包。
#   - datas: 运行时需要按文件路径读取的资源。
#   - hiddenimports: 动态导入或 C 扩展间接依赖，扫描器不一定能自动识别。
a = Analysis(
    ["main.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=ui_files,
    hiddenimports=[
        # PyQt5.sip 是 PyQt5 的绑定层，部分冻结环境需要显式声明。
        "PyQt5.sip",
        "PyQt5.QtCore",
        "PyQt5.QtGui",
        "PyQt5.QtWidgets",
        # Matplotlib 嵌入 Qt 使用 Qt5Agg 后端；冻结应用不会自动选择后端。
        "matplotlib.backends.backend_qt5agg",
        "matplotlib.backends.backend_qt5",
        # BER 曲线和湍流积分依赖 SciPy 的 special/integrate C 扩展。
        "scipy.special",
        "scipy.integrate",
        # 项目子包在运行时被 UI 和模型层交叉引用，显式列出便于冻结。
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

# Onedir EXE — only scripts, no binaries/datas.
# exclude_binaries=True 表示 EXE 阶段只生成启动器，真正的动态库和数据文件
# 交给下面的 COLLECT 打包到同一个目录结构中。这是 macOS .app bundle
# 更容易调试和签名的布局。
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

# Collect binaries and data into app bundle directory.
# COLLECT 会把 Python 动态库、Qt 框架、Matplotlib 数据文件和 .ui 文件
# 聚合到 dist/FSOPlatform/，随后 BUNDLE 再把它包装成 .app。
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

# macOS app bundle.
# info_plist 中的字段会写入 Info.plist，影响 Finder 显示名、版本号和
# Retina 高分屏支持。后续如需发布签名，可在 EXE 阶段补 codesign 配置。
app = BUNDLE(
    coll,
    name="FSOPlatform.app",
    icon=None,
    bundle_identifier="com.fso.platform",
    info_plist={
        "CFBundleName": "FSO Platform",
        "CFBundleDisplayName": "无线光通信系统链路特性可视化平台",
        "CFBundleShortVersionString": "1.0.3",
        "CFBundleVersion": "1.0.3",
        "NSHighResolutionCapable": True,
    },
)
