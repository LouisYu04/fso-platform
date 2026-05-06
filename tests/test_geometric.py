"""Tests for geometric loss and pointing error models."""

import pytest
import numpy as np
from fso_platform.models.geometric import (
    beam_diameter_at_distance,
    geometric_loss,
    geometric_loss_db,
    transmitter_gain,
    receiver_gain,
    pointing_error_loss,
    pointing_error_loss_simple,
)


# =============================================================================
# TestBeamDiameter — 光束直径传播测试
# 测试目的：验证 beam_diameter_at_distance() 函数在不同距离下的光束扩展行为。
# 测试原理：理想光束从发射端出发后，由于衍射效应产生发散角 theta_div_rad，
#           在距离 L 处的光束直径满足线性扩展模型：D(L) = D0 + theta_div_rad * L，
#           其中 D0 为初始光束直径，theta_div_rad 为全角发散角（弧度）。
# 预期行为：距离为零时直径等于初始值；距离增大时直径线性增长；
#           发散角越大，同等距离下的光斑扩展越显著。
# =============================================================================
class TestBeamDiameter:
    """Tests for beam_diameter_at_distance() — beam expansion model."""

    # 测试目的：验证距离为零时，光束直径等于初始直径。
    # 测试原理：当 L = 0 时，D(0) = D0 + θ * 0 = D0，光束尚未发生扩展。
    # 预期行为：返回值应精确等于初始光束直径 0.025 m。
    def test_zero_distance(self):
        D = beam_diameter_at_distance(0.025, 2e-3, 0.0)
        assert D == pytest.approx(0.025)

    # 测试目的：验证在较短传输距离下，光束直径略有增大。
    # 测试原理：D(100) = 0.025 + 2e-3 * 100 = 0.225 m，应大于初始直径。
    # 预期行为：返回的光束直径 > 0.025 m。
    def test_short_distance(self):
        D = beam_diameter_at_distance(0.025, 2e-3, 100.0)
        assert D > 0.025

    # 测试目的：验证在远距离传输下，光束直径显著增大。
    # 测试原理：D(5000) = 0.025 + 2e-3 * 5000 = 10.025 m，远大于初始直径。
    # 预期行为：返回的光束直径 > 5.0 m。
    def test_long_distance(self):
        D = beam_diameter_at_distance(0.025, 2e-3, 5000.0)
        assert D > 5.0

    # 测试目的：验证光束直径随传输距离线性增长的规律。
    # 测试原理：根据线性扩展模型 D(L) = D0 + θ * L，对不同距离参数化测试，
    #           验证每个距离下直径均精确满足线性关系。
    # 预期行为：对每个测试距离 L，D 精确等于 0.025 + 2e-3 * L。
    @pytest.mark.parametrize("L", [100, 500, 1000, 2000, 5000])
    def test_diameter_grows_with_distance(self, L):
        D = beam_diameter_at_distance(0.025, 2e-3, L)
        assert D == pytest.approx(0.025 + 2e-3 * L)

    # 测试目的：验证大发散角导致光束急剧扩展。
    # 测试原理：当发散角 θ = 0.01 rad、距离 L = 1000 m 时，
    #           D(1000) = 0.01 + 0.01 * 1000 = 10.01 m，光斑显著扩大。
    # 预期行为：返回的光束直径 > 10.0 m。
    def test_large_divergence(self):
        D = beam_diameter_at_distance(0.01, 0.01, 1000)
        assert D > 10.0


