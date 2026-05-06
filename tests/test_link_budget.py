"""
Tests for link budget and SNR calculation models.
链路预算与信噪比计算模型单元测试。

本文件包含以下测试类：
  - TestReceivedPower       线性域接收功率
  - TestReceivedPowerDBM    dBm域接收功率
  - TestNoiseThermal        热噪声方差
  - TestNoiseShot           散粒噪声方差
  - TestSNRPIN              PIN光电二极管信噪比
  - TestSNRAPD              雪崩光电二极管信噪比
  - TestLinkMargin          链路余量
  - TestBandwidthFromDatarate  数据速率到带宽转换
"""

import pytest
import numpy as np
from fso_platform.models.link_budget import (
    received_power,
    received_power_dbm,
    noise_thermal,
    noise_shot,
    snr_pin,
    snr_pin_db,
    snr_apd,
    link_margin,
    bandwidth_from_datarate,
)
from fso_platform.models.geometric import transmitter_gain


class TestReceivedPower:
    """
    测试目的：验证 received_power() 线性域接收功率函数的正确性。

    测试原理：
      接收功率的基本公式为：
        P_R = P_T · τ · L_geo · L_point · μ_T · μ_R · 10^(-L_M / 10)
      其中：
        P_T      — 发射功率 (W)
        τ        — 大气透过率 (0~1)
        L_geo    — 几何损耗因子 (0~1)
        L_point  — 指向误差损耗 (0~1)
        μ_T/μ_R — 发射/接收光学效率 (0~1)
        L_M      — 系统余量 (dB)

    预期行为：
      各参数独立作用于接收功率，函数应正确反映各因子的乘法关系。
    """

    def test_no_loss_all_power(self):
        """
        测试目的：验证无损耗时接收功率等于发射功率。
        测试原理：当 τ=1, L_geo=1 且无其他损耗时，P_R = P_T · 1 · 1 = P_T。
        预期行为：P_R 应精确等于 1.0 W。
        """
        P_R = received_power(1.0, 0, 0, 1.0, 1.0)
        assert P_R == pytest.approx(1.0)

    def test_atmospheric_loss(self):
        """
        测试目的：验证大气衰减对接收功率的独立影响。
        测试原理：τ=0.5 表示仅 50% 的光功率透过大气，P_R = 1.0 · 0.5 · 1.0 = 0.5。
        预期行为：P_R 应精确等于 0.5 W。
        """
        P_R = received_power(1.0, 0, 0, 0.5, 1.0)
        assert P_R == pytest.approx(0.5)

    def test_geometric_loss(self):
        """
        测试目的：验证几何损耗对接收功率的独立影响。
        测试原理：L_geo=0.01 表示因光束扩展仅 1% 的能量到达接收端，
                  P_R = 1.0 · 1.0 · 0.01 = 0.01。
        预期行为：P_R 应精确等于 0.01 W。
        """
        P_R = received_power(1.0, 0, 0, 1.0, 0.01)
        assert P_R == pytest.approx(0.01)

    def test_combined_loss(self):
        """
        测试目的：验证大气衰减与几何损耗联合作用下的接收功率。
        测试原理：P_R = P_T · τ · L_geo = 0.1 · 0.8 · 0.5 = 0.04。
        预期行为：P_R 应等于 P_T、τ、L_geo 三者的乘积。
        """
        P_T, tau, L_geo = 0.1, 0.8, 0.5
        P_R = received_power(P_T, 0, 0, tau, L_geo)
        assert P_R == pytest.approx(P_T * tau * L_geo)

    def test_pointing_loss(self):
        """
        测试目的：验证指向误差损耗对接收功率的影响。
        测试原理：L_point=0.5 表示指向偏差导致仅 50% 能量耦合入接收端，
                  P_R = 1.0 · 1.0 · 1.0 · 0.5 = 0.5。
        预期行为：P_R 应精确等于 0.5 W。
        """
        P_R = received_power(1.0, 0, 0, 1.0, 1.0, L_point=0.5)
        assert P_R == pytest.approx(0.5)

    def test_optical_efficiency(self):
        """
        测试目的：验证发射/接收光学效率对接收功率的影响。
        测试原理：μ_T=0.8（发射光学系统损耗 20%），μ_R=0.9（接收光学系统损耗 10%），
                  总光学效率因子 = μ_T · μ_R = 0.8 · 0.9 = 0.72。
        预期行为：P_R 应等于 0.72 W。
        """
        P_R = received_power(1.0, 0, 0, 1.0, 1.0, mu_T=0.8, mu_R=0.9)
        assert P_R == pytest.approx(0.8 * 0.9)

    def test_system_margin(self):
        """
        测试目的：验证系统余量（dB 域）对接收功率的衰减作用。
        测试原理：系统余量 L_M 以 dB 为单位，功率衰减因子为 10^(-L_M/10)。
                  L_M=3 dB 对应衰减因子 10^(-0.3) ≈ 0.5，即功率减半。
        预期行为：P_with_margin ≈ P_no_margin · 10^(-0.3)。
        """
        P_no_margin = received_power(1.0, 0, 0, 1.0, 1.0)
        P_with_margin = received_power(1.0, 0, 0, 1.0, 1.0, L_M_db=3.0)
        assert P_with_margin == pytest.approx(P_no_margin * 10**(-0.3), rel=1e-10)

    def test_gt_is_reserved_interface(self):
        """
        测试目的：验证 G_T（发射天线增益）参数作为保留接口，不影响计算结果。
        测试原理：几何损耗已通过 L_geo 参数完整描述，G_T 仅为接口兼容性保留。
                  传入任意 G_T 值（0、100、1e10）应得到相同的 P_R。
        预期行为：不同 G_T 值下的接收功率应完全一致。
        """
        """G_T parameter is accepted but does not affect result — L_geo handles all geometric effects."""
        P_no_gt = received_power(1.0, 0, 0, 0.5, 0.1)
        P_gt_100 = received_power(1.0, 100, 0, 0.5, 0.1)
        P_gt_large = received_power(1.0, 1e10, 0, 0.5, 0.1)
        assert P_no_gt == pytest.approx(P_gt_100)
        assert P_no_gt == pytest.approx(P_gt_large)


