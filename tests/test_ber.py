"""Tests for BER (Bit Error Rate) calculation models."""

import pytest
import numpy as np
from fso_platform.models.ber import (
    ber_ook,
    ber_ppm,
    ber_sim_bpsk,
    ber_ook_turbulence,
    ber_ppm_turbulence,
    ber_sim_turbulence,
    ber_vs_snr,
)


# ============================================================
# TestBerOOK — OOK 调制误码率测试
# 测试目的：验证开关键控（On-Off Keying, OOK）调制方式下，
#           BER 计算公式的正确性及各边界条件下的行为。
# 测试原理：OOK 是 FSO 中最简单的强度调制方式，用光脉冲的有无
#           表示比特"1"和"0"。其 BER 理论公式为：
#           BER_OOK = 0.5 * erfc(√(SNR/2))，其中 erfc 为
#           补余误差函数，SNR 为信噪比（线性值）。
#           该公式假设加性高斯白噪声（AWGN）信道。
# 预期行为：BER 应随 SNR 增加单调递减，范围在 [0, 0.5] 内，
#           SNR=0 时 BER=0.5（随机猜测），负 SNR 应返回 NaN。
# ============================================================
class TestBerOOK:
    """Tests for ber_ook() — OOK modulation BER."""

    # ----------------------------------------
    # 测试目的：验证高信噪比下 BER 趋近于零
    # 测试原理：当 SNR 足够高时，信号能量远大于噪声能量，
    #           误码概率应指数级下降。erfc(x) 在大 x 时
    #           以 e^(-x²) 速率衰减。
    # 预期行为：SNR=100 时 BER < 1e-12，即基本无误码。
    # ----------------------------------------
    def test_high_snr_low_ber(self):
        assert ber_ook(100) < 1e-12

    # ----------------------------------------
    # 测试目的：验证低信噪比下 BER 较高
    # 测试原理：当 SNR 很低时，信号几乎被噪声淹没，
    #           判决器难以区分"0"和"1"，误码概率上升。
    # 预期行为：SNR=0.1 时 BER > 0.01，即误码率显著高于零。
    # ----------------------------------------
    def test_low_snr_high_ber(self):
        ber = ber_ook(0.1)
        assert ber > 0.01

    # ----------------------------------------
    # 测试目的：验证 SNR=0 时 BER 为 0.5
    # 测试原理：当 SNR = 0 时，接收信号完全没有信息量，
    #           判决等同于抛硬币，误码概率为 0.5。
    #           这是 OOK 的理论极限：BER(0) = 0.5。
    # 预期行为：ber_ook(0.0) ≈ 0.5（浮点近似相等）。
    # ----------------------------------------
    def test_zero_snr_equals_0_5(self):
        assert ber_ook(0.0) == pytest.approx(0.5)

    # ----------------------------------------
    # 测试目的：验证 BER 始终在 [0, 0.5] 有效范围内
    # 测试原理：OOK 的 BER 公式由 erfc 函数产生，其值域为
    #           (0, 1)，乘以 0.5 后值域为 (0, 0.5)。
    #           这是 OOK 调制的理论性质。
    # 预期行为：对所有 SNR ≥ 0，0 ≤ BER ≤ 0.5。
    # ----------------------------------------
    def test_range_zero_to_half(self):
        for snr in [0.01, 0.1, 1.0, 10, 100]:
            ber = ber_ook(snr)
            assert 0 <= ber <= 0.5

    # ----------------------------------------
    # 测试目的：验证 BER 随 SNR 单调递减
    # 测试原理：erfc(x) 是 x 的单调递减函数，而 SNR 增大
    #           意味着 erfc 的自变量 √(SNR/2) 增大，
    #           因此 BER 应严格单调递减。
    # 预期行为：SNR 序列 [0.1, 1, 10, 100] 对应的 BER
    #           序列严格递减。
    # ----------------------------------------
    def test_monotonic_decreasing(self):
        snrs = np.array([0.1, 1.0, 10.0, 100.0])
        bers = ber_ook(snrs)
        for i in range(len(bers) - 1):
            assert bers[i + 1] < bers[i]

    # ----------------------------------------
    # 测试目的：验证函数支持 NumPy 向量化输入
    # 测试原理：BER 计算应能一次性处理数组输入，利用 NumPy
    #           的广播机制，避免 Python 层循环。
    # 预期行为：输入 4 个 SNR 值，输出形状为 (4,) 的数组。
    # ----------------------------------------
    def test_vectorized(self):
        snrs = np.array([0.1, 1.0, 10.0, 100.0])
        result = ber_ook(snrs)
        assert result.shape == (4,)

    # ----------------------------------------
    # 测试目的：验证极高 SNR 下 BER 趋近于零
    # 测试原理：SNR=36（约 15.6 dB）时，erfc 自变量约为
    #           √18 ≈ 4.24，erfc(4.24) 已非常小，
    #           对应 BER 应低于 10⁻⁸ 量级。
    # 预期行为：SNR=36 时 BER < 1e-8。
    # ----------------------------------------
    def test_very_high_snr_extremely_low_ber(self):
        ber = ber_ook(36.0)
        assert ber < 1e-8

    # ----------------------------------------
    # 测试目的：验证负 SNR 输入的处理
    # 测试原理：BER_OOK = 0.5 * erfc(√(SNR/2)) 中，
    #           当 SNR < 0 时，√(SNR/2) 为虚数，
    #           物理上无意义，函数应返回 NaN。
    # 预期行为：ber_ook(-1.0) 返回 NaN（非数字）。
    # ----------------------------------------
    def test_negative_snr_produces_nan(self):
        ber = ber_ook(-1.0)
        assert np.isnan(ber)


