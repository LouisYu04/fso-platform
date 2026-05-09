"""
FSO Platform — CLI entry point
支持 `python -m fso_platform` 和 pip install 后的 `fso-platform` 命令

这个文件和仓库根目录的 main.py 做的是同一件事，但服务的使用场景不同：

1. main.py 适合开发者直接从源码目录运行：`python main.py`。
2. 本文件适合包方式运行：`python -m fso_platform`，也作为 pyproject.toml
   中 console script `fso-platform` 的入口。

两处入口保持样式和初始化流程一致，可以避免“开发运行正常、安装后异常”
这类差异。后续如果调整 QApplication 初始化，建议同步修改两个入口。
"""

import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中（用于开发模式）。
# pip 安装后包路径由 site-packages 提供；但在源码目录直接执行
# `python -m fso_platform` 时，显式加入项目根目录可以让相对资源和本地包
# 解析更稳定，尤其适合 IDE 调试和 PyInstaller Analysis 阶段。
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from fso_platform.ui.main_window import MainWindow
from fso_platform.ui import theme
from fso_platform.utils.fonts import FONT_FAMILY, FONT_SIZE_APP, FONT_SIZE_XS


def main():
    """
    应用程序入口函数。

    初始化顺序很重要：
        1. 高 DPI 属性必须在 QApplication 创建前设置。
        2. QApplication 创建后再设置字体和全局 QSS。
        3. 主窗口创建后进入 Qt 事件循环。
    """
    # 高 DPI 支持必须在 QApplication 实例化前设置；否则 Retina/4K 屏幕上
    # 可能出现字体过小或图标模糊的问题。
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # 全局字体由 utils.fonts 按平台选择，保证中文界面在 macOS/Windows/Linux
    # 上尽量使用本机可用的 CJK 字体。
    font = QFont(FONT_FAMILY, FONT_SIZE_APP)
    app.setFont(font)

    # 入口处只设置应用级公共样式；具体面板、表格和按钮的样式在 theme.py
    # 以及各 UI 组件中维护，避免这里变成难以追踪的“样式总表”。
    app.setStyleSheet(f"""
        QMainWindow {{
            background-color: {theme.BG_APP};
        }}
        QToolTip {{
            background-color: {theme.BG_CARD};
            color: {theme.TEXT_PRIMARY};
            border: 1px solid {theme.BORDER};
            border-radius: 4px;
            padding: 4px 8px;
            font-family: "{FONT_FAMILY}";
            font-size: {FONT_SIZE_XS}px;
        }}
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

    window = MainWindow()
    window.show()
    # Qt 5 使用 exec_() 进入事件循环。sys.exit 会把 Qt 返回码传给系统，
    # 便于脚本或打包应用判断是否正常退出。
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