class TestReceivedPowerDBM:
    """
    测试目的：验证 received_power_dbm() dBm 域接收功率函数的正确性。

    测试原理：
      dBm 与线性功率的转换关系为：
        P_R_dBm = 10 · log10(P_R_W) + 30
      其中 P_R_W 为瓦特单位的接收功率，+30 源于 1 W = 1000 mW 的对数关系。

    预期行为：
      dBm 域结果应与线性域结果经 watt_to_dbm() 转换后一致，边界条件（零功率）应返回 -∞。
    """

    def test_one_watt_returns_30_dbm_without_loss(self):
        """
        测试目的：验证 1 W 无损耗对应 +30 dBm。
        测试原理：P_R_dBm = 10·log10(1.0) + 30 = 30 dBm。
        预期行为：返回 30.0 dBm。
        """
        P_R_dbm = received_power_dbm(1.0, 1.0, 1.0)
        assert P_R_dbm == pytest.approx(30.0)

    def test_zero_power_returns_neg_inf(self):
        """
        测试目的：验证零接收功率的 dBm 域表示。
        测试原理：log10(0) → -∞，因此 dBm 值应为负无穷。
        预期行为：返回非有限值（-inf），且小于 0。
        """
        P_R_dbm = received_power_dbm(0.0, 1.0, 1.0)
        assert not np.isfinite(P_R_dbm)
        assert P_R_dbm < 0

    def test_consistent_with_received_power(self):
        """
        测试目的：验证 dBm 域结果与线性域结果的一致性。
        测试原理：received_power_dbm() 的计算结果应等于
                  watt_to_dbm(received_power())。
        预期行为：两种路径得到的 dBm 值应高度一致（rel≤1e-10）。
        """
        P_T, tau, L_geo = 0.025, 0.8, 0.01
        P_R_linear = received_power(P_T, 0, 0, tau, L_geo)
        P_R_dbm = received_power_dbm(P_T, tau, L_geo)
        from fso_platform.utils.constants import watt_to_dbm
        assert P_R_dbm == pytest.approx(watt_to_dbm(P_R_linear), rel=1e-10)

    def test_system_margin_reduces_power(self):
        """
        测试目的：验证系统余量在 dBm 域降低接收功率。
        测试原理：L_M_db=3 dB 应使接收功率降低 3 dB。
        预期行为：加入余量后的 dBm 值严格小于无余量值。
        """
        P_no_margin = received_power_dbm(1.0, 1.0, 1.0)
        P_with_margin = received_power_dbm(1.0, 1.0, 1.0, L_M_db=3.0)
        assert P_with_margin < P_no_margin

    def test_received_power_dbm_signature(self):
        """
        测试目的：验证函数签名兼容性 — 不传递 G_T 参数时也能正常调用。
        测试原理：received_power_dbm() 的接口设计不要求 G_T 参数。
        预期行为：传递标准参数应返回有限数值。
        """
        """received_power_dbm() accepts standard parameters without G_T."""
        P_R = received_power_dbm(1.0, 0.5, 0.1)
        assert np.isfinite(P_R)