# ============================================================
# TestBerPPM — M-PPM 调制误码率测试
# 测试目的：验证脉冲位置调制（M-ary Pulse Position Modulation,
#           M-PPM）方式下 BER 计算公式的正确性。
# 测试原理：M-PPM 将每个符号周期划分为 M 个时隙，通过光脉冲
#           所在时隙位置编码 log₂(M) 比特信息。其 BER 公式为：
#           BER_PPM = 0.5 * erfc(√(SNR * M * log₂(M) / 4))。
#           与 OOK 相比，PPM 在相同 SNR 下有更低的 BER，
#           但需要更宽的带宽（因子 M）。
# 预期行为：BER 随 SNR 递增而单调递减，且 PPM 的 BER 低于 OOK。
# ============================================================
class TestBerPPM:
    """Tests for ber_ppm() — M-PPM modulation BER."""

    # ----------------------------------------
    # 测试目的：验证高信噪比下 PPM 的 BER 趋近于零
    # 测试原理：PPM 的 erfc 自变量包含 M*log₂(M) 增益因子，
    #           因此相同 SNR 下 PPM 的 BER 比 OOK 更低。
    #           M=4 时，自变量增加 4*2=8 倍，误码率更低。
    # 预期行为：SNR=100, M=4 时 BER < 1e-10。
    # ----------------------------------------
    def test_high_snr_low_ber(self):
        assert ber_ppm(100, M=4) < 1e-10

    # ----------------------------------------
    # 测试目的：验证低信噪比下 PPM 的 BER 较高
    # 测试原理：与 OOK 类似，SNR 很低时任何调制方式都会
    #           出现大量误码，PPM 也不例外。
    # 预期行为：SNR=0.1, M=4 时 BER > 0.01。
    # ----------------------------------------
    def test_low_snr_high_ber(self):
        ber = ber_ppm(0.1, M=4)
        assert ber > 0.01

    # ----------------------------------------
    # 测试目的：验证 PPM 的 BER 始终非负
    # 测试原理：BER 作为概率值，必须满足 BER ≥ 0。
    #           erfc 函数的值域为 (0, 2)，因此 0.5*erfc 始终为正。
    # 预期行为：对所有 SNR ≥ 0，BER ≥ 0。
    # ----------------------------------------
    def test_range_non_negative(self):
        for snr in [0.01, 0.1, 1.0, 10, 100]:
            ber = ber_ppm(snr, M=4)
            assert ber >= 0

    # ----------------------------------------
    # 测试目的：验证高 SNR 下 PPM 优于 OOK
    # 测试原理：PPM 的 BER 公式中多了一个 M*log₂(M)/2 的
    #           信噪比增益因子，使相同 SNR 下 PPM 的
    #           erfc 自变量更大，BER 更低。这是 PPM 相对于
    #           OOK 的主要优势——功率效率更高。
    # 预期行为：SNR=100 时，BER_PPM < BER_OOK。
    # ----------------------------------------
    def test_ppm_better_than_ook_at_high_snr(self):
        b_ook = ber_ook(100)
        b_ppm = ber_ppm(100, M=4)
        assert b_ppm < b_ook

    # ----------------------------------------
    # 测试目的：验证函数支持向量化输入
    # 测试原理：与 OOK 类似，实现应支持 NumPy 数组广播。
    # 预期行为：输入 3 个 SNR 值，输出形状为 (3,)。
    # ----------------------------------------
    def test_vectorized(self):
        snrs = np.array([1.0, 10.0, 100.0])
        result = ber_ppm(snrs, M=4)
        assert result.shape == (3,)

    # ----------------------------------------
    # 测试目的：验证 BER 随 SNR 单调递减
    # 测试原理：erfc 的单调性保证 BER 随 SNR 增大严格递减。
    # 预期行为：SNR 序列 [1, 5, 20, 100] 的 BER 严格递减。
    # ----------------------------------------
    def test_monotonic_decreasing(self):
        snrs = np.array([1.0, 5.0, 20.0, 100.0])
        bers = ber_ppm(snrs, M=4)
        for i in range(len(bers) - 1):
            assert bers[i + 1] < bers[i]

    # ----------------------------------------
    # 测试目的：验证不同 M 值下 BER 计算正确
    # 测试原理：M 越大，每个符号承载的比特数越多，
    #           但时隙宽度变窄，带宽效率降低。
    #           M=2,4,8,16 是最常用的 PPM 阶数。
    # 预期行为：所有 M 值下，BER ≥ 0。
    # ----------------------------------------
    @pytest.mark.parametrize("M", [2, 4, 8, 16])
    def test_different_m_values(self, M):
        ber = ber_ppm(100, M=M)
        assert ber >= 0


