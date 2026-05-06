"""
误码率(BER)计算模型
适用范围: 近地大气信道直接检测FSO系统

包含:
- OOK 调制 BER (式4.205)
- M-PPM 调制 BER (式4.215)
- SIM-BPSK 调制 BER (式4.220)
- 考虑湍流的平均BER (数值积分)
"""

import numpy as np
from scipy.special import erfc
from scipy.integrate import quad

from .distributions import (
    lognormal_pdf,
    gamma_gamma_pdf,
    gamma_gamma_alpha_beta,
    negative_exponential_pdf,
)


def ber_ook(snr_linear):
    """
    OOK 调制误码率 (无湍流, AWGN信道) (教材式4.207)
    BER = ½ · erfc(√(SNR / 2))

    参数:
        snr_linear: 电信噪比 (线性值)
    返回:
        ber: 误码率
    """
    snr_linear = np.asarray(snr_linear, dtype=float)
    return 0.5 * erfc(np.sqrt(snr_linear / 2))


def ber_ppm(snr_linear, M=4):
    """
    M-PPM 调制误码率 (无湍流) (教材式4.215)
    BER ≤ (M/2) / (M-1) · erfc(√(SNR·M·log2(M) / (4)))

    上界公式, 使用 union bound

    参数:
        snr_linear: 电信噪比 (每比特SNR, 线性值)
        M: PPM 阶数 (默认4)
    返回:
        ber: 误码率 (上界)
    """
    snr_linear = np.asarray(snr_linear, dtype=float)
    log2M = np.log2(M)
    # PPM的SNR增益
    arg = snr_linear * M * log2M / 4.0
    ber = (M / 2.0) / (M - 1) * 0.5 * erfc(np.sqrt(arg))
    return ber


def ber_sim_bpsk(snr_linear):
    """
    SIM-BPSK 调制误码率 (无湍流) (教材式4.222a)
    BER = ½ · erfc(√(SNR))

    副载波强度调制, BPSK调制

    参数:
        snr_linear: 电信噪比 (每比特SNR, 线性值)
    返回:
        ber: 误码率
    """
    snr_linear = np.asarray(snr_linear, dtype=float)
    return 0.5 * erfc(np.sqrt(snr_linear))


def ber_ook_turbulence(snr_linear, sigma_R2, num_points=50):
    """
    OOK 在湍流信道下的平均BER
    BER_avg = ∫ BER_OOK(SNR·I) · f(I) dI

    根据Rytov方差自动选择湍流分布 (依据开题报告式2.5阈值):
    - σ_R² < 1:       对数正态 (弱湍流)
    - 1 ≤ σ_R² ≤ 25:  Gamma-Gamma (中强湍流)
    - σ_R² > 25:      负指数 (饱和湍流)

    参数:
        snr_linear: 无湍流时的电SNR (线性值)
        sigma_R2: Rytov方差
        num_points: Gauss-Hermite积分点数 (对数正态)
    返回:
        ber_avg: 平均误码率
    """
    if sigma_R2 < 1.0:
        # 弱湍流: 对数正态分布
        # 使用 Gauss-Hermite 求积加速
        return _ber_avg_lognormal(snr_linear, sigma_R2, ber_ook, num_points)
    elif sigma_R2 <= 25.0:
        # 中强湍流: Gamma-Gamma分布
        alpha, beta = gamma_gamma_alpha_beta(sigma_R2)
        return _ber_avg_gamma_gamma(snr_linear, alpha, beta, ber_ook)
    else:
        # 饱和湍流: 负指数分布
        return _ber_avg_neg_exp(snr_linear, ber_ook)


def ber_ppm_turbulence(snr_linear, sigma_R2, M=4, num_points=50):
    """
    M-PPM 在湍流信道下的平均BER

    参数:
        snr_linear: 无湍流时的电SNR
        sigma_R2: Rytov方差
        M: PPM阶数
        num_points: 积分点数
    返回:
        ber_avg: 平均误码率
    """
    ber_func = lambda snr: ber_ppm(snr, M)

    if sigma_R2 < 1.0:
        return _ber_avg_lognormal(snr_linear, sigma_R2, ber_func, num_points)
    elif sigma_R2 <= 25.0:
        alpha, beta = gamma_gamma_alpha_beta(sigma_R2)
        return _ber_avg_gamma_gamma(snr_linear, alpha, beta, ber_func)
    else:
        return _ber_avg_neg_exp(snr_linear, ber_func)


