"""
UI 主题常量
集中管理配色方案、样式表片段，确保全局视觉一致性
"""

from fso_platform.utils.fonts import (
    FONT_FAMILY,
    FONT_MONO,
    FONT_SIZE_XS,
    FONT_SIZE_SM,
    FONT_SIZE_MD,
    FONT_SIZE_LG,
    FONT_SIZE_XL,
    FONT_SIZE_TITLE,
)

# ─── 主色调 ───────────────────────────────────────────────
PRIMARY = "#1565C0"  # 深蓝 — 主交互色
PRIMARY_LIGHT = "#E3F2FD"  # 浅蓝 — 主色高亮背景
PRIMARY_DARK = "#0D47A1"  # 深蓝 — hover 状态

SUCCESS = "#2E7D32"  # 绿色
SUCCESS_BG = "#E8F5E9"
WARNING = "#E65100"  # 橙色
WARNING_BG = "#FFF3E0"
ERROR = "#C62828"  # 红色
ERROR_BG = "#FFEBEE"
NEUTRAL = "#546E7A"  # 灰蓝
NEUTRAL_BG = "#ECEFF1"

# ─── 背景色 ───────────────────────────────────────────────
BG_APP = "#F0F2F5"  # 应用整体背景
BG_SIDEBAR = "#FAFAFA"  # 左侧栏背景
BG_CARD = "#FFFFFF"  # 卡片/面板背景
BG_SECTION = "#F5F7FA"  # 区段背景

# ─── 边框 ────────────────────────────────────────────────
BORDER = "#DDE3EC"
BORDER_LIGHT = "#EEF1F5"

# ─── 文字 ────────────────────────────────────────────────
TEXT_PRIMARY = "#1A1A2E"
TEXT_SECONDARY = "#546E7A"
TEXT_DIM = "#90A4AE"
TEXT_WHITE = "#FFFFFF"

# ─── 间距系统 (8px 基准网格) ─────────────────────────────
SPACING_XS = 2
SPACING_SM = 4
SPACING_MD = 8
SPACING_LG = 12
SPACING_XL = 16
SPACING_XXL = 24

# ─── 阴影 /  elevation ────────────────────────────────────
SHADOW_SM = "0 1px 2px rgba(0,0,0,0.04)"
SHADOW_MD = "0 2px 4px rgba(0,0,0,0.06)"
SHADOW_LG = "0 4px 8px rgba(0,0,0,0.08)"

# ─── 卡片状态颜色映射 ─────────────────────────────────────
def status_color(level: str) -> str:
    """返回状态对应的文字颜色"""
    return {
        "good": SUCCESS,
        "ok": PRIMARY,
        "warn": WARNING,
        "bad": ERROR,
        "neutral": NEUTRAL,
    }.get(level, NEUTRAL)


def status_bg(level: str) -> str:
    """返回状态对应的背景色"""
    return {
        "good": SUCCESS_BG,
        "ok": PRIMARY_LIGHT,
        "warn": WARNING_BG,
        "bad": ERROR_BG,
        "neutral": NEUTRAL_BG,
    }.get(level, NEUTRAL_BG)


# ─── 常用样式表片段 ───────────────────────────────────────
CARD_STYLE = f"""
    QFrame {{
        background-color: {BG_CARD};
        border: 1px solid {BORDER_LIGHT};
        border-radius: 8px;
    }}
"""

SIDEBAR_STYLE = f"""
    QWidget#sidebar {{
        background-color: {BG_SIDEBAR};
        border-right: 1px solid {BORDER};
    }}
"""

SECTION_HEADER_STYLE = f"""
    QToolButton {{
        font-family: "{FONT_FAMILY}";
        font-weight: bold;
        font-size: {FONT_SIZE_MD}px;
        color: {TEXT_PRIMARY};
        background-color: {BG_SECTION};
        border: none;
        border-radius: 4px;
        padding: 5px 8px;
        text-align: left;
    }}
    QToolButton:hover {{
        background-color: {PRIMARY_LIGHT};
        color: {PRIMARY};
    }}
"""

RUN_BTN_STYLE = f"""
    QPushButton {{
        background-color: {PRIMARY};
        color: {TEXT_WHITE};
        font-family: "{FONT_FAMILY}";
        font-weight: bold;
        font-size: {FONT_SIZE_LG}px;
        border: none;
        border-radius: 8px;
        padding: 9px 0;
    }}
    QPushButton:hover {{
        background-color: {PRIMARY_DARK};
    }}
    QPushButton:pressed {{
        background-color: {PRIMARY_DARK};
        padding-top: 10px;
        padding-bottom: 6px;
    }}
    QPushButton:disabled {{
        background-color: #B0BEC5;
    }}
"""

RESET_BTN_STYLE = f"""
    QPushButton {{
        background-color: transparent;
        color: {NEUTRAL};
        font-family: "{FONT_FAMILY}";
        font-size: {FONT_SIZE_MD}px;
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 5px 0;
    }}
    QPushButton:hover {{
        border-color: {PRIMARY};
        color: {PRIMARY};
        background-color: {PRIMARY_LIGHT};
    }}
"""

