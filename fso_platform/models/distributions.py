"""
光强概率密度分布模型
适用范围: 近地大气湍流信道中接收光强的统计特性

包含:
- 对数正态分布 (弱湍流, σ_R² < 1)
- Gamma-Gamma分布 (中强湍流, 1 ≤ σ_R² ≤ 25) (式4.194)
- 负指数分布 (饱和强湍流, σ_R² > 25) (式4.196)
"""

import numpy as np
from scipy.special import gamma as gamma_func, kv as bessel_kv, gammaln as lgamma
from .scintillation import sigma_ln_plane_wave


def lognormal_pdf(I, sigma_R2):
    """
    对数正态分布 PDF (弱湍流)

    f(I) = 1/(I·σ_l·√(2π)) · exp(-(ln(I) + σ_l²/2)² / (2σ_l²))

    其中 σ_l² = σ_R² (弱湍流近似)

    参数:
        I: 归一化光强 I/⟨I⟩ (>0)
        sigma_R2: Rytov方差，必须 > 0
    返回:
        pdf: 概率密度值
    异常:
        ValueError: sigma_R2 <= 0
    """
    if sigma_R2 <= 0:
        raise ValueError(f"sigma_R2 必须 > 0，当前值: {sigma_R2}")

    I = np.asarray(I, dtype=float)
    sigma_l2 = sigma_R2  # 弱湍流下对数振幅方差 ≈ σ_R²/4, 但对数光强方差 = σ_R²

    # 避免 I<=0 的情况
    pdf = np.zeros_like(I)
    mask = I > 0

    pdf[mask] = (1.0 / (I[mask] * np.sqrt(2 * np.pi * sigma_l2))) * np.exp(
        -((np.log(I[mask]) + sigma_l2 / 2) ** 2) / (2 * sigma_l2)
    )
    return pdf


def gamma_gamma_alpha_beta(sigma_R2):
    """
    Gamma-Gamma 分布的 α, β 参数计算
    根据平面波零内尺度模型:

    α = 1 / (exp(σ²_ln_x) - 1)
    β = 1 / (exp(σ²_ln_y) - 1)

    其中:
    σ²_ln_x = 0.49·σ_R² / (1 + 1.11·σ_R^(12/5))^(7/6)
    σ²_ln_y = 0.51·σ_R² / (1 + 0.69·σ_R^(12/5))^(5/6)

    参数:
        sigma_R2: Rytov方差，必须 > 0
    返回:
        (alpha, beta): 大尺度参数α, 小尺度参数β
    异常:
        ValueError: sigma_R2 <= 0
    """
    if sigma_R2 <= 0:
        raise ValueError(f"sigma_R2 必须 > 0，当前值: {sigma_R2}")

    sigma_ln_x2, sigma_ln_y2 = sigma_ln_plane_wave(sigma_R2)

    # 使用 np.expm1(x) = exp(x) - 1 避免小 x 时的灾难性消去
    alpha = 1.0 / np.expm1(sigma_ln_x2)
    beta = 1.0 / np.expm1(sigma_ln_y2)

    return alpha, beta


def gamma_gamma_pdf(I, alpha, beta):
    """
    Gamma-Gamma 分布 PDF (中强湍流) (教材式4.194)

    f(I) = 2(αβ)^((α+β)/2) / (Γ(α)·Γ(β)) · I^((α+β)/2 - 1) · K_{α-β}(2√(αβI))

    其中 K_v 是第二类修正贝塞尔函数

    参数:
        I: 归一化光强 I/⟨I⟩ (>0)
        alpha: 大尺度闪烁参数
        beta: 小尺度闪烁参数
    返回:
        pdf: 概率密度值
    """
    I = np.asarray(I, dtype=float)
    pdf = np.zeros_like(I)
    mask = I > 0

    I_pos = I[mask]
    ab = alpha * beta
    ab_sum_half = (alpha + beta) / 2.0
    order = alpha - beta

    # 使用对数运算避免大α·β时的溢出
    # ln(coeff) = ln(2) + ab_sum_half*ln(ab) - lgamma(alpha) - lgamma(beta)
    ln_coeff = np.log(2.0) + ab_sum_half * np.log(ab) - lgamma(alpha) - lgamma(beta)

    # ln(I^(ab_sum_half-1))
    ln_I_power = (ab_sum_half - 1.0) * np.log(I_pos)

    # K_{α-β}(2√(αβI))
    arg = 2.0 * np.sqrt(ab * I_pos)
    K_val = bessel_kv(order, arg)

    # 处理 K_val 中可能的零值或负值
    valid = K_val > 0
    pdf_pos = np.zeros_like(I_pos)
    if np.any(valid):
        ln_K = np.log(K_val[valid])
        pdf_pos[valid] = np.exp(ln_coeff + ln_I_power[valid] + ln_K)

    pdf[mask] = pdf_pos
    return pdf


def negative_exponential_pdf(I):
    """
    负指数分布 PDF (饱和强湍流) (教材式4.196)

    f(I) = exp(-I),  I ≥ 0

    (归一化光强 ⟨I⟩ = 1)

    参数:
        I: 归一化光强 (≥0)
    返回:
        pdf: 概率密度值
    """
    I = np.asarray(I, dtype=float)
    pdf = np.where(I >= 0, np.exp(-I), 0.0)
    return pdf


def select_distribution(sigma_R2):
    """
    根据Rytov方差自动选择合适的湍流分布模型 (依据开题报告式2.5阈值)

    σ_R² < 1       → 对数正态分布 (弱湍流)
    1 ≤ σ_R² ≤ 25  → Gamma-Gamma分布 (中强湍流)
    σ_R² > 25      → 负指数分布 (饱和湍流)

    参数:
        sigma_R2: Rytov方差，必须 >= 0
    返回:
        (name, pdf_func, params): 分布名称, PDF函数, 额外参数
    异常:
        ValueError: sigma_R2 < 0
    """
    if sigma_R2 < 0:
        raise ValueError(f"sigma_R2 必须 >= 0，当前值: {sigma_R2}")
    if sigma_R2 < 1.0:
        return ("对数正态分布", lognormal_pdf, {"sigma_R2": sigma_R2})
    elif sigma_R2 <= 25.0:
        alpha, beta = gamma_gamma_alpha_beta(sigma_R2)
        return ("Gamma-Gamma分布", gamma_gamma_pdf, {"alpha": alpha, "beta": beta})
    else:
        return ("负指数分布", negative_exponential_pdf, {})