def ber_sim_turbulence(snr_linear, sigma_R2, num_points=50):
    """
    SIM-BPSK 在湍流信道下的平均BER

    参数:
        snr_linear: 无湍流时的电SNR
        sigma_R2: Rytov方差
        num_points: 积分点数
    返回:
        ber_avg: 平均误码率
    """
    if sigma_R2 < 1.0:
        return _ber_avg_lognormal(snr_linear, sigma_R2, ber_sim_bpsk, num_points)
    elif sigma_R2 <= 25.0:
        alpha, beta = gamma_gamma_alpha_beta(sigma_R2)
        return _ber_avg_gamma_gamma(snr_linear, alpha, beta, ber_sim_bpsk)
    else:
        return _ber_avg_neg_exp(snr_linear, ber_sim_bpsk)


# ============ 内部积分辅助函数 ============


def _ber_avg_lognormal(snr_linear, sigma_R2, ber_func, num_points=50):
    """
    对数正态分布下的平均BER (Gauss-Hermite求积)

    变量替换: 令 x = (ln(I) + σ_l²/2) / (√2·σ_l)
    则 I = exp(√2·σ_l·x - σ_l²/2)
    ∫ BER(SNR·I)·f(I)dI = 1/√π · Σ w_i · BER(SNR·I_i)
    """
    sigma_l2 = sigma_R2
    sigma_l = np.sqrt(sigma_l2)

    # Gauss-Hermite 求积节点和权重
    x_nodes, weights = np.polynomial.hermite.hermgauss(num_points)

    # 变量替换
    I_vals = np.exp(np.sqrt(2) * sigma_l * x_nodes - sigma_l2 / 2)

    # 计算每个节点的BER
    ber_vals = ber_func(snr_linear * I_vals)

    # 加权求和
    ber_avg = np.sum(weights * ber_vals) / np.sqrt(np.pi)

    return ber_avg


def _ber_avg_gamma_gamma(snr_linear, alpha, beta, ber_func):
    """
    Gamma-Gamma分布下的平均BER (数值积分)
    BER_avg = ∫₀^∞ BER(SNR·I) · f_GG(I; α, β) dI
    """

    def integrand(I):
        if I <= 0:
            return 0.0
        pdf_val = gamma_gamma_pdf(np.array([I]), alpha, beta)[0]
        ber_val = float(ber_func(snr_linear * I))
        return ber_val * pdf_val

    # 数值积分, 上限取足够大
    result, error = quad(integrand, 1e-10, 50, limit=200, epsabs=1e-12, epsrel=1e-8)
    return result


def _ber_avg_neg_exp(snr_linear, ber_func):
    """
    负指数分布下的平均BER (数值积分)
    BER_avg = ∫₀^∞ BER(SNR·I) · exp(-I) dI
    """

    def integrand(I):
        if I <= 0:
            return 0.0
        ber_val = float(ber_func(snr_linear * I))
        return ber_val * np.exp(-I)

    result, error = quad(integrand, 0, 50, limit=200, epsabs=1e-15, epsrel=1e-10)
    return result


def ber_vs_snr(snr_db_range, modulation="OOK", sigma_R2=None, M_ppm=4):
    """
    生成 BER vs SNR 曲线数据 (方便绘图)

    参数:
        snr_db_range: SNR数组 (dB)
        modulation: 'OOK' / 'PPM' / 'SIM'
        sigma_R2: Rytov方差, None表示无湍流
        M_ppm: PPM阶数 (仅modulation='PPM'时使用)
    返回:
        ber_array: 对应每个SNR的BER值
    """
    snr_db = np.asarray(snr_db_range, dtype=float)
    snr_linear = 10 ** (snr_db / 10)

    if sigma_R2 is None or sigma_R2 == 0:
        # 无湍流 (AWGN) — 三种调制函数均支持向量化，直接传入数组
        if modulation == "OOK":
            return ber_ook(snr_linear)
        elif modulation == "PPM":
            return ber_ppm(snr_linear, M_ppm)
        elif modulation == "SIM":
            return ber_sim_bpsk(snr_linear)
        return np.zeros_like(snr_linear)

    # 有湍流 — 每点需数值积分，保留逐点循环
    ber_array = np.zeros_like(snr_linear)
    for i, snr_lin in enumerate(snr_linear):
        if modulation == "OOK":
            ber_array[i] = ber_ook_turbulence(snr_lin, sigma_R2)
        elif modulation == "PPM":
            ber_array[i] = ber_ppm_turbulence(snr_lin, sigma_R2, M_ppm)
        elif modulation == "SIM":
            ber_array[i] = ber_sim_turbulence(snr_lin, sigma_R2)
    return ber_array