class TestNoiseThermal:
    """
    测试目的：验证 noise_thermal() 热噪声方差计算的正确性。

    测试原理：
      热噪声（约翰逊-奈奎斯特噪声）的方差公式为：
        σ²_th = 4 · k_B · T · B / R
      其中：
        k_B = 1.380649 × 10⁻²³ J/K  — 玻尔兹曼常数
        T   — 绝对温度 (K)
        B   — 带宽 (Hz)
        R   — 负载电阻 (Ω)

      物理背景：热噪声源于导体内部载流子的随机热运动，与温度正相关，
               与带宽正相关（更宽的带宽允许更多频率的噪声通过），
               与负载电阻负相关（更高的电阻降低噪声电流）。

    预期行为：
      热噪声方差应与温度 T、带宽 B 成正比，与负载电阻 R 成反比。
    """

    def test_standard_formula(self):
        """
        测试目的：验证热噪声方差的标准公式计算结果。
        测试原理：σ² = 4 · k_B · 300 · 1e6 / 50。
        预期行为：计算结果与手算值在 rel=1e-10 精度内一致。
        """
        T, B, R = 300, 1e6, 50
        sigma2 = noise_thermal(T, B, R)
        expected = 4 * 1.380649e-23 * T * B / R
        assert sigma2 == pytest.approx(expected, rel=1e-10)

    def test_proportional_to_temperature(self):
        """
        测试目的：验证热噪声方差与温度的线性正比关系。
        测试原理：其他参数不变时，温度从 200 K 升至 300 K，噪声方差应增大。
        预期行为：σ²(T=300) > σ²(T=200)。
        """
        sigma_200 = noise_thermal(200, 1e6, 50)
        sigma_300 = noise_thermal(300, 1e6, 50)
        assert sigma_300 > sigma_200

    def test_proportional_to_bandwidth(self):
        """
        测试目的：验证热噪声方差与带宽的线性正比关系。
        测试原理：其他参数不变时，带宽从 1 MHz 增至 10 MHz，噪声方差应增大。
        预期行为：σ²(B=10M) > σ²(B=1M)。
        """
        sigma_1m = noise_thermal(300, 1e6, 50)
        sigma_10m = noise_thermal(300, 10e6, 50)
        assert sigma_10m > sigma_1m

    def test_inversely_proportional_to_resistance(self):
        """
        测试目的：验证热噪声方差与负载电阻的反比关系。
        测试原理：其他参数不变时，电阻从 50 Ω 增至 100 Ω，噪声方差应减小。
        预期行为：σ²(R=100) < σ²(R=50)。
        """
        sigma_50 = noise_thermal(300, 1e6, 50)
        sigma_100 = noise_thermal(300, 1e6, 100)
        assert sigma_100 < sigma_50


