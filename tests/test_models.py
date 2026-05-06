"""
核心模型验证测试
对照教材典型参数和已知理论值验证计算准确性

使用教材表4.6参数:
    d_R=8cm, d_T=2.5cm, θ=2mrad, OOK@155Mb/s
    P_T=14dBm, sensitivity=-30dBm, λ=850nm
"""

import sys
import os
import numpy as np

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fso_platform.utils.constants import (
    dbm_to_watt,
    watt_to_dbm,
    wavelength_to_wavenumber,
    db_to_linear,
)
from fso_platform.models.atmosphere import (
    kim_p,
    attenuation_coefficient,
    beer_lambert,
    atmospheric_attenuation_db,
    total_channel_loss_db,
    transmittance,
    rain_attenuation,
)
from fso_platform.models.turbulence import (
    rytov_variance,
    rytov_variance_spherical,
    turbulence_regime,
    scintillation_index_plane_wave,
    scintillation_index_spherical_wave,
    cn2_typical,
)
from fso_platform.models.distributions import (
    lognormal_pdf,
    gamma_gamma_pdf,
    gamma_gamma_alpha_beta,
    negative_exponential_pdf,
    select_distribution,
)
from fso_platform.models.geometric import (
    beam_diameter_at_distance,
    geometric_loss,
    geometric_loss_db,
    transmitter_gain,
    receiver_gain,
)
from fso_platform.models.link_budget import (
    received_power,
    snr_pin,
    snr_pin_db,
    noise_thermal,
    noise_shot,
    link_margin,
    bandwidth_from_datarate,
)
from fso_platform.models.ber import (
    ber_ook,
    ber_ppm,
    ber_sim_bpsk,
    ber_ook_turbulence,
    ber_ppm_turbulence,
    ber_sim_turbulence,
    ber_vs_snr,
)


