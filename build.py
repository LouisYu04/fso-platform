#!/usr/bin/env python3
"""
统一构建脚本
支持源码分发、macOS .app、Windows .exe 的构建

本脚本只是对标准构建命令做一层薄封装，目的是让本地构建和
README 中的命令保持一致：

1. 源码分发使用 `python -m build`，由 pyproject.toml 中的
   setuptools 后端生成 sdist 和 wheel。
2. 桌面应用使用 PyInstaller spec 文件构建。spec 文件里已经
   声明了 Qt UI 文件、Matplotlib 后端、SciPy 子模块等运行时
   依赖，因此这里不要再重复拼复杂参数。
3. macOS 和 Windows 的可执行包不能交叉构建。PyInstaller 会
   读取当前平台的动态库和 Qt 插件，所以本脚本会在平台不匹配
   时直接提示并返回。
"""

import argparse
import platform
import subprocess
import sys


def run(cmd: list[str], check: bool = True):
    """
    执行外部命令并回显完整命令行。

    参数:
        cmd: subprocess.run 接收的参数列表。使用 list 而不是字符串，
             可以避免 shell 转义问题，尤其是项目路径中包含空格时。
        check: 为 True 时，命令非零退出会抛出 CalledProcessError，
               构建流程立即失败，便于 CI 或本地终端发现错误。
    """
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=check)


def build_sdist_wheel():
    """
    构建 Python 包分发物。

    输出文件位于 dist/：
        - *.tar.gz: 源码包，适合上传 PyPI 或归档。
        - *.whl: wheel 包，适合本地安装和分发。

    注意：MANIFEST.in 会决定 sdist 中是否带上 .ui 等非 Python 文件；
    pyproject.toml 会决定包名、入口命令和依赖声明。
    """
    print("\n=== 构建源码分发 (sdist + wheel) ===")
    run([sys.executable, "-m", "build"])
    print("✅ 构建完成: dist/*.tar.gz + dist/*.whl")


def build_macos_app():
    """
    构建 macOS .app bundle（仅限 macOS）。

    PyInstaller 在 macOS 上会把当前解释器环境中的 Python、Qt 动态库、
    Matplotlib 数据文件等收集进 app bundle。构建前建议先确认当前
    虚拟环境已经安装 requirements.txt 中的依赖。
    """
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
    """
    构建 Windows onedir 可执行目录（仅限 Windows）。

    Windows 版本依赖 Qt 平台插件和 Matplotlib 数据文件，相关收集逻辑
    位于 fso_platform_windows.spec。这里保持命令简洁，避免命令行参数
    和 spec 文件出现两套不一致的配置。
    """
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
    # argparse 只负责选择构建目标；真正的平台差异由各 build_* 函数
    # 自己处理，这样 `--all` 可以在任意系统上安全执行。
    parser = argparse.ArgumentParser(description="FSO Platform 构建脚本")
    parser.add_argument("--sdist", action="store_true", help="构建 sdist + wheel")
    parser.add_argument("--macos", action="store_true", help="构建 macOS .app")
    parser.add_argument("--windows", action="store_true", help="构建 Windows .exe")
    parser.add_argument("--all", action="store_true", help="构建当前平台适用的所有目标")
    args = parser.parse_args()

    if not any([args.sdist, args.macos, args.windows, args.all]):
        # 没有指定目标时只打印帮助，不默认构建。桌面应用构建较慢，
        # 且会覆盖 dist/ 下的历史产物，显式选择更稳妥。
        parser.print_help()
        return

    # 执行顺序固定为：Python 分发物 -> 当前平台桌面包。
    # 这样 `--all` 的输出结构稳定，构建日志也更容易比较。
    if args.all or args.sdist:
        build_sdist_wheel()
    if args.all or args.macos:
        build_macos_app()
    if args.all or args.windows:
        build_windows_exe()


if __name__ == "__main__":
    main()
