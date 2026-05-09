"""
物理常量与单位换算工具
用于无线光通信系统链路特性计算

约定:
    - 所有物理常量使用 SI 单位。
    - 波长常量使用米 (m)，因为湍流、波数和频率公式都以 SI 单位书写。
    - dB/dBm 换算函数支持标量和 NumPy 数组；调用方负责保证输入物理有效。

注意:
    本模块不做过度输入校验。例如 watt_to_dbm(0) 会返回 -inf，
    watt_to_dbm(负数) 会返回 nan。这种行为来自 NumPy，测试中也覆盖了这些
    边界，便于上层模型按需要处理极端值。
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
    波长转波数。

    k = 2π/λ

    波数 k 是 Rytov 方差、Fried 参数等湍流公式的核心输入，单位为 rad/m。
    函数不限制 wavelength_m 的类型，因此可直接接收 ndarray 做向量化计算。

    参数:
        wavelength_m: 波长 (m)
    返回:
        波数 k (rad/m)
    """
    return 2 * PI / wavelength_m


def wavelength_to_frequency(wavelength_m):
    """
    波长转频率。

    f = c/λ

    主要用于需要从光波长推导光频率或光子能量的扩展模型。当前主流程多使用
    波长和波数，因此此函数更多作为通用工具保留。

    参数:
        wavelength_m: 波长 (m)
    返回:
        频率 f (Hz)
    """
    return C / wavelength_m


def dbm_to_watt(power_dbm):
    """
    dBm 转瓦特。

    P(W) = 10^(P(dBm)/10) / 1000

    dBm 是以 1 mW 为参考的绝对功率单位：
        0 dBm = 1 mW = 1e-3 W
        10 dBm = 10 mW
        30 dBm = 1 W

    参数:
        power_dbm: 功率 (dBm)
    返回:
        功率 (W)
    """
    return 10 ** (power_dbm / 10) / 1000


def watt_to_dbm(power_w):
    """
    瓦特转 dBm。

    P(dBm) = 10·log10(P(W)·1000)

    上层链路预算常用 dBm 展示功率，因为各类 dB 损耗可以直接相加减。
    若 power_w <= 0，NumPy 会返回 -inf 或 nan，调用方可据此判断无效功率。

    参数:
        power_w: 功率 (W)
    返回:
        功率 (dBm)
    """
    return 10 * np.log10(power_w * 1000)


def db_to_linear(value_db):
    """
    dB 转线性比例。

    适用于功率比值：
        linear = 10^(dB/10)

    例如 -3 dB 约等于 0.5，10 dB 等于 10。
    """
    return 10 ** (value_db / 10)


def linear_to_db(value_linear):
    """
    线性比例转 dB。

    适用于功率比值：
        dB = 10·log10(linear)

    注意这里不是 dBm；dBm 需要以 1 mW 为参考，应使用 watt_to_dbm()。
    """
    return 10 * np.log10(value_linear)
