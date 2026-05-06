"""
大气湍流模型
适用范围: 近地水平路径, Cn²为常量

包含:
- Rytov方差 (平面波/球面波) (式4.47, 4.139)
- 闪烁指数 (弱/强湍流)
- 湍流强度判断
"""

import warnings
import numpy as np
from ..utils.constants import wavelength_to_wavenumber
from .scintillation import sigma_ln_plane_wave, sigma_ln_spherical_wave


def rytov_variance(Cn2, wavelength_m, distance_m):
    """
    平面波 Rytov 方差 (教材式4.47)
    σ_R² = 1.23 · Cn² · k^(7/6) · L^(11/6)

    参数:
        Cn2: 大气折射率结构常数 (m^(-2/3))，必须 > 0
        wavelength_m: 波长 (m)，必须 > 0
        distance_m: 传输距离 (m)，必须 >= 0
    返回:
        sigma_R2: Rytov方差 (无量纲)
    异常:
        ValueError: Cn2 <= 0 / wavelength_m <= 0 / distance_m < 0
    """
    if Cn2 <= 0:
        raise ValueError(f"Cn2 必须 > 0，当前值: {Cn2}")
    if wavelength_m <= 0:
        raise ValueError(f"wavelength_m 必须 > 0，当前值: {wavelength_m}")
    distance_m = np.asarray(distance_m, dtype=float)
    if np.any(distance_m < 0):
        raise ValueError(f"distance_m 必须 >= 0，当前最小值: {float(np.min(distance_m))}")
    if np.all(distance_m == 0):
        return 0.0 if distance_m.ndim == 0 else np.zeros_like(distance_m)
    k = wavelength_to_wavenumber(wavelength_m)
    sigma_R2 = 1.23 * Cn2 * k ** (7.0 / 6.0) * distance_m ** (11.0 / 6.0)
    return sigma_R2


def rytov_variance_spherical(Cn2, wavelength_m, distance_m):
    """
    球面波 Rytov 方差 (教材式4.139)
    β₀² = 0.4 · σ_R²

    参数:
        Cn2: 大气折射率结构常数 (m^(-2/3))
        wavelength_m: 波长 (m)
        distance_m: 传输距离 (m)
    返回:
        beta_0_2: 球面波Rytov方差 (无量纲)
    """
    sigma_R2 = rytov_variance(Cn2, wavelength_m, distance_m)
    return 0.4 * sigma_R2


def turbulence_regime(sigma_R2):
    """
    判断湍流强度等级 (依据开题报告式2.5阈值)

    σ_R² < 1    → 弱湍流
    1 ≤ σ_R² ≤ 25 → 中强湍流
    σ_R² > 25   → 饱和湍流

    参数:
        sigma_R2: Rytov方差，必须 >= 0
    返回:
        regime: 字符串 '弱湍流' / '中强湍流' / '饱和湍流'
    异常:
        ValueError: sigma_R2 < 0
    """
    sigma_R2 = float(sigma_R2)
    if sigma_R2 < 0:
        raise ValueError(f"sigma_R2 必须 >= 0，当前值: {sigma_R2}")
    if sigma_R2 < 1.0:
        return "弱湍流"
    elif sigma_R2 <= 25.0:
        return "中强湍流"
    else:
        return "饱和湍流"


def scintillation_index_weak(sigma_R2):
    """
    弱湍流闪烁指数 (教材式4.48)
    弱湍流条件下: σ_I² ≈ σ_R² (平面波)

    参数:
        sigma_R2: Rytov方差，必须 >= 0；有效适用范围为 sigma_R2 < 1
    返回:
        sigma_I2: 闪烁指数
    异常:
        ValueError: sigma_R2 < 0
    警告:
        sigma_R2 > 1 时弱湍流近似失效，建议改用 scintillation_index_plane_wave()
    """
    sigma_R2 = np.asarray(sigma_R2, dtype=float)
    if np.any(sigma_R2 < 0):
        raise ValueError(f"sigma_R2 必须 >= 0，当前最小值: {float(np.min(sigma_R2))}")
    if np.any(sigma_R2 > 1.0):
        warnings.warn(
            f"sigma_R2={float(np.max(sigma_R2)):.3f} > 1，已超出弱湍流近似适用范围（sigma_R2 < 1），"
            f"结果可能严重失准，建议改用 scintillation_index_plane_wave()",
            stacklevel=2,
        )
    return sigma_R2


