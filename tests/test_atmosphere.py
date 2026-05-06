"""Tests for atmosphere attenuation models."""

import pytest
import numpy as np
from fso_platform.models.atmosphere import (
    kim_p,
    attenuation_coefficient,
    beer_lambert,
    atmospheric_attenuation_db,
    naboulsi_advection_fog,
    naboulsi_radiation_fog,
    rain_attenuation,
    snow_attenuation,
    total_channel_loss_db,
    transmittance,
)


class TestKimP:
    """
    Kim 模型粒子尺度分布系数 p(V) 的测试集。

    测试目的：
        验证 Kim 模型中粒子尺度分布系数 p 在不同能见度条件下的正确性。
        p 是波长修正因子，用于后续计算大气消光系数 sigma(lambda) = (3.91/V) x (lambda/550)^(-p)。

    测试原理：
        Kim 模型将能见度 V（单位：km）划分为五个区间，使用分段函数计算 p 值：
          - V < 0.5 km（浓雾）: p = 0.0，衰减与波长无关
          - 0.5 <= V < 1 km（雾）: p = V - 0.5
          - 1 <= V < 6 km（薄雾）: p = 0.16V + 0.34
          - 6 <= V <= 50 km（晴朗）: p = 1.3（常数）
          - V > 50 km（极晴朗）: p = 1.6（常数）
        该分段模型基于对不同大气条件下气溶胶粒子尺度分布的实验拟合。

    预期行为：
        在各能见度区间内返回对应的标量或数组 p 值，边界处行为符合分段函数定义，
        输入为 NumPy 数组时返回相同形状的数组，非法输入抛出 ValueError。
    """

    @pytest.mark.parametrize("V, expected", [
        (0.2, 0.0),
        (0.35, 0.0),
        (0.5, 0.0),
        (0.6, 0.1),
        (0.8, 0.3),
        (1.0, 0.5),
        (1.5, 0.58),
        (2.0, 0.66),
        (3.0, 0.82),
        (6.0, 1.3),
        (10.0, 1.3),
        (23.0, 1.3),
        (45.0, 1.3),
        (50.0, 1.3),
        (60.0, 1.6),
        (100.0, 1.6),
    ])
    def test_kim_p_known_values(self, V, expected):
        """
        测试 kim_p 在多个已知能见度值下的输出与预期值一致。

        测试目的：
            验证各能见度区间内 p 值的计算正确性。
        测试原理：
            使用参数化测试覆盖每个区间的典型值，包括边界值和区间内点。
        预期行为：
            每个 (V, expected) 对的计算结果在 abs=0.02 容差内匹配预期值。
        """
        result = kim_p(V)
        assert result == pytest.approx(expected, abs=0.02)

    @pytest.mark.parametrize("V", [0, -0.1, -1.0, -100.0])
    def test_value_error_non_positive_visibility(self, V):
        """
        测试非正能见度输入抛出 ValueError。

        测试目的：
            验证 Kim 模型对非法能见度输入（零或负值）的异常处理。
        测试原理：
            能见度必须为正数，零或负值在物理上没有意义。
        预期行为：
            抛出 ValueError 且异常信息包含 "visibility_km"。
        """
        with pytest.raises(ValueError, match="visibility_km"):
            kim_p(V)

    def test_vectorized_input(self):
        """
        测试 kim_p 支持 NumPy 数组批量输入。

        测试目的：
            验证函数对向量化输入的正确处理。
        测试原理：
            实际应用中能见度可能为数组形式（如时间序列），函数应支持广播计算。
        预期行为：
            输入数组时返回相同形状的数组，各元素值与标量输入一致。
        """
        V = np.array([0.2, 0.8, 2.0, 10.0, 60.0])
        result = kim_p(V)
        expected = np.array([0.0, 0.3, 0.66, 1.3, 1.6])
        assert result == pytest.approx(expected, abs=0.02)

    def test_vectorized_value_error(self):
        """
        测试向量化输入中任一元素非法时抛出 ValueError。

        测试目的：
            验证数组输入中包含零或负值时的异常行为。
        测试原理：
            数组中所有元素应为正能见度值，零值会触发错误。
        预期行为：
            输入包含 0 的数组时抛出 ValueError。
        """
        V = np.array([1.0, 0.0, 2.0])
        with pytest.raises(ValueError):
            kim_p(V)

    def test_returns_python_float_for_scalar(self):
        """
        测试标量输入返回 Python float 类型。

        测试目的：
            确保函数返回类型符合调用方的类型期望。
        测试原理：
            标量输入应返回标量 Python float，而非 NumPy 标量或数组。
        预期行为：
            kim_p(10.0) 的返回类型为 float。
        """
        assert isinstance(kim_p(10.0), float)

    def test_regime_boundary_above_50(self):
        """
        测试 V = 50 km 边界处的分段行为。

        测试目的：
            验证 V = 50 界限处的 p 值跳变。
        测试原理：
            V = 50 时属于 [6, 50] 区间，p = 1.3；
            V > 50 时进入极晴朗区间，p = 1.6。
        预期行为：
            V = 50 时 p approx= 1.3，V 略大于 50 时 p approx= 1.6。
        """
        assert kim_p(50.0) == pytest.approx(1.3, abs=0.01)
        assert kim_p(50.0001) == pytest.approx(1.6, abs=0.01)

    def test_regime_boundary_above_6(self):
        """
        测试 V = 6 km 边界处的连续性。

        测试目的：
            验证 V = 6 处两个区间的过渡。
        测试原理：
            V = 6 属于 [6, 50] 区间，p = 1.3；
            V 略大于 6 时仍在同一区间，p 保持 1.3（连续）。
        预期行为：
            V = 6 两侧（6.0 和 6.0001）p 值相同，均为 1.3。
        """
        assert kim_p(6.0) == pytest.approx(1.3, abs=0.01)
        assert kim_p(6.0001) == pytest.approx(1.3, abs=0.01)

    def test_regime_boundary_above_1(self):
        """
        测试 V = 1 km 边界处的分段行为。

        测试目的：
            验证 V = 1 处从线性段到常数段的过渡。
        测试原理：
            V = 1 时属于 [1, 6) 区间，p = 0.16 x 1 + 0.34 = 0.5；
            V 略大于 1 时仍在线性段，p 按公式 0.16V + 0.34 计算。
        预期行为：
            V = 1 时 p approx= 0.5，V = 1.0001 时 p approx= 0.16 x 1.0001 + 0.34。
        """
        assert kim_p(1.0) == pytest.approx(0.5, abs=0.01)
        assert kim_p(1.0001) == pytest.approx(0.16 * 1.0001 + 0.34, abs=0.01)

    def test_regime_boundary_above_half(self):
        """
        测试 V = 0.5 km 边界处的分段行为。

        测试目的：
            验证 V = 0.5 处从零段到线性段的过渡。
        测试原理：
            V = 0.5 时属于 [0, 0.5) 区间，p = 0.0；
            V 略大于 0.5 时进入 [0.5, 1) 区间，p = V - 0.5。
        预期行为：
            V = 0.5 时 p approx= 0.0，V = 0.5001 时 p approx= 0.5001 - 0.5。
        """
        assert kim_p(0.5) == pytest.approx(0.0, abs=0.01)
        assert kim_p(0.5001) == pytest.approx(0.5001 - 0.5, abs=0.01)

    def test_normalized_wavelength_factor(self):
        """
        测试晴朗天气的 p 值大于浓雾天气。

        测试目的：
            验证 p 值随能见度改善而增大的单调趋势。
        测试原理：
            极晴朗天气下 p = 1.6，浓雾天气下 p = 0.0。
            p 越大，波长对衰减的修正越显著。
        预期行为：
            kim_p(60) > kim_p(0.3)。
        """
        p_clear = kim_p(60)
        p_fog = kim_p(0.3)
        assert p_clear > p_fog


