"""
UI 层 — PyQt5 图形界面组件

导出:
    7 个类:  MainWindow, ParameterPanel, SimulationPanel,
             SimulationWorker, ResultPanel, PlotPanel, MplCanvas
    2 个常量: PRESET_SCENARIOS, SCENARIO_COLORS
    21 个颜色常量 + 2 个状态函数 + 14 个样式表字符串 (来自 theme)
"""

from fso_platform.ui.main_window import MainWindow

from fso_platform.ui.parameter_panel import (
    ParameterPanel,
    PRESET_SCENARIOS,
    SCENARIO_COLORS,
)

from fso_platform.ui.simulation_panel import SimulationPanel

from fso_platform.ui.simulation_worker import SimulationWorker

from fso_platform.ui.result_panel import ResultPanel

from fso_platform.ui.plot_widgets import PlotPanel, MplCanvas

from fso_platform.ui.theme import (
    # 21 颜色常量
    PRIMARY,
    PRIMARY_LIGHT,
    PRIMARY_DARK,
    SUCCESS,
    SUCCESS_BG,
    WARNING,
    WARNING_BG,
    ERROR,
    ERROR_BG,
    NEUTRAL,
    NEUTRAL_BG,
    BG_APP,
    BG_SIDEBAR,
    BG_CARD,
    BG_SECTION,
    BORDER,
    BORDER_LIGHT,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_DIM,
    TEXT_WHITE,
    # 2 函数
    status_color,
    status_bg,
    # 14 样式表
    CARD_STYLE,
    SIDEBAR_STYLE,
    SECTION_HEADER_STYLE,
    RUN_BTN_STYLE,
    RESET_BTN_STYLE,
    INPUT_STYLE,
    LABEL_STYLE,
    PROGRESS_STYLE,
    TAB_STYLE,
    INNER_TAB_STYLE,
    SCROLLAREA_STYLE,
    TABLE_STYLE,
    STATUSBAR_STYLE,
    LOG_STYLE,
)

__all__ = [
    # Classes (7)
    "MainWindow",
    "ParameterPanel",
    "SimulationPanel",
    "SimulationWorker",
    "ResultPanel",
    "PlotPanel",
    "MplCanvas",
    # Constants (2)
    "PRESET_SCENARIOS",
    "SCENARIO_COLORS",
    # Theme colors (21)
    "PRIMARY",
    "PRIMARY_LIGHT",
    "PRIMARY_DARK",
    "SUCCESS",
    "SUCCESS_BG",
    "WARNING",
    "WARNING_BG",
    "ERROR",
    "ERROR_BG",
    "NEUTRAL",
    "NEUTRAL_BG",
    "BG_APP",
    "BG_SIDEBAR",
    "BG_CARD",
    "BG_SECTION",
    "BORDER",
    "BORDER_LIGHT",
    "TEXT_PRIMARY",
    "TEXT_SECONDARY",
    "TEXT_DIM",
    "TEXT_WHITE",
    # Theme functions (2)
    "status_color",
    "status_bg",
    # Theme styles (14)
    "CARD_STYLE",
    "SIDEBAR_STYLE",
    "SECTION_HEADER_STYLE",
    "RUN_BTN_STYLE",
    "RESET_BTN_STYLE",
    "INPUT_STYLE",
    "LABEL_STYLE",
    "PROGRESS_STYLE",
    "TAB_STYLE",
    "INNER_TAB_STYLE",
    "SCROLLAREA_STYLE",
    "TABLE_STYLE",
    "STATUSBAR_STYLE",
    "LOG_STYLE",
]
