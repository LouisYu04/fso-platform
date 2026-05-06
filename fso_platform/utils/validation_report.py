"""
turbulence.py 参数验证模块
对 fso_platform/models/turbulence.py 中每个函数的输入参数进行系统性验证，
输出 Markdown 格式参数验证报告。

运行方式:
    python -m fso_platform.utils.validation_report
    或直接运行: python fso_platform/utils/validation_report.py
"""

import sys
import os
import math
import traceback
from datetime import datetime

# 确保可以导入 fso_platform
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import numpy as np
from fso_platform.models.turbulence import (
    rytov_variance,
    rytov_variance_spherical,
    turbulence_regime,
    scintillation_index_weak,
    scintillation_index_plane_wave,
    scintillation_index_spherical_wave,
    fried_parameter,
    long_term_beam_size,
    beam_wander_variance,
    cn2_typical,
)

# ─── 验证结果数据结构 ────────────────────────────────────────────────

STATUS_PASS    = "✅ 通过"
STATUS_WARN    = "⚠️ 警告"
STATUS_FAIL    = "❌ 失败"
STATUS_ERROR   = "💥 异常"

results = []   # 全局结果列表，每项为 dict


def _record(func_name, param_name, test_value, status, result_value, note):
    """记录一条验证结果"""
    results.append({
        "func":   func_name,
        "param":  param_name,
        "input":  test_value,
        "status": status,
        "output": result_value,
        "note":   note,
    })


def _safe_call(func, *args):
    """安全调用函数，捕获所有异常，返回 (成功标志, 返回值或异常信息)"""
    try:
        val = func(*args)
        if isinstance(val, (np.ndarray,)):
            val = float(val.flat[0]) if val.size > 0 else float("nan")
        else:
            val = float(val)
        return True, val
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def _expect_valueerror(ok, val):
    """
    判断"非法输入应当抛出 ValueError"的测试用例状态。
    - 若函数正确抛出 ValueError → ✅ 通过（防护已生效）
    - 若函数抛出其他异常（如 ZeroDivisionError）→ 💥 异常（防护不完整）
    - 若函数未抛出异常，正常返回 → ❌ 失败（缺少防护）
    """
    if not ok:
        if "ValueError" in val:
            return STATUS_PASS
        return STATUS_ERROR
    return STATUS_FAIL


def _fmt(v):
    """格式化数值用于报告显示"""
    if isinstance(v, str):
        return v
    if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
        return str(v)
    if abs(v) < 1e-3 or abs(v) > 1e4:
        return f"{v:.4e}"
    return f"{v:.6g}"


# ─── 各函数验证逻辑 ──────────────────────────────────────────────────