class TestAttenuationCoefficient:
    """
    Kim 模型消光系数 sigma(lambda) 的测试集。

    测试目的：
        验证大气消光系数 sigma(lambda) 在不同能见度和波长下的正确计算。

    测试原理：
        消光系数 sigma(lambda) 由 Kim 模型定义为：
          sigma(lambda) = (3.91 / V) x (lambda / 550)^(-p(V))
        其中 V 为能见度 (km)，lambda 为波长 (nm)，p(V) 为 Kim 粒子尺度分布系数。
        参考波长 550 nm 处（人眼最敏感波段），sigma = 3.91 / V，即 Koschmieder 定律。

    预期行为：
        能见度越低、波长越短，消光系数越大；非法输入抛出 ValueError。
    """

    def test_clear_air_typical(self):
        """
        测试晴朗天气下的消光系数在合理范围内。

        测试目的：
            验证典型晴朗条件（能见度 23 km，波长 1550 nm）下的衰减系数。
        测试原理：
            晴朗天气下消光系数较小，通常远小于 1 km^-1。
        预期行为：
            消光系数在 0.01 到 0.1 km^-1 之间。
        """
        sigma = attenuation_coefficient(23, 1550)
        assert 0.01 < sigma < 0.1

    def test_fog_typical(self):
        """
        测试浓雾天气下的消光系数较大。

        测试目的：
            验证浓雾条件（能见度 0.5 km）下的强衰减特性。
        测试原理：
            浓雾时能见度极低，消光系数显著增大。
        预期行为：
            消光系数大于 5.0 km^-1。
        """
        sigma = attenuation_coefficient(0.5, 1550)
        assert sigma > 5.0

    def test_wavelength_dependence_longer_less_attenuation(self):
        """
        测试较长波长（1550 nm）比较短波长（850 nm）衰减更小。

        测试目的：
            验证 FSO 通信中 1550 nm 窗口相比 850 nm 的优势。
        测试原理：
            Kim 模型中，衰减系数与 lambda^(-p) 成正比。
            p > 0 时波长越长衰减越小，这是 FSO 系统倾向使用 1550 nm 的原因。
        预期行为：
            sigma(1550 nm) < sigma(850 nm)。
        """
        sigma_850 = attenuation_coefficient(10, 850)
        sigma_1550 = attenuation_coefficient(10, 1550)
        assert sigma_1550 < sigma_850

    @pytest.mark.parametrize("V", [0, -0.5, -10])
    def test_value_error_non_positive_visibility(self, V):
        """
        测试非正能见度输入抛出 ValueError。

        测试目的：
            验证消光系数函数对非法能见度的异常处理。
        测试原理：
            能见度必须为正数，零或负值在物理上没有意义。
        预期行为：
            能见度为零或负值时抛出 ValueError，信息包含 "visibility_km"。
        """
        with pytest.raises(ValueError, match="visibility_km"):
            attenuation_coefficient(V)

    def test_attenuation_equals_3_91_over_v_at_reference_wavelength(self):
        """
        测试波长 lambda = 550 nm 时消光系数退化为 Koschmieder 定律。

        测试目的：
            验证 Kim 模型在参考波长处与经典 Koschmieder 公式一致。
        测试原理：
            lambda = 550 nm 时，(lambda/550)^(-p) = 1，sigma = 3.91 / V。
            这是 Kim 模型与 Kruse 模型的共同参考点。
        预期行为：
            sigma = 3.91 / V（相对容差 1e-10）。
        """
        V = 10.0
        sigma = attenuation_coefficient(V, 550)
        assert sigma == pytest.approx(3.91 / V, rel=1e-10)