# ============================================================
# TestBerSIMBPSK — SIM-BPSK 调制误码率测试
# 测试目的：验证子载波强度调制-二进制相移键控（Subcarrier
#           Intensity Modulation BPSK, SIM-BPSK）的 BER 公式。
# 测试原理：SIM-BPSK 先将数据调制到射频副载波上（BPSK），
#           再用该射频信号驱动光强度调制器。其 BER 公式为：
#           BER_BPSK = 0.5 * erfc(√SNR)。
#           与 OOK (0.5*erfc(√(SNR/2))) 相比，BPSK 有
#           3 dB 的信噪比优势（自变量相差 √2 倍）。
# 预期行为：BER 随 SNR 单调递减，BPSK 优于 OOK，SNR=0 时 BER=0.5。
# ============================================================
class TestBerSIMBPSK:
    """Tests for ber_sim_bpsk() — SIM-BPSK modulation BER."""

    # ----------------------------------------
    # 测试目的：验证高信噪比下 BPSK 的 BER 极低
    # 测试原理：BPSK 的 erfc 自变量为 √SNR（比 OOK 大 √2 倍），
    #           因此 BER = 0.5*erfc(√SNR) 在高 SNR 时衰减更快。
    #           SNR=100 时，erfc(10) 已接近双精度浮点下限。
    # 预期行为：SNR=100 时 BER < 1e-20。
    # ----------------------------------------
    def test_high_snr_low_ber(self):
        assert ber_sim_bpsk(100) < 1e-20

    # ----------------------------------------
    # 测试目的：验证低信噪比下 BPSK 的 BER 较高
    # 测试原理：所有调制方式在 SNR 极低时都会失效。
    # 预期行为：SNR=0.1 时 BER > 0.01。
    # ----------------------------------------
    def test_low_snr_high_ber(self):
        ber = ber_sim_bpsk(0.1)
        assert ber > 0.01

    # ----------------------------------------
    # 测试目的：验证 BPSK 比 OOK 有 3 dB 信噪比优势
    # 测试原理：BPSK 的 BER 公式中 erfc 自变量为 √SNR，
    #           而 OOK 为 √(SNR/2) ≈ 0.707*√SNR。
    #           意味着要达到相同 BER，OOK 需要约 2 倍 SNR
    #           （即 3 dB 的额外功率）。
    # 预期行为：SNR=20 时，BER_BPSK < BER_OOK。
    # ----------------------------------------
    def test_bpsk_better_than_ook(self):
        b_ook = ber_ook(20)
        b_bpsk = ber_sim_bpsk(20)
        assert b_bpsk < b_ook

    # ----------------------------------------
    # 测试目的：验证 SNR=0 时 BER 为 0.5
    # 测试原理：与 OOK 相同，SNR=0 时信号无信息量，
    #           二进制判决等价于随机猜测：BER = 0.5。
    # 预期行为：ber_sim_bpsk(0.0) ≈ 0.5。
    # ----------------------------------------
    def test_zero_snr_equals_0_5(self):
        assert ber_sim_bpsk(0.0) == pytest.approx(0.5)

    # ----------------------------------------
    # 测试目的：验证函数支持向量化输入
    # 测试原理：NumPy 广播机制应能处理数组输入。
    # 预期行为：输入 4 个 SNR 值，输出形状为 (4,)。
    # ----------------------------------------
    def test_vectorized(self):
        snrs = np.array([0.1, 1.0, 10.0, 100.0])
        result = ber_sim_bpsk(snrs)
        assert result.shape == (4,)

    # ----------------------------------------
    # 测试目的：验证 BER 随 SNR 单调递减
    # 测试原理：erfc 的单调递减性保证 BER 单调性。
    # 预期行为：SNR 序列的 BER 严格递减。
    # ----------------------------------------
    def test_monotonic_decreasing(self):
        snrs = np.array([0.1, 1.0, 10.0, 100.0])
        bers = ber_sim_bpsk(snrs)
        for i in range(len(bers) - 1):
            assert bers[i + 1] < bers[i]