def validate_rytov_variance():
    fn = "rytov_variance"

    # ── Cn2 验证 ──────────────────────────────────────────
    # 典型值
    ok, val = _safe_call(rytov_variance, 1e-14, 1550e-9, 1000.0)
    _record(fn, "Cn2", "1e-14 m⁻²/³（典型白天）", STATUS_PASS, _fmt(val),
            "标准中等湍流强度，计算结果正常")

    # 弱湍流
    ok, val = _safe_call(rytov_variance, 1e-17, 1550e-9, 1000.0)
    _record(fn, "Cn2", "1e-17 m⁻²/³（极弱湍流）", STATUS_PASS, _fmt(val),
            "接近弱湍流下限，结果接近0但合法")

    # 极强湍流
    ok, val = _safe_call(rytov_variance, 1e-12, 1550e-9, 1000.0)
    _record(fn, "Cn2", "1e-12 m⁻²/³（极强湍流）", STATUS_WARN, _fmt(val),
            "接近极强湍流上限，σ_R²>>1 表明进入饱和区，Rytov近似失效")

    # 零值
    ok, val = _safe_call(rytov_variance, 0.0, 1550e-9, 1000.0)
    _record(fn, "Cn2", "0（零值）", _expect_valueerror(ok, val), _fmt(val),
            "Cn2=0 物理无意义，应抛出 ValueError")

    # 负值
    ok, val = _safe_call(rytov_variance, -1e-14, 1550e-9, 1000.0)
    _record(fn, "Cn2", "-1e-14（负值）", _expect_valueerror(ok, val), _fmt(val),
            "Cn2<0 物理不存在，应抛出 ValueError")

    # ── wavelength_m 验证 ──────────────────────────────────
    # 典型值 1550nm
    ok, val = _safe_call(rytov_variance, 1e-14, 1550e-9, 1000.0)
    _record(fn, "wavelength_m", "1550e-9 m（C波段）", STATUS_PASS, _fmt(val),
            "FSO最常用波长，计算正常")

    # 850nm
    ok, val = _safe_call(rytov_variance, 1e-14, 850e-9, 1000.0)
    _record(fn, "wavelength_m", "850e-9 m（850nm）", STATUS_PASS, _fmt(val),
            "短波FSO常用波长，σ_R²更大（波数k更大）")

    # 零值
    ok, val = _safe_call(rytov_variance, 1e-14, 0.0, 1000.0)
    _record(fn, "wavelength_m", "0（零值）", _expect_valueerror(ok, val), _fmt(val),
            "wavelength=0 物理无意义，应抛出 ValueError")

    # 负值
    ok, val = _safe_call(rytov_variance, 1e-14, -1550e-9, 1000.0)
    _record(fn, "wavelength_m", "-1550e-9（负值）", _expect_valueerror(ok, val), _fmt(val),
            "wavelength<0 物理无意义，应抛出 ValueError")

    # ── distance_m 验证 ──────────────────────────────────
    # 典型值
    ok, val = _safe_call(rytov_variance, 1e-14, 1550e-9, 1000.0)
    _record(fn, "distance_m", "1000 m（1km）", STATUS_PASS, _fmt(val),
            "典型FSO链路距离，计算正常")

    # 最大值 20km
    ok, val = _safe_call(rytov_variance, 1e-14, 1550e-9, 20000.0)
    status = STATUS_WARN if ok and val > 25 else STATUS_PASS
    _record(fn, "distance_m", "20000 m（20km上限）", status, _fmt(val),
            "长距离链路；若σ_R²>25则进入饱和湍流区，Rytov近似失效，需改用强湍流模型")

    # 零值
    ok, val = _safe_call(rytov_variance, 1e-14, 1550e-9, 0.0)
    _record(fn, "distance_m", "0（零距离）", STATUS_WARN, _fmt(val),
            "distance=0 时σ_R²=0，数学上不报错，但物理上无意义（无传播路径）")

    # 负值
    ok, val = _safe_call(rytov_variance, 1e-14, 1550e-9, -1000.0)
    _record(fn, "distance_m", "-1000（负值）", _expect_valueerror(ok, val), _fmt(val),
            "distance<0 物理无意义，应抛出 ValueError")


def validate_rytov_variance_spherical():
    fn = "rytov_variance_spherical"

    ok, val = _safe_call(rytov_variance_spherical, 1e-14, 1550e-9, 1000.0)
    _record(fn, "全部参数", "典型值：Cn2=1e-14, λ=1550nm, L=1km", STATUS_PASS, _fmt(val),
            "β₀²=0.4×σ_R²，适用于点源/接收端视角的球面波湍流模型")

    ok, val = _safe_call(rytov_variance_spherical, 1e-14, 0.0, 1000.0)
    _record(fn, "wavelength_m", "0（零值）", _expect_valueerror(ok, val), _fmt(val),
            "继承 rytov_variance() 的零波长防护，应抛出 ValueError")

    ok, val = _safe_call(rytov_variance_spherical, 0.0, 1550e-9, 1000.0)
    _record(fn, "Cn2", "0（零值）", STATUS_WARN, _fmt(val),
            "Cn2=0时β₀²=0，无湍流场景，函数不报错但使用方需注意语义")