class TestBeerLambert:
    """
    Beer-Lambert 定律透射率计算的测试集。

    测试目的：
        验证 Beer-Lambert 定律 tau = exp(-sigma * d) 的正确实现。

    测试原理：
        Beer-Lambert 定律描述光在大气中传播时的指数衰减：
          tau = exp(-sigma * d)
        其中 tau 为透射率（0~1），sigma 为消光系数 (km^-1)，d 为传输距离 (km)。
        该定律假设介质均匀且吸收与散射独立。

    预期行为：
        无衰减或零距离时透射率为 1，衰减增大时透射率指数下降。
    """

    def test_no_attenuation(self):
        """
        测试无衰减（sigma = 0）时透射率为 1。

        测试目的：
            验证零消光系数下的理想传输情况。
        预期行为：
            tau = exp(0) = 1.0。
        """
        assert beer_lambert(0.0, 1.0) == pytest.approx(1.0)

    def test_partial_attenuation(self):
        """
        测试单位消光系数和单位距离下的透射率。

        测试目的：
            验证 Beer-Lambert 定律的基本指数衰减行为。
        预期行为：
            tau = exp(-1.0) ≈ 0.3679。
        """
        tau = beer_lambert(1.0, 1.0)
        assert tau == pytest.approx(np.exp(-1.0))

    def test_zero_distance(self):
        """
        测试零传输距离时透射率为 1。

        测试目的：
            验证距离为零时（发射端与接收端重合）无衰减。
        预期行为：
            tau = 1.0。
        """
        assert beer_lambert(10.0, 0.0) == pytest.approx(1.0)

    def test_severe_attenuation(self):
        """
        测试强衰减条件下的透射率趋近于零。

        测试目的：
            验证大消光系数与大传输距离组合时透射率接近于零。
        预期行为：
            tau < 1e-10（基本为零）。
        """
        tau = beer_lambert(10.0, 5.0)
        assert tau < 1e-10


