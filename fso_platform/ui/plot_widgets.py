"""
数据可视化面板
Matplotlib 嵌入 PyQt5，展示多种 FSO 链路特性图表

图表:
1. 大气透过率/衰减 vs 距离
2. 闪烁指数 vs 距离
3. 接收功率 vs 距离
4. 噪声分析饼图
5. BER vs SNR (AWGN 信道)
6. BER vs SNR (湍流信道)
7. 光强概率密度分布 (三种分布对比)
"""

from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QSizePolicy,
    QTabWidget,
    QFrame,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5 import uic

import numpy as np
import matplotlib

matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from fso_platform.utils.fonts import MPL_CJK_FONTS
from fso_platform.ui import theme

# ── Matplotlib 全局配置 ───────────────────────────────────────────────────────
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = MPL_CJK_FONTS
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.alpha"] = 0.25
plt.rcParams["grid.linestyle"] = "--"

# 主题色
_C_PRIMARY = theme.PRIMARY  # "#1565C0"
_C_SUCCESS = theme.SUCCESS  # "#2E7D32"
_C_WARNING = theme.WARNING  # "#E65100"
_C_ERROR = theme.ERROR  # "#C62828"
_C_NEUTRAL = theme.NEUTRAL  # "#546E7A"
_C_BG = "#FAFBFC"
_C_GRID = "#DDE3EC"