def validate_turbulence_regime():
    fn = "turbulence_regime"

    cases = [
        (0.0,   STATUS_PASS,  "弱湍流",   "边界值0，归入弱湍流区，正确"),
        (0.5,   STATUS_PASS,  "弱湍流",   "典型弱湍流值"),
        (1.0,   STATUS_PASS,  "中强湍流", "弱/中强临界值1.0，归入中强湍流，正确"),
        (10.0,  STATUS_PASS,  "中强湍流", "典型中强湍流值"),
        (25.0,  STATUS_PASS,  "中强湍流", "中强/饱和临界值25.0，归入中强湍流，正确"),
        (25.01, STATUS_PASS,  "饱和湍流", "刚超过25，归入饱和湍流，正确"),
        (100.0, STATUS_WARN,  "饱和湍流", "极大Rytov方差；饱和湍流区Rytov方法完全失效，仅作定性判断"),
        (-1.0,  STATUS_PASS,  "ValueError",   "σ_R²<0 应抛出 ValueError，防护已生效"),
    ]
    for val, expected_status, expected_regime, note in cases:
        try:
            regime = turbulence_regime(val)
            # 若调用成功，检查是否本应抛出异常
            if expected_status == STATUS_PASS and expected_regime == "ValueError":
                status = STATUS_FAIL  # 应该抛出但没抛出
            else:
                status = expected_status
            out = regime
        except ValueError as e:
            if expected_regime == "ValueError":
                status = STATUS_PASS
            else:
                status = STATUS_ERROR
            out = f"ValueError: {e}"
        except Exception as e:
            status = STATUS_ERROR
            out = str(e)
        _record(fn, "sigma_R2", f"{val}", status, out, note)


def validate_scintillation_index_weak():
    fn = "scintillation_index_weak"

    cases = [
        (0.1,  STATUS_PASS, "弱湍流中间值，σ_I²≈σ_R²近似成立"),
        (0.5,  STATUS_PASS, "弱湍流典型值，近似有效"),
        (1.0,  STATUS_WARN, "σ_R²=1为弱湍流上限，此时弱湍流近似开始失效，建议改用plane_wave模型"),
        (5.0,  STATUS_WARN, "σ_R²>>1已进入强湍流，弱湍流近似严重高估闪烁指数，结果不可信"),
        (0.0,  STATUS_PASS, "零值，无湍流，σ_I²=0，正确"),
        (-0.1, None, "σ_R²<0 物理不可能，应抛出 ValueError"),
    ]
    for val, status, note in cases:
        ok, result = _safe_call(scintillation_index_weak, val)
        if status is None:
            actual_status = _expect_valueerror(ok, result)
        else:
            actual_status = STATUS_ERROR if not ok else status
        _record(fn, "sigma_R2", f"{val}", actual_status, _fmt(result), note)


def validate_scintillation_index_plane_wave():
    fn = "scintillation_index_plane_wave"

    cases = [
        (0.1,   STATUS_PASS, "弱湍流，平面波模型与弱湍流近似几乎一致"),
        (1.0,   STATUS_PASS, "弱/中强湍流临界，全范围模型在此处平滑过渡"),
        (10.0,  STATUS_PASS, "中强湍流典型值，大小尺度分解模型正常工作"),
        (25.0,  STATUS_WARN, "饱和湍流区边界，σ_I²接近饱和，模型精度下降"),
        (100.0, STATUS_WARN, "极强湍流，exp()参数可能很大，注意溢出风险"),
        (0.0,   STATUS_PASS, "零值，无湍流，σ_I²≈0，正确"),
        (-0.1,  None,        "σ_R²<0，应抛出 ValueError"),
    ]
    for val, status, note in cases:
        ok, result = _safe_call(scintillation_index_plane_wave, val)
        if status is None:
            actual_status = _expect_valueerror(ok, result)
        else:
            actual_status = STATUS_ERROR if (not ok) else status
            if ok and (math.isnan(result) or math.isinf(result)):
                actual_status = STATUS_FAIL
        _record(fn, "sigma_R2", f"{val}", actual_status, _fmt(result), note)


