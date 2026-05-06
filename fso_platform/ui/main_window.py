"""
主窗口
无线光通信系统链路特性可视化平台

布局:
  左侧固定栏 (280 px): 参数配置
  右侧内容区 (可伸缩): 标签页
    - 仿真结果  : 指标卡片 + 仿真日志
    - 数据图表  : Matplotlib 多图
    - 历史对比  : 多场景对比表 + 报告导出
"""

from pathlib import Path
from PyQt5.QtWidgets import (
    QMainWindow,
    QMessageBox,
)
from PyQt5.QtCore import Qt, QThread
from PyQt5.QtGui import QFont
from PyQt5 import uic

from .simulation_worker import SimulationWorker

from .parameter_panel import ParameterPanel
from .simulation_panel import SimulationPanel
from .plot_widgets import PlotPanel
from .result_panel import ResultPanel
from .theme import (
    BG_APP,
    STATUSBAR_STYLE,
    TAB_STYLE,
    PRIMARY,
    BORDER,
    TEXT_SECONDARY,
    FONT_FAMILY,
)
from fso_platform.utils.fonts import FONT_FAMILY as _FONT_FAMILY

MAX_HISTORY = 50


class MainWindow(QMainWindow):
    """FSO 链路特性可视化平台 — 主窗口"""

    def __init__(self):
        super().__init__()

        # 加载 UI 文件
        ui_path = Path(__file__).parent / "main_window.ui"
        uic.loadUi(ui_path, self)

        self.simulation_results: dict = {}
        self.history: list = []
        self._thread: QThread | None = None
        self._worker: SimulationWorker | None = None

        self._init_ui()
        self._init_menubar()
        self._connect_signals()

    # ─────────────────────── 界面初始化 ─────────────────────────────

    def _init_ui(self):
        """初始化子面板并应用样式"""
        # 应用样式表
        self.menubar.setStyleSheet(
            f"""
            QMenuBar {{
                font-family: "{_FONT_FAMILY}";
                font-size: 12px;
                background-color: #FFFFFF;
                border-bottom: 1px solid {BORDER};
            }}
            QMenuBar::item:selected {{
                background-color: #E3F2FD;
                color: {PRIMARY};
                border-radius: 4px;
            }}
            QMenu {{
                font-family: "{_FONT_FAMILY}";
                font-size: 12px;
                background-color: #FFFFFF;
                border: 1px solid {BORDER};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 20px 6px 12px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: #E3F2FD;
                color: {PRIMARY};
            }}
            """
        )

        self.statusbar.setStyleSheet(STATUSBAR_STYLE)
        self.contentTabs.setStyleSheet(TAB_STYLE)
        self.contentTabs.setFont(QFont(_FONT_FAMILY, 13))
        self.contentTabs.tabBar().setElideMode(Qt.ElideNone)

        # 创建子面板
        self.param_panel = ParameterPanel()
        self.leftPanel.setParent(None)  # 移除占位符
        self.mainSplitter.insertWidget(0, self.param_panel)

        # 创建标签页面板
        self.sim_panel = SimulationPanel()
        self.plot_panel = PlotPanel()
        self.result_panel = ResultPanel()

        # 移除占位标签页，添加真实面板
        self.contentTabs.clear()
        self.contentTabs.addTab(self.sim_panel, "  仿真结果  ")
        self.contentTabs.addTab(self.plot_panel, "  数据图表  ")
        self.contentTabs.addTab(self.result_panel, "  历史对比  ")

        # 设置分割器拉伸因子
        self.mainSplitter.setStretchFactor(0, 0)
        self.mainSplitter.setStretchFactor(1, 1)
        self.mainSplitter.setSizes([288, 1152])

        self.statusbar.showMessage("就绪 — 在左侧配置参数后点击「开始仿真」")

    def _init_menubar(self):
        """连接菜单动作"""
        self.actionReset.triggered.connect(self._on_reset)
        self.actionExit.triggered.connect(self.close)
        self.actionRun.triggered.connect(self._on_run_simulation)
        self.actionAbout.triggered.connect(self._on_about)

    def _connect_signals(self):
        """连接各面板信号"""
        # 参数变更 → 仿真面板同步
        self.param_panel.params_changed.connect(self.sim_panel.update_params)
        # 仿真完成 → 刷新图表和历史
        self.sim_panel.simulation_done.connect(self._on_simulation_done)
        # 参数面板"开始仿真"按钮
        self.param_panel.run_requested.connect(self._on_run_simulation)
        # 历史清空按钮
        self.result_panel.clear_requested.connect(self.clear_history)

    # ─────────────────────── 事件处理 ───────────────────────────────

    def _on_run_simulation(self):
        if self._thread is not None and self._thread.isRunning():
            return

        params = self.param_panel.get_params()
        if params is None:
            return

        self.statusbar.showMessage("正在仿真，请稍候…")
        self.contentTabs.setCurrentIndex(0)
        self.sim_panel.start_simulation(params)
        self.param_panel.set_running(True)

        self._thread = QThread()
        self._worker = SimulationWorker(params)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)

        self._worker.progress.connect(self.sim_panel.progressBar.setValue)
        self._worker.log_line.connect(self.sim_panel._log)
        self._worker.result_update.connect(self.sim_panel._update_result)
        self._worker.simulation_done.connect(self._on_simulation_done)
        self._worker.error_occurred.connect(self._on_simulation_error)

        self._worker.simulation_done.connect(self._cleanup_simulation)
        self._worker.error_occurred.connect(self._cleanup_simulation)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _cleanup_simulation(self):
        self.param_panel.set_running(False)
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(1000)
        self._thread = None
        self._worker = None

    def _on_simulation_done(self, results: dict):
        self.simulation_results = results

        params = self.param_panel.get_params()
        scenario_name = self.param_panel.get_scenario_name()
        self.history.append(
            {"name": scenario_name, "params": params, "results": results}
        )
        while len(self.history) > MAX_HISTORY:
            self.history.pop(0)

        self.plot_panel.update_plots(params, results)
        self.result_panel.update_results(params, results, self.history)

        ber = results.get("ber_ook", 0)
        p_r = results.get("P_R_dbm", -999)
        margin = results.get("margin", 0)
        link_ok = "良好" if margin > 6 else ("可用" if margin > 0 else "不可用")
        self.statusbar.showMessage(
            f"仿真完成 | 场景: {scenario_name}  "
            f"接收功率: {p_r:.1f} dBm  "
            f"BER(OOK): {ber:.2e}  "
            f"链路: {link_ok}"
        )

    def _on_simulation_error(self, msg: str):
        self.statusbar.showMessage(f"仿真出错: {msg}")
        QMessageBox.critical(self, "仿真错误", msg)

    def _on_reset(self):
        self.param_panel.reset_params()
        self.statusbar.showMessage("参数已重置为默认值")

    def _on_about(self):
        QMessageBox.about(
            self,
            "关于本软件",
            "<b>无线光通信系统链路特性可视化平台</b><br><br>"
            "适用范围：近地水平路径 FSO 链路仿真<br><br>"
            "核心模型：<br>"
            "　Beer-Lambert 大气衰减 / Kim 能见度模型<br>"
            "　Rytov 湍流方差 / 大尺度小尺度闪烁<br>"
            "　对数正态 / Gamma-Gamma / 负指数光强分布<br>"
            "　OOK / M-PPM / SIM-BPSK 调制 BER",
        )

    def clear_history(self):
        self.history.clear()
        self.result_panel.clear()
        self.statusbar.showMessage("历史记录已清空")

    def closeEvent(self, event):
        if self._thread is not None and self._thread.isRunning():
            if self._worker is not None:
                self._worker.cancel()
            self._thread.quit()
            self._thread.wait(2000)
        self.plot_panel.cleanup()
        event.accept()