class TestNoiseShot:
    """
    测试目的：验证 noise_shot() 散粒噪声方差计算的正确性。

    测试原理：
      散粒噪声源于光生载流子的随机离散性（光子到达服从泊松分布），其方差为：
        σ²_sh = 2 · e · R_p · (P_R + P_B) · B
      其中：
        e   = 1.602176634 × 10⁻¹⁹ C  — 基本电荷量
        R_p — 光电探测器响应度 (A/W)
        P_R — 信号光接收功率 (W)
        P_B — 背景光功率 (W)
        B   — 带宽 (Hz)

      物理背景：散粒噪声是量子噪声，即使在没有背景光的情况下也存在；
               信号光和背景光都对散粒噪声有贡献（两者线性相加）。

    预期行为：
      散粒噪声方差应正比于响应度、总光功率和带宽。
    """

    def test_standard_formula(self):
        """
        测试目的：验证散粒噪声方差的标准公式计算结果。
        测试原理：σ² = 2 · e · 0.5 · (1e-6 + 0.0) · 1e6。
        预期行为：计算结果与手算值在 rel=1e-10 精度内一致。
        """
        R_p, P_R, P_B, B = 0.5, 1e-6, 0.0, 1e6
        sigma2 = noise_shot(R_p, P_R, P_B, B)
        expected = 2 * 1.602176634e-19 * R_p * (P_R + P_B) * B
        assert sigma2 == pytest.approx(expected, rel=1e-10)

    def test_zero_power_nonzero_shot(self):
        """
        测试目的：验证零总光功率下散粒噪声为零。
        测试原理：当 P_R=0 且 P_B=0 时，(P_R+P_B)=0，σ²_sh = 0。
        预期行为：散粒噪声方差应精确等于 0.0。
        """
        sigma2 = noise_shot(0.5, 0.0, 0.0, 1e6)
        assert sigma2 == pytest.approx(0.0)

    def test_proportional_to_power(self):
        """
        测试目的：验证散粒噪声方差与光功率的正比关系。
        测试原理：其他参数不变时，信号功率从 1 μW 增至 10 μW，噪声方差应增大。
        预期行为：σ²(P_R=10μW) > σ²(P_R=1μW)。
        """
        s_low = noise_shot(0.5, 1e-6, 0.0, 1e6)
        s_high = noise_shot(0.5, 10e-6, 0.0, 1e6)
        assert s_high > s_low

    def test_background_noise_adds(self):
        """
        测试目的：验证背景光对散粒噪声的贡献。
        测试原理：有背景光时 (P_B=1μW)，总光功率增大，散粒噪声增大。
        预期行为：σ²(有背景光) > σ²(无背景光)。
        """
        s_sig = noise_shot(0.5, 1e-6, 0.0, 1e6)
        s_bg = noise_shot(0.5, 1e-6, 1e-6, 1e6)
        assert s_bg > s_sig