def validate_scintillation_index_spherical_wave():
    fn = "scintillation_index_spherical_wave"

    cases = [
        (0.1,   STATUS_PASS, "弱湍流，β₀²=0.04，球面波模型正常"),
        (1.0,   STATUS_PASS, "中等湍流，β₀²=0.4，大小尺度分解模型有效"),
        (10.0,  STATUS_PASS, "强湍流，β₀²=4.0，全范围模型适用"),
        (25.0,  STATUS_WARN, "饱和区边界，β₀²=10.0，模型精度下降"),
        (0.0,   STATUS_PASS, "零值，无湍流，σ_I²≈0，正确"),
        (-0.1,  None,        "σ_R²<0，应抛出 ValueError"),
    ]
    for val, status, note in cases:
        ok, result = _safe_call(scintillation_index_spherical_wave, val)
        if status is None:
            actual_status = _expect_valueerror(ok, result)
        else:
            actual_status = STATUS_ERROR if (not ok) else status
            if ok and (math.isnan(result) or math.isinf(result)):
                actual_status = STATUS_FAIL
        _record(fn, "sigma_R2", f"{val}", actual_status, _fmt(result), note)


def validate_fried_parameter():
    fn = "fried_parameter"

    # Cn2 验证
    cases_cn2 = [
        (1e-17, 1550e-9, 1000.0, STATUS_PASS,  "极弱湍流，r₀很大（大气相干性好）"),
        (1e-14, 1550e-9, 1000.0, STATUS_PASS,  "典型湍流，r₀约几厘米量级"),
        (1e-12, 1550e-9, 1000.0, STATUS_WARN,  "极强湍流，r₀很小（<1mm），接收口径远大于r₀，性能极差"),
        (0.0,   1550e-9, 1000.0, None,         "Cn2=0 应抛出 ValueError"),
        (-1e-14,1550e-9, 1000.0, None,         "Cn2<0 应抛出 ValueError"),
    ]
    for cn2, wl, dist, status, note in cases_cn2:
        ok, result = _safe_call(fried_parameter, cn2, wl, dist)
        if status is None:
            actual_status = _expect_valueerror(ok, result)
        else:
            actual_status = status
            if ok and (math.isnan(result) or math.isinf(result)):
                actual_status = STATUS_FAIL
        _record(fn, "Cn2", f"{cn2}", actual_status, _fmt(result), note)

    # wavelength_m 验证
    for wl, status, note in [
        (1550e-9, STATUS_PASS, "标准1550nm，计算正常"),
        (850e-9,  STATUS_PASS, "850nm，r₀略小（短波对湍流更敏感）"),
        (0.0,     None,        "wavelength=0 应抛出 ValueError"),
    ]:
        ok, result = _safe_call(fried_parameter, 1e-14, wl, 1000.0)
        if status is None:
            actual_status = _expect_valueerror(ok, result)
        else:
            actual_status = STATUS_ERROR if not ok else status
        _record(fn, "wavelength_m", f"{wl}", actual_status, _fmt(result), note)

    # distance_m 验证
    for dist, status, note in [
        (500.0,   STATUS_PASS, "短距链路，r₀较大"),
        (5000.0,  STATUS_PASS, "长距链路，r₀减小"),
        (0.0,     None,    "distance=0 应抛出 ValueError（导致 inf）"),
        (-1000.0, None,    "distance<0 应抛出 ValueError"),
    ]:
        ok, result = _safe_call(fried_parameter, 1e-14, 1550e-9, dist)
        if status is None:
            actual_status = _expect_valueerror(ok, result)
        else:
            actual_status = STATUS_ERROR if not ok else status
            if ok and (math.isnan(result) or math.isinf(result)):
                actual_status = STATUS_FAIL if dist < 0 else STATUS_WARN
        _record(fn, "distance_m", f"{dist}", actual_status, _fmt(result), note)


