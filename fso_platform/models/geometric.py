"""
几何损耗与指向误差模型
适用范围: 近地水平路径FSO链路

包含:
- 光束扩展与几何损耗 (式2.25, 4.7)
- 发射/接收增益 (式2.30, 2.33)
- 指向误差损耗模型
"""

import numpy as np
from ..utils.constants import PI


def beam_diameter_at_distance(D_T_m, theta_div_rad, distance_m):
    """
    传输距离L处的光斑直径 (远场近似)
    D_beam ≈ D_T + θ_div · L

    对于激光束:
    D_beam = D_T · [1 + (λR / (D_T²))²]^(1/2)  (教材式2.25, 近似)

    简化为: D_beam ≈ θ_div · L (远场 L >> D_T²/λ)

    参数:
        D_T_m: 发射口径 (m)
        theta_div_rad: 全角发散角 (rad)
        distance_m: 传输距离 (m)
    返回:
        D_beam: 距离L处的光斑直径 (m)
    """
    D_beam = D_T_m + theta_div_rad * distance_m
    return D_beam


def geometric_loss(D_R_m, D_beam_m):
    """
    几何损耗 (教材式4.7)
    L_geo = (D_R / D_beam)²

    当接收口径 < 光斑直径时, 只能捕获部分光功率

    参数:
        D_R_m: 接收口径直径 (m)
        D_beam_m: 接收面处光斑直径 (m)
    返回:
        L_geo: 几何损耗 (0~1, 线性值)
    """
    if D_R_m >= D_beam_m:
        return 1.0  # 接收口径大于光斑, 无几何损耗
    return (D_R_m / D_beam_m) ** 2


def geometric_loss_db(D_R_m, D_beam_m):
    """
    几何损耗 (dB)

    参数:
        D_R_m: 接收口径直径 (m)
        D_beam_m: 接收面处光斑直径 (m)
    返回:
        L_geo_db: 几何损耗 (dB, 负值表示损耗)
    """
    L = geometric_loss(D_R_m, D_beam_m)
    if L <= 0:
        return -np.inf
    return 10 * np.log10(L)


def transmitter_gain(D_T_m, wavelength_m):
    """
    发射增益 (教材式2.30)
    G_T ≈ (4·D_T / λ)²

    注: 这是假设均匀照明口径的近似公式

    参数:
        D_T_m: 发射口径 (m)
        wavelength_m: 波长 (m)
    返回:
        G_T: 发射增益 (线性值)
    """
    return (4 * D_T_m / wavelength_m) ** 2


def receiver_gain(D_R_m, wavelength_m):
    """
    接收增益 (教材式2.33)
    G_R = (4π / λ²) · A_R

    其中 A_R = π(D_R/2)² 为接收孔径面积

    参数:
        D_R_m: 接收口径直径 (m)
        wavelength_m: 波长 (m)
    返回:
        G_R: 接收增益 (线性值)
    """
    A_R = PI * (D_R_m / 2) ** 2
    G_R = (4 * PI / wavelength_m**2) * A_R
    return G_R


def pointing_error_loss(sigma_s_rad, beam_waist_m, distance_m, wavelength_m=1550e-9):
    """
    指向误差引起的功率损耗 (统计平均)

    指向抖动建模为瞄准误差角的高斯分布, 标准差为 σ_s
    等效光束宽度: w_eq² = w_z² · √(π)·erf(v)/(2v·exp(-v²))
    其中 v = √(π)·a/(√2·w_z), a = D_R/2, w_z = 接收面处光束半径

    简化模型 (Farid & Hranilovic):
    h_p(r) = A_0 · exp(-2r²/w_eq²)

    平均指向损耗 ≈ A_0 · σ_s² / (σ_s² + w_eq²/(4))
    (A_0 为零偏移时的最大收集效率)

    参数:
        sigma_s_rad: 指向抖动标准差 (rad)
        beam_waist_m: 发射光束束腰半径 (m)
        distance_m: 传输距离 (m)
        wavelength_m: 工作波长 (m)，默认 1550e-9 (1550 nm)
    返回:
        (avg_loss, A_0): 平均指向损耗(0~1), 零偏移收集效率
    """
    # 接收面处光束半径 (1/e²)
    w_z = beam_waist_m * np.sqrt(
        1 + (distance_m * wavelength_m / (PI * beam_waist_m**2)) ** 2
    )

    # 指向抖动在接收面的线性偏移标准差
    sigma_jitter_m = sigma_s_rad * distance_m

    # 简化: A_0 ≈ 1 (假设接收口径匹配时)
    A_0 = 1.0

    # 等效光束宽度 (简化)
    w_eq_sq = w_z**2

    # 平均指向损耗
    avg_loss = A_0 * w_eq_sq / (w_eq_sq + 4 * sigma_jitter_m**2)

    return avg_loss, A_0


def pointing_error_loss_simple(sigma_s_rad, theta_div_rad):
    """
    简化指向误差损耗模型
    L_point ≈ exp(-2·(σ_s/θ_div)²)

    当指向抖动远小于发散角时损耗很小

    参数:
        sigma_s_rad: 指向抖动标准差 (rad)
        theta_div_rad: 光束发散半角 (rad)，必须 > 0
    返回:
        L_point: 指向误差损耗 (0~1)
    异常:
        ValueError: theta_div_rad <= 0
    """
    if theta_div_rad <= 0:
        raise ValueError(f"theta_div_rad 必须 > 0，当前值: {theta_div_rad}")
    return np.exp(-2 * (sigma_s_rad / theta_div_rad) ** 2)