def separator(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def test_atmosphere():
    """测试大气衰减模型"""
    separator("1. 大气衰减模型测试")

    # --- Kim模型 p 值测试 ---
    print("\n[Kim模型 p值]")
    test_cases_p = [
        (0.2, 0.0, "浓雾 V=0.2km"),
        (0.5, 0.0, "雾 V=0.5km"),
        (0.8, 0.3, "薄雾 V=0.8km"),
        (2.0, 0.66, "轻雾 V=2km"),
        (10.0, 1.3, "晴天 V=10km"),
        (23.0, 1.3, "极清 V=23km"),
    ]
    all_pass = True
    for V, expected_p, label in test_cases_p:
        p = kim_p(V)
        match = abs(p - expected_p) < 0.01
        status = "OK" if match else "FAIL"
        if not match:
            all_pass = False
        print(f"  {label}: p={p:.3f} (期望{expected_p:.2f}) [{status}]")
    print(f"  Kim模型: {'全部通过' if all_pass else '存在错误!'}")

    # --- 衰减系数测试 ---
    print("\n[衰减系数 σ(λ)  — 单位: Naperian km⁻¹]")
    # 教材表4.5: 清晰天气 V~23km
    sigma_clear = attenuation_coefficient(23, 1550)
    sigma_fog = attenuation_coefficient(0.5, 1550)
    print(
        f"  晴天(V=23km, λ=1550nm): σ = {sigma_clear:.3f} Nap/km  → {4.343 * sigma_clear:.3f} dB/km"
    )
    print(
        f"  浓雾(V=0.5km, λ=1550nm): σ = {sigma_fog:.2f} Nap/km  → {4.343 * sigma_fog:.2f} dB/km"
    )
    print(
        f"  浓雾(V=0.5km, λ=850nm):  σ = {attenuation_coefficient(0.5, 850):.2f} Nap/km"
    )

    print("\n[Beer-Lambert 透过率  — τ = exp(-σ·L), σ 单位 Naperian km⁻¹]")
    # 1km, 晴天
    tau_clear_1km = beer_lambert(sigma_clear, 1.0)
    tau_fog_1km = beer_lambert(sigma_fog, 1.0)
    print(f"  晴天 1km: τ = {tau_clear_1km:.4f} ({4.343 * sigma_clear:.2f} dB 衰减)")
    print(f"  浓雾 1km: τ = {tau_fog_1km:.6f} ({4.343 * sigma_fog:.1f} dB 衰减)")

    # 5km 距离
    tau_clear_5km = beer_lambert(sigma_clear, 5.0)
    print(
        f"  晴天 5km: τ = {tau_clear_5km:.4f} ({4.343 * sigma_clear * 5:.2f} dB 衰减)"
    )

    # --- 雨天衰减 ---
    print("\n[雨天衰减]")
    rain_25 = rain_attenuation(2.5)
    rain_10 = rain_attenuation(10)
    print(f"  中雨(2.5mm/h): {rain_25:.2f} dB/km")
    print(f"  大雨(10mm/h):  {rain_10:.2f} dB/km")

    # --- 综合信道损耗 ---
    print("\n[综合信道损耗]")
    loss_clear = total_channel_loss_db(23, 1.0, 1550)
    loss_fog = total_channel_loss_db(0.5, 1.0, 1550)
    loss_rain = total_channel_loss_db(5, 1.0, 1550, rainfall_rate=10)
    print(f"  晴天 1km:   {loss_clear:.2f} dB")
    print(f"  浓雾 1km:   {loss_fog:.2f} dB")
    print(f"  雨天 1km:   {loss_rain:.2f} dB (V=5km + 10mm/h雨)")


def test_turbulence():
    """测试大气湍流模型"""
    separator("2. 大气湍流模型测试")

    # 教材参考: λ=1.55μm, Cn²=10^-14, L=1000m (图4-23)
    wavelength = 1.55e-6
    Cn2 = 1e-14
    L = 1000

    sigma_R2 = rytov_variance(Cn2, wavelength, L)
    k = wavelength_to_wavenumber(wavelength)
    print(f"\n[Rytov方差] λ={wavelength * 1e6:.2f}μm, Cn²={Cn2:.0e}, L={L}m")
    print(f"  k = {k:.2f} rad/m")
    print(f"  σ_R² = {sigma_R2:.4f}")
    print(f"  湍流强度: {turbulence_regime(sigma_R2)}")

    # 球面波
    beta2 = rytov_variance_spherical(Cn2, wavelength, L)
    print(f"  β₀² (球面波) = {beta2:.4f}")
    print(f"  验证: β₀²/σ_R² = {beta2 / sigma_R2:.2f} (应为0.4)")

    # 不同距离的Rytov方差
    print(f"\n[Rytov方差 vs 距离] λ=1.55μm, Cn²=1e-14")
    for L_test in [100, 500, 1000, 2000, 5000]:
        sr2 = rytov_variance(Cn2, wavelength, L_test)
        regime = turbulence_regime(sr2)
        print(f"  L={L_test:5d}m: σ_R²={sr2:.4f} ({regime})")

    # 闪烁指数 (弱到强)
    print(f"\n[闪烁指数 - 平面波]")
    for sr2 in [0.1, 0.5, 1.0, 5.0, 10.0, 50.0]:
        si2 = scintillation_index_plane_wave(sr2)
        print(f"  σ_R²={sr2:5.1f}: σ_I²={si2:.4f} ({turbulence_regime(sr2)})")
    print(f"  注: 强湍流下 σ_I² 应趋近于 1.0")


def test_distributions():
    """测试光强概率分布"""
    separator("3. 光强概率分布测试")

    I_vals = np.linspace(0.01, 5.0, 500)

    # --- 对数正态 (弱湍流) ---
    sigma_R2 = 0.1
    pdf_ln = lognormal_pdf(I_vals, sigma_R2)
    integral_ln = np.trapezoid(pdf_ln, I_vals)
    mean_ln = np.trapezoid(I_vals * pdf_ln, I_vals)
    print(f"\n[对数正态] σ_R²={sigma_R2}")
    print(f"  积分 = {integral_ln:.4f} (应≈1.0)")
    print(f"  均值 = {mean_ln:.4f} (应≈1.0)")

    # --- Gamma-Gamma (中强湍流) ---
    sigma_R2 = 2.0
    alpha, beta = gamma_gamma_alpha_beta(sigma_R2)
    pdf_gg = gamma_gamma_pdf(I_vals, alpha, beta)
    integral_gg = np.trapezoid(pdf_gg, I_vals)
    mean_gg = np.trapezoid(I_vals * pdf_gg, I_vals)
    print(f"\n[Gamma-Gamma] σ_R²={sigma_R2}")
    print(f"  α={alpha:.4f}, β={beta:.4f}")
    print(f"  积分 = {integral_gg:.4f} (应≈1.0)")
    print(f"  均值 = {mean_gg:.4f} (应≈1.0)")

    # --- 负指数 (饱和湍流) ---
    pdf_ne = negative_exponential_pdf(I_vals)
    integral_ne = np.trapezoid(pdf_ne, I_vals)
    mean_ne = np.trapezoid(I_vals * pdf_ne, I_vals)
    print(f"\n[负指数]")
    print(f"  积分 = {integral_ne:.4f} (应≈1.0)")
    print(f"  均值 = {mean_ne:.4f} (应≈1.0)")

    # --- 自动选择 ---
    print(f"\n[分布自动选择]")
    for sr2 in [0.1, 1.0, 10.0]:
        name, _, params = select_distribution(sr2)
        print(f"  σ_R²={sr2}: {name} {params}")


def test_geometric():
    """测试几何损耗"""
    separator("4. 几何损耗测试")

    # 教材表4.6参数: d_T=2.5cm, d_R=8cm, θ=2mrad
    D_T = 0.025  # 2.5 cm
    D_R = 0.08  # 8 cm
    theta_div = 2e-3  # 2 mrad (全角)

    print(f"\n[光斑扩展] D_T={D_T * 100}cm, θ={theta_div * 1e3}mrad")
    for L in [100, 500, 1000, 2000, 5000]:
        D_beam = beam_diameter_at_distance(D_T, theta_div, L)
        L_geo = geometric_loss(D_R, D_beam)
        L_geo_db = geometric_loss_db(D_R, D_beam)
        print(
            f"  L={L:5d}m: D_beam={D_beam * 100:.1f}cm, "
            f"L_geo={L_geo:.6f} ({L_geo_db:.2f} dB)"
        )

    # 增益
    wavelength = 850e-9
    GT = transmitter_gain(D_T, wavelength)
    GR = receiver_gain(D_R, wavelength)
    print(f"\n[增益] λ=850nm")
    print(f"  G_T = {GT:.2e} ({10 * np.log10(GT):.1f} dB)")
    print(f"  G_R = {GR:.2e} ({10 * np.log10(GR):.1f} dB)")


def test_link_budget():
    """测试链路预算"""
    separator("5. 链路预算测试")

    # 教材表4.6参数
    P_T_dbm = 14  # dBm
    P_T_w = dbm_to_watt(P_T_dbm)
    wavelength = 850e-9
    D_T = 0.025
    D_R = 0.08
    theta_div = 2e-3
    L = 1000  # 1 km
    V = 23  # 晴天能见度
    R_p = 0.5  # 响应度 A/W
    T = 300  # 温度 K
    R_L = 50  # 负载电阻 Ω
    data_rate = 155e6  # 155 Mbps
    B = bandwidth_from_datarate(data_rate, "OOK")

    print(f"\n[链路参数]")
    print(f"  P_T = {P_T_dbm} dBm = {P_T_w * 1000:.2f} mW")
    print(f"  λ = {wavelength * 1e9:.0f} nm")
    print(f"  L = {L} m")
    print(f"  V = {V} km (晴天)")

    # 大气衰减
    from fso_platform.models.atmosphere import attenuation_coefficient

    sigma = attenuation_coefficient(V, wavelength * 1e9)
    tau_atm = beer_lambert(sigma, L / 1000)
    print(
        f"  大气衰减: σ={sigma:.3f} Nap/km ({4.343 * sigma:.3f} dB/km), τ={tau_atm:.4f}"
    )

    # 几何损耗
    D_beam = beam_diameter_at_distance(D_T, theta_div, L)
    L_geo = geometric_loss(D_R, D_beam)
    print(
        f"  光斑直径: {D_beam * 100:.1f} cm, 几何损耗: {geometric_loss_db(D_R, D_beam):.2f} dB"
    )

    # 接收功率 (G_T/G_R为预留接口, 实际由L_geo统一处理)
    P_R = received_power(P_T_w, 0, 0, tau_atm, L_geo)
    P_R_dbm = watt_to_dbm(P_R)
    print(f"  接收功率: {P_R_dbm:.2f} dBm ({P_R * 1e6:.4f} μW)")

    # SNR
    snr = snr_pin(P_R, R_p, 1.0, T, B, R_L)
    snr_db = 10 * np.log10(snr)
    print(f"  SNR = {snr_db:.2f} dB (B={B / 1e6:.0f} MHz)")

    # 链路余量
    sensitivity = -30  # dBm
    margin = link_margin(P_R_dbm, sensitivity)
    print(f"  灵敏度 = {sensitivity} dBm")
    print(f"  链路余量 = {margin:.2f} dB")

    # 噪声分解
    n_th = noise_thermal(T, B, R_L)
    n_sh = noise_shot(R_p, P_R, 0, B)
    print(f"\n[噪声分析]")
    print(f"  热噪声: {n_th:.2e} A²")
    print(f"  散粒噪声: {n_sh:.2e} A²")
    ratio = n_th / n_sh if n_sh > 0 else float("inf")
    dominant = (
        "热噪声主导" if ratio > 10 else "散粒噪声主导" if ratio < 0.1 else "两者相当"
    )
    print(f"  热/散粒比: {ratio:.1f} ({dominant})")


def test_ber():
    """测试BER模型"""
    separator("6. BER计算测试")

    # --- 无湍流 BER ---
    print(f"\n[无湍流 BER vs SNR]")
    print(f"  {'SNR(dB)':>8}  {'OOK':>12}  {'4-PPM':>12}  {'SIM-BPSK':>12}")
    print(f"  {'---':>8}  {'---':>12}  {'---':>12}  {'---':>12}")
    for snr_db in [0, 5, 10, 15, 20, 25, 30]:
        snr_lin = 10 ** (snr_db / 10)
        b_ook = ber_ook(snr_lin)
        b_ppm = ber_ppm(snr_lin, M=4)
        b_sim = ber_sim_bpsk(snr_lin)
        print(f"  {snr_db:8d}  {b_ook:12.4e}  {b_ppm:12.4e}  {b_sim:12.4e}")

    # 验证: OOK BER=10^-9 所需的SNR
    # 理论值: SNR ≈ 15.6 dB (36倍线性)
    from scipy.optimize import brentq

    snr_9 = brentq(lambda x: ber_ook(10 ** (x / 10)) - 1e-9, 10, 25)
    print(f"\n  OOK达到BER=10⁻⁹所需SNR: {snr_9:.2f} dB (理论值~15.6 dB)")

    # --- 有湍流 BER ---
    print(f"\n[湍流影响] SNR=20dB 时的 BER 比较")
    snr_20 = 10 ** (20 / 10)  # 100

    for sigma_R2 in [0.0, 0.1, 0.5, 1.0, 3.0]:
        if sigma_R2 == 0:
            b_ook = ber_ook(snr_20)
            b_ppm = ber_ppm(snr_20, 4)
            b_sim = ber_sim_bpsk(snr_20)
            label = "无湍流"
        else:
            b_ook = ber_ook_turbulence(snr_20, sigma_R2)
            b_ppm = ber_ppm_turbulence(snr_20, sigma_R2, 4)
            b_sim = ber_sim_turbulence(snr_20, sigma_R2)
            label = turbulence_regime(sigma_R2)
        print(
            f"  σ_R²={sigma_R2:.1f} ({label:4s}): "
            f"OOK={b_ook:.4e}, 4-PPM={b_ppm:.4e}, SIM={b_sim:.4e}"
        )


def test_end_to_end():
    """端到端仿真: 教材表4.6场景"""
    separator("7. 端到端仿真 (教材表4.6场景)")

    # 系统参数
    P_T_dbm = 14
    P_T_w = dbm_to_watt(P_T_dbm)
    wavelength_nm = 850
    wavelength_m = wavelength_nm * 1e-9
    D_T = 0.025  # 2.5 cm
    D_R = 0.08  # 8 cm
    theta_div = 2e-3  # 2 mrad
    R_p = 0.5  # A/W
    T = 300  # K
    R_L = 50  # Ω
    data_rate = 155e6  # 155 Mbps

    # 不同天气场景
    scenarios = [
        ("晴天", 23, 1e-15, 0, 0),
        ("薄雾", 2, 5e-14, 0, 0),
        ("浓雾", 0.5, 1e-13, 0, 0),
        ("中雨", 5, 5e-14, 10, 0),
        ("大雪", 1, 1e-13, 0, 15),
    ]

    B = bandwidth_from_datarate(data_rate, "OOK")

    print(
        f"\n{'场景':>6} | {'衰减(dB)':>8} | {'P_R(dBm)':>9} | {'SNR(dB)':>8} | "
        f"{'σ_R²':>6} | {'BER-OOK':>10} | {'BER-PPM':>10} | {'BER-SIM':>10}"
    )
    print("-" * 100)

    for name, V, Cn2, rain, snow in scenarios:
        # 大气衰减
        loss_db = total_channel_loss_db(
            V, 1.0, wavelength_nm, rainfall_rate=rain, snowfall_rate=snow
        )
        tau = 10 ** (-loss_db / 10)

        # 几何损耗
        D_beam = beam_diameter_at_distance(D_T, theta_div, 1000)
        L_geo = geometric_loss(D_R, D_beam)

        # 接收功率 (G_T/G_R为预留接口, 实际由L_geo统一处理)
        P_R = received_power(P_T_w, 0, 0, tau, L_geo)
        P_R_dbm = watt_to_dbm(P_R) if P_R > 0 else -999

        # SNR
        snr = snr_pin(P_R, R_p, 1.0, T, B, R_L) if P_R > 0 else 0
        snr_db = 10 * np.log10(snr) if snr > 0 else -999

        # Rytov方差
        sigma_R2 = rytov_variance(Cn2, wavelength_m, 1000)

        # BER
        if snr > 0 and sigma_R2 > 0:
            b_ook = ber_ook_turbulence(snr, sigma_R2)
            b_ppm = ber_ppm_turbulence(snr, sigma_R2, 4)
            b_sim = ber_sim_turbulence(snr, sigma_R2)
        elif snr > 0:
            b_ook = ber_ook(snr)
            b_ppm = ber_ppm(snr, 4)
            b_sim = ber_sim_bpsk(snr)
        else:
            b_ook = b_ppm = b_sim = 1.0

        print(
            f"{name:>6} | {loss_db:8.2f} | {P_R_dbm:9.2f} | {snr_db:8.2f} | "
            f"{sigma_R2:6.4f} | {b_ook:10.4e} | {b_ppm:10.4e} | {b_sim:10.4e}"
        )


if __name__ == "__main__":
    print("=" * 60)
    print("  FSO链路特性可视化平台 — 核心模型验证测试")
    print("  近地大气信道模型")
    print("=" * 60)

    test_atmosphere()
    test_turbulence()
    test_distributions()
    test_geometric()
    test_link_budget()
    test_ber()
    test_end_to_end()

    print(f"\n{'=' * 60}")
    print("  所有测试完成!")
    print(f"{'=' * 60}")
