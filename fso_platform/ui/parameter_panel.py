"""
参数配置面板 — 左侧固定宽度侧边栏
包含: 预设场景选择、可折叠参数分组、开始仿真按钮

计算逻辑不在此模块，仅负责参数输入与校验。
信号接口与原版保持完全兼容。
"""

from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QComboBox,
    QPushButton,
    QDoubleSpinBox,
    QSpinBox,
    QMessageBox,
    QScrollArea,
    QFrame,
    QToolButton,
    QSizePolicy,
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont, QColor
from PyQt5 import uic

from .theme import (
    BG_SIDEBAR,
    BG_CARD,
    BG_SECTION,
    BORDER,
    BORDER_LIGHT,
    PRIMARY,
    PRIMARY_LIGHT,
    PRIMARY_DARK,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_WHITE,
    RUN_BTN_STYLE,
    RESET_BTN_STYLE,
    INPUT_STYLE,
    SCROLLAREA_STYLE,
)
from fso_platform.utils.fonts import (
    FONT_FAMILY,
    FONT_MONO,
    FONT_SIZE_XS,
    FONT_SIZE_SM,
    FONT_SIZE_MD,
)


# ─── 预设场景 ──────────────────────────────────────────────────────
PRESET_SCENARIOS = {
    "自定义": {},
    "晴天": {
        "visibility": 23.0,
        "Cn2_exp": -15,
        "Cn2_coeff": 1.0,
        "rainfall": 0.0,
        "snowfall": 0.0,
        "snow_type": "湿雪",
    },
    "薄雾": {
        "visibility": 2.0,
        "Cn2_exp": -14,
        "Cn2_coeff": 5.0,
        "rainfall": 0.0,
        "snowfall": 0.0,
        "snow_type": "湿雪",
    },
    "浓雾": {
        "visibility": 0.5,
        "Cn2_exp": -13,
        "Cn2_coeff": 1.0,
        "rainfall": 0.0,
        "snowfall": 0.0,
        "snow_type": "湿雪",
    },
    "中雨": {
        "visibility": 5.0,
        "Cn2_exp": -14,
        "Cn2_coeff": 5.0,
        "rainfall": 10.0,
        "snowfall": 0.0,
        "snow_type": "湿雪",
    },
    "大雨": {
        "visibility": 2.0,
        "Cn2_exp": -14,
        "Cn2_coeff": 5.0,
        "rainfall": 25.0,
        "snowfall": 0.0,
        "snow_type": "湿雪",
    },
    "雪天": {
        "visibility": 1.0,
        "Cn2_exp": -13,
        "Cn2_coeff": 1.0,
        "rainfall": 0.0,
        "snowfall": 5.0,
        "snow_type": "湿雪",
    },
}

# 场景对应的小标签颜色（供 ComboBox 条目使用）
SCENARIO_COLORS = {
    "晴天": "#2E7D32",
    "薄雾": "#1565C0",
    "浓雾": "#546E7A",
    "中雨": "#1565C0",
    "大雨": "#C62828",
    "雪天": "#546E7A",
    "自定义": "#9E9E9E",
}


# ─── 可折叠区段组件 ────────────────────────────────────────────────
class _CollapsibleSection(QWidget):
    """带折叠/展开的参数分组区段"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 4)
        outer.setSpacing(0)

        # 标题按钮
        self.toggle = QToolButton()
        self.toggle.setText(f"  {title}")
        self.toggle.setCheckable(True)
        self.toggle.setChecked(True)
        self.toggle.setArrowType(Qt.DownArrow)
        self.toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.toggle.setMinimumHeight(28)
        self.toggle.setStyleSheet(
            f"""
            QToolButton {{
                font-family: "{FONT_FAMILY}";
                font-size: {FONT_SIZE_MD}px;
                font-weight: bold;
                color: {TEXT_PRIMARY};
                background-color: {BG_SECTION};
                border: none;
                border-radius: 5px;
                padding: 0 8px;
                text-align: left;
            }}
            QToolButton:hover {{
                background-color: {PRIMARY_LIGHT};
                color: {PRIMARY};
            }}
            """
        )
        self.toggle.clicked.connect(self._on_toggle)
        outer.addWidget(self.toggle)

        # 内容容器
        self.content = QFrame()
        self.content.setStyleSheet(
            f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_LIGHT};
                border-radius: 0 0 5px 5px;
            }}
            """
        )
        self.content_layout = QGridLayout(self.content)
        self.content_layout.setContentsMargins(8, 4, 8, 6)
        self.content_layout.setSpacing(4)
        self.content_layout.setColumnStretch(1, 1)
        outer.addWidget(self.content)

    def _on_toggle(self, checked: bool):
        self.content.setVisible(checked)
        self.toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)

    def add_row(self, row: int, label_text: str, widget: QWidget, range_hint: str = ""):
        lbl = QLabel(label_text)
        lbl.setStyleSheet(
            f"font-family: '{FONT_FAMILY}'; font-size: {FONT_SIZE_SM}px; "
            f"color: {TEXT_SECONDARY}; background: transparent; border: none;"
        )
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        # 每个参数占两个 grid 行：偶数行为控件，奇数行为范围提示
        grid_row = row * 2
        self.content_layout.addWidget(lbl, grid_row, 0)
        self.content_layout.addWidget(widget, grid_row, 1)
        if range_hint:
            hint_lbl = QLabel(range_hint)
            hint_lbl.setStyleSheet(
                f"font-family: '{FONT_FAMILY}'; font-size: {FONT_SIZE_XS}px; "
                f"color: {TEXT_SECONDARY}; background: transparent; border: none; "
                f"padding-bottom: 2px;"
            )
            hint_lbl.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            self.content_layout.addWidget(hint_lbl, grid_row + 1, 1)
            # 存储引用供显隐控制使用
            widget._range_hint_label = hint_lbl