# ============================================================
# TestBerOOKTurbulence — OOK 在大气湍流下的误码率测试
# 测试目的：验证 OOK 调制在大气湍流信道中的平均 BER 计算。
# 测试原理：大气湍流引起光强闪烁（scintillation），使接收
#           光强随机起伏，导致 SNR 随机波动。湍流信道下的
#           平均 BER 需对湍流引起的 SNR 概率分布求期望：
#           ⟨BER⟩ = ∫ BER(SNR) · f_I(I) dI，其中 f_I(I)
#           为光强起伏的概率密度函数（常用对数正态分布或
#           Gamma-Gamma 分布）。σ_R²（Rytov 方差）表征
#           湍流强度：σ_R² < 0.3 为弱湍流，0.3~1 为中湍流，
#           >1 为强湍流。
# 预期行为：湍流越强 BER 越高，但始终 ∈ [0, 1]。
# ============================================================
class TestBerOOKTurbulence:
    """Tests for ber_ook_turbulence() — OOK BER with turbulence."""

    # ----------------------------------------
    # 测试目的：验证弱湍流下 BER 在有效范围内
    # 测试原理：σ_R²=0.1（弱湍流），闪烁效应较小，
    #           BER 应略高于无湍流情况但仍在 [0,1] 内。
    # 预期行为：BER ∈ [0, 1]。
    # ----------------------------------------
    def test_weak_turbulence(self):
        ber = ber_ook_turbulence(100, 0.1)
        assert 0 <= ber <= 1

    # ----------------------------------------
    # 测试目的：验证中等湍流下 BER 在有效范围内
    # 测试原理：σ_R²=2.0（中湍流），闪烁效应明显，
    #           接收光强起伏增大，BER 上升。
    # 预期行为：BER ∈ [0, 1]。
    # ----------------------------------------
    def test_moderate_turbulence(self):
        ber = ber_ook_turbulence(100, 2.0)
        assert 0 <= ber <= 1

    # ----------------------------------------
    # 测试目的：验证强湍流下 BER 在有效范围内
    # 测试原理：σ_R²=50.0（强湍流），闪烁非常剧烈，
    #           接收光强可能深度衰落，BER 显著上升。
    # 预期行为：BER ∈ [0, 1]。
    # ----------------------------------------
    def test_strong_turbulence(self):
        ber = ber_ook_turbulence(100, 50.0)
        assert 0 <= ber <= 1

    # ----------------------------------------
    # 测试目的：验证湍流强度越大 BER 越高
    # 测试原理：湍流导致光强闪烁，等效于 SNR 的随机波动。
    #           根据 Jensen 不等式，erfc 为凸函数，
    #           ⟨erfc(SNR)⟩ ≥ erfc(⟨SNR⟩)，即湍流
    #           总是使平均 BER 高于无湍流情况。
    # 预期行为：BER(强湍流) > BER(弱湍流) > BER(无湍流)。
    # ----------------------------------------
    def test_turbulence_increases_ber(self):
        b_no_turb = ber_ook(100)
        b_weak = ber_ook_turbulence(100, 0.1)
        b_moderate = ber_ook_turbulence(100, 5.0)
        assert b_moderate > b_weak
        assert b_weak > b_no_turb

    # ----------------------------------------
    # 测试目的：验证相同湍流下 SNR 越高 BER 越低
    # 测试原理：即使在湍流信道中，提高发射功率仍可
    #           降低误码率。SNR 增加带来的改善部分
    #           抵消湍流的不利影响。
    # 预期行为：σ_R²=0.5 时，SNR=100 的 BER < SNR=10 的 BER。
    # ----------------------------------------
    def test_higher_snr_lower_ber(self):
        b_low = ber_ook_turbulence(10, 0.5)
        b_high = ber_ook_turbulence(100, 0.5)
        assert b_high < b_low

    # ----------------------------------------
    # 测试目的：验证边界条件下计算的稳定性
    # 测试原理：σ_R²=1.0 是弱/中湍流的分界点，
    #           σ_R²=25.0 是中/强湍流的典型值。
    #           边界值（0.99, 1.0, 25.0, 25.01）处
    #           应无数值溢出或异常。
    # 预期行为：所有边界值下 BER ∈ [0, 1]。
    # ----------------------------------------
    def test_boundary_conditions(self):
        for sr2 in [0.99, 1.0, 25.0, 25.01]:
            ber = ber_ook_turbulence(100, sr2)
            assert 0 <= ber <= 1


