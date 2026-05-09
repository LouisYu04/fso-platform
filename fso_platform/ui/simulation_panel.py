"""
链路仿真面板 — 仿真结果仪表板
─────────────────────────────────────────────────────────────────────
【重要】run_simulation() 及其调用的所有计算代码完全不变。
        仅重构了 _init_ui()、_update_result()、_log() 的显示层。
─────────────────────────────────────────────────────────────────────
显示布局:
  ① 进度条（顶部，细条形）
  ② 四大指标卡片 (接收功率 / SNR / BER-OOK / 链路余量)
  ③ 次要指标网格 (大气衰减 / 几何损耗 / 总损耗 / Rytov方差 / 湍流强度 / 闪烁指数 / BER-PPM / BER-SIM / 光强分布)
  ④ 可折叠仿真日志
"""

from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QTextEdit,
    QProgressBar,
    QFrame,
    QSizePolicy,
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont, QColor, QTextCursor
from PyQt5 import uic

import numpy as np
import re

from .simulation_worker import SimulationWorker
from .theme import (
    BG_APP,
    BG_CARD,
    BG_SECTION,
    BORDER,
    BORDER_LIGHT,
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
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_DIM,
    PROGRESS_STYLE,
    SCROLLAREA_STYLE,
    LOG_STYLE,
    status_color,
    status_bg,
)
from fso_platform.utils.fonts import (
    FONT_FAMILY,
    FONT_MONO,
    FONT_SIZE_SM,
    FONT_SIZE_MD,
    FONT_SIZE_LG,
)


# ─── 指标卡片 ──────────────────────────────────────────────────────
class _MetricCard(QFrame):
    """单个关键指标卡片"""

    def __init__(self, title: str, unit: str = "", parent=None):
        super().__init__(parent)
        self._unit = unit
        self._title_text = title
        self.setMinimumWidth(140)
        self.setMinimumHeight(88)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._apply_card_style("neutral")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        # 标题
        self._title_lbl = QLabel(title)
        self._title_lbl.setStyleSheet(
            f"font-family: '{FONT_FAMILY}'; font-size: {FONT_SIZE_MD}px; "
            f"color: {TEXT_SECONDARY}; background: transparent; border: none;"
        )
        layout.addWidget(self._title_lbl)

        # 数值行（值 + 单位）
        val_row = QHBoxLayout()
        val_row.setSpacing(6)
        val_row.setContentsMargins(0, 0, 0, 0)

        self._val_lbl = QLabel("—")
        self._val_lbl.setStyleSheet(
            f"font-family: '{FONT_MONO}'; font-size: 24px; font-weight: bold; "
            f"color: {TEXT_PRIMARY}; background: transparent; border: none;"
        )
        val_row.addWidget(self._val_lbl)

        self._unit_lbl = QLabel(unit)
        self._unit_lbl.setStyleSheet(
            f"font-family: '{FONT_FAMILY}'; font-size: {FONT_SIZE_SM}px; "
            f"color: {TEXT_DIM}; background: transparent; border: none;"
        )
        self._unit_lbl.setAlignment(Qt.AlignBottom | Qt.AlignLeft)
        val_row.addWidget(self._unit_lbl)
        val_row.addStretch()
        layout.addLayout(val_row)

        layout.addStretch()

        # 状态标签
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(
            f"font-family: '{FONT_FAMILY}'; font-size: {FONT_SIZE_SM}px; "
            f"color: {TEXT_DIM}; background: transparent; border: none;"
        )
        layout.addWidget(self._status_lbl)

    def _apply_card_style(self, level: str):
        bg = status_bg(level)
        border = status_color(level) if level != "neutral" else BORDER_LIGHT
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            """
        )

    def update_value(self, text: str, status: str = "neutral", status_text: str = ""):
        self._val_lbl.setText(text)
        color = status_color(status)
        self._val_lbl.setStyleSheet(
            f"font-family: '{FONT_MONO}'; font-size: 24px; font-weight: bold; "
            f"color: {color}; background: transparent; border: none;"
        )
        if status_text:
            dot = {"good": "●", "ok": "●", "warn": "●", "bad": "●"}.get(status, "○")
            self._status_lbl.setText(f"{dot}  {status_text}")
            self._status_lbl.setStyleSheet(
                f"font-family: '{FONT_FAMILY}'; font-size: {FONT_SIZE_SM}px; "
                f"color: {color}; background: transparent; border: none;"
            )
        self._apply_card_style(status)


# ─── 次要指标行 ────────────────────────────────────────────────────
class _SecondaryMetric(QWidget):
    """紧凑型次要指标: 标签 + 数值"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        self._lbl = QLabel(title)
        self._lbl.setStyleSheet(
            f"font-family: '{FONT_FAMILY}'; font-size: {FONT_SIZE_SM}px; "
            f"color: {TEXT_SECONDARY}; background: transparent; border: none;"
        )
        self._lbl.setFixedWidth(100)
        layout.addWidget(self._lbl)

        self._val = QLabel("—")
        self._val.setStyleSheet(
            f"font-family: '{FONT_MONO}'; font-size: {FONT_SIZE_MD}px; font-weight: bold; "
            f"color: {TEXT_PRIMARY}; background: transparent; border: none;"
        )
        layout.addWidget(self._val, 1)

    def update(self, text: str, color: str = TEXT_PRIMARY):
        self._val.setText(text)
        self._val.setStyleSheet(
            f"font-family: '{FONT_MONO}'; font-size: {FONT_SIZE_MD}px; font-weight: bold; "
            f"color: {color}; background: transparent; border: none;"
        )