class TestSNRPIN:
    """
    测试目的：验证 snr_pin() 和 snr_pin_db() 中 PIN 光电二极管信噪比计算的正确性。

    测试原理：
      PIN 光电二极管的 SNR 定义为信号功率与总噪声功率之比：
        SNR_PIN = (R_p · P_R)² / (σ²_th + σ²_sh)
      其中：
        R_p      — 响应度 (A/W)
        P_R      — 接收光功率 (W)
        σ²_th    — 热噪声方差
        σ²_sh    — 散粒噪声方差

      物理背景：SNR 随接收光功率和响应度增大而提高，
               随温度、带宽增大而降低（因热噪声增大）。

    预期行为：
      SNR 为正且随功率/响应度增大而增大，随温度/带宽增大而减小；
      dB 域与线性域结果应满足 10·log10 的关系。
    """

    def test_positive_snr(self):
        """
        测试目的：验证在典型参数下 SNR 为正数。
        测试原理：信号功率 R_p·P_R 应大于噪声的均方根值。
        预期行为：SNR > 0。
        """
        P_R = 1e-6
        snr = snr_pin(P_R, 0.5, 1.0, 300, 1e6, 50)
        assert snr > 0

    def test_zero_power_gives_zero_snr(self):
        """
        测试目的：验证零接收光功率时 SNR 为零。
        测试原理：P_R=0 → 信号电流为零 → SNR = 0。
        预期行为：SNR 精确等于 0.0。
        """
        snr = snr_pin(0.0, 0.5, 1.0, 300, 1e6, 50)
        assert snr == pytest.approx(0.0)

    def test_snr_increases_with_power(self):
        """
        测试目的：验证 SNR 随接收光功率增大而单调递增。
        测试原理：信号功率正比于 P_R²，而散粒噪声仅正比于 P_R，
                  因此 SNR 总体上随 P_R 增大而增大。
        预期行为：SNR(P_R=10μW) > SNR(P_R=1μW)。
        """
        s_low = snr_pin(1e-6, 0.5, 1.0, 300, 1e6, 50)
        s_high = snr_pin(10e-6, 0.5, 1.0, 300, 1e6, 50)
        assert s_high > s_low

    def test_snr_increases_with_responsivity(self):
        """
        测试目的：验证 SNR 随探测器响应度增大而提高。
        测试原理：响应度 R_p 越高，相同光功率下产生的光电流越大，SNR 越高。
        预期行为：SNR(R_p=0.7) > SNR(R_p=0.3)。
        """
        s_low = snr_pin(1e-6, 0.3, 1.0, 300, 1e6, 50)
        s_high = snr_pin(1e-6, 0.7, 1.0, 300, 1e6, 50)
        assert s_high > s_low

    def test_snr_decreases_with_temp(self):
        """
        测试目的：验证 SNR 随温度升高而降低。
        测试原理：温度升高 → 热噪声增大 → SNR 降低。
        预期行为：SNR(T=200K) > SNR(T=400K)。
        """
        s_cold = snr_pin(1e-6, 0.5, 1.0, 200, 1e6, 50)
        s_hot = snr_pin(1e-6, 0.5, 1.0, 400, 1e6, 50)
        assert s_cold > s_hot

    def test_snr_decreases_with_bandwidth(self):
        """
        测试目的：验证 SNR 随带宽增大而降低。
        测试原理：带宽增大 → 热噪声和散粒噪声均增大 → SNR 降低。
        预期行为：SNR(B=100kHz) > SNR(B=10MHz)。
        """
        s_narrow = snr_pin(1e-6, 0.5, 1.0, 300, 1e5, 50)
        s_wide = snr_pin(1e-6, 0.5, 1.0, 300, 1e7, 50)
        assert s_narrow > s_wide

    def test_snr_db_consistent_with_linear(self):
        """
        测试目的：验证 dB 域 SNR 与线性域 SNR 的转换一致性。
        测试原理：SNR_dB = 10 · log10(SNR_linear)。
        预期行为：snr_pin_db() 的结果等于 10·log10(snr_pin())。
        """
        P_R = 1e-6
        snr_lin = snr_pin(P_R, 0.5, 1.0, 300, 1e6, 50)
        snr_dB = snr_pin_db(P_R, 0.5, 1.0, 300, 1e6, 50)
        assert snr_dB == pytest.approx(10 * np.log10(snr_lin), rel=1e-10)

    def test_snr_db_zero_snr_returns_neg_inf(self):
        """
        测试目的：验证零 SNR 的 dB 域表示为负无穷。
        测试原理：log10(0) → -∞。
        预期行为：返回非有限值（-inf）。
        """
        snr_dB = snr_pin_db(0.0, 0.5, 1.0, 300, 1e6, 50)
        assert not np.isfinite(snr_dB)
        assert snr_dB < 0