# ============================================================
# TestBerPPMTurbulence — PPM 在大气湍流下的误码率测试
# 测试目的：验证 M-PPM 调制在大气湍流信道中的平均 BER 计算。
# 测试原理：与 OOK 湍流类似，PPM 在湍流信道中也需要对
#           光强闪烁效应求平均。但由于 PPM 的 BER 公式
#           中有 M*log₂(M) 的增益因子，其在湍流下仍比
#           OOK 表现更好。平均 BER 计算公式为：
#           ⟨BER_PPM⟩ = ∫ BER_PPM(SNR) · f_I(I) dI。
# 预期行为：湍流增加 BER，但 BER 始终在 [0, 1] 范围内。
# ============================================================
class TestBerPPMTurbulence:
    """Tests for ber_ppm_turbulence() — PPM BER with turbulence."""

    # ----------------------------------------
    # 测试目的：验证弱湍流下 PPM 的 BER 在有效范围内
    # 测试原理：M=4, σ_R²=0.1，弱湍流对 PPM 影响较小。
    # 预期行为：BER ∈ [0, 1]。
    # ----------------------------------------
    def test_weak_turbulence(self):
        ber = ber_ppm_turbulence(100, 0.1, M=4)
        assert 0 <= ber <= 1

    # ----------------------------------------
    # 测试目的：验证中等湍流下 PPM 的 BER 在有效范围内
    # 测试原理：M=4, σ_R²=5.0，中等湍流使 PPM 的 BER 上升。
    # 预期行为：BER ∈ [0, 1]。
    # ----------------------------------------
    def test_moderate_turbulence(self):
        ber = ber_ppm_turbulence(100, 5.0, M=4)
        assert 0 <= ber <= 1

    # ----------------------------------------
    # 测试目的：验证湍流使 PPM 的 BER 增大
    # 测试原理：与 OOK 相同，Jensen 不等式保证
    #           ⟨BER_PPM⟩ ≥ BER_PPM(⟨SNR⟩)。
    # 预期行为：σ_R²=5.0 的 BER > 无湍流的 BER。
    # ----------------------------------------
    def test_turbulence_increases_ber(self):
        b_no_turb = ber_ppm(100, M=4)
        b_turb = ber_ppm_turbulence(100, 5.0, M=4)
        assert b_turb > b_no_turb

    # ----------------------------------------
    # 测试目的：验证 PPM 湍流模型在边界值处的稳定性
    # 测试原理：与 OOK 湍流相同，σ_R² 边界值处应计算稳定。
    # 预期行为：所有边界值下 BER ∈ [0, 1]。
    # ----------------------------------------
    def test_boundary_conditions(self):
        for sr2 in [0.99, 1.0, 25.0, 25.01]:
            ber = ber_ppm_turbulence(100, sr2, M=4)
            assert 0 <= ber <= 1


