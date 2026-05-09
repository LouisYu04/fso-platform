"""
结果分析面板
仿真结果摘要卡片、多场景对比表、报告导出

本面板不重新计算任何模型结果，只展示 MainWindow 传入的 params/results/history。
这样可以保证“仿真日志、图表、历史对比、导出报告”看到的是同一次 worker
生成的数据，而不是各自重复计算后的近似值。
"""

from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QFileDialog,
    QHeaderView,
    QMessageBox,
    QScrollArea,
    QFrame,
    QSplitter,
    QSizePolicy,
    QAbstractItemView,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from PyQt5 import uic

import csv

from fso_platform.ui import theme
from fso_platform.utils.fonts import (
    FONT_FAMILY,
    FONT_MONO,
    FONT_SIZE_SM,
    FONT_SIZE_MD,
)


# ─── 小帮手：单行摘要条目 ───────────────────────────────────────────────────
class _SummaryRow(QWidget):
    """
    左侧标签 + 右侧值的一行，用于摘要卡片。

    值 QLabel 开启 TextSelectableByMouse，便于用户从结果面板复制关键数值
    到论文、报告或调试记录中。
    """

    def __init__(self, label: str, value: str = "—", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 3, 0, 3)
        layout.setSpacing(8)

        self._lbl = QLabel(label)
        self._lbl.setStyleSheet(
            f"font-family: '{FONT_FAMILY}'; font-size: {FONT_SIZE_SM}px;"
            f" color: {theme.TEXT_SECONDARY}; background: transparent; border: none;"
        )
        self._lbl.setFixedWidth(120)

        self._val = QLabel(value)
        self._val.setStyleSheet(
            f"font-family: '{FONT_MONO}'; font-size: {FONT_SIZE_MD}px;"
            f" color: {theme.TEXT_PRIMARY}; background: transparent; border: none;"
        )
        self._val.setTextInteractionFlags(Qt.TextSelectableByMouse)

        layout.addWidget(self._lbl)
        layout.addWidget(self._val, 1)

    def set_value(self, value: str):
        self._val.setText(value)

    def set_highlight(self, color: str):
        self._val.setStyleSheet(
            f"font-family: '{FONT_MONO}'; font-size: {FONT_SIZE_MD}px; font-weight: bold;"
            f" color: {color}; background: transparent; border: none;"
        )


class _SummarySection(QFrame):
    """
    带标题的摘要区段（浅色 QFrame 卡片）。

    内部用 key -> _SummaryRow 建立索引，update_summary 时可以按业务键更新，
    不依赖控件在布局中的位置，后续增删行更安全。
    """

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame {{ background-color: {theme.BG_CARD};"
            f" border: 1px solid {theme.BORDER_LIGHT};"
            f" border-radius: 8px; }}"
        )
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        v = QVBoxLayout(self)
        v.setContentsMargins(12, 8, 12, 10)
        v.setSpacing(0)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"font-family: '{FONT_FAMILY}'; font-size: {FONT_SIZE_MD}px; font-weight: bold;"
            f" color: {theme.TEXT_SECONDARY}; background: transparent; border: none;"
            f" padding-bottom: 6px;"
        )
        v.addWidget(title_lbl)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"color: {theme.BORDER_LIGHT}; background: {theme.BORDER_LIGHT};")
        line.setFixedHeight(1)
        v.addWidget(line)

        self._rows_layout = QVBoxLayout()
        self._rows_layout.setSpacing(0)
        self._rows_layout.setContentsMargins(0, 6, 0, 0)
        v.addLayout(self._rows_layout)

        self._rows: dict[str, _SummaryRow] = {}

    def add_row(self, key: str, label: str, value: str = "—") -> "_SummaryRow":
        row = _SummaryRow(label, value)
        self._rows_layout.addWidget(row)
        self._rows[key] = row
        return row

    def set_value(self, key: str, value: str):
        if key in self._rows:
            self._rows[key].set_value(value)

    def set_highlight(self, key: str, color: str):
        if key in self._rows:
            self._rows[key].set_highlight(color)