class TestAtmosphericAttenuationDB:
    """
    大气衰减 dB 值计算的测试集。

    测试目的：
        验证衰减分贝值 L(dB) = -10 * log10(tau) = 4.343 * sigma * d 的正确实现。

    测试原理：
        透射率 tau 与 dB 衰减之间的关系：
          L(dB) = -10 * log10(tau)
        利用 tau = exp(-sigma * d) 可得：
          L(dB) = -10 * log10(exp(-sigma * d)) = 10 * sigma * d / ln(10) ≈ 4.343 * sigma * d

    预期行为：
        零距离衰减为 0 dB，与 Beer-Lambert 定律一致，与 4.343 系数一致。
    """

    def test_relation_to_beer_lambert(self):
        """
        测试 dB 衰减与 Beer-Lambert 透射率之间的转换关系。

        测试目的：
            验证 L(dB) = -10 * log10(tau) 的数学一致性。
        预期行为：
            两种方式计算的结果在相对容差 1e-4 内一致。
        """
        sigma = 0.5
        d = 2.0
        tau = beer_lambert(sigma, d)
        L_db = atmospheric_attenuation_db(sigma, d)
        assert L_db == pytest.approx(-10 * np.log10(tau), rel=1e-4)

    def test_zero_distance(self):
        """
        测试零距离时衰减为 0 dB。

        测试目的：
            验证零传输距离下无衰减的物理事实。
        预期行为：
            atmospheric_attenuation_db(1.0, 0.0) ≈ 0.0。
        """
        assert atmospheric_attenuation_db(1.0, 0.0) == pytest.approx(0.0)

    def test_factor_4_343(self):
        """
        测试衰减系数与 4.343 * sigma * d 的等价性。

        测试目的：
            验证 dB 衰减的线性近似 L = 4.343 * sigma * d。
        测试原理：
            由 L = -10 * log10(exp(-sigma*d)) = 10 * sigma * d / ln(10) ≈ 4.343 * sigma * d。
        预期行为：
            L ≈ 4.343 × 0.3 × 1.0。
        """
        sigma, d = 0.3, 1.0
        L_db = atmospheric_attenuation_db(sigma, d)
        assert L_db == pytest.approx(4.343 * sigma * d, rel=1e-4)


