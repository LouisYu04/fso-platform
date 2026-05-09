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
from ..utils.constants import H, C, Q_E, K_B

from .distributions import (
    lognormal_pdf,
    gamma_gamma_pdf,
    gamma_gamma_alpha_beta,
    negative_exponential_pdf,
)


def ber_ook(snr_linear):
    """
    OOK 调制误码率 (文献式4.207)

    文献在图4-44前定义归一化 SNR = (R·E[I])² / σ²。等概率符号、
    消光比为 0 时最佳固定阈值 i_th = 0.5·R·I，因此
    P_ec = Q(i_th/σ) = Q(0.5·√SNR)
          = 0.5·erfc(0.5·√SNR / √2)。

    参数:
        snr_linear: 电信噪比 (线性值)
    返回:
        ber: 误码率
    """
    snr_linear = np.asarray(snr_linear, dtype=float)
    return _qfunc(0.5 * np.sqrt(snr_linear))


def ber_ppm(snr_linear, M=4):
    """
    M-PPM 调制误码率上界的 SNR 形式。

    文献式(4.212)和(4.215)的严格变量是每时隙光子数 K_s、背景光子数
    K_Bg、APD 增益和热噪声计数。为兼容 BER-vs-SNR 曲线，本函数把
    snr_linear 解释为式(4.212)中 Q 函数根号内的等效判决 SNR，并使用
    M-PPM 上界 P_e^M <= M/2 * Q(sqrt(snr_eff))。

    真实链路计算应优先使用 ber_ppm_photon()。

    上界公式, 使用 union bound

    参数:
        snr_linear: 电信噪比 (每比特SNR, 线性值)
        M: PPM 阶数 (默认4)
    返回:
        ber: 误码率 (上界)
    """
    snr_linear = np.asarray(snr_linear, dtype=float)
    return np.minimum(1.0, (M / 2.0) * _qfunc(np.sqrt(snr_linear)))


def ber_sim_bpsk(snr_linear):
    """
    SIM-BPSK 调制误码率 (文献式4.220附近)
    P_ec = Q(√γ) = ½ · erfc(√γ / √2)

    副载波强度调制, BPSK调制

    参数:
        snr_linear: 电信噪比 (每比特SNR, 线性值)
    返回:
        ber: 误码率
    """
    snr_linear = np.asarray(snr_linear, dtype=float)
    return _qfunc(np.sqrt(snr_linear))


def _qfunc(x):
    """Gaussian Q 函数 Q(x)=0.5*erfc(x/sqrt(2))，支持标量和数组。"""
    return 0.5 * erfc(np.asarray(x, dtype=float) / np.sqrt(2.0))


def ppm_slot_duration(bit_rate_bps, M):
    """
    文献式(4.210): T_s = T·log2(M)/M，其中 T=1/R_b。
    """
    if bit_rate_bps <= 0:
        raise ValueError(f"bit_rate_bps 必须 > 0，当前值: {bit_rate_bps}")
    if M <= 1:
        raise ValueError(f"M 必须 > 1，当前值: {M}")
    return np.log2(M) / (M * bit_rate_bps)


def ppm_photon_count(P_R_w, wavelength_m, bit_rate_bps, M, quantum_efficiency=1.0):
    """
    文献式(4.211): K_s = eta·lambda·P_R·T_s / (h·c)。
    """
    T_s = ppm_slot_duration(bit_rate_bps, M)
    return quantum_efficiency * wavelength_m * P_R_w * T_s / (H * C)


def ber_ppm_photon(
    P_R_w,
    P_B_w,
    wavelength_m,
    bit_rate_bps,
    M=4,
    quantum_efficiency=1.0,
    apd_gain=1.0,
    apd_noise_factor=1.0,
    temperature_K=300.0,
    R_L_ohm=50.0,
):
    """
    M-PPM 光子计数误码率上界 (文献式4.212/4.215)。

    对 M=2 时为二元 PPM 条件误码率；M>2 时按式(4.215)给出上界。
    """
    K_s = ppm_photon_count(P_R_w, wavelength_m, bit_rate_bps, M, quantum_efficiency)
    K_bg = ppm_photon_count(P_B_w, wavelength_m, bit_rate_bps, M, quantum_efficiency)
    T_s = ppm_slot_duration(bit_rate_bps, M)
    sigma_th_count2 = 2.0 * K_B * temperature_K * T_s / (R_L_ohm * Q_E)
    denominator = (apd_gain * Q_E) ** 2 * apd_noise_factor * (K_s + 2.0 * K_bg)
    denominator += 2.0 * (Q_E**2) * sigma_th_count2
    if denominator <= 0:
        return 0.5
    argument = np.sqrt(((apd_gain * Q_E) ** 2 * K_s**2) / denominator)
    multiplier = 1.0 if M == 2 else M / 2.0
    return min(1.0, float(multiplier * _qfunc(argument)))


def ber_ook_turbulence(snr_linear, sigma_R2, num_points=50):
    """
    OOK 在湍流信道下的平均BER（固定阈值，文献式4.204~4.208）

    阈值固定在平均光强对应的一半: i_th = 0.5·R·E[I]。归一化 E[I]=1 后:
    P_e = 0.5·Q(0.5√SNR) + 0.5·∫Q((I-0.5)√SNR)f(I)dI。

    该形式能复现文献图4-44/4-45讨论的固定阈值 BER floor；它不同于
    对 BER(SNR·I) 直接平均的自适应阈值近似。

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
    sqrt_snr = np.sqrt(float(snr_linear))
    no_pulse_error = _qfunc(0.5 * sqrt_snr)

    def pulse_error(I):
        return _qfunc((I - 0.5) * sqrt_snr)

    if sigma_R2 < 1.0:
        pulse_avg = _expectation_lognormal(sigma_R2, pulse_error, num_points)
    elif sigma_R2 <= 25.0:
        alpha, beta = gamma_gamma_alpha_beta(sigma_R2)
        pulse_avg = _expectation_gamma_gamma(alpha, beta, pulse_error)
    else:
        pulse_avg = _expectation_neg_exp(pulse_error)
    return float(0.5 * no_pulse_error + 0.5 * pulse_avg)


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


def _expectation_lognormal(sigma_R2, func, num_points=50):
    """计算 E[func(I)]，其中 I 为均值归一化的对数正态光强。"""
    sigma_l2 = sigma_R2
    sigma_l = np.sqrt(sigma_l2)
    x_nodes, weights = np.polynomial.hermite.hermgauss(num_points)
    I_vals = np.exp(np.sqrt(2) * sigma_l * x_nodes - sigma_l2 / 2)
    vals = func(I_vals)
    return np.sum(weights * vals) / np.sqrt(np.pi)


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


def _expectation_gamma_gamma(alpha, beta, func):
    """计算 Gamma-Gamma 分布下的 E[func(I)]。"""

    def integrand(I):
        if I <= 0:
            return 0.0
        pdf_val = gamma_gamma_pdf(np.array([I]), alpha, beta)[0]
        return float(func(I)) * pdf_val

    result, _error = quad(integrand, 1e-10, 50, limit=200, epsabs=1e-12, epsrel=1e-8)
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


def _expectation_neg_exp(func):
    """计算负指数分布下的 E[func(I)]。"""

    def integrand(I):
        if I <= 0:
            return 0.0
        return float(func(I)) * np.exp(-I)

    result, _error = quad(integrand, 0, 50, limit=200, epsabs=1e-15, epsrel=1e-10)
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