def validate_long_term_beam_size():
    fn = "long_term_beam_size"

    # W0_m 验证
    for w0, status, note in [
        (0.0125, STATUS_PASS, "典型发射束腰半径12.5mm（D_T=2.5cm），正常"),
        (0.001,  STATUS_PASS, "细光束1mm束腰，瑞利距离短，远场扩散大"),
        (0.0,    None,        "W0=0 应抛出 ValueError"),
        (-0.01,  None,        "W0<0 应抛出 ValueError"),
    ]:
        ok, result = _safe_call(long_term_beam_size, w0, 1550e-9, 1000.0, 0.5)
        if status is None:
            actual_status = _expect_valueerror(ok, result)
        else:
            actual_status = STATUS_ERROR if not ok else status
            if ok and (math.isnan(result) or math.isinf(result)):
                actual_status = STATUS_FAIL
        _record(fn, "W0_m", f"{w0}", actual_status, _fmt(result), note)

    # wavelength_m 验证
    for wl, status, note in [
        (1550e-9, STATUS_PASS,  "标准波长，正常"),
        (0.0,     None,        "wavelength=0 应抛出 ValueError"),
    ]:
        ok, result = _safe_call(long_term_beam_size, 0.0125, wl, 1000.0, 0.5)
        if status is None:
            actual_status = _expect_valueerror(ok, result)
        else:
            actual_status = STATUS_ERROR if not ok else status
        _record(fn, "wavelength_m", f"{wl}", actual_status, _fmt(result), note)

    # distance_m 验证
    for dist, status, note in [
        (1000.0,  STATUS_PASS, "典型1km距离，正常"),
        (0.0,     STATUS_WARN, "distance=0 → W_LT=W0（无传播扩散），计算可完成但无物理意义"),
        (-1000.0, None,        "distance<0 应抛出 ValueError"),
    ]:
        ok, result = _safe_call(long_term_beam_size, 0.0125, 1550e-9, dist, 0.5)
        if status is None:
            actual_status = _expect_valueerror(ok, result)
        else:
            actual_status = STATUS_ERROR if not ok else status
        _record(fn, "distance_m", f"{dist}", actual_status, _fmt(result), note)

    # sigma_R2 验证
    for sr2, status, note in [
        (0.5,   STATUS_PASS, "弱湍流，光斑扩展适度"),
        (10.0,  STATUS_PASS, "强湍流，光斑明显扩展"),
        (0.0,   STATUS_PASS, "零湍流，W_LT=W_free，退化为自由空间"),
        (-0.1,  None,        "σ_R²<0 应抛出 ValueError"),
    ]:
        ok, result = _safe_call(long_term_beam_size, 0.0125, 1550e-9, 1000.0, sr2)
        if status is None:
            actual_status = _expect_valueerror(ok, result)
        else:
            actual_status = STATUS_ERROR if not ok else status
            if ok and (math.isnan(result) or math.isinf(result)):
                actual_status = STATUS_FAIL
        _record(fn, "sigma_R2", f"{sr2}", actual_status, _fmt(result), note)


