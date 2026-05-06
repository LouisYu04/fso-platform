"""
共享闪烁对数-强度方差计算模块

提供平面波和球面波的大尺度/小尺度对数闪烁方差
（σ²_ln_x, σ²_ln_y），供 turbulence.py 与 distributions.py
共同引用，避免公式重复。
"""

import numpy as np


def sigma_ln_plane_wave(sigma_R2):
    """
    平面波大尺度/小尺度对数闪烁方差（零内尺度模型）

    σ²_ln_x = 0.49·σ_R² / (1 + 1.11·σ_R^(12/5))^(7/6)   大尺度
    σ²_ln_y = 0.51·σ_R² / (1 + 0.69·σ_R^(12/5))^(5/6)   小尺度

    参数:
        sigma_R2: Rytov 方差，必须 >= 0（支持标量和 ndarray）
    返回:
        (sigma_ln_x2, sigma_ln_y2): 大尺度/小尺度对数闪烁方差
    异常:
        ValueError: 任意元素 < 0
    """
    sigma_R2 = np.asarray(sigma_R2, dtype=float)
    if np.any(sigma_R2 < 0):
        raise ValueError(f"sigma_R2 必须 >= 0，当前最小值: {float(np.min(sigma_R2))}")

    sigma_R_12_5 = sigma_R2 ** (6.0 / 5.0)

    sigma_ln_x2 = 0.49 * sigma_R2 / (1 + 1.11 * sigma_R_12_5) ** (7.0 / 6.0)
    sigma_ln_y2 = 0.51 * sigma_R2 / (1 + 0.69 * sigma_R_12_5) ** (5.0 / 6.0)

    return sigma_ln_x2, sigma_ln_y2


def sigma_ln_spherical_wave(sigma_R2):
    """
    球面波大尺度/小尺度对数闪烁方差（零内尺度模型）

    β₀² = 0.4·σ_R²

    σ²_ln_x = 0.49·β₀² / (1 + 0.56·β₀^(12/5))^(7/6)
    σ²_ln_y = 0.51·β₀² / (1 + 0.69·β₀^(12/5))^(5/6)

    参数:
        sigma_R2: 平面波 Rytov 方差，必须 >= 0（支持标量和 ndarray）
    返回:
        (sigma_ln_x2, sigma_ln_y2): 大尺度/小尺度对数闪烁方差
    异常:
        ValueError: 任意元素 < 0
    """
    sigma_R2 = np.asarray(sigma_R2, dtype=float)
    if np.any(sigma_R2 < 0):
        raise ValueError(f"sigma_R2 必须 >= 0，当前最小值: {float(np.min(sigma_R2))}")

    beta_0_2 = 0.4 * sigma_R2
    beta_12_5 = beta_0_2 ** (6.0 / 5.0)

    sigma_ln_x2 = 0.49 * beta_0_2 / (1 + 0.56 * beta_12_5) ** (7.0 / 6.0)
    sigma_ln_y2 = 0.51 * beta_0_2 / (1 + 0.69 * beta_12_5) ** (5.0 / 6.0)

    return sigma_ln_x2, sigma_ln_y2