class TestSNRAPD:
    """
    测试目的：验证 snr_apd() 中雪崩光电二极管信噪比计算的正确性。

    测试原理：
      APD 通过内部雪崩倍增效应放大光电流，其 SNR 公式为：
        SNR_APD = (M · R_p · P_R)² / [σ²_th + σ²_sh · M² · F(M)]
      其中：
        M     — 雪崩倍增因子（通常 10~100）
        F(M)  — 过量噪声因子，反映雪崩过程的随机性
        F(M) = M^x，x 为电离系数比（0~1）

      物理背景：APD 通过倍增放大了信号功率（正比于 M²），
               但同时放大了散粒噪声（也正比于 M²·F(M)）。
               过量噪声因子 F(M) > 1，使得 APD 的噪声放大超过信号放大。
               在信号功率足够时，APD 的 SNR 优于 PIN。

    预期行为：
      APD 的 SNR 为正，且在充足光功率下高于 PIN；
      倍增因子 M 越大 SNR 越高，过量噪声因子 F 越大 SNR 越低。
    """

    def test_positive_snr(self):
        """
        测试目的：验证典型参数下 APD 的 SNR 为正数。
        测试原理：信号功率 (M·R_p·P_R)² 应超过总噪声功率。
        预期行为：SNR > 0。
        """
        P_R = 1e-6
        snr = snr_apd(P_R, 0.5, 10, 3.0, 1.0, 300, 1e6, 50)
        assert snr > 0

    def test_apd_higher_than_pin_for_sufficient_power(self):
        """
        测试目的：验证充足光功率下 APD 的 SNR 高于 PIN。
        测试原理：APD 的倍增效应使信号电流放大 M 倍，
                  在热噪声为主要噪声源时，SNR 可提升约 M²/F(M) 倍。
        预期行为：SNR_APD > SNR_PIN。
        """
        P_R = 1e-6
        snr_pin_val = snr_pin(P_R, 0.5, 1.0, 300, 1e6, 50)
        snr_apd_val = snr_apd(P_R, 0.5, 10, 3.0, 1.0, 300, 1e6, 50)
        assert snr_apd_val > snr_pin_val

    def test_gain_increases_snr(self):
        """
        测试目的：验证倍增因子 M 增大时 SNR 提高。
        测试原理：在热噪声主导的系统中，SNR 近似正比于 M²/F(M)。
                  M=2→10 时，尽管 F(M) 也增大，但净效果 SNR 提升。
        预期行为：SNR(M=10, F=3.0) > SNR(M=2, F=1.5)。
        """
        s_low = snr_apd(1e-6, 0.5, 2, 1.5, 1.0, 300, 1e6, 50)
        s_high = snr_apd(1e-6, 0.5, 10, 3.0, 1.0, 300, 1e6, 50)
        assert s_high > s_low

    def test_zero_power_gives_zero_snr(self):
        """
        测试目的：验证零接收光功率时 APD 的 SNR 为零。
        测试原理：P_R=0 → 信号电流为零 → SNR = 0。
        预期行为：SNR 精确等于 0.0。
        """
        snr = snr_apd(0.0, 0.5, 10, 3.0, 1.0, 300, 1e6, 50)
        assert snr == pytest.approx(0.0)

    def test_excess_noise_factor_reduces_snr(self):
        """
        测试目的：验证过量噪声因子 F(M) 增大时 SNR 降低。
        测试原理：F(M) 反映雪崩过程的随机性，F 越大散粒噪声放大越严重。
                  在散粒噪声显著时，F 增大 → SNR 降低。
        预期行为：SNR(F=5.0) < SNR(F=2.0)。
        """
        s_low_f = snr_apd(1e-6, 0.5, 10, 2.0, 1.0, 300, 1e6, 50)
        s_high_f = snr_apd(1e-6, 0.5, 10, 5.0, 1.0, 300, 1e6, 50)
        assert s_low_f > s_high_f


class TestLinkMargin:
    """
    测试目的：验证 link_margin() 链路余量计算的正确性。

    测试原理：
      链路余量定义为接收功率（dBm）与接收机灵敏度（dBm）之差：
        M_link = P_R_dBm - S_dBm
      其中 S_dBm 是接收机达到所需 BER 所需的最小功率。

      物理意义：
        M_link > 0  → 链路有余量，可正常工作
        M_link = 0  → 链路处于临界状态
        M_link < 0  → 链路余量不足，可能无法正常工作

    预期行为：
      正余量、负余量和零余量三种情况均应正确计算。
    """

    def test_basic_margin(self):
        """
        测试目的：验证正链路余量的计算。
        测试原理：P_R=-20 dBm，灵敏度=-30 dBm，M = (-20) - (-30) = 10 dB。
        预期行为：链路余量应为 10.0 dB。
        """
        margin = link_margin(-20, -30)
        assert margin == pytest.approx(10.0)

    def test_negative_margin(self):
        """
        测试目的：验证负链路余量（链路预算不足）的计算。
        测试原理：P_R=-35 dBm，灵敏度=-30 dBm，M = (-35) - (-30) = -5 dB。
        预期行为：链路余量应为 -5.0 dB。
        """
        margin = link_margin(-35, -30)
        assert margin == pytest.approx(-5.0)

    def test_zero_margin(self):
        """
        测试目的：验证零链路余量（临界状态）的计算。
        测试原理：P_R=-30 dBm，灵敏度=-30 dBm，M = (-30) - (-30) = 0 dB。
        预期行为：链路余量应为 0.0 dB。
        """
        margin = link_margin(-30, -30)
        assert margin == pytest.approx(0.0)