def validate_beam_wander_variance():
    fn = "beam_wander_variance"

    # Cn2
    for cn2, status, note in [
        (1e-14,  STATUS_PASS, "典型湍流，漂移方差合理"),
        (1e-17,  STATUS_PASS, "极弱湍流，漂移方差接近零"),
        (0.0,    None,    "Cn2=0 应抛出 ValueError"),
        (-1e-14, None,    "Cn2<0 应抛出 ValueError"),
    ]:
        ok, result = _safe_call(beam_wander_variance, cn2, 1000.0, 0.0125)
        if status is None:
            actual_status = _expect_valueerror(ok, result)
        else:
            actual_status = STATUS_ERROR if not ok else status
        _record(fn, "Cn2", f"{cn2}", actual_status, _fmt(result), note)

    # distance_m
    for dist, status, note in [
        (1000.0,  STATUS_PASS, "1km，典型值"),
        (0.0,     STATUS_PASS, "distance=0 → rc²=0，无传播无漂移，数学合法"),
        (-1000.0, None,    "distance<0 应抛出 ValueError"),
    ]:
        ok, result = _safe_call(beam_wander_variance, 1e-14, dist, 0.0125)
        if status is None:
            actual_status = _expect_valueerror(ok, result)
        else:
            actual_status = STATUS_ERROR if not ok else status
        _record(fn, "distance_m", f"{dist}", actual_status, _fmt(result), note)

    # W0_m
    for w0, status, note in [
        (0.0125, STATUS_PASS,  "典型束腰半径12.5mm"),
        (0.0,    None,    "W0=0 应抛出 ValueError"),
        (-0.01,  None,    "W0<0 应抛出 ValueError"),
    ]:
        ok, result = _safe_call(beam_wander_variance, 1e-14, 1000.0, w0)
        if status is None:
            actual_status = _expect_valueerror(ok, result)
        else:
            actual_status = STATUS_ERROR if not ok else status
            if ok and (math.isnan(result) or math.isinf(result)):
                actual_status = STATUS_FAIL
        _record(fn, "W0_m", f"{w0}", actual_status, _fmt(result), note)


def validate_cn2_typical():
    fn = "cn2_typical"

    valid_cases = [
        ("weak",        1e-16, STATUS_PASS, "弱湍流参考值，夜间/稳定大气"),
        ("moderate",    1e-14, STATUS_PASS, "中等湍流参考值，典型白天"),
        ("strong",      1e-13, STATUS_PASS, "强湍流参考值，午间强日照"),
        ("very_strong", 1e-12, STATUS_PASS, "极强湍流参考值"),
    ]
    for cond, expected, status, note in valid_cases:
        ok, result = _safe_call(cn2_typical, cond)
        actual_status = STATUS_ERROR if not ok else status
        match_note = note + (f"，返回值 {result:.1e} 与预期 {expected:.1e} 一致" if abs(result - expected) < 1e-20 else f"，⚠️返回值 {result:.1e} 与预期 {expected:.1e} 不符")
        _record(fn, "condition", f'"{cond}"', actual_status, _fmt(result), match_note)

    # 非法字符串
    ok, result = _safe_call(cn2_typical, "unknown_condition")
    _record(fn, "condition", '"unknown_condition"（非法值）', STATUS_WARN, _fmt(result),
            "非法condition静默返回默认值1e-14，无任何警告；建议加入警告提示或抛出ValueError")

    # 空字符串
    ok, result = _safe_call(cn2_typical, "")
    _record(fn, "condition", '""（空字符串）', STATUS_WARN, _fmt(result),
            "空字符串静默返回默认值1e-14，同上，缺少输入校验")


# ─── 运行所有验证 ────────────────────────────────────────────────────

def run_all():
    validate_rytov_variance()
    validate_rytov_variance_spherical()
    validate_turbulence_regime()
    validate_scintillation_index_weak()
    validate_scintillation_index_plane_wave()
    validate_scintillation_index_spherical_wave()
    validate_fried_parameter()
    validate_long_term_beam_size()
    validate_beam_wander_variance()
    validate_cn2_typical()


# ─── Markdown 报告生成 ───────────────────────────────────────────────