# =============================================================================
# TestGeometricLoss — 几何耦合损耗测试
# 测试目的：验证 geometric_loss() 函数对接收器与光束直径比值引起的几何损耗计算。
# 测试原理：几何损耗定义为接收器收集到的光功率与入射光功率之比。
#           当接收器直径 D_R ≥ 光束直径 D_beam 时，全部光功率被接收，损耗为 1（无损耗）；
#           当 D_R < D_beam 时，仅部分光被接收，损耗比为 (D_R / D_beam)²，
#           该公式基于圆形孔径的面积比推导得出。
# 预期行为：损耗值始终在 (0, 1] 区间内；D_R ≥ D_beam 时损耗为 1；
#           D_R < D_beam 时损耗精确等于 (D_R / D_beam)²。
# =============================================================================
class TestGeometricLoss:
    """Tests for geometric_loss() — geometric coupling loss."""

    # 测试目的：验证接收器直径大于光束直径时实现完全接收（无损耗）。
    # 测试原理：当 D_R (0.1 m) > D_beam (0.05 m) 时，光束完全落在接收器孔径内。
    # 预期行为：几何损耗 = 1.0，表示全部光功率被捕获。
    def test_full_capture(self):
        L_geo = geometric_loss(0.1, 0.05)
        assert L_geo == pytest.approx(1.0)

    # 测试目的：验证接收器直径等于光束直径时同样实现完全接收。
    # 测试原理：当 D_R = D_beam 时，光束恰好完全覆盖接收器孔径，无几何损耗。
    # 预期行为：几何损耗 = 1.0。
    def test_equal_diameters(self):
        L_geo = geometric_loss(0.1, 0.1)
        assert L_geo == pytest.approx(1.0)

    # 测试目的：验证部分接收时损耗按面积比计算。
    # 测试原理：当 D_R < D_beam 时，接收面积与光束截面积之比为 (D_R / D_beam)²，
    #           该比值即为几何耦合效率。
    # 预期行为：损耗精确等于 (0.08 / 0.5)² = 0.0256。
    def test_partial_capture(self):
        D_R, D_beam = 0.08, 0.5
        L_geo = geometric_loss(D_R, D_beam)
        assert L_geo == pytest.approx((0.08 / 0.5) ** 2)

    # 测试目的：验证极小接收器时的极端损耗情况。
    # 测试原理：D_R = 0.01 m, D_beam = 1.0 m，面积比 = (0.01/1.0)² = 1e-4。
    # 预期行为：损耗精确等于 0.0001，表示仅万分之一的光功率被接收。
    def test_small_receiver(self):
        L_geo = geometric_loss(0.01, 1.0)
        assert L_geo == pytest.approx(0.0001)

    # 测试目的：验证几何损耗始终在有效物理范围内。
    # 测试原理：对不同接收器直径和光束直径的组合进行遍历测试，确保结果符合
    #           能量守恒约束：0 < 损耗 ≤ 1。
    # 预期行为：所有组合的损耗值均严格在 (0, 1] 区间内。
    def test_range_zero_to_one(self):
        for D_R in [0.01, 0.05, 0.1, 0.2]:
            for D_beam in [0.1, 0.5, 1.0, 5.0]:
                L_geo = geometric_loss(D_R, D_beam)
                assert 0.0 < L_geo <= 1.0


# =============================================================================
# TestGeometricLossDB — 几何损耗分贝值测试
# 测试目的：验证 geometric_loss_db() 函数将线性几何损耗转换为 dB 单位的正确性。
# 测试原理：几何损耗的分贝表示为 L_dB = 10 * log10(L_linear)，其中 L_linear 为线性损耗值。
#           完全接收时 L_linear = 1，对应 L_dB = 0 dB（无损耗）；
#           部分接收时 L_linear < 1，对应 L_dB < 0 dB（负值表示损耗）。
# 预期行为：dB 值与线性值严格满足 10*log10() 换算关系；
#           完全接收时返回 0 dB；接收器直径为零时返回负无穷。
# =============================================================================
class TestGeometricLossDB:
    """Tests for geometric_loss_db() — geometric loss in dB."""

    # 测试目的：验证完全接收时 dB 损耗为零。
    # 测试原理：当 D_R (0.1) > D_beam (0.05) 时，L_linear = 1，
    #           L_dB = 10 * log10(1) = 0 dB。
    # 预期行为：返回 0.0 dB，表示无损耗。
    def test_full_capture_zero_db(self):
        L_db = geometric_loss_db(0.1, 0.05)
        assert L_db == pytest.approx(0.0)

    # 测试目的：验证部分接收时 dB 值为负数。
    # 测试原理：部分接收时 L_linear < 1，根据对数函数性质，log10(<1) < 0，
    #           因此 L_dB 为负值。
    # 预期行为：返回负值 dB。
    def test_partial_capture_negative_db(self):
        L_db = geometric_loss_db(0.08, 0.8)
        assert L_db < 0

    # 测试目的：验证接收器大于光束时的 dB 零值（该测试方法名存在误导性）。
    # 测试原理：当 D_R (1.0) > D_beam (0.5) 时，完全接收，L_linear = 1。
    # 预期行为：返回 0.0 dB。
    def test_negative_infinity_when_no_loss(self):
        L_db = geometric_loss_db(1.0, 0.5)
        assert L_db == 0.0

    # 测试目的：验证 dB 值与线性值之间的换算一致性。
    # 测试原理：同一组 (D_R, D_beam) 下，geometric_loss_db() 的结果应与
    #           10 * log10(geometric_loss()) 的结果严格一致。
    # 预期行为：dB 损耗与手动换算值在 1e-10 相对容差内相等。
    def test_db_consistent_with_linear(self):
        D_R, D_beam = 0.08, 0.5
        L_linear = geometric_loss(D_R, D_beam)
        L_db = geometric_loss_db(D_R, D_beam)
        assert L_db == pytest.approx(10 * np.log10(L_linear), rel=1e-10)

    # 测试目的：验证接收器直径为零时的边界情况。
    # 测试原理：当 D_R = 0 时，接收面积为零，L_linear = 0，
    #           L_dB = 10 * log10(0) → -∞（负无穷）。
    # 预期行为：返回非有限值（负无穷），且数值小于 0。
    def test_zero_diameter_returns_neg_inf(self):
        L_db = geometric_loss_db(0.0, 1.0)
        assert not np.isfinite(L_db)
        assert L_db < 0