class MplCanvas(FigureCanvas):
    """Matplotlib 画布基类"""

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, tight_layout=True)
        self.fig.patch.set_facecolor(_C_BG)
        super().__init__(self.fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(f"background-color: {_C_BG}; border: none;")

    def close_figure(self):
        """释放 Matplotlib Figure 占用的 C 级资源"""
        import matplotlib.pyplot as plt

        plt.close(self.fig)

    def _styled_ax(self):
        """返回一个已应用主题样式的 Axes"""
        ax = self.fig.add_subplot(111)
        ax.set_facecolor(_C_BG)
        for spine in ax.spines.values():
            spine.set_edgecolor(_C_GRID)
        ax.tick_params(colors=theme.TEXT_SECONDARY, labelsize=9)
        ax.xaxis.label.set_color(theme.TEXT_SECONDARY)
        ax.yaxis.label.set_color(theme.TEXT_SECONDARY)
        ax.title.set_color(theme.TEXT_PRIMARY)
        return ax


class PlotPanel(QWidget):
    """数据可视化面板"""

    def __init__(self):
        super().__init__()

        # 加载 UI 文件
        ui_path = Path(__file__).parent / "plot_widgets.ui"
        uic.loadUi(ui_path, self)

        self._init_ui()

    # ─────────────────────────────────────────────────────────────────────────
    def _init_ui(self):
        """初始化 Matplotlib 画布"""
        # 应用按钮样式
        self.btnSaveAll.setStyleSheet(theme.RESET_BTN_STYLE)
        self.btnSaveAll.clicked.connect(self._save_all_plots)

        # 应用 Tab 样式，并禁止文字省略（防止 CJK 字符被裁剪）
        self.plotTabs.setStyleSheet(theme.TAB_STYLE)
        self.plotTabs.tabBar().setElideMode(Qt.ElideNone)

        # ── Tab 1: 链路特性 (2x2 网格) ──────────────────────────────────────
        link_grid = QGridLayout(self.linkContainer)
        link_grid.setContentsMargins(4, 4, 4, 4)
        link_grid.setSpacing(4)

        self.canvas_atm = MplCanvas(self.linkContainer, width=4, height=3, dpi=90)
        self.canvas_scint = MplCanvas(self.linkContainer, width=4, height=3, dpi=90)
        self.canvas_power = MplCanvas(self.linkContainer, width=4, height=3, dpi=90)
        self.canvas_noise = MplCanvas(self.linkContainer, width=4.5, height=3, dpi=90)

        link_grid.addWidget(self._wrap(self.canvas_atm), 0, 0)
        link_grid.addWidget(self._wrap(self.canvas_scint), 0, 1)
        link_grid.addWidget(self._wrap(self.canvas_power), 1, 0)
        link_grid.addWidget(self._wrap(self.canvas_noise), 1, 1)

        # ── Tab 2: 误码率分析 (1x2) ─────────────────────────────────────────
        ber_grid = QGridLayout(self.berContainer)
        ber_grid.setContentsMargins(4, 4, 4, 4)
        ber_grid.setSpacing(4)

        self.canvas_ber = MplCanvas(self.berContainer, width=6, height=4, dpi=90)
        self.canvas_ber_turb = MplCanvas(self.berContainer, width=6, height=4, dpi=90)

        ber_grid.addWidget(self._wrap(self.canvas_ber), 0, 0)
        ber_grid.addWidget(self._wrap(self.canvas_ber_turb), 0, 1)

        # ── Tab 3: 光强分布 (1x1) ───────────────────────────────────────────
        dist_layout = QVBoxLayout(self.distContainer)
        dist_layout.setContentsMargins(4, 4, 4, 4)

        self.canvas_dist = MplCanvas(self.distContainer, width=8, height=5, dpi=90)
        dist_layout.addWidget(self._wrap(self.canvas_dist))

        # ── Tab 4: 链路预算瀑布图 (1x1) ─────────────────────────────────────
        budget_layout = QVBoxLayout(self.budgetContainer)
        budget_layout.setContentsMargins(4, 4, 4, 4)

        self.canvas_budget = MplCanvas(self.budgetContainer, width=8, height=5, dpi=90)
        budget_layout.addWidget(self._wrap(self.canvas_budget))

        # 画初始空图
        self._draw_empty()

    def cleanup(self):
        """释放所有 Matplotlib Figure 资源"""
        for canvas in [
            self.canvas_atm,
            self.canvas_scint,
            self.canvas_power,
            self.canvas_noise,
            self.canvas_ber,
            self.canvas_ber_turb,
            self.canvas_dist,
            self.canvas_budget,
        ]:
            canvas.close_figure()

    # ─── 辅助 ─────────────────────────────────────────────────────────────────
    @staticmethod
    def _wrap(canvas: MplCanvas) -> QFrame:
        """将画布包在带圆角边框的 QFrame 中"""
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background-color: {_C_BG}; border: 1px solid {theme.BORDER_LIGHT};"
            f" border-radius: 6px; }}"
        )
        v = QVBoxLayout(frame)
        v.setContentsMargins(2, 2, 2, 2)
        v.addWidget(canvas)
        return frame

    @staticmethod
    def _apply_grid(ax):
        ax.grid(True, which="major", linestyle="--", alpha=0.25, color=_C_GRID)

    # ─────────────────────────────────────────────────────────────────────────
    def _draw_empty(self):
        """画空白占位图"""
        pairs = [
            (self.canvas_atm, "大气衰减 vs 距离"),
            (self.canvas_scint, "闪烁指数 vs 距离"),
            (self.canvas_power, "接收功率 vs 距离"),
            (self.canvas_noise, "噪声分析"),
            (self.canvas_ber, "BER vs SNR (AWGN)"),
            (self.canvas_ber_turb, "BER vs SNR (湍流)"),
            (self.canvas_dist, "光强概率密度分布"),
            (self.canvas_budget, "链路预算瀑布图"),
        ]
        for canvas, title in pairs:
            ax = canvas._styled_ax()
            ax.set_title(title, fontsize=12, fontweight="bold", pad=8)
            ax.text(
                0.5,
                0.5,
                "等待仿真数据…",
                ha="center",
                va="center",
                transform=ax.transAxes,
                fontsize=12,
                color=theme.TEXT_DIM,
            )
            ax.set_xticks([])
            ax.set_yticks([])
            canvas.draw()

    # ─────────────────────────────────────────────────────────────────────────
    def update_plots(self, params, results):
        """根据仿真结果更新所有图表"""
        self._plot_atm(params, results)
        self._plot_scintillation(params, results)
        self._plot_power(params, results)
        self._plot_noise(params, results)
        self._plot_ber_awgn(params, results)
        self._plot_ber_turbulence(params, results)
        self._plot_distributions(params, results)
        self._plot_waterfall(params, results)

    # ─────────────────────────────────────────────────────────────────────────
    def _plot_atm(self, params, results):
        """大气衰减 vs 距离"""
        self.canvas_atm.fig.clear()
        ax = self.canvas_atm._styled_ax()

        dist = results["dist_range_km"]
        loss = results["atm_loss_curve"]

        ax.plot(dist, loss, color=_C_PRIMARY, linewidth=2)
        ax.axhline(
            y=results["atm_loss_db"],
            color=_C_ERROR,
            linestyle="--",
            alpha=0.75,
            linewidth=1.2,
            label=f"当前: {results['atm_loss_db']:.2f} dB @ {params['distance_km']}km",
        )
        ax.axvline(x=params["distance_km"], color=_C_ERROR, linestyle=":", alpha=0.5)

        ax.set_xlabel("传输距离 (km)", fontsize=10)
        ax.set_ylabel("大气衰减 (dB)", fontsize=10)
        ax.set_title(
            f"大气衰减 vs 距离  (V={params['visibility_km']}km, λ={params['wavelength_nm']:.0f}nm)",
            fontsize=12,
            fontweight="bold",
            pad=6,
        )
        ax.legend(fontsize=9)
        self._apply_grid(ax)
        self.canvas_atm.draw()

    def _plot_scintillation(self, params, results):
        """闪烁指数 vs 距离"""
        self.canvas_scint.fig.clear()
        ax = self.canvas_scint._styled_ax()

        dist = results["dist_range_km"]
        si2 = results["sigma_I2_curve"]

        ax.plot(dist, si2, color=_C_WARNING, linewidth=2)
        ax.axhline(
            y=1.0,
            color=_C_NEUTRAL,
            linestyle="--",
            alpha=0.5,
            linewidth=1,
            label="饱和值 σ_I²=1",
        )
        ax.axhline(
            y=results["sigma_I2"],
            color=_C_PRIMARY,
            linestyle="--",
            alpha=0.7,
            linewidth=1.2,
            label=f"当前: {results['sigma_I2']:.4f}",
        )
        ax.axvline(x=params["distance_km"], color=_C_PRIMARY, linestyle=":", alpha=0.5)

        ax.set_xlabel("传输距离 (km)", fontsize=10)
        ax.set_ylabel("闪烁指数 σ_I²", fontsize=10)
        ax.set_title(
            f"闪烁指数 vs 距离  (Cn²={params['Cn2']:.1e})",
            fontsize=12,
            fontweight="bold",
            pad=6,
        )
        ax.legend(fontsize=9)
        self._apply_grid(ax)
        self.canvas_scint.draw()

    def _plot_power(self, params, results):
        """接收功率 vs 距离"""
        self.canvas_power.fig.clear()
        ax = self.canvas_power._styled_ax()

        dist = results["dist_range_km"]
        power = results["P_R_curve"]

        ax.plot(dist, power, color=_C_SUCCESS, linewidth=2)
        ax.axhline(
            y=params["sensitivity_dbm"],
            color=_C_ERROR,
            linestyle="--",
            linewidth=1.2,
            label=f"灵敏度: {params['sensitivity_dbm']} dBm",
        )
        ax.axhline(
            y=results["P_R_dbm"],
            color=_C_PRIMARY,
            linestyle="--",
            alpha=0.7,
            linewidth=1.2,
            label=f"当前: {results['P_R_dbm']:.2f} dBm",
        )

        ax.set_xlabel("传输距离 (km)", fontsize=10)
        ax.set_ylabel("接收功率 (dBm)", fontsize=10)
        ax.set_title("接收功率 vs 距离", fontsize=12, fontweight="bold", pad=6)
        ax.legend(fontsize=9)
        self._apply_grid(ax)
        self.canvas_power.draw()

    def _plot_noise(self, params, results):
        """噪声分析饼图"""
        self.canvas_noise.fig.clear()
        ax = self.canvas_noise.fig.add_subplot(111)
        ax.set_facecolor(_C_BG)
        ax.title.set_color(theme.TEXT_PRIMARY)

        n_th = results["noise_thermal"]
        n_sh = results["noise_shot"]
        total = n_th + n_sh

        if total > 0:
            sizes = [n_th / total * 100, n_sh / total * 100]
            labels = [
                f"热噪声  {n_th:.2e} A² ({sizes[0]:.1f}%)",
                f"散粒噪声  {n_sh:.2e} A² ({sizes[1]:.1f}%)",
            ]
            wedge_colors = [_C_WARNING, _C_PRIMARY]
            wedges, _ = ax.pie(
                sizes,
                labels=None,
                colors=wedge_colors,
                startangle=90,
                wedgeprops={"linewidth": 1, "edgecolor": _C_BG},
            )
            ax.legend(
                wedges,
                labels,
                loc="center left",
                bbox_to_anchor=(1.05, 0.5),
                fontsize=9,
                frameon=False,
            )
            ax.set_title("噪声功率组成", fontsize=12, fontweight="bold", pad=6)
        else:
            ax.text(
                0.5,
                0.5,
                "无噪声数据",
                ha="center",
                va="center",
                transform=ax.transAxes,
                color=theme.TEXT_DIM,
            )

        self.canvas_noise.draw()

    def _plot_ber_awgn(self, params, results):
        """BER vs SNR — AWGN 信道"""
        self.canvas_ber.fig.clear()
        ax = self.canvas_ber._styled_ax()

        snr_db = results["snr_db_range"]
        M = results.get("M_ppm", 4)

        ax.semilogy(
            snr_db, results["ber_ook_curve"], color=_C_PRIMARY, linewidth=2, label="OOK"
        )
        ax.semilogy(
            snr_db,
            results["ber_ppm_curve"],
            color=_C_WARNING,
            linewidth=2,
            label=f"{M}-PPM",
        )
        ax.semilogy(
            snr_db,
            results["ber_sim_curve"],
            color=_C_SUCCESS,
            linewidth=2,
            label="SIM-BPSK",
        )

        if results["snr_db"] > 0:
            ax.axvline(
                x=results["snr_db"],
                color=_C_NEUTRAL,
                linestyle=":",
                alpha=0.6,
                label=f"当前 SNR={results['snr_db']:.1f} dB",
            )

        ax.axhline(y=1e-9, color=_C_NEUTRAL, linestyle="--", alpha=0.3, linewidth=1)
        ax.text(1, 1.5e-9, "BER=10⁻⁹", fontsize=9, color=_C_NEUTRAL)

        ax.set_xlabel("SNR (dB)", fontsize=10)
        ax.set_ylabel("误码率 (BER)", fontsize=10)
        ax.set_title(
            "BER vs SNR — AWGN 信道 (无湍流)", fontsize=12, fontweight="bold", pad=6
        )
        ax.set_ylim(1e-15, 1)
        ax.set_xlim(0, 40)
        ax.legend(fontsize=9)
        ax.grid(True, which="both", linestyle="--", alpha=0.2, color=_C_GRID)
        self.canvas_ber.draw()

    def _plot_ber_turbulence(self, params, results):
        """BER vs SNR — 湍流信道"""
        self.canvas_ber_turb.fig.clear()
        ax = self.canvas_ber_turb._styled_ax()

        snr_db = results["snr_db_range"]
        M = results.get("M_ppm", 4)
        sr2 = results["sigma_R2"]

        # AWGN 虚线 (参考)
        ax.semilogy(
            snr_db,
            results["ber_ook_curve"],
            color=_C_PRIMARY,
            linestyle="--",
            alpha=0.35,
            linewidth=1.2,
        )
        ax.semilogy(
            snr_db,
            results["ber_ppm_curve"],
            color=_C_WARNING,
            linestyle="--",
            alpha=0.35,
            linewidth=1.2,
        )
        ax.semilogy(
            snr_db,
            results["ber_sim_curve"],
            color=_C_SUCCESS,
            linestyle="--",
            alpha=0.35,
            linewidth=1.2,
            label="─ ─  AWGN (参考)",
        )

        # 湍流实线
        ax.semilogy(
            snr_db,
            results["ber_ook_turb_curve"],
            color=_C_PRIMARY,
            linewidth=2,
            label=f"OOK  (σ_R²={sr2:.3f})",
        )
        ax.semilogy(
            snr_db,
            results["ber_ppm_turb_curve"],
            color=_C_WARNING,
            linewidth=2,
            label=f"{M}-PPM (σ_R²={sr2:.3f})",
        )
        ax.semilogy(
            snr_db,
            results["ber_sim_turb_curve"],
            color=_C_SUCCESS,
            linewidth=2,
            label=f"SIM  (σ_R²={sr2:.3f})",
        )

        if results["snr_db"] > 0:
            ax.axvline(x=results["snr_db"], color=_C_NEUTRAL, linestyle=":", alpha=0.5)
        ax.axhline(y=1e-9, color=_C_NEUTRAL, linestyle="--", alpha=0.3, linewidth=1)

        ax.set_xlabel("SNR (dB)", fontsize=10)
        ax.set_ylabel("误码率 (BER)", fontsize=10)
        ax.set_title(
            f"BER vs SNR — 湍流信道 ({results['regime']})",
            fontsize=12,
            fontweight="bold",
            pad=6,
        )
        ax.set_ylim(1e-12, 1)
        ax.set_xlim(0, 40)
        ax.legend(fontsize=9, loc="lower left")
        ax.grid(True, which="both", linestyle="--", alpha=0.2, color=_C_GRID)
        self.canvas_ber_turb.draw()

    def _plot_distributions(self, params, results):
        """光强概率密度分布"""
        self.canvas_dist.fig.clear()
        ax = self.canvas_dist._styled_ax()

        I = results["I_range"]
        sigma_R2 = results["sigma_R2"]

        ax.plot(
            I,
            results["pdf_lognormal"],
            color=_C_PRIMARY,
            linewidth=2,
            label=f"对数正态 (弱湍流, σ_R²={max(sigma_R2, 0.05):.3f})",
        )

        if np.any(results["pdf_gamma_gamma"] > 0):
            ax.plot(
                I,
                results["pdf_gamma_gamma"],
                color=_C_WARNING,
                linewidth=2,
                label=f"Gamma-Gamma (α={results['gg_alpha']:.2f}, β={results['gg_beta']:.2f})",
            )

        ax.plot(
            I,
            results["pdf_neg_exp"],
            color=_C_SUCCESS,
            linewidth=2,
            label="负指数 (饱和湍流)",
        )

        ax.set_xlabel("归一化光强 I/<I>", fontsize=10)
        ax.set_ylabel("概率密度 f(I)", fontsize=10)
        ax.set_title(
            f"接收光强概率密度分布 — 当前: {results['dist_name']}",
            fontsize=12,
            fontweight="bold",
            pad=6,
        )
        ax.legend(fontsize=9)
        self._apply_grid(ax)
        ax.set_xlim(0, 5)
        self.canvas_dist.draw()

    def _plot_waterfall(self, params, results):
        """链路预算瀑布图 (Waterfall Chart)

        从发射功率出发，逐级显示各损耗项，最终到达接收功率，
        并标注接收机灵敏度线与链路余量区间。
        """
        from fso_platform.utils.constants import watt_to_dbm

        self.canvas_budget.fig.clear()
        ax = self.canvas_budget.fig.add_subplot(111)
        ax.set_facecolor(_C_BG)
        for spine in ax.spines.values():
            spine.set_edgecolor(_C_GRID)
        ax.tick_params(colors=theme.TEXT_SECONDARY, labelsize=9)
        ax.xaxis.label.set_color(theme.TEXT_SECONDARY)
        ax.yaxis.label.set_color(theme.TEXT_SECONDARY)
        ax.title.set_color(theme.TEXT_PRIMARY)

        # ── 收集各功率/损耗数据 ──────────────────────────────────────────────
        P_T_dbm = watt_to_dbm(params["power_w"])
        atm_db = results["atm_loss_db"]  # 大气衰减 (正值)
        geo_db = abs(results["L_geo_db"])  # 几何损耗 (取正值)
        opt_db = results.get("opt_loss_db", 0.0)  # 光学效率损耗
        pnt_db = results.get("L_point_db", 0.0)  # 指向误差损耗 (由仿真计算)
        P_R_dbm = results["P_R_dbm"]
        sens = params["sensitivity_dbm"]
        margin = results["margin"]

        # ── 瀑布各条 ─────────────────────────────────────────────────────────
        # 每条 bar 用 (bottom, height) 表示：
        #   "向下" 损耗条 → height = -loss，bottom = 前一级电平
        #   "电平" 条     → height = 值，bottom = 0（从 y=0 起画，但用 y 轴偏移显示）
        # 为直观显示，以 P_T_dbm 为基准，y 轴显示绝对 dBm 值。

        labels = [
            "发射功率\nP_T",
            "大气\n衰减",
            "几何\n损耗",
            "光学\n损耗",
            "指向误差",
            "接收功率\nP_R",
        ]
        x_pos = list(range(len(labels)))

        # 累计电平（从 P_T 开始逐步下降）
        levels = [
            P_T_dbm,
            P_T_dbm - atm_db,
            P_T_dbm - atm_db - geo_db,
            P_T_dbm - atm_db - geo_db - opt_db,
            P_T_dbm - atm_db - geo_db - opt_db - pnt_db,
            P_R_dbm,  # 应等于上一级（允许微小浮点差异）
        ]

        # bar 颜色：功率电平=蓝，损耗=红/橙系列，接收=绿
        bar_colors = [
            _C_PRIMARY,  # P_T — 蓝
            _C_ERROR,  # 大气衰减 — 红
            "#E65100",  # 几何损耗 — 深橙
            "#F57C00",  # 光学损耗 — 橙
            "#FB8C00",  # 指向误差 — 浅橙
            _C_SUCCESS,  # P_R — 绿
        ]

        # 绘制：P_T 和 P_R 为实心柱（从 sens 底部往上）
        # 损耗条从 levels[i] 向下延伸 loss_i dBm
        y_min_display = min(sens - 6, P_R_dbm - 4)

        for i, (label, color) in enumerate(zip(labels, bar_colors)):
            if i == 0:
                # 发射功率：从 y_min_display 到 P_T_dbm
                bottom = y_min_display
                height = P_T_dbm - y_min_display
                ax.bar(
                    i,
                    height,
                    bottom=bottom,
                    color=color,
                    alpha=0.85,
                    width=0.55,
                    zorder=3,
                )
            elif i == len(labels) - 1:
                # 接收功率：从 y_min_display 到 P_R_dbm
                bottom = y_min_display
                height = P_R_dbm - y_min_display
                ax.bar(
                    i,
                    height,
                    bottom=bottom,
                    color=color,
                    alpha=0.85,
                    width=0.55,
                    zorder=3,
                )
            else:
                # 损耗条：从上一级电平 向下 loss
                top = levels[i - 1]
                bottom = levels[i]
                height = top - bottom  # 正值
                ax.bar(
                    i,
                    -height,
                    bottom=top,
                    color=color,
                    alpha=0.82,
                    width=0.55,
                    zorder=3,
                )
                # 连接线（从上一条右端到本条左端）
                ax.plot(
                    [i - 0.5, i - 0.275],
                    [bottom, bottom],
                    color=theme.TEXT_SECONDARY,
                    linewidth=0.8,
                    linestyle="--",
                    alpha=0.5,
                    zorder=4,
                )

        # 各条顶端数值标注
        value_labels = [
            f"{P_T_dbm:.1f} dBm",
            f"−{atm_db:.1f} dB",
            f"−{geo_db:.1f} dB",
            f"−{opt_db:.1f} dB",
            f"−{pnt_db:.1f} dB",
            f"{P_R_dbm:.1f} dBm",
        ]
        for i, txt in enumerate(value_labels):
            if i == 0:
                y_txt = P_T_dbm + 0.5
            elif i == len(labels) - 1:
                y_txt = P_R_dbm + 0.5
            else:
                y_txt = levels[i - 1] + 0.5  # 顶端上方
            ax.text(
                i,
                y_txt,
                txt,
                ha="center",
                va="bottom",
                fontsize=8.5,
                color=theme.TEXT_PRIMARY,
                zorder=5,
                fontweight="bold" if i in (0, len(labels) - 1) else "normal",
            )

        # ── 灵敏度线 ─────────────────────────────────────────────────────────
        ax.axhline(
            y=sens,
            color=_C_ERROR,
            linestyle="--",
            linewidth=1.5,
            alpha=0.75,
            zorder=2,
            label=f"接收机灵敏度  {sens:.1f} dBm",
        )

        # ── 链路余量阴影区 ────────────────────────────────────────────────────
        if P_R_dbm > sens:
            ax.axhspan(sens, P_R_dbm, alpha=0.10, color=_C_SUCCESS, zorder=1)
            # 余量标注（在最后一条右侧）
            ax.annotate(
                "",
                xy=(len(labels) - 0.5, P_R_dbm),
                xytext=(len(labels) - 0.5, sens),
                arrowprops=dict(arrowstyle="<->", color=_C_SUCCESS, lw=1.5),
                zorder=5,
            )
            ax.text(
                len(labels) - 0.3,
                (P_R_dbm + sens) / 2,
                f"余量\n{margin:.1f} dB",
                ha="left",
                va="center",
                fontsize=8.5,
                color=_C_SUCCESS,
                fontweight="bold",
                zorder=5,
            )

        # ── 轴设置 ────────────────────────────────────────────────────────────
        ax.set_xticks(x_pos)
        ax.set_xticklabels(labels, fontsize=9)
        ax.set_ylabel("功率电平 (dBm)", fontsize=10)
        ax.set_title(
            f"链路预算瀑布图  (距离={params['distance_km']} km, "
            f"λ={params['wavelength_nm']:.0f} nm)",
            fontsize=12,
            fontweight="bold",
            pad=8,
        )
        ax.set_xlim(-0.6, len(labels) - 0.3)
        y_top = P_T_dbm + 4
        ax.set_ylim(y_min_display - 2, y_top)
        ax.legend(fontsize=9, loc="upper right")
        ax.grid(True, axis="y", linestyle="--", alpha=0.25, color=_C_GRID)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        self.canvas_budget.draw()

    # ─────────────────────────────────────────────────────────────────────────
    def _save_all_plots(self):
        """保存所有图表"""
        directory = QFileDialog.getExistingDirectory(self, "选择保存目录")
        if not directory:
            return

        canvases = {
            "atmospheric_attenuation": self.canvas_atm,
            "scintillation_index": self.canvas_scint,
            "received_power": self.canvas_power,
            "noise_analysis": self.canvas_noise,
            "ber_awgn": self.canvas_ber,
            "ber_turbulence": self.canvas_ber_turb,
            "intensity_distribution": self.canvas_dist,
            "link_budget_waterfall": self.canvas_budget,
        }

        for name, canvas in canvases.items():
            filepath = f"{directory}/{name}.png"
            canvas.fig.savefig(filepath, dpi=150, bbox_inches="tight", facecolor=_C_BG)