class TestNaboulsiFog:
    """
    Naboulsi 平流雾与辐射雾模型的测试集。

    测试目的：
        验证 Naboulsi 提出的两种雾模型在不同能见度和波长下的衰减系数计算。

    测试原理：
        Naboulsi 模型基于雾的物理成因将雾分为两类：
          - 平流雾（advection fog）：暖湿空气流经冷地面形成，液滴粒径较小
          - 辐射雾（radiation fog）：夜间地表辐射冷却形成，液滴粒径较大
        两种模型均基于特定波长和能见度的经验公式计算衰减系数 alpha (dB/km)。

    预期行为：
        能见度越低衰减越强，波长越长衰减越强（与雾滴的 Mie 散射特性有关），
        非法输入抛出 ValueError。
    """

    @pytest.mark.parametrize("func", [naboulsi_advection_fog, naboulsi_radiation_fog])
    @pytest.mark.parametrize("V", [0, -0.5, -10])
    def test_value_error_non_positive_visibility(self, func, V):
        """
        测试 Naboulsi 模型对非正能见度输入的异常处理。

        测试目的：
            验证两种雾模型均拒绝非法能见度输入。
        测试原理：
            能见度必须为正数，零或负值在物理上没有意义。
        预期行为：
            均抛出 ValueError，错误信息包含 "visibility_km"。
        """
        with pytest.raises(ValueError, match="visibility_km"):
            func(V)

    def test_advection_fog_dense(self):
        """
        测试浓平流雾（能见度 0.1 km）时的强衰减。

        测试目的：
            验证极低能见度下平流雾的强衰减特性。
        预期行为：
            衰减系数 alpha > 30 dB/km。
        """
        alpha = naboulsi_advection_fog(0.1, 1550)
        assert alpha > 30

    def test_radiation_fog_dense(self):
        """
        测试浓辐射雾（能见度 0.1 km）时的强衰减。

        测试目的：
            验证极低能见度下辐射雾的强衰减特性。
        预期行为：
            衰减系数 alpha > 30 dB/km。
        """
        alpha = naboulsi_radiation_fog(0.1, 1550)
        assert alpha > 30

    def test_advection_vs_radiation_clear(self):
        """
        测试晴朗天气下两种雾模型均返回正衰减。

        测试目的：
            验证在较好能见度下两种模型仍正确返回正衰减值。
        预期行为：
            两种模型在能见度 10 km 时衰减均大于 0。
        """
        a_adv = naboulsi_advection_fog(10, 1550)
        a_rad = naboulsi_radiation_fog(10, 1550)
        assert a_adv > 0
        assert a_rad > 0

    def test_attenuation_decreases_with_visibility(self):
        """
        测试衰减系数随能见度增大而单调递减。

        测试目的：
            验证物理趋势：能见度越好，衰减越小。
        预期行为：
            V = 0.5 km 时的衰减 > V = 10.0 km 时的衰减。
        """
        a_05 = naboulsi_advection_fog(0.5)
        a_10 = naboulsi_advection_fog(10.0)
        assert a_05 > a_10

    def test_wavelength_dependence_advection(self):
        """
        测试平流雾中波长依赖关系（1550 nm 衰减大于 850 nm）。

        测试目的：
            验证 Naboulsi 平流雾模型与 Kim 模型相反的波长趋势。
        测试原理：
            与 Kim 模型不同，Naboulsi 模型中雾滴的 Mie 散射导致较长波长衰减更大。
            这是因为雾滴粒径与 1550 nm 波长的相对尺寸使散射截面更大。
        预期行为：
            平流雾中 alpha(1550) > alpha(850)。
        """
        a_850 = naboulsi_advection_fog(0.5, 850)
        a_1550 = naboulsi_advection_fog(0.5, 1550)
        assert a_1550 > a_850

    def test_wavelength_dependence_radiation(self):
        """
        测试辐射雾中波长依赖关系（1550 nm 衰减大于 850 nm）。

        测试目的：
            验证 Naboulsi 辐射雾模型的波长趋势。
        测试原理：
            与平流雾类似，辐射雾中雾滴的 Mie 散射也使较长波长衰减更大。
        预期行为：
            辐射雾中 alpha(1550) > alpha(850)。
        """
        a_850 = naboulsi_radiation_fog(0.5, 850)
        a_1550 = naboulsi_radiation_fog(0.5, 1550)
        assert a_1550 > a_850


