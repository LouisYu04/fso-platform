"""
主窗口
无线光通信系统链路特性可视化平台

布局:
  左侧固定栏 (280 px): 参数配置
  右侧内容区 (可伸缩): 标签页
    - 仿真结果  : 指标卡片 + 仿真日志
    - 数据图表  : Matplotlib 多图
    - 历史对比  : 多场景对比表 + 报告导出

职责边界:
  MainWindow 只负责“协调”：
    - 从 ParameterPanel 读取参数；
    - 启动 SimulationWorker 所在线程；
    - 将 worker 的信号分发给仿真面板、图表面板和结果面板；
    - 维护有限长度的历史记录。

  具体计算公式不放在这里，避免 GUI 控制流和物理模型耦合。
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
from fso_platform.utils.fonts import FONT_FAMILY as _FONT_FAMILY, FONT_SIZE_SM

# 历史记录只保留最近 50 次仿真，避免长时间使用后表格和内存无限增长。
MAX_HISTORY = 50


class MainWindow(QMainWindow):
    """
    FSO 链路特性可视化平台 — 主窗口。

    Qt Designer 生成的 main_window.ui 中只保留主框架和占位控件；
    真实业务面板在运行时创建并插入。这样 UI 文件负责“骨架”，Python
    代码负责“行为”，两边改动互不干扰。
    """

    def __init__(self):
        super().__init__()

        # 加载 UI 文件。uic.loadUi 会把 .ui 中的对象名绑定为 self.xxx，
        # 后续代码中的 menubar、statusbar、mainSplitter 等属性都来自这里。
        ui_path = Path(__file__).parent / "main_window.ui"
        uic.loadUi(ui_path, self)

        # 最近一次仿真的完整结果，供其他动作或调试时访问。
        self.simulation_results: dict = {}
        # 历史记录项结构:
        # {"name": 场景名, "params": 参数字典, "results": 结果字典}
        self.history: list = []
        # Worker 放在单独 QThread 中运行，避免 BER 积分和曲线生成阻塞 UI。
        self._thread: QThread | None = None
        self._worker: SimulationWorker | None = None

        self._init_ui()
        self._init_menubar()
        self._connect_signals()

    # ─────────────────────── 界面初始化 ─────────────────────────────

    def _init_ui(self):
        """
        初始化子面板并应用样式。

        主窗口 UI 文件里预留了 leftPanel 和 contentTabs 占位符。这里会把
        leftPanel 替换成参数面板，并把三个功能页面加入右侧 Tab。
        """
        # 应用菜单栏样式。菜单栏属于 QMainWindow 顶层控件，放在这里统一设置
        # 比让各子面板关心全局菜单更清晰。
        self.menubar.setStyleSheet(
            f"""
            QMenuBar {{
                font-family: "{_FONT_FAMILY}";
                font-size: {FONT_SIZE_SM}px;
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
                font-size: {FONT_SIZE_SM}px;
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

        # 创建子面板。ParameterPanel 会立即构建默认参数并发出参数变更信号，
        # 因此信号连接放在 _connect_signals 中统一处理。
        self.param_panel = ParameterPanel()
        # 移除 Qt Designer 中的占位符，保留 splitter 布局本身。
        self.leftPanel.setParent(None)
        self.mainSplitter.insertWidget(0, self.param_panel)

        # 创建标签页面板。三个面板共享同一份 results 字典，但各自只关心
        # 自己需要展示的键。
        self.sim_panel = SimulationPanel()
        self.plot_panel = PlotPanel()
        self.result_panel = ResultPanel()

        # 移除 .ui 中为了设计时预览保留的占位标签页，添加真实面板。
        self.contentTabs.clear()
        self.contentTabs.addTab(self.sim_panel, "仿真结果")
        self.contentTabs.addTab(self.plot_panel, "数据图表")
        self.contentTabs.addTab(self.result_panel, "历史对比")

        # 设置分割器拉伸因子：左侧参数栏固定偏窄，右侧内容区吃掉剩余空间。
        self.mainSplitter.setStretchFactor(0, 0)
        self.mainSplitter.setStretchFactor(1, 1)
        self.mainSplitter.setSizes([320, 1120])

        self.statusbar.showMessage("就绪 — 在左侧配置参数后点击「开始仿真」")

    def _init_menubar(self):
        """连接菜单动作。菜单 action 对象来自 main_window.ui。"""
        self.actionReset.triggered.connect(self._on_reset)
        self.actionExit.triggered.connect(self.close)
        self.actionRun.triggered.connect(self._on_run_simulation)
        self.actionAbout.triggered.connect(self._on_about)

    def _connect_signals(self):
        """
        连接各面板信号。

        信号流大致为：
            ParameterPanel.run_requested
                -> MainWindow._on_run_simulation
                -> SimulationWorker 在 QThread 中计算
                -> MainWindow._on_simulation_done
                -> PlotPanel / ResultPanel 刷新展示
        """
        # 参数变更 → 仿真面板同步
        self.param_panel.params_changed.connect(self.sim_panel.update_params)
        # 仿真完成 → 刷新图表和历史
        self.sim_panel.simulation_done.connect(self._on_simulation_done)
        # 参数面板"开始仿真"按钮
        self.param_panel.run_requested.connect(self._on_run_simulation)
        self.param_panel.cancel_requested.connect(self._on_cancel_simulation)
        # 历史清空按钮
        self.result_panel.clear_requested.connect(self.clear_history)

    # ─────────────────────── 事件处理 ───────────────────────────────

    def _on_run_simulation(self):
        """
        启动一次仿真。

        如果已有 worker 正在运行，则忽略新的启动请求，防止多个线程同时写
        同一组 UI 控件和历史记录。真正的取消逻辑由 cancel_requested/worker
        负责，不能在这里直接启动第二个 worker。
        """
        if self._thread is not None and self._thread.isRunning():
            return

        # get_params() 会完成 UI 输入到 SI 单位的转换，并在失败时返回 None。
        params = self.param_panel.get_params()
        if params is None:
            return

        # 先清空仿真面板、切换状态，再启动线程；即使计算很快，用户也能看到
        # 一次完整的状态切换。
        self.statusbar.showMessage("正在仿真，请稍候…")
        self.contentTabs.setCurrentIndex(0)
        self.sim_panel.start_simulation(params)
        self.param_panel.set_running(True)

        # Qt 约定：QObject 通过 moveToThread 迁移线程亲和性，真正执行函数由
        # QThread.started 信号触发。不要直接在主线程调用 worker.run()。
        self._thread = QThread()
        self._worker = SimulationWorker(params)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)

        # worker 只发信号，不直接接触 GUI 控件；所有 UI 更新都回到主线程执行。
        self._worker.progress.connect(self.sim_panel.progressBar.setValue)
        self._worker.log_line.connect(self.sim_panel._log)
        self._worker.result_update.connect(self.sim_panel._update_result)
        self._worker.simulation_done.connect(self._on_simulation_done)
        self._worker.error_occurred.connect(self._on_simulation_error)

        # 无论成功还是报错，都应恢复按钮状态并回收线程对象。
        self._worker.simulation_done.connect(self._cleanup_simulation)
        self._worker.error_occurred.connect(self._cleanup_simulation)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _cleanup_simulation(self):
        """
        结束 worker 线程并恢复运行按钮状态。

        wait(1000) 给线程最多 1 秒退出；如果后续增加更耗时的清理逻辑，
        这里需要同步调整等待策略，避免主窗口提前丢弃线程引用。
        """
        self.param_panel.set_running(False)
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(1000)
        self._thread = None
        self._worker = None

    def _on_cancel_simulation(self):
        """请求取消当前后台仿真。"""
        if self._worker is None:
            return
        self._worker.cancel()
        self.statusbar.showMessage("正在取消仿真…")

    def _on_simulation_done(self, results: dict):
        """
        接收完整仿真结果并刷新所有展示面板。

        results 是 SimulationWorker 统一生成的数据包，既包含数值指标，也包含
        绘图所需的曲线数组。这里不重新计算任何物理量，只做展示和历史记录。
        """
        self.simulation_results = results

        # 重新读取 params 而不是复用 worker 内部参数，是为了记录用户当前界面
        # 上显示的参数快照。正常情况下二者一致。
        params = self.param_panel.get_params()
        scenario_name = self.param_panel.get_scenario_name()
        self.history.append(
            {"name": scenario_name, "params": params, "results": results}
        )
        # 历史记录采用先进先出裁剪，保证 ResultPanel 表格不会无限增长。
        while len(self.history) > MAX_HISTORY:
            self.history.pop(0)

        self.plot_panel.update_plots(params, results)
        self.result_panel.update_results(params, results, self.history)

        # 状态栏只放最关键的几个指标，详细数据交给右侧面板。
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
        """显示 worker 捕获到的异常信息。"""
        self.statusbar.showMessage(f"仿真出错: {msg}")
        QMessageBox.critical(self, "仿真错误", msg)

    def _on_reset(self):
        """恢复参数面板默认值。"""
        self.param_panel.reset_params()
        self.statusbar.showMessage("参数已重置为默认值")

    def _on_about(self):
        """显示软件说明对话框。"""
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
        """清空历史记录和历史对比面板。"""
        self.history.clear()
        self.result_panel.clear()
        self.statusbar.showMessage("历史记录已清空")

    def closeEvent(self, event):
        """
        窗口关闭前释放后台线程和 Matplotlib Figure。

        Qt 在窗口关闭时不会自动等待自定义 worker 完成。这里先请求取消，
        再退出线程，最后释放绘图资源，避免进程退出时出现 QThread 警告或
        Matplotlib 后端资源泄漏。
        """
        if self._thread is not None and self._thread.isRunning():
            if self._worker is not None:
                self._worker.cancel()
            self._thread.quit()
            self._thread.wait(2000)
        self.plot_panel.cleanup()
        event.accept()