# ─── 主参数面板 ────────────────────────────────────────────────────
class ParameterPanel(QWidget):
    """左侧参数配置侧边栏"""

    params_changed = pyqtSignal(dict)
    run_requested = pyqtSignal()
    cancel_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._running = False

        # 加载 UI 文件
        ui_path = Path(__file__).parent / "parameter_panel.ui"
        uic.loadUi(ui_path, self)

        # 应用样式和输入控件样式
        self.setStyleSheet(self.styleSheet() + "\n" + INPUT_STYLE)
        self.scrollArea.setStyleSheet(SCROLLAREA_STYLE)
        self.btnRun.setStyleSheet(RUN_BTN_STYLE)
        self.btnReset.setStyleSheet(RESET_BTN_STYLE)

        # 创建三个折叠区段
        self._sec_sys = _CollapsibleSection("系统参数")
        self._sec_ch = _CollapsibleSection("信道参数")
        self._sec_det = _CollapsibleSection("探测器参数")

        # 移除占位符 spacer，添加参数区段
        # 注意：uic.loadUi() 不会将 .ui 文件中的 spacer 暴露为属性，需要遍历布局查找
        for i in range(self.paramsLayout.count() - 1, -1, -1):
            item = self.paramsLayout.itemAt(i)
            if item and item.spacerItem() is not None:
                self.paramsLayout.removeItem(item)
                break

        self.paramsLayout.addWidget(self._sec_sys)
        self.paramsLayout.addWidget(self._sec_ch)
        self.paramsLayout.addWidget(self._sec_det)
        self.paramsLayout.addStretch()

        # 构建参数输入控件
        self._build_system_params(self._sec_sys)
        self._build_channel_params(self._sec_ch)
        self._build_detector_params(self._sec_det)

        # APD 行默认隐藏（初始为 PIN），探测器类型变化时动态显隐
        self._update_apd_rows_visibility("PIN")
        self.detector_combo.currentTextChanged.connect(self._update_apd_rows_visibility)

        # 连接信号
        self.scenarioCombo.setCurrentText("晴天")
        self.scenarioCombo.currentTextChanged.connect(self._on_scenario_changed)
        self.btnRun.clicked.connect(self._on_run_button_clicked)
        self.btnReset.clicked.connect(self.reset_params)

        # 应用预设
        self._apply_preset("晴天")
        self._connect_param_change_signals()
        self._emit_params_changed()

    # ── UI 构建 ───────────────────────────────────────────────────

    def _build_system_params(self, sec: _CollapsibleSection):
        row = 0

        # 波长
        self.wavelength_input = self._spinbox(380, 1600, 1550, 0, 10)
        sec.add_row(row, "波长 (nm)", self.wavelength_input, "范围: 380 – 1600 nm")
        row += 1

        # 发射功率
        self.power_input = self._spinbox(0.01, 1000, 25.0, 2, 1)
        sec.add_row(row, "发射功率 (mW)", self.power_input, "范围: 0.01 – 1000 mW")
        row += 1

        # 发射口径
        self.D_T_input = self._spinbox(0.1, 50, 2.5, 1, 0.5)
        sec.add_row(row, "发射口径 (cm)", self.D_T_input, "范围: 0.1 – 50 cm")
        row += 1

        # 接收口径
        self.D_R_input = self._spinbox(0.5, 100, 8.0, 1, 1)
        sec.add_row(row, "接收口径 (cm)", self.D_R_input, "范围: 0.5 – 100 cm")
        row += 1

        # 发散角
        self.divergence_input = self._spinbox(0.01, 50, 2.0, 2, 0.1)
        sec.add_row(row, "发散角 (mrad)", self.divergence_input, "范围: 0.01 – 50 mrad")
        row += 1

        # 指向抖动 (0 = 无指向误差)
        self.jitter_input = self._spinbox(0, 1000, 0.0, 1, 1)
        sec.add_row(row, "指向抖动 (μrad)", self.jitter_input, "范围: 0 – 1000 μrad")
        row += 1

        # 调制方式
        self.modulation_combo = QComboBox()
        self.modulation_combo.addItems(["OOK", "4-PPM", "8-PPM", "16-PPM", "SIM-BPSK"])
        self.modulation_combo.setMinimumHeight(24)
        sec.add_row(row, "调制方式", self.modulation_combo)
        row += 1

        # 数据速率
        self.datarate_input = self._spinbox(0.1, 10000, 155, 1, 10)
        sec.add_row(row, "速率 (Mbps)", self.datarate_input, "范围: 0.1 – 10000 Mbps")
        row += 1

        # 发射光学效率
        self.mu_T_input = self._spinbox(0.01, 1.0, 0.8, 2, 0.05)
        sec.add_row(row, "发射效率 η_T", self.mu_T_input, "范围: 0.01 – 1.0")
        row += 1

        # 接收光学效率
        self.mu_R_input = self._spinbox(0.01, 1.0, 0.8, 2, 0.05)
        sec.add_row(row, "接收效率 η_R", self.mu_R_input, "范围: 0.01 – 1.0")

    def _build_channel_params(self, sec: _CollapsibleSection):
        row = 0

        # 传输距离
        self.distance_input = self._spinbox(0.01, 20, 1.0, 2, 0.1)
        sec.add_row(row, "传输距离 (km)", self.distance_input, "范围: 0.01 – 20 km")
        row += 1

        # 能见度
        self.visibility_input = self._spinbox(0.01, 100, 23.0, 2, 1)
        sec.add_row(row, "能见度 (km)", self.visibility_input, "范围: 0.01 – 100 km")
        row += 1

        # Cn² — 两个控件放在一个容器里
        cn2_widget = QWidget()
        cn2_widget.setStyleSheet("background: transparent;")
        cn2_h = QHBoxLayout(cn2_widget)
        cn2_h.setContentsMargins(0, 0, 0, 0)
        cn2_h.setSpacing(4)

        self.cn2_coeff_input = self._spinbox(0.1, 99.9, 1.0, 1, 1)
        self.cn2_coeff_input.setMaximumWidth(60)
        cn2_h.addWidget(self.cn2_coeff_input)

        x_lbl = QLabel("×10^")
        x_lbl.setStyleSheet(
            f"font-size: {FONT_SIZE_SM}px; color: {TEXT_SECONDARY}; background: transparent; border: none;"
        )
        cn2_h.addWidget(x_lbl)

        self.cn2_exp_input = QSpinBox()
        self.cn2_exp_input.setRange(-17, -12)
        self.cn2_exp_input.setValue(-15)
        self.cn2_exp_input.setMinimumHeight(24)
        cn2_h.addWidget(self.cn2_exp_input, 1)

        sec.add_row(row, "Cn² (m⁻²/³)", cn2_widget, "系数: 0.1 – 99.9 × 指数: -17 – -12")
        row += 1

        # 降雨量
        self.rainfall_input = self._spinbox(0, 200, 0, 1, 1)
        sec.add_row(row, "降雨量 (mm/h)", self.rainfall_input, "范围: 0 – 200 mm/h")
        row += 1

        # 降雪量
        self.snowfall_input = self._spinbox(0, 100, 0, 1, 1)
        sec.add_row(row, "降雪量 (mm/h)", self.snowfall_input, "范围: 0 – 100 mm/h")
        row += 1

        # 雪类型
        self.snow_type_combo = QComboBox()
        self.snow_type_combo.addItems(["湿雪", "干雪"])
        self.snow_type_combo.setMinimumHeight(24)
        sec.add_row(row, "降雪类型", self.snow_type_combo)

    def _build_detector_params(self, sec: _CollapsibleSection):
        row = 0

        # 探测器类型
        self.detector_combo = QComboBox()
        self.detector_combo.addItems(["PIN", "APD"])
        self.detector_combo.setMinimumHeight(24)
        sec.add_row(row, "探测器类型", self.detector_combo)
        row += 1

        # APD 增益 (仅 APD 模式有效)
        self.apd_gain_input = self._spinbox(1, 500, 50, 0, 5)
        sec.add_row(row, "APD 增益 M", self.apd_gain_input, "范围: 1 – 500")
        self._apd_gain_row = row  # 保存行号供显隐控制
        row += 1

        # APD 噪声因子 (仅 APD 模式有效)
        self.apd_F_input = self._spinbox(1.0, 10.0, 3.0, 1, 0.1)
        sec.add_row(row, "APD 噪声因子 F", self.apd_F_input, "范围: 1.0 – 10.0")
        self._apd_F_row = row
        row += 1

        # 响应度
        self.responsivity_input = self._spinbox(0.01, 2.0, 0.5, 2, 0.1)
        sec.add_row(row, "响应度 (A/W)", self.responsivity_input, "范围: 0.01 – 2.0 A/W")
        row += 1

        # 负载电阻
        self.R_L_input = self._spinbox(1, 10000, 50, 0, 10)
        sec.add_row(row, "负载电阻 (Ω)", self.R_L_input, "范围: 1 – 10000 Ω")
        row += 1

        # 噪声温度
        self.temperature_input = self._spinbox(200, 400, 300, 0, 10)
        sec.add_row(row, "噪声温度 (K)", self.temperature_input, "范围: 200 – 400 K")
        row += 1

        # 背景光功率
        self.P_B_input = self._spinbox(0, 10000, 0, 1, 1)
        sec.add_row(row, "背景光 (nW)", self.P_B_input, "范围: 0 – 10000 nW")
        row += 1

        # 接收灵敏度
        self.sensitivity_input = self._spinbox(-60, 0, -30, 1, 1)
        sec.add_row(row, "灵敏度 (dBm)", self.sensitivity_input, "范围: -60 – 0 dBm")

    # ── 内部辅助 ──────────────────────────────────────────────────

    @staticmethod
    def _spinbox(min_v, max_v, default, decimals, step) -> QDoubleSpinBox:
        sb = QDoubleSpinBox()
        sb.setRange(min_v, max_v)
        sb.setValue(default)
        sb.setDecimals(decimals)
        sb.setSingleStep(step)
        sb.setMinimumHeight(24)
        return sb

    # ── 探测器行显隐 ──────────────────────────────────────────────

    def _update_apd_rows_visibility(self, detector_type: str):
        """根据探测器类型显隐 APD 专有参数行（含范围提示）"""
        show = (detector_type == "APD")
        for row in (self._apd_gain_row, self._apd_F_row):
            # 每个参数占两个 grid 行：grid_row = row*2 为控件行，grid_row+1 为范围提示行
            for grid_row in (row * 2, row * 2 + 1):
                for col in (0, 1):
                    item = self._sec_det.content_layout.itemAtPosition(grid_row, col)
                    if item and item.widget():
                        item.widget().setVisible(show)

    def _connect_param_change_signals(self):
        """将参数控件变化统一转发为 params_changed 信号"""
        value_widgets = (
            self.wavelength_input,
            self.power_input,
            self.D_T_input,
            self.D_R_input,
            self.divergence_input,
            self.jitter_input,
            self.datarate_input,
            self.mu_T_input,
            self.mu_R_input,
            self.distance_input,
            self.visibility_input,
            self.cn2_coeff_input,
            self.cn2_exp_input,
            self.rainfall_input,
            self.snowfall_input,
            self.apd_gain_input,
            self.apd_F_input,
            self.responsivity_input,
            self.R_L_input,
            self.temperature_input,
            self.P_B_input,
            self.sensitivity_input,
        )
        text_widgets = (
            self.modulation_combo,
            self.snow_type_combo,
            self.detector_combo,
        )

        for widget in value_widgets:
            widget.valueChanged.connect(self._emit_params_changed)
        for widget in text_widgets:
            widget.currentTextChanged.connect(self._emit_params_changed)

    def _emit_params_changed(self, *_args):
        params = self.get_params()
        if params is not None:
            self.params_changed.emit(params)

    # ── 场景预设 ──────────────────────────────────────────────────

    def _on_scenario_changed(self, name: str):
        if name != "自定义":
            self._apply_preset(name)
        self._emit_params_changed()

    def _apply_preset(self, name: str):
        preset = PRESET_SCENARIOS.get(name, {})
        if not preset:
            return
        self.visibility_input.setValue(preset.get("visibility", 23.0))
        self.cn2_coeff_input.setValue(preset.get("Cn2_coeff", 1.0))
        self.cn2_exp_input.setValue(preset.get("Cn2_exp", -15))
        self.rainfall_input.setValue(preset.get("rainfall", 0.0))
        self.snowfall_input.setValue(preset.get("snowfall", 0.0))
        snow = preset.get("snow_type", "湿雪")
        idx = self.snow_type_combo.findText(snow)
        if idx >= 0:
            self.snow_type_combo.setCurrentIndex(idx)

    # ── 参数接口（与原版保持完全相同的键名和数值）─────────────────

    def get_params(self) -> dict | None:
        try:
            params = {
                # 系统参数
                "wavelength_nm": self.wavelength_input.value(),
                "wavelength_m": self.wavelength_input.value() * 1e-9,
                "power_mw": self.power_input.value(),
                "power_w": self.power_input.value() * 1e-3,
                "D_T_cm": self.D_T_input.value(),
                "D_T_m": self.D_T_input.value() * 1e-2,
                "D_R_cm": self.D_R_input.value(),
                "D_R_m": self.D_R_input.value() * 1e-2,
                "divergence_mrad": self.divergence_input.value(),
                "divergence_rad": self.divergence_input.value() * 1e-3,
                "modulation": self._get_modulation(),
                "M_ppm": self._get_ppm_order(),
                "data_rate_mbps": self.datarate_input.value(),
                "data_rate_bps": self.datarate_input.value() * 1e6,
                "mu_T": self.mu_T_input.value(),
                "mu_R": self.mu_R_input.value(),
                # 信道参数
                "distance_km": self.distance_input.value(),
                "distance_m": self.distance_input.value() * 1e3,
                "visibility_km": self.visibility_input.value(),
                "Cn2": self.cn2_coeff_input.value() * 10 ** self.cn2_exp_input.value(),
                "rainfall_rate": self.rainfall_input.value(),
                "snowfall_rate": self.snowfall_input.value(),
                "snow_type": "wet"
                if self.snow_type_combo.currentText() == "湿雪"
                else "dry",
                # 探测器参数
                "detector_type": self.detector_combo.currentText(),
                "R_p": self.responsivity_input.value(),
                "R_L": self.R_L_input.value(),
                "temperature": self.temperature_input.value(),
                "P_B_w": self.P_B_input.value() * 1e-9,
                "sensitivity_dbm": self.sensitivity_input.value(),
                "M_apd": self.apd_gain_input.value(),
                "F_apd": self.apd_F_input.value(),
                # 系统参数（指向误差）
                "pointing_jitter_urad": self.jitter_input.value(),
                "pointing_jitter_rad": self.jitter_input.value() * 1e-6,
            }
            return params
        except Exception as e:
            QMessageBox.critical(self, "参数错误", f"参数获取失败:\n{e}")
            return None

    def _get_modulation(self) -> str:
        text = self.modulation_combo.currentText()
        if "PPM" in text:
            return "PPM"
        if "SIM" in text:
            return "SIM"
        return "OOK"

    def _get_ppm_order(self) -> int:
        text = self.modulation_combo.currentText()
        if "16-PPM" in text:
            return 16
        if "8-PPM" in text:
            return 8
        return 4

    def get_scenario_name(self) -> str:
        name = self.scenarioCombo.currentText()
        if name == "自定义":
            return f"自定义(V={self.visibility_input.value()}km)"
        return name

    def reset_params(self):
        """重置为默认参数（晴天场景）"""
        self.wavelength_input.setValue(1550)
        self.power_input.setValue(25.0)
        self.D_T_input.setValue(2.5)
        self.D_R_input.setValue(8.0)
        self.divergence_input.setValue(2.0)
        self.modulation_combo.setCurrentIndex(0)
        self.datarate_input.setValue(155)
        self.mu_T_input.setValue(0.8)
        self.mu_R_input.setValue(0.8)
        self.distance_input.setValue(1.0)
        self.scenarioCombo.setCurrentText("晴天")
        self._apply_preset("晴天")
        self.detector_combo.setCurrentIndex(0)
        self.responsivity_input.setValue(0.5)
        self.R_L_input.setValue(50)
        self.temperature_input.setValue(300)
        self.P_B_input.setValue(0)
        self.sensitivity_input.setValue(-30)
        self.apd_gain_input.setValue(50)
        self.apd_F_input.setValue(3.0)
        self.jitter_input.setValue(0.0)
        self._emit_params_changed()

    def set_running(self, running: bool):
        """切换运行状态，更新按钮文字"""
        self._running = running
        if running:
            self.btnRun.setText("取消仿真")
        else:
            self.btnRun.setText("开始仿真")

    def _on_run_button_clicked(self):
        if self._running:
            self.cancel_requested.emit()
        else:
            self.run_requested.emit()
