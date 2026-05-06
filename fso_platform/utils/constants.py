"""
物理常量定义
用于无线光通信系统链路特性计算
"""

import numpy as np

# 光速 (m/s) — 精确值
C = 299792458.0

# 玻尔兹曼常量 (J/K) — CODATA 2018 精确值
K_B = 1.380649e-23

# 电子电荷 (C) — CODATA 2018 精确值
Q_E = 1.602176634e-19

# 普朗克常量 (J·s) — CODATA 2018 精确值
H = 6.62607015e-34

# 圆周率
PI = np.pi

# --- 常用波长 (m) ---
LAMBDA_850 = 850e-9  # 850 nm
LAMBDA_1064 = 1064e-9  # 1064 nm
LAMBDA_1550 = 1550e-9  # 1550 nm

# --- 参考波长 (nm) ---
LAMBDA_REF_NM = 550  # Kim模型参考波长 550 nm


def wavelength_to_wavenumber(wavelength_m):
    """
    波长转波数
    k = 2π/λ

    参数:
        wavelength_m: 波长 (m)
    返回:
        波数 k (rad/m)
    """
    return 2 * PI / wavelength_m


def wavelength_to_frequency(wavelength_m):
    """
    波长转频率
    f = c/λ

    参数:
        wavelength_m: 波长 (m)
    返回:
        频率 f (Hz)
    """
    return C / wavelength_m


def dbm_to_watt(power_dbm):
    """
    dBm 转 瓦特
    P(W) = 10^(P(dBm)/10) / 1000

    参数:
        power_dbm: 功率 (dBm)
    返回:
        功率 (W)
    """
    return 10 ** (power_dbm / 10) / 1000


def watt_to_dbm(power_w):
    """
    瓦特 转 dBm
    P(dBm) = 10·log10(P(W)·1000)

    参数:
        power_w: 功率 (W)
    返回:
        功率 (dBm)
    """
    return 10 * np.log10(power_w * 1000)


def db_to_linear(value_db):
    """dB 转线性值"""
    return 10 ** (value_db / 10)


def linear_to_db(value_linear):
    """线性值 转 dB"""
    return 10 * np.log10(value_linear)