class TestRainAttenuation:
    """
    Carbonneau 雨衰减经验模型的测试集。

    测试目的：
        验证雨衰减模型在不同降雨率下的衰减系数计算。

    测试原理：
        Carbonneau 模型是 FSO 通信中常用的雨衰减经验模型：
          alpha_rain = 1.076 * R^(2/3)  (dB/km)
        其中 R 为降雨率 (mm/h)。该模型基于 Mie 散射理论的简化拟合，
        适用于 0.1~100 mm/h 的降雨率范围。

    预期行为：
        无雨时衰减为 0，衰减随降雨率单调递增。
    """

    def test_no_rain(self):
        """
        测试无雨（R = 0）和负值输入时衰减为 0。

        测试目的：
            验证零降雨率和非法负值输入的正确处理。
        预期行为：
            rain_attenuation(0.0) = 0.0，rain_attenuation(-1.0) = 0.0。
        """
        assert rain_attenuation(0.0) == 0.0
        assert rain_attenuation(-1.0) == 0.0

    def test_light_rain(self):
        """
        测试小雨（R = 2.5 mm/h）的衰减范围。

        测试目的：
            验证小雨条件下的典型衰减值。
        预期行为：
            衰减在 1.0 到 3.0 dB/km 之间。
        """
        alpha = rain_attenuation(2.5)
        assert 1.0 < alpha < 3.0

    def test_moderate_rain(self):
        """
        测试中雨（R = 10 mm/h）的衰减范围。

        测试目的：
            验证中雨条件下的典型衰减值。
        预期行为：
            衰减在 3.0 到 10.0 dB/km 之间。
        """
        alpha = rain_attenuation(10.0)
        assert 3.0 < alpha < 10.0

    def test_heavy_rain(self):
        """
        测试大雨（R = 25 mm/h）衰减大于中雨衰减。

        测试目的：
            验证降雨率增大时衰减相应增大。
        预期行为：
            25 mm/h 的衰减 > 10 mm/h 的衰减。
        """
        alpha_25 = rain_attenuation(25.0)
        alpha_10 = rain_attenuation(10.0)
        assert alpha_25 > alpha_10

    def test_monotonic(self):
        """
        测试雨衰减随降雨率单调递增。

        测试目的：
            验证衰减函数的单调性，确保物理合理性。
        预期行为：
            降雨率序列 [0.1, 1, 5, 10, 25, 50, 100] 对应的衰减值单调非减。
        """
        rates = [0.1, 1.0, 5.0, 10.0, 25.0, 50.0, 100.0]
        alphas = [rain_attenuation(r) for r in rates]
        for i in range(len(alphas) - 1):
            assert alphas[i + 1] >= alphas[i]


class TestSnowAttenuation:
    """
    雪衰减经验模型的测试集。

    测试目的：
        验证雪衰减模型在不同降雪率和雪类型（干雪/湿雪）下的衰减系数计算。

    测试原理：
        雪衰减基于经验公式，分干雪和湿雪两种类型：
          - 干雪（dry）：衰减系数相对较小，因干雪密度低、介电常数小
          - 湿雪（wet）：衰减系数较大，因湿雪含水量高、介电常数大
        衰减系数与降雪率 S (mm/h) 呈指数关系，湿雪的衰减系数通常大于干雪。

    预期行为：
        无雪时衰减为 0，湿雪衰减大于干雪衰减，衰减随降雪率单调递增。
    """

    def test_no_snow(self):
        """
        测试无雪（S = 0）和负值输入时衰减为 0。

        测试目的：
            验证零降雪率和非法负值输入的正确处理。
        预期行为：
            各种无雪输入下衰减均为 0.0。
        """
        assert snow_attenuation(0.0) == 0.0
        assert snow_attenuation(0.0, "dry") == 0.0
        assert snow_attenuation(-1.0) == 0.0

    def test_dry_snow_typical(self):
        """
        测试干雪（S = 5 mm/h）的衰减典型值。

        测试目的：
            验证干雪在中等降雪率下的衰减量级。
        预期行为：
            干雪衰减 > 5.0 dB/km。
        """
        alpha = snow_attenuation(5.0, "dry")
        assert alpha > 5.0

    def test_wet_snow_typical(self):
        """
        测试湿雪（S = 5 mm/h）的衰减典型值。

        测试目的：
            验证湿雪在中等降雪率下的衰减量级。
        预期行为：
            湿雪衰减 > 0.0 dB/km。
        """
        alpha = snow_attenuation(5.0, "wet")
        assert alpha > 0.0

    def test_wet_worse_than_dry_at_high_rate(self):
        """
        测试高降雪率下湿雪衰减大于干雪。

        测试目的：
            验证湿雪因含水量高导致更强的衰减。
        测试原理：
            湿雪颗粒表面有水膜，介电常数增大，导致对光波的散射和吸收更强。
        预期行为：
            S = 40 mm/h 时，湿雪衰减 > 干雪衰减。
        """
        alpha_wet = snow_attenuation(40.0, "wet")
        alpha_dry = snow_attenuation(40.0, "dry")
        assert alpha_wet > alpha_dry

    def test_default_is_wet(self):
        """
        测试默认雪类型为湿雪。

        测试目的：
            验证 snow_attenuation 在不指定 snow_type 时的默认行为。
        预期行为：
            snow_attenuation(5.0) == snow_attenuation(5.0, "wet")。
        """
        assert snow_attenuation(5.0) == snow_attenuation(5.0, "wet")

    def test_monotonic_wet(self):
        """
        测试湿雪衰减随降雪率单调递增。

        测试目的：
            验证湿雪衰减函数的单调性。
        预期行为：
            降雪率 [1, 3, 5, 10, 15] 对应的衰减值单调非减。
        """
        rates = [1.0, 3.0, 5.0, 10.0, 15.0]
        alphas = [snow_attenuation(r, "wet") for r in rates]
        for i in range(len(alphas) - 1):
            assert alphas[i + 1] >= alphas[i]


