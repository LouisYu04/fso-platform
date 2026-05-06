#!/usr/bin/env python3
"""
统一构建脚本
支持源码分发、macOS .app、Windows .exe 的构建
"""

import argparse
import platform
import subprocess
import sys


def run(cmd: list[str], check: bool = True):
    """执行命令并打印输出。"""
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=check)


def build_sdist_wheel():
    """构建源码分发 (sdist + wheel)。"""
    print("\n=== 构建源码分发 (sdist + wheel) ===")
    run([sys.executable, "-m", "build"])
    print("✅ 构建完成: dist/*.tar.gz + dist/*.whl")


def build_macos_app():
    """构建 macOS .app bundle（仅限 macOS）。"""
    if platform.system() != "Darwin":
        print("⚠️  macOS .app 只能在 macOS 上构建")
        return
    print("\n=== 构建 macOS .app ===")
    run([
        sys.executable, "-m", "PyInstaller",
        "fso_platform_macos.spec",
        "--clean", "--noconfirm",
    ])
    print("✅ 构建完成: dist/FSOPlatform.app")


def build_windows_exe():
    """构建 Windows .exe（仅限 Windows）。"""
    if platform.system() != "Windows":
        print("⚠️  Windows .exe 只能在 Windows 上构建")
        print("   提示: 可使用 GitHub Actions 自动构建，见 .github/workflows/build.yml")
        return
    print("\n=== 构建 Windows .exe ===")
    run([
        sys.executable, "-m", "PyInstaller",
        "fso_platform_windows.spec",
        "--clean", "--noconfirm",
    ])
    print("✅ 构建完成: dist/FSOPlatform/FSOPlatform.exe")


def main():
    parser = argparse.ArgumentParser(description="FSO Platform 构建脚本")
    parser.add_argument("--sdist", action="store_true", help="构建 sdist + wheel")
    parser.add_argument("--macos", action="store_true", help="构建 macOS .app")
    parser.add_argument("--windows", action="store_true", help="构建 Windows .exe")
    parser.add_argument("--all", action="store_true", help="构建当前平台适用的所有目标")
    args = parser.parse_args()

    if not any([args.sdist, args.macos, args.windows, args.all]):
        parser.print_help()
        return

    if args.all or args.sdist:
        build_sdist_wheel()
    if args.all or args.macos:
        build_macos_app()
    if args.all or args.windows:
        build_windows_exe()


if __name__ == "__main__":
    main()