# =============================================================================
# TestTransmitterGain — 发射天线增益测试
# 测试目的：验证 transmitter_gain() 函数对发射天线增益的计算。
# 测试原理：在 FSO 系统中，发射天线增益由孔径直径和波长决定，
#           理论公式为 G_t = (πD / λ)² * 16 / π² ... 简化后为 G_t = (4D/λ)²，
#           反映了发射天线对光束的聚焦能力。增益随孔径增大而增大，
#           随波长增大而减小。
# 预期行为：增益始终大于 1（相对于各向同性辐射体）；增益与孔径平方成正比，
#           与波长平方成反比。
# =============================================================================
class TestTransmitterGain:
    """Tests for transmitter_gain() — transmit antenna gain."""

    # 测试目的：验证发射天线增益始终大于 1。
    # 测试原理：天线增益相对于各向同性辐射体（isotropic radiator），
    #           由于天线方向性聚焦，增益应大于 1。
    # 预期行为：给定参数下，增益值 > 1。
    def test_gain_positive(self):
        assert transmitter_gain(0.01, 1550e-9) > 1

    # 测试目的：验证增益随发射孔径增大而增大。
    # 测试原理：G_t ∝ D²，发射孔径越大，光束聚焦能力越强，增益越高。
    # 预期行为：D = 0.1 m 时的增益大于 D = 0.01 m 时的增益。
    def test_gain_increases_with_aperture(self):
        g_small = transmitter_gain(0.01, 1550e-9)
        g_large = transmitter_gain(0.1, 1550e-9)
        assert g_large > g_small

    # 测试目的：验证增益随波长增大而减小。
    # 测试原理：G_t ∝ 1/λ²，波长越长，衍射效应越显著，定向性越差。
    #           850 nm（近红外）的增益应大于 1550 nm 的增益。
    # 预期行为：850 nm 的增益 > 1550 nm 的增益。
    def test_gain_decreases_with_wavelength(self):
        g_850 = transmitter_gain(0.05, 850e-9)
        g_1550 = transmitter_gain(0.05, 1550e-9)
        assert g_850 > g_1550

    # 测试目的：验证发射增益公式的平方关系。
    # 测试原理：发射天线增益理论公式为 G_t = (πD/λ)²，在 FSO 常用简化形式中，
    #           可写为 G_t = (4D/λ)²。该测试验证函数输出与理论公式一致。
    # 预期行为：transmitter_gain(D, wl) 精确等于 (4 * D / wl)²。
    def test_formula_square_relation(self):
        D, wl = 0.025, 850e-9
        assert transmitter_gain(D, wl) == pytest.approx((4 * D / wl) ** 2)