def scintillation_index_plane_wave(sigma_R2):
    """
    平面波闪烁指数 (适用于弱到强全范围)
    使用大尺度/小尺度闪烁分解模型:

    σ_I² = exp(σ²_ln_x + σ²_ln_y) - 1

    其中 (零内尺度模型):
    σ²_ln_x = 0.49·σ_R² / (1 + 1.11·σ_R^(12/5))^(7/6)   大尺度
    σ²_ln_y = 0.51·σ_R² / (1 + 0.69·σ_R^(12/5))^(5/6)   小尺度

    参数:
        sigma_R2: Rytov方差，必须 >= 0（支持标量和 ndarray）
    返回:
        sigma_I2: 闪烁指数
    异常:
        ValueError: 任意元素 < 0
    """
    sigma_R2 = np.asarray(sigma_R2, dtype=float)
    if np.any(sigma_R2 < 0):
        raise ValueError(f"sigma_R2 必须 >= 0，当前最小值: {float(np.min(sigma_R2))}")

    sigma_ln_x2, sigma_ln_y2 = sigma_ln_plane_wave(sigma_R2)

    # 总闪烁指数
    sigma_I2 = np.exp(sigma_ln_x2 + sigma_ln_y2) - 1

    return sigma_I2


def scintillation_index_spherical_wave(sigma_R2):
    """
    球面波闪烁指数 (适用于弱到强全范围)
    β₀² = 0.4·σ_R²

    σ²_ln_x = 0.49·β₀² / (1 + 0.56·β₀^(12/5))^(7/6)
    σ²_ln_y = 0.51·β₀² / (1 + 0.69·β₀^(12/5))^(5/6)

    σ_I² = exp(σ²_ln_x + σ²_ln_y) - 1

    参数:
        sigma_R2: 平面波Rytov方差，必须 >= 0（支持标量和 ndarray）
    返回:
        sigma_I2: 球面波闪烁指数
    异常:
        ValueError: 任意元素 < 0
    """
    sigma_R2 = np.asarray(sigma_R2, dtype=float)
    if np.any(sigma_R2 < 0):
        raise ValueError(f"sigma_R2 必须 >= 0，当前最小值: {float(np.min(sigma_R2))}")
    sigma_ln_x2, sigma_ln_y2 = sigma_ln_spherical_wave(sigma_R2)

    sigma_I2 = np.exp(sigma_ln_x2 + sigma_ln_y2) - 1
    return sigma_I2


def fried_parameter(Cn2, wavelength_m, distance_m):
    """
    Fried 参数 r₀（大气相干宽度）(开题报告式2.9)
    r₀ = (0.423 · k² · Cn² · L)^(-3/5)

    均匀水平路径近似（Cn²为常量）。r₀ 越大表示大气相干性越好、
    光束质量越高；r₀ 越小表示湍流越强、波前畸变越严重。

    参数:
        Cn2: 大气折射率结构常数 (m^(-2/3))，必须 > 0
        wavelength_m: 波长 (m)，必须 > 0
        distance_m: 传输距离 (m)，必须 > 0
    返回:
        r0: Fried 参数 (m)
    异常:
        ValueError: Cn2 <= 0 / wavelength_m <= 0 / distance_m <= 0
    """
    if Cn2 <= 0:
        raise ValueError(f"Cn2 必须 > 0，当前值: {Cn2}")
    if wavelength_m <= 0:
        raise ValueError(f"wavelength_m 必须 > 0，当前值: {wavelength_m}")
    if distance_m <= 0:
        raise ValueError(f"distance_m 必须 > 0，当前值: {distance_m}（distance=0 会导致结果为 inf）")
    k = wavelength_to_wavenumber(wavelength_m)
    r0 = (0.423 * k**2 * Cn2 * distance_m) ** (-3.0 / 5.0)
    return r0