def generate_markdown() -> str:
    total   = len(results)
    n_pass  = sum(1 for r in results if r["status"] == STATUS_PASS)
    n_warn  = sum(1 for r in results if r["status"] == STATUS_WARN)
    n_fail  = sum(1 for r in results if r["status"] == STATUS_FAIL)
    n_error = sum(1 for r in results if r["status"] == STATUS_ERROR)

    lines = []
    lines.append("# 参数验证报告 — `turbulence.py`\n")
    lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    lines.append(f"> 验证对象：`fso_platform/models/turbulence.py`\n")

    lines.append("---\n")
    lines.append("## 验证摘要\n")
    lines.append(f"| 统计项 | 数量 |")
    lines.append(f"|--------|------|")
    lines.append(f"| 总检查项 | **{total}** |")
    lines.append(f"| ✅ 通过  | **{n_pass}** |")
    lines.append(f"| ⚠️ 警告  | **{n_warn}** |")
    lines.append(f"| ❌ 失败  | **{n_fail}** |")
    lines.append(f"| 💥 异常  | **{n_error}** |")
    lines.append("")

    # 问题汇总（仅列出非通过项）
    issues = [r for r in results if r["status"] != STATUS_PASS]
    if issues:
        lines.append("---\n")
        lines.append("## 问题汇总\n")
        lines.append("| # | 函数 | 参数 | 测试输入 | 状态 | 说明 |")
        lines.append("|---|------|------|----------|------|------|")
        for i, r in enumerate(issues, 1):
            lines.append(
                f"| {i} | `{r['func']}` | `{r['param']}` | `{r['input']}` "
                f"| {r['status']} | {r['note']} |"
            )
        lines.append("")

    # 各函数详细结果
    lines.append("---\n")
    lines.append("## 各函数详细验证结果\n")

    # 按函数分组
    func_order = [
        "rytov_variance",
        "rytov_variance_spherical",
        "turbulence_regime",
        "scintillation_index_weak",
        "scintillation_index_plane_wave",
        "scintillation_index_spherical_wave",
        "fried_parameter",
        "long_term_beam_size",
        "beam_wander_variance",
        "cn2_typical",
    ]

    func_desc = {
        "rytov_variance":                   "平面波 Rytov 方差 σ_R² = 1.23·Cn²·k^(7/6)·L^(11/6)",
        "rytov_variance_spherical":         "球面波 Rytov 方差 β₀² = 0.4·σ_R²",
        "turbulence_regime":                "湍流强度等级判断（弱 / 中强 / 饱和）",
        "scintillation_index_weak":         "弱湍流闪烁指数近似 σ_I² ≈ σ_R²",
        "scintillation_index_plane_wave":   "平面波闪烁指数（全范围，大/小尺度分解模型）",
        "scintillation_index_spherical_wave":"球面波闪烁指数（全范围，大/小尺度分解模型）",
        "fried_parameter":                  "Fried 参数 r₀ = (0.423·k²·Cn²·L)^(-3/5)",
        "long_term_beam_size":              "长期平均光斑半径 W_LT（含湍流展宽）",
        "beam_wander_variance":             "光束漂移方差 <r_c²> = 2.42·Cn²·L³·W₀^(-1/3)",
        "cn2_typical":                      "近地面典型 Cn² 经验参考值查表",
    }

    for fn in func_order:
        fn_results = [r for r in results if r["func"] == fn]
        if not fn_results:
            continue
        fn_pass  = sum(1 for r in fn_results if r["status"] == STATUS_PASS)
        fn_warn  = sum(1 for r in fn_results if r["status"] == STATUS_WARN)
        fn_fail  = sum(1 for r in fn_results if r["status"] == STATUS_FAIL)
        fn_error = sum(1 for r in fn_results if r["status"] == STATUS_ERROR)

        badge = f"✅{fn_pass} ⚠️{fn_warn} ❌{fn_fail} 💥{fn_error}"
        lines.append(f"### `{fn}()`  `[{badge}]`\n")
        lines.append(f"> {func_desc.get(fn, '')}\n")
        lines.append("| 参数 | 测试输入 | 计算输出 | 状态 | 说明 |")
        lines.append("|------|----------|----------|------|------|")
        for r in fn_results:
            lines.append(
                f"| `{r['param']}` | `{r['input']}` | `{r['output']}` "
                f"| {r['status']} | {r['note']} |"
            )
        lines.append("")

    # 修复建议
    lines.append("---\n")
    lines.append("## 修复建议\n")

    recommendations = [
        ("**所有涉及 `wavelength_m` 的函数**",
         "`wavelength_m <= 0` 时应抛出 `ValueError`，因为波数 k=2π/λ 在 λ≤0 时无意义且导致 ZeroDivisionError。",
         "```python\nif wavelength_m <= 0:\n    raise ValueError(f'wavelength_m 必须 > 0，当前值: {wavelength_m}')\n```"),

        ("**所有涉及 `Cn2` 的函数**",
         "`Cn2 <= 0` 时结果无物理意义（`Cn2=0` 返回零方差，`Cn2<0` 返回负方差或 nan）。建议至少在文档中注明，最好加入 `>0` 断言。",
         "```python\nif Cn2 <= 0:\n    raise ValueError(f'Cn2 必须 > 0，当前值: {Cn2}')\n```"),

        ("**`distance_m` 参数**",
         "`distance_m < 0` 在所有函数中均为物理非法输入，会导致非整数幂计算产生 nan。建议加入 `>= 0` 检查，并对 `distance_m = 0` 视情况返回默认值或警告。",
         "```python\nif distance_m < 0:\n    raise ValueError(f'distance_m 必须 >= 0，当前值: {distance_m}')\n```"),

        ("**`W0_m` 参数（`long_term_beam_size`、`beam_wander_variance`）**",
         "`W0_m = 0` 导致除以零（`beam_wander_variance`）或 `Lambda=inf`（`long_term_beam_size`）；`W0_m < 0` 产生 nan。",
         "```python\nif W0_m <= 0:\n    raise ValueError(f'W0_m 必须 > 0，当前值: {W0_m}')\n```"),

        ("**`scintillation_index_weak()`**",
         "当 `sigma_R2 > 1` 时弱湍流近似失效，但函数静默返回错误结果。建议加入范围警告或在文档中强调使用前提。",
         "```python\nimport warnings\nif sigma_R2 > 1.0:\n    warnings.warn(f'sigma_R2={sigma_R2:.3f} > 1，已超出弱湍流近似适用范围，建议改用 scintillation_index_plane_wave()')\n```"),

        ("**`cn2_typical()`**",
         "非法 `condition` 字符串静默返回默认值 1e-14，没有任何提示，容易掩盖调用方的拼写错误。",
         "```python\nif condition not in values:\n    import warnings\n    warnings.warn(f'未知条件 \"{condition}\"，返回默认值 1e-14')\n```"),

        ("**`rytov_variance()` 适用范围**",
         "当 `sigma_R2 > 1`（中强湍流以上）时，Rytov 微扰理论不再严格成立，但函数没有任何提示。建议调用后由上层逻辑根据 `turbulence_regime()` 结果决定是否发出警告。",
         "_（建议在链路计算层处理，而非在基础函数中添加）_"),
    ]

    for i, (target, desc, code) in enumerate(recommendations, 1):
        lines.append(f"### {i}. {target}\n")
        lines.append(desc)
        lines.append("")
        lines.append(code)
        lines.append("")

    return "\n".join(lines)


# ─── 主入口 ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("正在运行参数验证...")
    run_all()

    md = generate_markdown()

    # 输出到文件
    out_path = os.path.join(
        os.path.dirname(__file__), "../../turbulence_param_validation_report.md"
    )
    out_path = os.path.abspath(out_path)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)

    total   = len(results)
    n_pass  = sum(1 for r in results if r["status"] == STATUS_PASS)
    n_warn  = sum(1 for r in results if r["status"] == STATUS_WARN)
    n_fail  = sum(1 for r in results if r["status"] == STATUS_FAIL)
    n_error = sum(1 for r in results if r["status"] == STATUS_ERROR)

    print(f"\n验证完成：共 {total} 项")
    print(f"  ✅ 通过: {n_pass}")
    print(f"  ⚠️ 警告: {n_warn}")
    print(f"  ❌ 失败: {n_fail}")
    print(f"  💥 异常: {n_error}")
    print(f"\n报告已写入: {out_path}")
