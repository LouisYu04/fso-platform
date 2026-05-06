"""
链路预算与信噪比计算
适用范围: 近地水平路径直接检测(IM/DD) FSO链路

包含:
- 链路预算 (接收功率计算) (式2.34, 2.35)
- PIN/APD 探测器 SNR 计算 (式2.8, 2.11, 2.12)
- 噪声功率计算 (热噪声, 散粒噪声)
"""

import numpy as np
from ..utils.constants import K_B, Q_E, H, C, PI, watt_to_dbm, dbm_to_watt


def received_power(
    P_T_w, G_T, G_R, tau_atm, L_geo, L_point=1.0, mu_T=1.0, mu_R=1.0, L_M_db=0.0
):
    """
    接收功率 (链路预算公式, 开题报告式2.16)
    P_R = P_T - 4.343·L·βa - L_Geom - L₀ - Lp - L_M  (dB域)

    线性域等价形式:
    P_R = P_T · τ_atm · L_geo · L_point · μ_T · μ_R · 10^(-L_M/10)

    注: G_T和G_R为预留接口参数, 当前由L_geo统一处理几何损耗,
        不单独计入以避免与孔径效应重复计算.
        τ_atm 已包含大气散射/吸收损耗 (Beer-Lambert).
        L_geo 已包含几何扩散损耗 (含发射/接收孔径).
        L₀/μ_T/μ_R 为光学元件效率.
        L_M 为系统余量 (dB), 用于设计预留, 默认0不影响向后兼容.

    参数:
        P_T_w: 发射功率 (W)
        G_T: 发射增益 (线性, 预留接口-当前由L_geo统一处理)
        G_R: 接收增益 (线性, 预留接口-当前由L_geo统一处理)
        tau_atm: 大气透过率 (0~1)
        L_geo: 几何损耗 (0~1)
        L_point: 指向误差损耗 (0~1), 默认1无损耗
        mu_T: 发射光学效率 (0~1), 默认1
        mu_R: 接收光学效率 (0~1), 默认1
        L_M_db: 系统余量 (dB, 默认0), 对应开题报告式2.16中的 L_M 项
    返回:
        P_R: 接收功率 (W)
    """
    L_M_linear = 10 ** (-L_M_db / 10.0)
    P_R = P_T_w * tau_atm * L_geo * L_point * mu_T * mu_R * L_M_linear
    return P_R


def received_power_dbm(
    P_T_w, tau_atm, L_geo, L_point=1.0, mu_T=1.0, mu_R=1.0, L_M_db=0.0
):
    """
    接收功率 (dBm)

    参数: 同 received_power (省略 G_T, G_R)
        L_M_db: 系统余量 (dB, 默认0)
    返回:
        P_R_dbm: 接收功率 (dBm)
    """
    L_M_linear = 10 ** (-L_M_db / 10.0)
    P_R = P_T_w * tau_atm * L_geo * L_point * mu_T * mu_R * L_M_linear
    return watt_to_dbm(P_R) if P_R > 0 else -np.inf


def noise_thermal(T_K, bandwidth_Hz, R_L_ohm):
    """
    热噪声方差 (教材式2.7)
    σ²_th = 4·k_B·T·B / R_L

    参数:
        T_K: 温度 (K)
        bandwidth_Hz: 电带宽 (Hz)
        R_L_ohm: 负载电阻 (Ω)
    返回:
        sigma2_th: 热噪声功率 (A²)
    """
    return 4 * K_B * T_K * bandwidth_Hz / R_L_ohm


def noise_shot(R_p, P_R_w, P_B_w, bandwidth_Hz):
    """
    散粒噪声方差 (教材式2.7)
    σ²_sh = 2·q·R_p·(P_R + P_B)·B

    参数:
        R_p: 探测器响应度 (A/W)
        P_R_w: 接收信号功率 (W)
        P_B_w: 背景光功率 (W)
        bandwidth_Hz: 电带宽 (Hz)
    返回:
        sigma2_sh: 散粒噪声功率 (A²)
    """
    return 2 * Q_E * R_p * (P_R_w + P_B_w) * bandwidth_Hz