# =============================================================================
# TestReceiverGain — 接收天线增益测试
# 测试目的：验证 receiver_gain() 函数对接收天线增益的计算。
# 测试原理：接收天线增益公式为 G_r = (4π/λ²) * A，其中 A = π(D/2)² 为接收孔径面积。
#           与发射增益不同，接收增益同时依赖于孔径面积和波长平方的倒数。
#           增益随孔径增大而增大，随波长增大而减小。
# 预期行为：增益始终大于 1；增益与孔径面积成正比，与波长平方成反比。
# =============================================================================
class TestReceiverGain:
    """Tests for receiver_gain() — receive antenna gain."""

    # 测试目的：验证接收天线增益始终大于 1。
    # 测试原理：接收天线增益 G_r = (4π/λ²) * A，由于聚焦作用，增益 > 1。
    # 预期行为：给定参数下，增益值 > 1。
    def test_gain_positive(self):
        assert receiver_gain(0.08, 1550e-9) > 1

    # 测试目的：验证接收增益随接收孔径增大而增大。
    # 测试原理：G_r ∝ A ∝ D²，接收孔径越大，收集光功率的能力越强，增益越高。
    # 预期行为：D = 0.1 m 时的增益大于 D = 0.01 m 时的增益。
    def test_gain_increases_with_aperture(self):
        g_small = receiver_gain(0.01, 1550e-9)
        g_large = receiver_gain(0.1, 1550e-9)
        assert g_large > g_small

    # 测试目的：验证接收增益随波长增大而减小。
    # 测试原理：G_r ∝ 1/λ²，波长越长，接收天线的有效口径越小，增益越低。
    # 预期行为：850 nm 的增益 > 1550 nm 的增益。
    def test_gain_decreases_with_wavelength(self):
        g_850 = receiver_gain(0.08, 850e-9)
        g_1550 = receiver_gain(0.08, 1550e-9)
        assert g_850 > g_1550

    # 测试目的：验证接收增益公式的正确性。
    # 测试原理：接收天线增益理论公式为 G_r = (4π/λ²) * A，
    #           其中接收孔径面积 A = π(D/2)²。
    #           该测试验证函数输出与手动计算的理论值一致。
    # 预期行为：receiver_gain(D, wl) 精确等于 (4π/λ²) * π(D/2)²。
    def test_receiver_gain_formula(self):
        D, wl = 0.08, 1550e-9
        A = np.pi * (D / 2) ** 2
        expected = (4 * np.pi / wl**2) * A
        assert receiver_gain(D, wl) == pytest.approx(expected)


# =============================================================================
# TestPointingErrorLoss — 统计指向误差损耗测试
# 测试目的：验证 pointing_error_loss() 函数对由于瞄准抖动引起的统计平均指向误差损耗的计算。
# 测试原理：在 FSO 系统中，发射端瞄准抖动（jitter）服从高斯分布，导致光束在接收端
#           产生随机偏移。该模型返回两个值：
#           1. 平均损耗因子 avg_loss（0~1，统计平均的接收功率比例）
#           2. 峰值指向增益 A0（当抖动为零时的最大接收效率）
#           抖动越大，光束偏移越严重，平均接收功率越低。
# 预期行为：返回 (avg_loss, A0) 二元组；A0 通常为 1.0；avg_loss 在 (0, 1] 区间内；
#           抖动为零时 avg_loss = 1.0；抖动增大时 avg_loss 减小。
# =============================================================================
class TestPointingErrorLoss:
    """Tests for pointing_error_loss() — statistical pointing error."""

    # 测试目的：验证函数返回值为二元组。
    # 测试原理：pointing_error_loss() 返回 (平均损耗, 峰值指向增益) 两个值。
    # 预期行为：返回类型为 tuple，长度为 2。
    def test_returns_tuple(self):
        result = pointing_error_loss(1e-4, 0.01, 1000)
        assert isinstance(result, tuple)
        assert len(result) == 2

    # 测试目的：验证峰值指向增益 A0 为 1.0。
    # 测试原理：A0 表示无指向误差时的最大接收效率，理论上为 1.0（完全对准）。
    # 预期行为：A0 == 1.0。
    def test_a0_equals_one(self):
        _, A0 = pointing_error_loss(1e-4, 0.01, 1000)
        assert A0 == pytest.approx(1.0)

    # 测试目的：验证平均损耗因子在物理有效范围内。
    # 测试原理：由于能量守恒，统计平均的接收功率比例不可能超过 1（完全接收），
    #           也不可能低于或等于 0（总有部分能量被接收）。
    # 预期行为：0 < avg_loss ≤ 1.0。
    def test_avg_loss_between_zero_and_one(self):
        avg_loss, _ = pointing_error_loss(1e-4, 0.01, 1000)
        assert 0.0 < avg_loss <= 1.0

    # 测试目的：验证增大抖动导致更大的指向损耗。
    # 测试原理：抖动标准差越大，光束偏离接收器的概率越高，统计平均损耗越大。
    #           比较小抖动（1e-5 rad）和大抖动（1e-3 rad）两种情况。
    # 预期行为：大抖动的 avg_loss < 小抖动的 avg_loss。
    def test_large_jitter_causes_loss(self):
        avg_loss_small, _ = pointing_error_loss(1e-5, 0.01, 1000)
        avg_loss_large, _ = pointing_error_loss(1e-3, 0.01, 1000)
        assert avg_loss_large < avg_loss_small

    # 测试目的：验证无抖动时无指向损耗。
    # 测试原理：当抖动 σ = 0 时，光束始终精确对准接收器，无指向误差损耗。
    # 预期行为：avg_loss = 1.0（完全接收）。
    def test_zero_jitter_no_loss(self):
        avg_loss, _ = pointing_error_loss(0.0, 0.01, 1000)
        assert avg_loss == pytest.approx(1.0)