# ─── 多列日志容器 ────────────────────────────────────────────────────
class _LogTextEdit(QTextEdit):
    """隐藏缓冲区：重写 clear() 联动清空所有可见列"""

    def __init__(self, columns: list):
        super().__init__()
        self._columns = columns
        self.setVisible(False)

    def clear(self):
        super().clear()
        for col in self._columns:
            col.clear()


# ─── 主仿真面板 ────────────────────────────────────────────────────
class SimulationPanel(QWidget):
    """链路仿真结果仪表板"""

    simulation_done = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self._params = {}
        self._cur_col = 0

        # 加载 UI 文件
        ui_path = Path(__file__).parent / "simulation_panel.ui"
        uic.loadUi(ui_path, self)

        self.logHeader.setFont(QFont(FONT_FAMILY, FONT_SIZE_MD, QFont.Bold))
        self.logHeader.setStyleSheet(
            f"color: {TEXT_SECONDARY}; background-color: {BG_SECTION}; "
            f"border: none; border-radius: 8px 8px 0 0; padding: 0 12px;"
        )

        self._init_ui()

    # ── 界面构建 ─────────────────────────────────────────────────

    def _init_ui(self):
        """初始化动态控件和样式"""
        # 应用样式
        self.progressBar.setStyleSheet(PROGRESS_STYLE)
        self._build_context_bar()

        # ② 四大指标卡片
        self._card_PR = _MetricCard("接收功率", "dBm")
        self._card_SNR = _MetricCard("信噪比 SNR", "dB")
        self._card_BER = _MetricCard("BER  (OOK)")
        self._card_margin = _MetricCard("链路余量", "dB")

        for card in (self._card_PR, self._card_SNR, self._card_BER, self._card_margin):
            self.cardsLayout.addWidget(card)

        # ③ 次要指标区（3 列网格）
        def _sep():
            f = QFrame()
            f.setFrameShape(QFrame.VLine)
            f.setStyleSheet(f"color: {BORDER_LIGHT}; background: {BORDER_LIGHT};")
            f.setFixedWidth(1)
            return f

        self._sec = {}
        items = [
            ("atm_loss", "大气衰减"),
            ("geo_loss", "几何损耗"),
            ("total_loss", "总链路损耗"),
            ("sigma_R2", "Rytov 方差"),
            ("regime", "湍流强度"),
            ("sigma_I2", "闪烁指数"),
            ("ber_ppm", "BER (PPM)"),
            ("ber_sim", "BER (SIM)"),
            ("dist", "光强分布"),
        ]
        for i, (key, label) in enumerate(items):
            r, c = divmod(i, 3)
            widget = _SecondaryMetric(label)
            self._sec[key] = widget
            self.secondaryGrid.addWidget(widget, r, c * 2)
            if c < 2:
                self.secondaryGrid.addWidget(_sep(), r, c * 2 + 1)

        # ④ 仿真日志（三列横向排布）
        self._log_cols = []
        col_names = ["大气 / 几何", "链路 / 噪声", "湍流 / BER"]
        for i, name in enumerate(col_names):
            col_wrap = QWidget()
            col_wrap.setStyleSheet("background: transparent; border: none;")
            col_vbox = QVBoxLayout(col_wrap)
            col_vbox.setContentsMargins(0, 0, 0, 0)
            col_vbox.setSpacing(4)

            col_title = QLabel(f"  {name}")
            col_title.setFixedHeight(24)
            col_title.setStyleSheet(
                f"font-family: '{FONT_FAMILY}'; font-size: {FONT_SIZE_SM}px; font-weight: bold; "
                f"color: {TEXT_DIM}; background: transparent; border: none; "
                f"border-top: 1px solid {BORDER_LIGHT}; padding-top: 4px;"
            )
            col_vbox.addWidget(col_title)

            col_te = QTextEdit()
            col_te.setReadOnly(True)
            col_te.setStyleSheet(LOG_STYLE)
            col_te.document().setDocumentMargin(6)
            col_te.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            col_vbox.addWidget(col_te)
            self._log_cols.append(col_te)

            self.logColumnsLayout.addWidget(col_wrap)

            if i < 2:
                vsep = QFrame()
                vsep.setFrameShape(QFrame.VLine)
                vsep.setStyleSheet(f"color: {BORDER_LIGHT}; background: {BORDER_LIGHT};")
                vsep.setFixedWidth(1)
                self.logColumnsLayout.addWidget(vsep)

        # 隐藏缓冲区：run_simulation() 直接调用 .clear()，子类会联动清空各列
        self.log_text = _LogTextEdit(self._log_cols)

        # 内部映射供 _update_result 使用
        # 保持与原版相同的 dict 结构: key → (label_widget, unit_str)
        # 这里 label_widget 来自卡片 / 次要指标，unit 已嵌入卡片本身
        self.result_labels = {}
        # 主卡片
        self.result_labels["P_R"] = (self._card_PR, "dBm")
        self.result_labels["snr"] = (self._card_SNR, "dB")
        self.result_labels["ber_ook"] = (self._card_BER, "")
        self.result_labels["margin"] = (self._card_margin, "dB")
        # 次要指标（存储 _SecondaryMetric 实例）
        self.result_labels["atm_loss"] = (self._sec["atm_loss"], "dB")
        self.result_labels["geo_loss"] = (self._sec["geo_loss"], "dB")
        self.result_labels["total_loss"] = (self._sec["total_loss"], "dB")
        self.result_labels["sigma_R2"] = (self._sec["sigma_R2"], "")
        self.result_labels["regime"] = (self._sec["regime"], "")
        self.result_labels["sigma_I2"] = (self._sec["sigma_I2"], "")
        self.result_labels["ber_ppm"] = (self._sec["ber_ppm"], "")
        self.result_labels["ber_sim"] = (self._sec["ber_sim"], "")

    def _build_context_bar(self):
        """构建仿真页顶部的本次参数上下文条。"""
        self._context_frame = QFrame()
        self._context_frame.setStyleSheet(
            f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_LIGHT};
                border-radius: 8px;
            }}
            """
        )
        row = QHBoxLayout(self._context_frame)
        row.setContentsMargins(12, 8, 12, 8)
        row.setSpacing(10)

        self._context_title = QLabel("等待仿真")
        self._context_title.setStyleSheet(
            f"font-family: '{FONT_FAMILY}'; font-size: {FONT_SIZE_MD}px; font-weight: bold; "
            f"color: {TEXT_PRIMARY}; background: transparent; border: none;"
        )
        row.addWidget(self._context_title)

        self._context_detail = QLabel("左侧参数变化会同步到这里")
        self._context_detail.setStyleSheet(
            f"font-family: '{FONT_FAMILY}'; font-size: {FONT_SIZE_SM}px; "
            f"color: {TEXT_SECONDARY}; background: transparent; border: none;"
        )
        self._context_detail.setWordWrap(False)
        row.addWidget(self._context_detail, 1)

        self._context_badge = QLabel("待运行")
        self._context_badge.setAlignment(Qt.AlignCenter)
        self._set_context_badge("neutral", "待运行")
        row.addWidget(self._context_badge)

        self.verticalLayout.insertWidget(0, self._context_frame)

    def _set_context_badge(self, level: str, text: str):
        """更新上下文条右侧状态胶囊。"""
        color = status_color(level)
        bg = status_bg(level)
        self._context_badge.setText(text)
        self._context_badge.setStyleSheet(
            f"font-family: '{FONT_FAMILY}'; font-size: {FONT_SIZE_SM}px; font-weight: bold; "
            f"color: {color}; background-color: {bg}; border: 1px solid {color}; "
            f"border-radius: 8px; padding: 3px 10px;"
        )

    def _update_context(self, params: dict, badge_level: str = "neutral", badge_text: str = "待运行"):
        """根据当前参数刷新上下文条。"""
        if not params or not hasattr(self, "_context_detail"):
            return
        modulation = params.get("modulation", "OOK")
        if modulation == "PPM":
            modulation = f"{params.get('M_ppm', 4)}-PPM"
        elif modulation == "SIM":
            modulation = "SIM-BPSK"
        fog_label = {
            "kim": "Kim",
            "naboulsi_advection": "Naboulsi 平流",
            "naboulsi_radiation": "Naboulsi 辐射",
        }.get(params.get("fog_model", "kim"), "Kim")
        self._context_title.setText(f"{params.get('distance_km', 0):.2f} km 链路")
        self._context_detail.setText(
            f"{params.get('wavelength_nm', 0):.0f} nm · V={params.get('visibility_km', 0):.2f} km · "
            f"{fog_label} · {modulation} · {params.get('detector_type', 'PIN')}"
        )
        self._set_context_badge(badge_level, badge_text)

    # ── 信号/数据接口 ─────────────────────────────────────────────

    def update_params(self, params: dict):
        self._params = params
        self._update_context(params)

    def _log(self, msg: str):
        """按节号将 HTML 路由到对应列（col0: [1-2/6], col1: [3-4/6], col2: [5-6/6]+收尾）"""
        m = re.match(r"^\n?\[(\d+)/6\]", msg)
        if m:
            n = int(m.group(1))
            self._cur_col = 0 if n <= 2 else (1 if n <= 4 else 2)

        html = self._render_log_html(msg)
        target = self._log_cols[self._cur_col]
        cursor = target.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertHtml(html)
        target.setTextCursor(cursor)
        target.ensureCursorVisible()

    @staticmethod
    def _render_log_html(msg: str) -> str:
        """将纯文本日志行转换为带样式的 HTML 片段（inline <br>，不创建段落块）"""

        has_nl = msg.startswith("\n")
        line = msg.lstrip("\n")
        stripped = line.strip()
        extra_br = "<br>" if has_nl else ""
        if not stripped:
            return "<br>"
        # All-equals separator
        if re.match(r"^=+$", stripped):
            return f'{extra_br}<span style="color:{PRIMARY};">{"━" * 38}</span><br>'
        # Main title
        if "开始仿真" in stripped or "FSO链路特性" in stripped:
            return (
                f'{extra_br}<b style="color:{PRIMARY};">&nbsp;&nbsp;{stripped}</b><br>'
            )
        # Completion line
        if "仿真完成" in stripped:
            return f'{extra_br}<b style="color:{SUCCESS};">&nbsp;&nbsp;✓&nbsp;{stripped}</b><br>'
        # Section header [N/N]
        m = re.match(r"^\[(\d+/\d+)\]\s+(.+)$", stripped)
        if m:
            return (
                f'{extra_br}<b style="color:{PRIMARY_DARK};">'
                f"▶&nbsp;[{m.group(1)}]&nbsp;{m.group(2)}</b><br>"
            )
        # 生成可视化
        if stripped.startswith("生成可视化"):
            return f'{extra_br}<span style="color:{NEUTRAL};">&nbsp;&nbsp;{stripped}</span><br>'
        # BER table header (AWGN / 湍流信道)
        if "AWGN" in stripped or "湍流信道" in stripped:
            return f'&nbsp;&nbsp;&nbsp;&nbsp;<b style="color:{TEXT_SECONDARY};">{stripped}</b><br>'
        # Lines with scientific notation (BER value rows)
        if re.search(r"\d+\.\d{4}e[+-]\d+", stripped):

            def _ber_c(mm):
                try:
                    v = float(mm.group(1))
                    c = (
                        SUCCESS
                        if v < 1e-9
                        else PRIMARY
                        if v < 1e-6
                        else WARNING
                        if v < 1e-3
                        else ERROR
                    )
                except Exception:
                    c = TEXT_PRIMARY
                return f'<b style="color:{c};">{mm.group(1)}</b>'

            html_v = re.sub(r"(\d+\.\d{4}e[+-]\d+)", _ber_c, stripped)
            return f'&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:{TEXT_SECONDARY};">{html_v}</span><br>'
        # key = value lines
        kv = re.match(r"^(\s*)([^=]{2,40}?)\s+=\s+(.+)$", line)
        if kv:
            key = kv.group(2).strip()
            raw = kv.group(3).strip()

            def _cv(v: str) -> str:
                v = re.sub(r"(-?[\d.]+)\s*(dBm\b)", r"<b>\1</b>&thinsp;\2", v)
                v = re.sub(r"(-?[\d.]+)\s*(dB\b)", r"<b>\1</b>&thinsp;\2", v)
                v = re.sub(r"(-?[\d.]+)\s*(MHz|km|mW|nW|μW)", r"<b>\1</b>&thinsp;\2", v)
                v = re.sub(r"(?<![>\w])(-?[\d]+\.[\d]{4,})(?![\w<])", r"<b>\1</b>", v)
                return v

            return (
                f"&nbsp;&nbsp;&nbsp;&nbsp;"
                f'<span style="color:{TEXT_SECONDARY};">{key}</span>'
                f'&nbsp;<span style="color:{TEXT_DIM};">=</span>&nbsp;'
                f'<span style="color:{TEXT_PRIMARY};">{_cv(raw)}</span><br>'
            )
        # Fallback: plain text with indent preserved
        n_sp = len(line) - len(line.lstrip(" "))
        nbsp = "&nbsp;" * n_sp
        return (
            f'{extra_br}{nbsp}<span style="color:{TEXT_PRIMARY};">{stripped}</span><br>'
        )

    def _update_result(self, key: str, value, fmt: str = None):
        """更新指定指标的显示值（兼容原版调用接口）"""
        if key not in self.result_labels:
            return

        widget, unit = self.result_labels[key]

        # 格式化文字
        if fmt:
            text = fmt.format(value)
        elif isinstance(value, float):
            if abs(value) < 0.01 and value != 0:
                text = f"{value:.3e}"
            else:
                text = f"{value:.3f}"
        else:
            text = str(value)

        if unit:
            display_text = f"{text}"
        else:
            display_text = text

        if isinstance(widget, _MetricCard):
            # 确定状态
            status, status_text = self._infer_status(key, value)
            widget.update_value(display_text, status, status_text)
            if key == "margin":
                self._set_context_badge(status, "完成" if status in ("good", "ok") else status_text)
        elif isinstance(widget, _SecondaryMetric):
            color = TEXT_PRIMARY
            if key == "regime":
                if "弱" in text:
                    color = SUCCESS
                elif "中强" in text:
                    color = WARNING
                elif "饱和" in text:
                    color = ERROR
            if unit:
                widget.update(f"{text} {unit}", color)
            else:
                widget.update(text, color)

    def _infer_status(self, key: str, value) -> tuple:
        """根据指标键和值推断状态等级与状态文字"""
        if key == "P_R":
            sensitivity = self._params.get("sensitivity_dbm", -30.0)
            margin_to_sensitivity = value - sensitivity
            if margin_to_sensitivity > 6:
                return "good", "高于灵敏度 6 dB+"
            elif margin_to_sensitivity > 0:
                return "ok", "高于接收灵敏度"
            elif margin_to_sensitivity > -3:
                return "warn", "接近接收灵敏度"
            else:
                return "bad", "低于接收灵敏度"
        elif key == "snr":
            if value > 25:
                return "good", "信噪比优秀"
            elif value > 15:
                return "ok", "信噪比良好"
            elif value > 8:
                return "warn", "信噪比偏低"
            else:
                return "bad", "信噪比过低"
        elif key == "ber_ook":
            if isinstance(value, float) and value > 0:
                if value < 1e-9:
                    return "good", "误码率极低"
                elif value < 1e-6:
                    return "ok", "误码率可接受"
                elif value < 1e-3:
                    return "warn", "误码率偏高"
                else:
                    return "bad", "误码率过高"
            return "neutral", ""
        elif key == "margin":
            if value > 6:
                return "good", "链路余量充足"
            elif value > 3:
                return "ok", "链路可用"
            elif value > 0:
                return "warn", "余量不足"
            else:
                return "bad", "链路中断"
        return "neutral", ""

    # ═══════════════════════════════════════════════════════════════
    # 线程接口 — 委托给 SimulationWorker
    # ═══════════════════════════════════════════════════════════════

    def start_simulation(self, params: dict):
        """启动仿真 Worker（由 MainWindow 在线程中运行）"""
        self._params = params
        self.log_text.clear()
        self.progressBar.setValue(0)
        self._update_context(params, "ok", "运行中")

    def cancel_simulation(self):
        """取消当前仿真（由 MainWindow 调用）"""
        pass  # Worker 的 cancel 由 MainWindow 直接调用