def long_term_beam_size(W0_m, wavelength_m, distance_m, sigma_R2):
    """
    湍流条件下高斯光束的长期光斑尺寸 W_LT (开题报告式2.8)
    W_LT² = W(L)² · (1 + 1.33 · σ_R² · Λ^(5/6))

    其中:
    - W(L) = W₀·√(1+(L/z_R)²)  为自由空间光斑半径 (m), z_R=π·W₀²/λ
    - Λ = 2L/(k·W₀²)           为菲涅耳比（光束参数）

    参数:
        W0_m: 发射端光束束腰半径 (m)，必须 > 0
        wavelength_m: 波长 (m)，必须 > 0
        distance_m: 传输距离 (m)，必须 >= 0
        sigma_R2: 平面波 Rytov 方差，必须 >= 0
    返回:
        W_LT: 长期平均光斑半径 (m)
    异常:
        ValueError: W0_m <= 0 / wavelength_m <= 0 / distance_m < 0 / sigma_R2 < 0
    """
    if W0_m <= 0:
        raise ValueError(f"W0_m 必须 > 0，当前值: {W0_m}")
    if wavelength_m <= 0:
        raise ValueError(f"wavelength_m 必须 > 0，当前值: {wavelength_m}")
    distance_m = np.asarray(distance_m, dtype=float)
    if np.any(distance_m < 0):
        raise ValueError(f"distance_m 必须 >= 0，当前最小值: {float(np.min(distance_m))}")
    sigma_R2 = np.asarray(sigma_R2, dtype=float)
    if np.any(sigma_R2 < 0):
        raise ValueError(f"sigma_R2 必须 >= 0，当前最小值: {float(np.min(sigma_R2))}")

    k = wavelength_to_wavenumber(wavelength_m)

    # 瑞利距离
    z_R = np.pi * W0_m**2 / wavelength_m

    # 自由空间光斑半径（高斯光束传播公式）
    W_free = W0_m * np.sqrt(1.0 + (distance_m / z_R) ** 2)

    # 菲涅耳比 Λ = 2L/(k·W₀²)
    Lambda = 2.0 * distance_m / (k * W0_m**2)

    # 长期光斑半径
    W_LT = W_free * np.sqrt(1.0 + 1.33 * sigma_R2 * Lambda ** (5.0 / 6.0))
    return W_LT


def beam_wander_variance(Cn2, distance_m, W0_m):
    """
    光束漂移方差 <r_c²> (开题报告式2.8 附属公式)
    <r_c²> = 2.42 · Cn² · L³ · W₀^(-1/3)

    光束漂移是大气湍流导致光斑中心随机偏移的现象，
    在长距离链路中是接收功率起伏的重要来源之一。

    参数:
        Cn2: 大气折射率结构常数 (m^(-2/3))，必须 > 0
        distance_m: 传输距离 (m)，必须 >= 0
        W0_m: 发射端光束束腰半径 (m)，必须 > 0
    返回:
        rc2: 光束漂移方差 (m²)
    异常:
        ValueError: Cn2 <= 0 / distance_m < 0 / W0_m <= 0
    """
    if Cn2 <= 0:
        raise ValueError(f"Cn2 必须 > 0，当前值: {Cn2}")
    distance_m = np.asarray(distance_m, dtype=float)
    if np.any(distance_m < 0):
        raise ValueError(f"distance_m 必须 >= 0，当前最小值: {float(np.min(distance_m))}")
    if W0_m <= 0:
        raise ValueError(f"W0_m 必须 > 0，当前值: {W0_m}")
    rc2 = 2.42 * Cn2 * distance_m**3 * W0_m ** (-1.0 / 3.0)
    return rc2


def cn2_typical(condition="moderate"):
    """
    近地面典型 Cn² 值 (经验参考值)

    参数:
        condition: 'weak' / 'moderate' / 'strong' / 'very_strong'
    返回:
        Cn2: m^(-2/3)
    警告:
        condition 不在有效列表时发出 UserWarning，返回默认值 1e-14
    """
    values = {
        "weak": 1e-16,        # 弱湍流 (夜间/稳定大气)
        "moderate": 1e-14,    # 中等湍流 (典型白天)
        "strong": 1e-13,      # 强湍流 (午间强日照)
        "very_strong": 1e-12, # 极强湍流
    }
    if condition not in values:
        warnings.warn(
            f"未知 condition \"{condition}\"，返回默认值 1e-14。"
            f"有效值: {list(values.keys())}",
            UserWarning,
            stacklevel=2,
        )
    return values.get(condition, 1e-14)