# =============================================================================
# TestPointingErrorLossSimple — 简化指向误差损耗测试
# 测试目的：验证 pointing_error_loss_simple() 函数对简化指向误差模型的计算。
# 测试原理：简化模型假设光束为高斯分布，指向误差引起的平均损耗满足指数关系：
#           L = exp(-2 * (σ / θ)²)，其中 σ 为瞄准抖动标准差（rad），
#           θ 为光束发散角（rad）。该模型不考虑接收器孔径尺寸和距离。
# 预期行为：无抖动时损耗为 1.0；抖动远大于发散角时损耗趋近于 0；
#           发散角为零或负值时抛出 ValueError。
# =============================================================================
class TestPointingErrorLossSimple:
    """Tests for pointing_error_loss_simple() — simplified pointing error."""

    # 测试目的：验证无抖动时无指向误差损耗。
    # 测试原理：当 σ = 0 时，L = exp(-2 * (0/θ)²) = exp(0) = 1.0。
    # 预期行为：返回 1.0，表示完全接收。
    def test_no_loss_when_no_jitter(self):
        L = pointing_error_loss_simple(0.0, 0.001)
        assert L == pytest.approx(1.0)

    # 测试目的：验证损耗值在有效物理范围内。
    # 测试原理：指向误差损耗 L = exp(-2*(σ/θ)²)，指数函数的输出在 (0, 1] 区间内。
    # 预期行为：0 < L ≤ 1。
    def test_loss_between_zero_and_one(self):
        L = pointing_error_loss_simple(1e-4, 0.001)
        assert 0 < L <= 1

    # 测试目的：验证抖动远大于发散角时损耗趋近于零。
    # 测试原理：σ = 0.01 rad, θ = 0.001 rad, σ/θ = 10,
    #           L = exp(-2 * 10²) = exp(-200) ≈ 1.38e-87，极小。
    # 预期行为：L < 0.01。
    def test_large_jitter_approaches_zero(self):
        L = pointing_error_loss_simple(0.01, 0.001)
        assert L < 0.01

    # 测试目的：验证发散角为零时抛出异常。
    # 测试原理：发散角 θ = 0 时，σ/θ 为无穷大，公式无定义，
    #           应主动抛出 ValueError 防止误导性结果。
    # 预期行为：抛出 ValueError，异常消息包含 "theta_div_rad"。
    def test_value_error_zero_divergence(self):
        with pytest.raises(ValueError, match="theta_div_rad"):
            pointing_error_loss_simple(1e-4, 0.0)

    # 测试目的：验证发散角为负值时抛出异常。
    # 测试原理：发散角为负值在物理上没有意义（发散角应为正值），
    #           函数应拒绝此类无效输入。
    # 预期行为：抛出 ValueError，异常消息包含 "theta_div_rad"。
    def test_value_error_negative_divergence(self):
        with pytest.raises(ValueError, match="theta_div_rad"):
            pointing_error_loss_simple(1e-4, -0.001)

    # 测试目的：验证简化指向误差的指数形式公式。
    # 测试原理：简化模型的理论公式为 L = exp(-2 * (σ/θ)²)，
    #           该测试直接验证函数输出与理论公式一致。
    # 预期行为：pointing_error_loss_simple(σ, θ) 精确等于 exp(-2 * (σ/θ)²)。
    def test_exponential_form(self):
        sigma, theta = 1e-4, 0.001
        L = pointing_error_loss_simple(sigma, theta)
        assert L == pytest.approx(np.exp(-2 * (sigma / theta) ** 2))