class TestTotalChannelLoss:
    """
    大气信道总损耗计算的测试集。

    测试目的：
        验证 total_channel_loss_db() 函数正确汇总各类大气衰减源
        （雾衰减 + 雨衰减 + 雪衰减）的总信道损耗。

    测试原理：
        总信道损耗 (dB) = 大气衰减 (dB/km) x 距离 (km) + 雨衰减 (dB/km) x 距离 + 雪衰减 (dB/km) x 距离。
        大气衰减可根据能见度选择 Kim 模型或 Naboulsi 模型计算。
        该损耗是 FSO 链路预算分析的核心输入参数。

    预期行为：
        各种天气条件下的总损耗在物理合理范围内，且各衰减源具有叠加性。
    """

    def test_clear_sky_kim(self):
        """
        测试晴朗天气下 Kim 模型的总信道损耗。

        测试目的：
            验证典型晴朗 FSO 链路的损耗在合理范围内。
        预期行为：
            能见度 23 km、距离 1 km、波长 1550 nm 时，总损耗在 0~5 dB 之间。
        """
        loss = total_channel_loss_db(23, 1.0, 1550)
        assert 0.0 < loss < 5.0

    def test_fog_kim(self):
        """
        测试浓雾天气下 Kim 模型的总信道损耗显著增大。

        测试目的：
            验证浓雾对 FSO 链路的严重影响。
        预期行为：
            能见度 0.5 km 时总损耗大于 20 dB。
        """
        loss = total_channel_loss_db(0.5, 1.0, 1550)
        assert loss > 20

    def test_fog_model_advection(self):
        """
        测试不同雾模型（Kim vs Naboulsi 平流雾）均返回正损耗。

        测试目的：
            验证两种雾模型在相同条件下均能正确计算衰减。
        预期行为：
            两种模型的总损耗均大于 0。
        """
        loss_kim = total_channel_loss_db(0.5, 1.0, 1550, fog_model="kim")
        loss_adv = total_channel_loss_db(0.5, 1.0, 1550, fog_model="naboulsi_advection")
        assert loss_kim > 0
        assert loss_adv > 0

    def test_fog_model_radiation(self):
        """
        测试 Naboulsi 辐射雾模型返回正损耗。

        测试目的：
            验证 Naboulsi 辐射雾模型的总损耗正确性。
        预期行为：
            辐射雾模型的总损耗大于 0。
        """
        loss_rad = total_channel_loss_db(0.5, 1.0, 1550, fog_model="naboulsi_radiation")
        assert loss_rad > 0

    def test_rain_contribution(self):
        """
        测试降雨对总信道损耗的附加贡献。

        测试目的：
            验证雨衰减作为独立分量被正确叠加到总损耗中。
        预期行为：
            有雨时的总损耗 > 无雨时的总损耗。
        """
        loss_no_rain = total_channel_loss_db(10, 1.0, 1550, rainfall_rate=0)
        loss_rain = total_channel_loss_db(10, 1.0, 1550, rainfall_rate=10)
        assert loss_rain > loss_no_rain

    def test_snow_contribution(self):
        """
        测试降雪对总信道损耗的附加贡献。

        测试目的：
            验证雪衰减作为独立分量被正确叠加到总损耗中。
        预期行为：
            有雪时的总损耗 > 无雪时的总损耗。
        """
        loss_no_snow = total_channel_loss_db(10, 1.0, 1550)
        loss_snow = total_channel_loss_db(10, 1.0, 1550, snowfall_rate=5, snow_type="dry")
        assert loss_snow > loss_no_snow

    def test_loss_proportional_to_distance(self):
        """
        测试信道损耗与传输距离成正比。

        测试目的：
            验证衰减的线性距离依赖关系。
        测试原理：
            总损耗 approx= (各衰减系数之和) x 距离，因此距离翻倍损耗翻倍。
        预期行为：
            距离 2 km 的总损耗 > 距离 1 km 的总损耗。
        """
        loss_1km = total_channel_loss_db(10, 1.0)
        loss_2km = total_channel_loss_db(10, 2.0)
        assert loss_2km > loss_1km

    def test_zero_distance(self):
        """
        测试零距离时总信道损耗为 0 dB。

        测试目的：
            验证零传输距离的边界条件。
        预期行为：
            total_channel_loss_db(23, 0.0) approx= 0.0。
        """
        loss = total_channel_loss_db(23, 0.0)
        assert loss == pytest.approx(0.0)

    def test_composite_weather(self):
        """
        测试复合天气条件（雾+雨+雪）下的总损耗。

        测试目的：
            验证多种衰减源同时存在时的叠加效果。
        预期行为：
            复合天气的总损耗 > 仅雾条件下的总损耗。
        """
        loss = total_channel_loss_db(5, 1.0, 1550, rainfall_rate=10, snowfall_rate=5, snow_type="wet")
        assert loss > total_channel_loss_db(5, 1.0, 1550)