# ─── 主面板 ───────────────────────────────────────────────────────────────────
class ResultPanel(QWidget):
    """
    结果分析面板。

    对外主要接口:
        update_results(params, results, history): 刷新摘要和历史对比表。
        clear(): 清空摘要和历史表。

    导出按钮直接读取 self._history，导出的内容和屏幕中的历史表保持一致。
    """

    clear_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        # 保存 MainWindow 传入的历史列表引用/快照，用于 CSV 和报告导出。
        self._history: list = []

        # 加载 UI 文件。result_panel.ui 只定义滚动区、表格和按钮区域；
        # 摘要卡片根据第一次结果动态创建。
        ui_path = Path(__file__).parent / "result_panel.ui"
        uic.loadUi(ui_path, self)

        self._init_ui()

    # ─────────────────────────────────────────────────────────────────────────
    def _init_ui(self):
        """应用样式并连接信号。"""
        for btn in (self.btnExportCsv, self.btnExportReport, self.btnClear):
            btn.setStyleSheet(theme.RESET_BTN_STYLE)
            btn.setMinimumHeight(32)
            btn.setMaximumWidth(100)

        self.btnExportCsv.clicked.connect(self._export_csv)
        self.btnExportReport.clicked.connect(self._export_report)
        self.btnClear.clicked.connect(self.clear_requested.emit)

        self.toolbarLayout.setSpacing(8)
        self.titleLabel.setStyleSheet(
            f"font-family: '{FONT_FAMILY}'; font-size: {FONT_SIZE_MD}px; font-weight: bold;"
            f" color: {theme.TEXT_PRIMARY}; background: transparent; border: none;"
        )

        self.summaryScroll.setStyleSheet(theme.SCROLLAREA_STYLE)
        self.compareTable.setStyleSheet(theme.TABLE_STYLE)
        self.compareTable.setAlternatingRowColors(True)
        self.compareTable.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.compareTable.setSortingEnabled(True)
        self.compareTable.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )

        # 摘要区段（延迟创建）。初始状态只显示 noDataLabel，第一次仿真完成后
        # 才创建这些 QWidget，避免空白页面里出现无意义的占位卡片。
        self._sec_system: _SummarySection | None = None
        self._sec_channel: _SummarySection | None = None
        self._sec_link: _SummarySection | None = None
        self._sec_turb: _SummarySection | None = None
        self._sec_ber: _SummarySection | None = None
        self._sec_status: _SummarySection | None = None

    def _summary_sections(self) -> tuple[_SummarySection, ...]:
        """返回已经创建的摘要区段，供清空/遍历时使用。"""
        return tuple(
            sec
            for sec in (
                self._sec_system,
                self._sec_channel,
                self._sec_link,
                self._sec_turb,
                self._sec_ber,
                self._sec_status,
            )
            if sec is not None
        )

    # ─────────────────────────────────────────────────────────────────────────
    def _build_summary_sections(self):
        """
        首次调用时创建六个摘要区段。

        分组顺序与仿真流程基本一致：系统/信道输入 -> 链路预算 -> 湍流 ->
        BER -> 综合状态。这样用户从上到下阅读时能对应 SimulationWorker 日志。
        """
        # 移除占位标签
        self.noDataLabel.setVisible(False)

        # 系统参数
        self._sec_system = _SummarySection("系统参数")
        self._sec_system.add_row("wavelength", "波长")
        self._sec_system.add_row("power_mw", "发射功率")
        self._sec_system.add_row("D_T", "发射口径")
        self._sec_system.add_row("D_R", "接收口径")
        self._sec_system.add_row("divergence", "发散角")
        self._sec_system.add_row("data_rate", "数据速率")

        # 信道参数
        self._sec_channel = _SummarySection("信道参数")
        self._sec_channel.add_row("distance", "传输距离")
        self._sec_channel.add_row("visibility", "能见度")
        self._sec_channel.add_row("fog_model", "雾模型")
        self._sec_channel.add_row("Cn2", "Cn²")
        self._sec_channel.add_row("rainfall", "降雨量")
        self._sec_channel.add_row("snowfall", "降雪量")

        # 链路分析
        self._sec_link = _SummarySection("链路分析")
        self._sec_link.add_row("atm_loss", "大气衰减")
        self._sec_link.add_row("geo_loss", "几何损耗")
        self._sec_link.add_row("total_loss", "总链路损耗")
        self._sec_link.add_row("P_R", "接收功率")
        self._sec_link.add_row("snr", "SNR")
        self._sec_link.add_row("margin", "链路余量")

        # 湍流分析
        self._sec_turb = _SummarySection("湍流分析")
        self._sec_turb.add_row("sigma_R2", "Rytov 方差")
        self._sec_turb.add_row("regime", "湍流强度")
        self._sec_turb.add_row("sigma_I2", "闪烁指数")
        self._sec_turb.add_row("dist_name", "光强分布")

        # BER
        self._sec_ber = _SummarySection("误码率 (BER)")
        self._sec_ber.add_row("ber_ook_awgn", "OOK — AWGN")
        self._sec_ber.add_row("ber_ook", "OOK — 湍流")
        self._sec_ber.add_row("ber_ppm_awgn", "PPM — AWGN")
        self._sec_ber.add_row("ber_ppm", "PPM — 湍流")
        self._sec_ber.add_row("ber_sim_awgn", "SIM — AWGN")
        self._sec_ber.add_row("ber_sim", "SIM — 湍流")

        # 链路状态
        self._sec_status = _SummarySection("链路状态")
        self._sec_status.add_row("status", "综合评估")

        # 填入网格 (2 列)。固定两列可以在桌面宽度下保持信息密度，同时避免
        # 单列过长导致滚动距离过大。
        g = self.summaryGrid
        g.addWidget(self._sec_system, 0, 0)
        g.addWidget(self._sec_channel, 0, 1)
        g.addWidget(self._sec_link, 1, 0)
        g.addWidget(self._sec_turb, 1, 1)
        g.addWidget(self._sec_ber, 2, 0)
        g.addWidget(self._sec_status, 2, 1)

    # ─────────────────────────────────────────────────────────────────────────
    def update_results(self, params, results, history):
        """
        更新结果显示（外部调用接口保持不变）。

        params 是本次仿真的输入快照，results 是 worker 输出，history 是主窗口
        维护的最近 N 次仿真列表。
        """
        self._history = history
        self._update_summary(params, results)
        self._update_comparison_table(history)

    def _update_summary(self, params, results):
        """
        填充摘要区段。

        这里假定 results 中存在 SimulationWorker 写入的标准键；如果后续模型层
        改名，应优先在 worker 输出处保持兼容，而不是让展示层到处兜底。
        """
        if self._sec_system is None:
            self._build_summary_sections()

        M = results.get("M_ppm", 4)

        # 系统参数
        s = self._sec_system
        s.set_value("wavelength", f"{params['wavelength_nm']:.0f} nm")
        s.set_value("power_mw", f"{params['power_mw']:.2f} mW")
        s.set_value("D_T", f"{params['D_T_cm']:.1f} cm")
        s.set_value("D_R", f"{params['D_R_cm']:.1f} cm")
        s.set_value("divergence", f"{params['divergence_mrad']:.2f} mrad")
        s.set_value("data_rate", f"{params['data_rate_mbps']:.1f} Mbps")

        # 信道参数
        c = self._sec_channel
        c.set_value("distance", f"{params['distance_km']:.2f} km")
        c.set_value("visibility", f"{params['visibility_km']:.2f} km")
        c.set_value("fog_model", params.get("fog_model", "kim"))
        c.set_value("Cn2", f"{params['Cn2']:.2e} m⁻²/³")
        c.set_value("rainfall", f"{params['rainfall_rate']:.1f} mm/h")
        c.set_value("snowfall", f"{params['snowfall_rate']:.1f} mm/h")

        # 链路分析
        lk = self._sec_link
        lk.set_value("atm_loss", f"{results['atm_loss_db']:.4f} dB")
        lk.set_value("geo_loss", f"{results['L_geo_db']:.2f} dB")
        lk.set_value("total_loss", f"{results['total_loss_db']:.2f} dB")
        lk.set_value("P_R", f"{results['P_R_dbm']:.2f} dBm")
        lk.set_value("snr", f"{results['snr_db']:.2f} dB")
        lk.set_highlight("P_R", self._margin_color(results["P_R_dbm"] - params["sensitivity_dbm"]))
        lk.set_highlight("snr", self._snr_color(results["snr_db"]))

        margin = results["margin"]
        lk.set_value("margin", f"{margin:.2f} dB")
        margin_color = self._margin_color(margin)
        lk.set_highlight("margin", margin_color)

        # 湍流
        t = self._sec_turb
        t.set_value("sigma_R2", f"{results['sigma_R2']:.6f}")
        t.set_value("regime", results["regime"])
        t.set_value("sigma_I2", f"{results['sigma_I2']:.6f}")
        t.set_value("dist_name", results["dist_name"])

        # BER
        b = self._sec_ber
        b.set_value("ber_ook_awgn", f"{results['ber_ook_awgn']:.4e}")
        b.set_value("ber_ook", f"{results['ber_ook']:.4e}")
        b.set_value("ber_ppm_awgn", f"{results['ber_ppm_awgn']:.4e}")
        b.set_value("ber_ppm", f"{results['ber_ppm']:.4e}")
        b.set_value("ber_sim_awgn", f"{results['ber_sim_awgn']:.4e}")
        b.set_value("ber_sim", f"{results['ber_sim']:.4e}")
        b.set_highlight("ber_ook", self._ber_color(results["ber_ook"]))
        b.set_highlight("ber_ppm", self._ber_color(results["ber_ppm"]))
        b.set_highlight("ber_sim", self._ber_color(results["ber_sim"]))

        # 链路状态。这里使用链路余量作为综合判断的主指标，阈值与仿真面板
        # 的关键指标卡片保持一致，避免不同页面给出相互矛盾的状态描述。
        if margin > 6:
            status_text = "良好 — 余量充足"
            status_color = theme.SUCCESS
        elif margin > 3:
            status_text = "可用 — 余量较小"
            status_color = theme.PRIMARY
        elif margin > 0:
            status_text = "勉强可用 — 余量不足"
            status_color = theme.WARNING
        else:
            status_text = "不可用 — 低于灵敏度"
            status_color = theme.ERROR

        st = self._sec_status
        st.set_value("status", status_text)
        st.set_highlight("status", status_color)

    @staticmethod
    def _margin_color(margin: float) -> str:
        """链路余量配色，与仿真面板保持一致。"""
        if margin > 6:
            return theme.SUCCESS
        if margin > 3:
            return theme.PRIMARY
        if margin > 0:
            return theme.WARNING
        return theme.ERROR

    @staticmethod
    def _snr_color(snr_db: float) -> str:
        """SNR 配色。"""
        if snr_db > 25:
            return theme.SUCCESS
        if snr_db > 15:
            return theme.PRIMARY
        if snr_db > 8:
            return theme.WARNING
        return theme.ERROR

    @staticmethod
    def _ber_color(ber: float) -> str:
        """BER 配色。"""
        if ber < 1e-9:
            return theme.SUCCESS
        if ber < 1e-6:
            return theme.PRIMARY
        if ber < 1e-3:
            return theme.WARNING
        return theme.ERROR

    # ─────────────────────────────────────────────────────────────────────────
    def _update_comparison_table(self, history):
        """
        更新场景对比表。

        表格每一行对应一次仿真历史记录，列只选取最适合横向比较的指标。
        更完整的参数和结果保存在 self._history 中，供 CSV/文本报告导出。
        """
        if not history:
            return

        columns = [
            "场景",
            "距离(km)",
            "衰减(dB)",
            "P_R(dBm)",
            "SNR(dB)",
            "σ_R²",
            "湍流",
            "BER-OOK",
            "BER-PPM",
            "BER-SIM",
            "余量(dB)",
        ]

        self.compareTable.setSortingEnabled(False)
        self.compareTable.setRowCount(len(history))
        self.compareTable.setColumnCount(len(columns))
        self.compareTable.setHorizontalHeaderLabels(columns)

        for i, record in enumerate(history):
            # history 由 MainWindow 维护，record 结构固定为:
            # {"name": 场景名, "params": 参数字典, "results": 结果字典}
            p = record["params"]
            r = record["results"]
            mg = r["margin"]

            row_data = [
                record["name"],
                f"{p['distance_km']:.2f}",
                f"{r['atm_loss_db']:.2f}",
                f"{r['P_R_dbm']:.2f}",
                f"{r['snr_db']:.2f}",
                f"{r['sigma_R2']:.4f}",
                r["regime"],
                f"{r['ber_ook']:.2e}",
                f"{r['ber_ppm']:.2e}",
                f"{r['ber_sim']:.2e}",
                f"{mg:.2f}",
            ]

            for j, val in enumerate(row_data):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                # 历史表用于展示和复制，不允许在表格中编辑。若用户需要修改参数，
                # 应回到左侧参数面板重新仿真。
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)

                # 余量列着色：绿色表示余量充足，黄色表示勉强可用，红色表示
                # 低于接收灵敏度。颜色只用于辅助阅读，具体数值仍保留。
                if j == len(columns) - 1:
                    if mg > 6:
                        item.setForeground(QColor(theme.SUCCESS))
                    elif mg > 0:
                        item.setForeground(QColor(theme.WARNING))
                    else:
                        item.setForeground(QColor(theme.ERROR))

                self.compareTable.setItem(i, j, item)
        self.compareTable.setSortingEnabled(True)

    # ─────────────────────────────────────────────────────────────────────────
    def clear(self):
        """
        清空历史结果和摘要区段。

        摘要区段是动态创建的 QWidget，清空时需要从 layout 移除并 deleteLater，
        否则下一次构建会在同一网格里叠加旧控件。
        """
        self._history = []
        self.compareTable.setRowCount(0)

        # 重置摘要区段，并恢复“暂无数据”占位提示。
        if self._sec_system is not None:
            for sec in self._summary_sections():
                self.summaryGrid.removeWidget(sec)
                sec.deleteLater()
            self._sec_system = None
            self._sec_channel = None
            self._sec_link = None
            self._sec_turb = None
            self._sec_ber = None
            self._sec_status = None
        self.noDataLabel.setVisible(True)

    # ─────────────────────────────────────────────────────────────────────────
    def _export_csv(self):
        """
        导出历史记录为 CSV。

        使用 utf-8-sig 编码是为了兼容 Excel：带 BOM 的 UTF-8 文件在中文
        Windows/Excel 中更容易被正确识别为 UTF-8，避免中文列名乱码。
        """
        if not self._history:
            QMessageBox.information(self, "提示", "暂无仿真数据可导出")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出 CSV", "fso_results.csv", "CSV 文件 (*.csv)"
        )
        if not filepath:
            return

        headers = [
            "场景",
            "距离(km)",
            "能见度(km)",
            "Cn²(m⁻²/³)",
            "大气衰减(dB)",
            "几何损耗(dB)",
            "总损耗(dB)",
            "接收功率(dBm)",
            "SNR(dB)",
            "σ_R²",
            "湍流强度",
            "σ_I²",
            "BER-OOK(AWGN)",
            "BER-OOK(湍流)",
            "BER-PPM(AWGN)",
            "BER-PPM(湍流)",
            "BER-SIM(AWGN)",
            "BER-SIM(湍流)",
            "链路余量(dB)",
        ]

        try:
            with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for record in self._history:
                    # CSV 保留原始数值而不是全部格式化成字符串，便于后续用
                    # Excel、MATLAB 或 Python 继续做统计分析。
                    p = record["params"]
                    r = record["results"]
                    writer.writerow(
                        [
                            record["name"],
                            p["distance_km"],
                            p["visibility_km"],
                            p["Cn2"],
                            r["atm_loss_db"],
                            r["L_geo_db"],
                            r["total_loss_db"],
                            r["P_R_dbm"],
                            r["snr_db"],
                            r["sigma_R2"],
                            r["regime"],
                            r["sigma_I2"],
                            r["ber_ook_awgn"],
                            r["ber_ook"],
                            r["ber_ppm_awgn"],
                            r["ber_ppm"],
                            r["ber_sim_awgn"],
                            r["ber_sim"],
                            r["margin"],
                        ]
                    )
            QMessageBox.information(self, "导出成功", f"数据已导出到:\n{filepath}")
        except OSError as e:
            QMessageBox.critical(self, "导出失败", f"无法写入文件:\n{e}")

    def _export_report(self):
        """
        导出人类可读的文本报告。

        报告按场景逐段展开，适合直接作为论文/课程设计附录的初稿；若存在
        多个历史场景，末尾额外生成一张简短对比表。
        """
        if not self._history:
            QMessageBox.information(self, "提示", "暂无仿真数据可导出")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出报告", "fso_report.txt", "文本文件 (*.txt)"
        )
        if not filepath:
            return

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                f.write("  无线光通信系统链路特性分析报告\n")
                f.write("  (近地大气信道)\n")
                f.write("=" * 60 + "\n\n")

                for idx, record in enumerate(self._history, 1):
                    # 每个场景独立输出输入参数、链路结果、湍流结果和 BER 对比。
                    # 这里不重新计算，完全使用历史记录中冻结的 params/results。
                    p = record["params"]
                    r = record["results"]
                    M = r.get("M_ppm", 4)

                    f.write(f"\n{'─' * 50}\n")
                    f.write(f"  场景 {idx}: {record['name']}\n")
                    f.write(f"{'─' * 50}\n\n")

                    f.write("  系统参数:\n")
                    f.write(f"    波长 = {p['wavelength_nm']:.0f} nm\n")
                    f.write(f"    发射功率 = {p['power_mw']:.2f} mW\n")
                    f.write(f"    发射/接收口径 = {p['D_T_cm']:.1f}/{p['D_R_cm']:.1f} cm\n")
                    f.write(f"    发散角 = {p['divergence_mrad']:.2f} mrad\n")
                    f.write(f"    数据速率 = {p['data_rate_mbps']:.1f} Mbps\n\n")

                    f.write("  信道参数:\n")
                    f.write(f"    传输距离 = {p['distance_km']:.2f} km\n")
                    f.write(f"    能见度 = {p['visibility_km']:.2f} km\n")
                    f.write(f"    雾模型 = {p.get('fog_model', 'kim')}\n")
                    f.write(f"    Cn² = {p['Cn2']:.2e} m⁻²/³\n\n")

                    f.write("  链路分析结果:\n")
                    f.write(f"    大气衰减 = {r['atm_loss_db']:.4f} dB\n")
                    f.write(f"    几何损耗 = {r['L_geo_db']:.2f} dB\n")
                    f.write(f"    接收功率 = {r['P_R_dbm']:.2f} dBm\n")
                    f.write(f"    SNR = {r['snr_db']:.2f} dB\n")
                    f.write(f"    链路余量 = {r['margin']:.2f} dB\n\n")

                    f.write("  湍流分析:\n")
                    f.write(f"    Rytov 方差 = {r['sigma_R2']:.6f}\n")
                    f.write(f"    湍流强度 = {r['regime']}\n")
                    f.write(f"    闪烁指数 = {r['sigma_I2']:.6f}\n")
                    f.write(f"    光强分布 = {r['dist_name']}\n\n")

                    f.write("  误码率:\n")
                    f.write(f"    {'':15} {'AWGN':>12}  {'湍流信道':>12}\n")
                    f.write(
                        f"    {'OOK':15} {r['ber_ook_awgn']:12.4e}  {r['ber_ook']:12.4e}\n"
                    )
                    f.write(
                        f"    {f'{M}-PPM':15} {r['ber_ppm_awgn']:12.4e}  {r['ber_ppm']:12.4e}\n"
                    )
                    f.write(
                        f"    {'SIM-BPSK':15} {r['ber_sim_awgn']:12.4e}  {r['ber_sim']:12.4e}\n"
                    )

                if len(self._history) > 1:
                    # 多场景总结只保留最关键的工程指标，便于快速比较天气或距离
                    # 变化对链路可用性的影响。
                    f.write(f"\n\n{'=' * 60}\n  场景对比总结\n{'=' * 60}\n\n")
                    f.write(
                        f"  {'场景':>6} | {'衰减(dB)':>8} | {'P_R(dBm)':>9} |"
                        f" {'BER-OOK':>10} | {'余量(dB)':>8}\n"
                    )
                    f.write(f"  {'-' * 60}\n")
                    for record in self._history:
                        r = record["results"]
                        f.write(
                            f"  {record['name']:>6} | {r['atm_loss_db']:8.2f} |"
                            f" {r['P_R_dbm']:9.2f} | {r['ber_ook']:10.2e} |"
                            f" {r['margin']:8.2f}\n"
                        )

            QMessageBox.information(self, "导出成功", f"报告已导出到:\n{filepath}")
        except OSError as e:
            QMessageBox.critical(self, "导出失败", f"无法写入文件:\n{e}")