class TestBandwidthFromDatarate:
    """
    测试目的：验证 bandwidth_from_datarate() 数据速率到带宽转换的正确性。

    测试原理：
      不同调制格式所需带宽不同：
        - OOK（开关键控）：B = R_b（带宽等于数据速率）
        - SIM（子载波强度调制）：B = R_b（带宽等于数据速率）
        - PPM（脉冲位置调制）：B = M · R_b / log₂(M)
          其中 M 为 PPM 时隙数，log₂(M) 为每符号比特数

      物理背景：PPM 通过增加时隙数 M 换取更高的功率效率，
               但需要更宽的带宽（带宽扩展因子 M/log₂(M)）。

    预期行为：
      OOK 和 SIM 的带宽等于数据速率；PPM 的带宽按 M/log₂(M) 扩展；
      未知调制模式默认回退为 B=R_b。
    """

    def test_ook_bandwidth_equals_rate(self):
        """
        测试目的：验证 OOK 调制的带宽等于数据速率。
        测试原理：OOK 每个符号传输 1 bit，B = R_b。
        预期行为：B = 155e6 Hz。
        """
        assert bandwidth_from_datarate(155e6, "OOK") == pytest.approx(155e6)

    def test_sim_bandwidth_equals_rate(self):
        """
        测试目的：验证 SIM 调制的带宽等于数据速率。
        测试原理：SIM（子载波强度调制）每个符号传输 1 bit，B = R_b。
        预期行为：B = 155e6 Hz。
        """
        assert bandwidth_from_datarate(155e6, "SIM") == pytest.approx(155e6)

    def test_ppm_bandwidth(self):
        """
        测试目的：验证 PPM-4 调制的带宽计算公式。
        测试原理：M=4 时，B = 4 · 100e6 / log₂(4) = 400e6 / 2 = 200 MHz。
        预期行为：B 应等于 M · R_b / log₂(M)。
        """
        R_b, M = 100e6, 4
        B = bandwidth_from_datarate(R_b, "PPM", M)
        assert B == pytest.approx(M * R_b / np.log2(M))

    def test_ppm_m8(self):
        """
        测试目的：验证 PPM-8 调制的带宽计算公式。
        测试原理：M=8 时，B = 8 · 100e6 / log₂(8) = 800e6 / 3 ≈ 266.7 MHz。
        预期行为：B 应等于 M · R_b / log₂(M)。
        """
        R_b, M = 100e6, 8
        B = bandwidth_from_datarate(R_b, "PPM", M)
        assert B == pytest.approx(M * R_b / np.log2(M))

    def test_unknown_modulation_defaults_to_rate(self):
        """
        测试目的：验证未知调制格式的默认回退行为。
        测试原理：不支持的调制格式应安全地返回 B = R_b。
        预期行为：B = 100e6 Hz。
        """
        B = bandwidth_from_datarate(100e6, "UNKNOWN")
        assert B == pytest.approx(100e6)

    @pytest.mark.parametrize("mod", ["OOK", "SIM", "PPM"])
    def test_all_modes_positive(self, mod):
        """
        测试目的：验证所有支持的调制格式下带宽均为正数。
        测试原理：无论何种调制方式，带宽应为物理上合理的正值。
        预期行为：B > 0。
        """
        B = bandwidth_from_datarate(100e6, mod, M_ppm=4)
        assert B > 0
