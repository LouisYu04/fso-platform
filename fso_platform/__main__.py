"""
FSO Platform — CLI entry point
支持 `python -m fso_platform` 和 pip install 后的 `fso-platform` 命令
"""

import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中（用于开发模式）
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from fso_platform.ui.main_window import MainWindow
from fso_platform.ui import theme
from fso_platform.utils.fonts import FONT_FAMILY, FONT_SIZE_APP, FONT_SIZE_XS


def main():
    """应用程序入口函数"""
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    font = QFont(FONT_FAMILY, FONT_SIZE_APP)
    app.setFont(font)

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
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