# ============================================================
# TestBerSIMTurbulence — SIM-BPSK 在大气湍流下的误码率测试
# 测试目的：验证 SIM-BPSK 调制在大气湍流信道中的平均 BER，
#           以及湍流下各调制方式的性能对比。
# 测试原理：SIM-BPSK 的湍流平均 BER 同样通过对光强起伏
#           概率分布求期望得到。由于 BPSK 有 3 dB 信噪比
#           优势（相对 OOK），在湍流信道中这一优势仍然保持。
#           湍流对三种调制的影响基本对称——都因闪烁效应
#           而性能下降，但相对优劣关系不变。
# 预期行为：湍流使 BER 增大，但 BPSK < PPM < OOK 的
#           性能排序在湍流下仍然成立。
# ============================================================
class TestBerSIMTurbulence:
    """Tests for ber_sim_turbulence() — SIM-BPSK BER with turbulence."""

    # ----------------------------------------
    # 测试目的：验证弱湍流下 BPSK 的 BER 在有效范围内
    # 测试原理：σ_R²=0.1，弱湍流对 BPSK 影响有限。
    # 预期行为：BER ∈ [0, 1]。
    # ----------------------------------------
    def test_weak_turbulence(self):
        ber = ber_sim_turbulence(100, 0.1)
        assert 0 <= ber <= 1

    # ----------------------------------------
    # 测试目的：验证中等湍流下 BPSK 的 BER 在有效范围内
    # 测试原理：σ_R²=5.0，中等湍流使 BPSK 的 BER 上升。
    # 预期行为：BER ∈ [0, 1]。
    # ----------------------------------------
    def test_moderate_turbulence(self):
        ber = ber_sim_turbulence(100, 5.0)
        assert 0 <= ber <= 1

    # ----------------------------------------
    # 测试目的：验证湍流使 BPSK 的 BER 增大
    # 测试原理：与 OOK 和 PPM 相同，Jensen 不等式保证
    #           平均 BER 高于无湍流时的 BER。
    # 预期行为：σ_R²=5.0 的 BER > 无湍流的 BER。
    # ----------------------------------------
    def test_turbulence_increases_ber(self):
        b_no_turb = ber_sim_bpsk(100)
        b_turb = ber_sim_turbulence(100, 5.0)
        assert b_turb > b_no_turb

    # ----------------------------------------
    # 测试目的：验证湍流下 BPSK 仍优于 PPM 和 OOK
    # 测试原理：BPSK 的 3 dB 信噪比优势在湍流信道中
    #           仍然保持。PPM 的 M*log₂(M) 增益使其
    #           同样优于 OOK。三种调制方式的相对性能
    #           排序不受湍流影响：BPSK < PPM < OOK。
    # 预期行为：σ_R²=2.0 时，BER_BPSK < BER_OOK 且
    #           BER_PPM < BER_OOK。
    # ----------------------------------------
    def test_bpsk_still_best_under_turbulence(self):
        b_ook = ber_ook_turbulence(100, 2.0)
        b_ppm = ber_ppm_turbulence(100, 2.0, M=4)
        b_bpsk = ber_sim_turbulence(100, 2.0)
        assert b_bpsk < b_ook
        assert b_ppm < b_ook