def snr_pin(P_R_w, R_p, m, T_K, bandwidth_Hz, R_L_ohm, P_B_w=0.0):
    """
    PIN探测器信噪比 (教材式2.8)
    SNR = ½·m²·(R_p·P_R)² / (σ²_th + σ²_sh)

    其中:
    σ²_th = 4k_BT·B/R_L  (热噪声)
    σ²_sh = 2q·R_p·(P_R+P_B)·B  (散粒噪声)

    参数:
        P_R_w: 接收功率 (W)
        R_p: 响应度 (A/W)
        m: 调制深度 (0~1), OOK时m=1
        T_K: 等效噪声温度 (K)
        bandwidth_Hz: 电带宽 (Hz)
        R_L_ohm: 负载电阻 (Ω)
        P_B_w: 背景光功率 (W)
    返回:
        snr: 信噪比 (线性值)
    """
    signal_power = 0.5 * m**2 * (R_p * P_R_w) ** 2

    sigma2_th = noise_thermal(T_K, bandwidth_Hz, R_L_ohm)
    sigma2_sh = noise_shot(R_p, P_R_w, P_B_w, bandwidth_Hz)

    noise_power = sigma2_th + sigma2_sh

    if noise_power <= 0:
        return np.inf

    return signal_power / noise_power


def snr_pin_db(P_R_w, R_p, m, T_K, bandwidth_Hz, R_L_ohm, P_B_w=0.0):
    """
    PIN探测器信噪比 (dB)

    参数: 同 snr_pin
    返回:
        snr_db: 信噪比 (dB)
    """
    snr = snr_pin(P_R_w, R_p, m, T_K, bandwidth_Hz, R_L_ohm, P_B_w)
    return 10 * np.log10(snr) if snr > 0 else -np.inf


def snr_apd(P_R_w, R_p, M_apd, F_apd, m, T_K, bandwidth_Hz, R_L_ohm, P_B_w=0.0):
    """
    APD探测器信噪比 (教材式2.12)
    SNR = ½·m²·(M·R_p·P_R)² / (2q·R_p·M²·F·(P_R+P_B)·B + 4k_BT·B/R_L)

    参数:
        P_R_w: 接收功率 (W)
        R_p: 未增益响应度 (A/W)
        M_apd: APD增益
        F_apd: APD噪声因子 F = M^x, x~0.3(Si), 0.7(InGaAs)
        m: 调制深度
        T_K: 温度 (K)
        bandwidth_Hz: 电带宽 (Hz)
        R_L_ohm: 负载电阻 (Ω)
        P_B_w: 背景光功率 (W)
    返回:
        snr: 信噪比 (线性值)
    """
    signal = 0.5 * m**2 * (M_apd * R_p * P_R_w) ** 2

    shot = 2 * Q_E * R_p * M_apd**2 * F_apd * (P_R_w + P_B_w) * bandwidth_Hz
    thermal = noise_thermal(T_K, bandwidth_Hz, R_L_ohm)

    noise = shot + thermal

    if noise <= 0:
        return np.inf

    return signal / noise


def link_margin(P_R_dbm, sensitivity_dbm):
    """
    链路余量
    Margin = P_R(dBm) - Sensitivity(dBm)

    参数:
        P_R_dbm: 接收功率 (dBm)
        sensitivity_dbm: 接收灵敏度 (dBm)
    返回:
        margin_db: 链路余量 (dB), >0 表示链路可用
    """
    return P_R_dbm - sensitivity_dbm


def bandwidth_from_datarate(data_rate_bps, modulation="OOK", M_ppm=4):
    """
    根据数据速率估算所需电带宽

    OOK: B ≈ R_b
    PPM: B ≈ M·R_b / log2(M)  (M-PPM)
    SIM: B ≈ R_b

    参数:
        data_rate_bps: 数据速率 (bps)
        modulation: 'OOK' / 'PPM' / 'SIM'
        M_ppm: PPM 阶数 (仅 modulation='PPM' 时使用, 默认4)
    返回:
        bandwidth_Hz: 电带宽 (Hz)
    """
    if modulation == "OOK":
        return data_rate_bps
    elif modulation == "PPM":
        return M_ppm * data_rate_bps / np.log2(M_ppm)
    elif modulation == "SIM":
        return data_rate_bps
    else:
        return data_rate_bps