INPUT_STYLE = f"""
    QDoubleSpinBox, QSpinBox, QComboBox {{
        font-family: "{FONT_FAMILY}";
        font-size: {FONT_SIZE_SM}px;
        color: {TEXT_PRIMARY};
        background-color: {BG_CARD};
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 3px 6px;
        min-height: 24px;
    }}
    QDoubleSpinBox:hover, QSpinBox:hover, QComboBox:hover {{
        border-color: {PRIMARY};
        background-color: {BG_CARD};
    }}
    QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {{
        border-color: {PRIMARY};
        background-color: #FFFFFF;
    }}
    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}
    QComboBox QAbstractItemView {{
        border: 1px solid {BORDER};
        border-radius: 5px;
        background-color: {BG_CARD};
        selection-background-color: {PRIMARY_LIGHT};
        selection-color: {PRIMARY};
        padding: 4px;
    }}
"""

LABEL_STYLE = f"""
    QLabel {{
        font-family: "{FONT_FAMILY}";
        font-size: {FONT_SIZE_SM}px;
        color: {TEXT_SECONDARY};
        background: transparent;
        border: none;
    }}
"""

PROGRESS_STYLE = f"""
    QProgressBar {{
        border: none;
        border-radius: 4px;
        background-color: {BORDER_LIGHT};
        height: 6px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background-color: {PRIMARY};
        border-radius: 4px;
    }}
"""

TAB_STYLE = f"""
    QTabWidget::pane {{
        border: 1px solid {BORDER};
        border-top: none;
        border-radius: 0 0 8px 8px;
        background-color: {BG_CARD};
    }}
    QTabBar::tab {{
        font-family: "{FONT_FAMILY}";
        font-size: {FONT_SIZE_MD}px;
        color: {TEXT_SECONDARY};
        background-color: transparent;
        border: none;
        padding: 8px 14px;
        min-width: 72px;
        min-height: 32px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        color: {PRIMARY};
        font-weight: bold;
        border-bottom: 2px solid {PRIMARY};
    }}
    QTabBar::tab:hover:!selected {{
        color: {TEXT_PRIMARY};
        background-color: {PRIMARY_LIGHT};
        border-radius: 4px 4px 0 0;
    }}
"""

INNER_TAB_STYLE = f"""
    QTabWidget::pane {{
        border: 1px solid {BORDER};
        border-top: none;
        border-radius: 0 0 6px 6px;
        background-color: {BG_CARD};
    }}
    QTabBar::tab {{
        font-family: "{FONT_FAMILY}";
        font-size: {FONT_SIZE_LG}px;
        color: {TEXT_SECONDARY};
        background-color: transparent;
        border: none;
        padding: 10px 16px;
        min-width: 80px;
        min-height: 36px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        color: {PRIMARY};
        font-weight: bold;
        border-bottom: 2px solid {PRIMARY};
    }}
    QTabBar::tab:hover:!selected {{
        color: {TEXT_PRIMARY};
        background-color: {PRIMARY_LIGHT};
        border-radius: 4px 4px 0 0;
    }}
"""

SCROLLAREA_STYLE = f"""
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}
    QScrollBar:vertical {{
        width: 6px;
        background: transparent;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER};
        border-radius: 3px;
        min-height: 40px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {TEXT_DIM};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        height: 6px;
        background: transparent;
        margin: 0px;
    }}
    QScrollBar::handle:horizontal {{
        background: {BORDER};
        border-radius: 3px;
        min-width: 40px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {TEXT_DIM};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}
"""

TABLE_STYLE = f"""
    QTableWidget {{
        font-family: "{FONT_MONO}";
        font-size: {FONT_SIZE_MD}px;
        color: {TEXT_PRIMARY};
        background-color: {BG_CARD};
        gridline-color: {BORDER_LIGHT};
        border: 1px solid {BORDER};
        border-radius: 8px;
        alternate-background-color: {BG_SECTION};
        selection-background-color: {PRIMARY_LIGHT};
        selection-color: {PRIMARY};
    }}
    QTableWidget::item {{
        padding: 5px 10px;
        border: none;
    }}
    QTableWidget::item:selected {{
        background-color: {PRIMARY_LIGHT};
        color: {PRIMARY};
    }}
    QHeaderView::section {{
        font-family: "{FONT_FAMILY}";
        font-size: {FONT_SIZE_MD}px;
        font-weight: bold;
        color: {TEXT_SECONDARY};
        background-color: {BG_SECTION};
        border: none;
        border-bottom: 1px solid {BORDER};
        border-radius: 0px;
        padding: 6px 10px;
    }}
    QHeaderView::section:first {{
        border-top-left-radius: 8px;
    }}
    QHeaderView::section:last {{
        border-top-right-radius: 8px;
    }}
"""

STATUSBAR_STYLE = f"""
    QStatusBar {{
        font-family: "{FONT_FAMILY}";
        font-size: {FONT_SIZE_SM}px;
        color: {TEXT_SECONDARY};
        background-color: {BG_SIDEBAR};
        border-top: 1px solid {BORDER};
        padding: 2px 12px;
    }}
    QStatusBar::item {{
        border: none;
    }}
"""

LOG_STYLE = f"""
    QTextEdit {{
        font-family: "{FONT_MONO}";
        font-size: {FONT_SIZE_SM}px;
        color: {TEXT_PRIMARY};
        background-color: #FAFBFC;
        border: 1px solid {BORDER_LIGHT};
        border-radius: 6px;
        padding: 6px;
        line-height: 1.5;
    }}
"""