class TestTransmittance:
    """
    大气透射率计算的测试集。

    测试目的：
        验证 transmittance() 函数将 dB 损耗正确转换为透射率 tau。

    测试原理：
        透射率 tau 与 dB 损耗 L 之间的关系：
          tau = 10^(-L/10)
        其中 L 由 total_channel_loss_db() 计算得出。
        tau 的取值范围为 0（完全衰减）到 1（完全传输）。

    预期行为：
        零损耗时透射率为 1，损耗增大时透射率单调递减至 0。
    """

    def test_perfect_transmission(self):
        """
        测试零损耗时的完美透射率。

        测试目的：
            验证零距离或零衰减下的完全传输。
        预期行为：
            transmittance(1000, 0.0) approx= 1.0（即使能见度差，距离为零时仍完全传输）。
        """
        tau = transmittance(1000, 0.0)
        assert tau == pytest.approx(1.0)

    def test_partial_transmission(self):
        """
        测试典型晴朗天气下的部分透射率。

        测试目的：
            验证典型 FSO 链路下的透射率介于 0~1 之间。
        预期行为：
            透射率在 0 到 1 之间。
        """
        tau = transmittance(23, 1.0)
        assert 0 < tau < 1

    def test_relation_to_total_loss(self):
        """
        测试透射率与总损耗之间的换算关系一致性。

        测试目的：
            验证 tau = 10^(-L/10) 的数学正确性。
        预期行为：
            两种计算方式得到的透射率一致。
        """
        loss = total_channel_loss_db(23, 1.0)
        tau = transmittance(23, 1.0)
        assert tau == pytest.approx(10 ** (-loss / 10))

    def test_severe_attenuation_approaches_zero(self):
        """
        测试极强衰减条件下透射率趋近于零。

        测试目的：
            验证严重雾衰减下的极端情况。
        预期行为：
            能见度 0.1 km、距离 5 km 时，透射率 < 0.01。
        """
        tau = transmittance(0.1, 5.0, fog_model="naboulsi_advection")
        assert tau < 0.01

    def test_monotonic_decreasing_with_distance(self):
        """
        测试透射率随距离增大而单调递减。

        测试目的：
            验证透射率的物理单调性。
        测试原理：
            距离越长，光通过的衰减介质越厚，透射率越低。
        预期行为：
            距离 2 km 的透射率 < 距离 1 km 的透射率。
        """
        tau_1 = transmittance(10, 1.0)
        tau_2 = transmittance(10, 2.0)
        assert tau_2 < tau_1
