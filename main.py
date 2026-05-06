"""
无线光通信系统链路特性可视化平台
=================================

功能概述:
    本文件是 FSO (Free Space Optics) 通信系统仿真平台的入口文件，
    负责初始化 PyQt5 应用环境、配置全局样式，并启动主窗口。

启动流程:
    1. 启用高 DPI 显示适配（适配 4K / Retina 屏幕）
    2. 创建 QApplication 实例并配置全局字体
    3. 注入全局 QSS 样式（主窗口背景、工具提示、滚动条等）
    4. 实例化并显示主窗口 MainWindow
    5. 进入 Qt 事件循环，等待用户交互

依赖:
    - PyQt5:         GUI 框架（需提前安装: pip install PyQt5）
    - fso_platform:  本项目的业务模块包（models / ui / utils）

运行方式:
    python main.py

平台兼容性:
    - macOS / Windows / Linux 均支持
    - 高 DPI 缩放由 Qt 自动处理（AA_EnableHighDpiScaling）
"""

import sys
import os

# 将项目根目录加入 sys.path，确保 `import fso_platform` 可被解析。
# 当通过 `python main.py` 直接运行时，__file__ 所在目录即为项目根；
# 但若从其它工作目录调用（如 IDE 调试），sys.path 中可能缺少此路径，
# 因此需要显式插入。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── PyQt5 核心导入 ──────────────────────────────────────────────────────────
# QApplication : Qt 应用单例，管理事件循环和全局配置
# QFont        : 全局字体设置
# Qt           : Qt 命名空间常量（如 AA_EnableHighDpiScaling）
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

# ── 项目业务模块导入 ────────────────────────────────────────────────────────
# MainWindow : 主窗口类，包含侧边栏导航和页面栈
# theme      : 全局主题常量（颜色、圆角等），用于 QSS 样式注入
# FONT_FAMILY: 跨平台字体族名称（macOS 用 'PingFang SC'，Windows 用 'Microsoft YaHei' 等）
from fso_platform.ui.main_window import MainWindow
from fso_platform.ui import theme
from fso_platform.utils.fonts import FONT_FAMILY, FONT_SIZE_APP, FONT_SIZE_XS


def main():
    """
    应用程序入口函数

    执行流程:
        1. 启用高 DPI 缩放支持
        2. 创建 QApplication 实例
        3. 设置全局字体（平台自适应）
        4. 注入全局 QSS 样式表
        5. 创建并显示主窗口
        6. 进入 Qt 事件循环（阻塞直到窗口关闭）
    """
    # ── 高 DPI 支持 ─────────────────────────────────────────────────────────
    # AA_EnableHighDpiScaling : 允许 Qt 自动根据显示器 DPI 缩放 UI 元素
    # AA_UseHighDpiPixmaps    : 使用高分辨率像素图，避免图标/图片模糊
    # 这两个属性必须在 QApplication 实例化之前设置才生效
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # 创建 QApplication 单例（sys.argv 传递命令行参数给 Qt）
    app = QApplication(sys.argv)

    # ── 全局字体 ─────────────────────────────────────────────────────────────
    # FONT_FAMILY 由 utils/fonts.py 根据操作系统自动选择:
    #   macOS  → 'PingFang SC'
    #   Windows→ 'Microsoft YaHei'
    #   Linux  → 'Noto Sans CJK SC' / 'WenQuanYi Micro Hei'
    # 字号 10pt 为界面基准，各组件可通过 QSS 或 setFont 局部覆盖
    font = QFont(FONT_FAMILY, FONT_SIZE_APP)
    app.setFont(font)

    # ── 全局 QSS 样式表 ─────────────────────────────────────────────────────
    # 此处定义应用级基础样式；各子组件的细化样式已在 theme.py 中按需注入。
    # 样式优先级: 组件级 setStyleSheet > 全局 app.setStyleSheet > Qt 默认
    app.setStyleSheet(f"""
        /* 主窗口背景色（深色/浅色主题由 theme.BG_APP 控制） */
        QMainWindow {{
            background-color: {theme.BG_APP};
        }}

        /* 工具提示样式 */
        QToolTip {{
            background-color: {theme.BG_CARD};
            color: {theme.TEXT_PRIMARY};
            border: 1px solid {theme.BORDER};
            border-radius: 4px;
            padding: 4px 8px;
            font-family: "{FONT_FAMILY}";
            font-size: {FONT_SIZE_XS}px;
        }}

        /* 垂直滚动条: 6px 宽，无上下箭头，圆角滑块 */
        QScrollBar:vertical {{
            width: 6px;
            background: transparent;
        }}
        QScrollBar::handle:vertical {{
            background: {theme.BORDER};
            border-radius: 3px;
            min-height: 30px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}

        /* 水平滚动条: 6px 高，无左右箭头，圆角滑块 */
        QScrollBar:horizontal {{
            height: 6px;
            background: transparent;
        }}
        QScrollBar::handle:horizontal {{
            background: {theme.BORDER};
            border-radius: 3px;
            min-width: 30px;
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
        }}
    """)

    # ── 主窗口 ───────────────────────────────────────────────────────────────
    # MainWindow 内部包含:
    #   - 侧边栏导航 (Sidebar)
    #   - 页面栈 (QStackedWidget): 大气衰减 / 湍流闪烁 / 链路预算 / BER 分析
    #   - 状态栏 / 工具栏等
    window = MainWindow()
    window.show()

    # ── 进入事件循环 ─────────────────────────────────────────────────────────
    # app.exec_() 启动 Qt 事件循环，阻塞直到所有窗口关闭。
    # sys.exit() 确保退出时返回正确的进程退出码（0 表示正常退出）。
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