# ============================================================
# TestBerVsSNR — BER 曲线生成函数测试
# 测试目的：验证 ber_vs_snr() 集成函数能正确生成不同调制
#           方式在有无湍流下的 BER 曲线数据。
# 测试原理：ber_vs_snr() 是顶层封装函数，根据调制类型
#           （"OOK"/"PPM"/"SIM"）和湍流参数（sigma_R2）
#           自动选择对应的 BER 计算函数（ber_ook / ber_ppm /
#           ber_sim_bpsk / *_turbulence），并对 SNR（dB 值）
#           进行线性化转换。该函数用于生成 BER vs SNR 曲线
#           的绘图数据点。
# 预期行为：输出为与输入 SNR 长度相同的 BER 数组，BER 随
#           SNR 增大递减，未知调制类型返回全零。
# ============================================================
class TestBerVsSNR:
    """Tests for ber_vs_snr() — BER curve generation."""

    # ----------------------------------------
    # 测试目的：验证无湍流下 OOK 的 BER 曲线单调递减
    # 测试原理：SNR 从 0 到 20 dB（线性值 1 到 100），
    #           BER 应严格单调递减。
    # 预期行为：输出 5 个点，单调递减。
    # ----------------------------------------
    def test_ook_no_turbulence(self):
        snr_db = np.array([0, 5, 10, 15, 20])
        bers = ber_vs_snr(snr_db, "OOK")
        assert bers.shape == (5,)
        for i in range(len(bers) - 1):
            assert bers[i + 1] < bers[i]

    # ----------------------------------------
    # 测试目的：验证无湍流下 PPM 的 BER 曲线生成
    # 测试原理：PPM 需要额外参数 M_ppm，输出形状应与输入一致。
    # 预期行为：输出形状为 (5,)。
    # ----------------------------------------
    def test_ppm_no_turbulence(self):
        snr_db = np.array([0, 5, 10, 15, 20])
        bers = ber_vs_snr(snr_db, "PPM", M_ppm=4)
        assert bers.shape == (5,)

    # ----------------------------------------
    # 测试目的：验证无湍流下 SIM-BPSK 的 BER 曲线生成
    # 测试原理：SIM 不带湍流时调用 ber_sim_bpsk。
    # 预期行为：输出形状为 (5,)。
    # ----------------------------------------
    def test_sim_no_turbulence(self):
        snr_db = np.array([0, 5, 10, 15, 20])
        bers = ber_vs_snr(snr_db, "SIM")
        assert bers.shape == (5,)

    # ----------------------------------------
    # 测试目的：验证 OOK 在湍流下的 BER 曲线
    # 测试原理：sigma_R2=0.5 指定弱到中等湍流，BER 应
    #           在 [0, 1] 范围内。
    # 预期行为：输出形状为 (3,)，所有值 ∈ [0, 1]。
    # ----------------------------------------
    def test_ook_with_turbulence(self):
        snr_db = np.array([10, 15, 20])
        bers = ber_vs_snr(snr_db, "OOK", sigma_R2=0.5)
        assert bers.shape == (3,)
        assert np.all(bers >= 0)
        assert np.all(bers <= 1)

    # ----------------------------------------
    # 测试目的：验证 PPM 在湍流下的 BER 曲线
    # 测试原理：sigma_R2=2.0（中湍流），M=4。
    # 预期行为：输出形状为 (3,)。
    # ----------------------------------------
    def test_ppm_with_turbulence(self):
        snr_db = np.array([10, 15, 20])
        bers = ber_vs_snr(snr_db, "PPM", sigma_R2=2.0, M_ppm=4)
        assert bers.shape == (3,)

    # ----------------------------------------
    # 测试目的：验证 SIM-BPSK 在湍流下的 BER 曲线
    # 测试原理：sigma_R2=0.5，验证函数能正确处理
    #           BPSK 加湍流的组合。
    # 预期行为：输出形状为 (3,)。
    # ----------------------------------------
    def test_sim_with_turbulence(self):
        snr_db = np.array([10, 15, 20])
        bers = ber_vs_snr(snr_db, "SIM", sigma_R2=0.5)
        assert bers.shape == (3,)

    # ----------------------------------------
    # 测试目的：验证极低 SNR（dB 负值）时 BER 接近 0.5
    # 测试原理：SNR = -100 dB 对应线性值 ≈ 10⁻¹⁰，
    #           相当于无信号，BER 应逼近 0.5。
    # 预期行为：BER > 0.49（非常接近 0.5 的随机猜测）。
    # ----------------------------------------
    def test_zero_snr(self):
        bers = ber_vs_snr(np.array([-100]), "OOK")
        assert bers[0] > 0.49

    # ----------------------------------------
    # 测试目的：验证所有调制方式在宽 SNR 范围内输出有效
    # 测试原理：SNR 从 0 到 30 dB 分成 20 个点，
    #           三种调制方式在有无湍流下都应输出
    #           概率意义上的有效 BER 值。
    # 预期行为：所有输出 ∈ [0, 1]。
    # ----------------------------------------
    def test_returns_all_non_negative(self):
        snr_db = np.linspace(0, 30, 20)
        for mod in ["OOK", "PPM", "SIM"]:
            bers = ber_vs_snr(snr_db, mod, sigma_R2=None, M_ppm=4)
            assert np.all(bers >= 0)
            assert np.all(bers <= 1)

    # ----------------------------------------
    # 测试目的：验证大样本向量化输入的单调性
    # 测试原理：50 个 SNR 点从 0 到 20 dB 线性采样，
    #           用 np.diff 验证所有相邻点间单调递减。
    # 预期行为：所有相邻差值为负（严格递减）。
    # ----------------------------------------
    def test_vectorized_non_turbulence(self):
        snr_db = np.linspace(0, 20, 50)
        bers = ber_vs_snr(snr_db, "OOK")
        assert bers.shape == (50,)
        assert np.all(np.diff(bers) < 0)

    # ----------------------------------------
    # 测试目的：验证未知调制类型的错误处理
    # 测试原理：当传入不受支持的调制类型时，
    #           ber_vs_snr 应安全返回全零数组，
    #           而非抛出异常。
    # 预期行为：输出全零数组。
    # ----------------------------------------
    def test_unknown_modulation_returns_zeros(self):
        snr_db = np.array([10, 20])
        bers = ber_vs_snr(snr_db, "UNKNOWN")
        assert np.all(bers == 0)
