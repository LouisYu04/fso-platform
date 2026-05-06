"""Tests for optical intensity probability distribution models."""

import pytest
import numpy as np
from fso_platform.models.distributions import (
    lognormal_pdf,
    gamma_gamma_alpha_beta,
    gamma_gamma_pdf,
    negative_exponential_pdf,
    select_distribution,
)


# =============================================================================
# 测试类：TestLognormalPDF
# 测试目的：验证 lognormal_pdf() 函数 —— 弱湍流条件下的光强概率密度分布
# 测试原理：在弱湍流条件下（Rytov 方差 σ_R² << 1），光强 I 的起伏服从对数正态分布。
#           该分布的概率密度函数为：
#               p(I) = (1 / (I · σ_I · √(2π))) · exp(-(ln I + σ_I²/2)² / (2σ_I²))
#           其中 σ_I² ≈ σ_R² 为光强对数方差。归一化光强满足 ⟨I⟩ = 1。
#           对数正态分布是 FSO 弱湍流信道建模的经典模型，适用于地面-近地链路。
# 预期行为：PDF 值非负，积分归一化为 1，均值为 1，非物理输入返回 0，
#           非法参数（σ_R² ≤ 0）抛出 ValueError。
# =============================================================================
class TestLognormalPDF:
    """Tests for lognormal_pdf() — weak turbulence intensity distribution."""

    # -------------------------------------------------------------------------
    # 测试目的：验证 PDF 在所有光强值上均非负
    # 测试原理：概率密度函数必须满足 p(I) ≥ 0 对所有 I 成立。
    #           在 [0.01, 3.0] 范围内密集采样并计算 PDF 值进行检查。
    # 预期行为：所有采样点的 PDF 值 ≥ 0
    # -------------------------------------------------------------------------
    def test_non_negative_values(self):
        I = np.linspace(0.01, 3.0, 100)
        pdf = lognormal_pdf(I, 0.1)
        assert np.all(pdf >= 0)

    # -------------------------------------------------------------------------
    # 测试目的：验证光强 I = 0 时 PDF 值为 0
    # 测试原理：对数正态分布的定义域为 I > 0。当 I = 0 时，ln(I) 趋于 -∞，
    #           物理上意味着光强为零的概率测度为 0。
    # 预期行为：lognormal_pdf(0) = 0.0
    # -------------------------------------------------------------------------
    def test_zero_returns_zero(self):
        result = lognormal_pdf(np.array([0.0]), 0.1)
        assert result[0] == 0.0

    # -------------------------------------------------------------------------
    # 测试目的：验证负光强输入时 PDF 值为 0
    # 测试原理：光强为物理非负量，负光强无物理意义。函数应对负输入安全处理，
    #           返回 0 而非报错或产生 NaN 等非法数值。
    # 预期行为：lognormal_pdf(-0.5) = 0.0
    # -------------------------------------------------------------------------
    def test_negative_returns_zero(self):
        result = lognormal_pdf(np.array([-0.5]), 0.1)
        assert result[0] == 0.0

    # -------------------------------------------------------------------------
    # 测试目的：验证 PDF 在全定义域上的归一化性质（积分为 1）
    # 测试原理：任何合法的概率密度函数必须满足 ∫₀^∞ p(I) dI = 1。
    #           使用数值梯形积分法在 [0.01, 5.0] 上近似计算积分值。
    #           由于截断误差和离散化误差，允许 ±0.05 的容差。
    # 预期行为：∫ p(I) dI ≈ 1.0，容差 ±0.05
    # -------------------------------------------------------------------------
    def test_approximate_normalization(self):
        I = np.linspace(0.01, 5.0, 1000)
        pdf = lognormal_pdf(I, 0.1)
        integral = np.trapezoid(pdf, I)
        assert integral == pytest.approx(1.0, abs=0.05)

    # -------------------------------------------------------------------------
    # 测试目的：验证对数正态分布的数学期望（均值）为 1
    # 测试原理：对于归一化光强，参数选择使得 ⟨I⟩ = exp(μ + σ²/2) = 1。
    #           通过数值计算 E[I] = ∫ I · p(I) dI 来验证均值性质。
    #           均值恒为 1 是归一化光强分布的基本约束。
    # 预期行为：E[I] ≈ 1.0，容差 ±0.1
    # -------------------------------------------------------------------------
    def test_mean_approaches_one(self):
        I = np.linspace(0.01, 5.0, 1000)
        pdf = lognormal_pdf(I, 0.2)
        mean = np.trapezoid(I * pdf, I)
        assert mean == pytest.approx(1.0, abs=0.1)

    # -------------------------------------------------------------------------
    # 测试目的：验证 σ_R² = 0 时抛出 ValueError 异常
    # 测试原理：σ_R² = 0 表示无湍流，此时对数正态分布退化为确定值（δ 分布），
    #           分布参数计算中出现除零。从物理和数值角度看，此输入均为非法。
    # 预期行为：抛出 ValueError，异常信息中应包含参数名 "sigma_R2"
    # -------------------------------------------------------------------------
    def test_value_error_zero_sigma(self):
        with pytest.raises(ValueError, match="sigma_R2"):
            lognormal_pdf(np.array([1.0]), 0.0)

    # -------------------------------------------------------------------------
    # 测试目的：验证 σ_R² < 0 时抛出 ValueError 异常
    # 测试原理：Rytov 方差 σ_R² 是湍流强度的度量，物理上必须为正数。
    #           负方差无物理意义，函数应明确拒绝此类非法输入。
    # 预期行为：抛出 ValueError，异常信息中应包含参数名 "sigma_R2"
    # -------------------------------------------------------------------------
    def test_value_error_negative_sigma(self):
        with pytest.raises(ValueError, match="sigma_R2"):
            lognormal_pdf(np.array([1.0]), -0.1)

    # -------------------------------------------------------------------------
    # 测试目的：验证函数支持向量化（数组）输入
    # 测试原理：基于 NumPy 实现的函数应支持批量计算，输入数组返回同形状数组。
    #           这是进行高效数值计算和绘图的前提条件。
    # 预期行为：输入形状 (4,) 的数组，输出形状也为 (4,)
    # -------------------------------------------------------------------------
    def test_vectorized_input(self):
        I = np.array([0.1, 0.5, 1.0, 2.0])
        pdf = lognormal_pdf(I, 0.1)
        assert pdf.shape == (4,)

    # -------------------------------------------------------------------------
    # 测试目的：验证对数正态分布的众数（mode）小于均值 1
    # 测试原理：对数正态分布的众数公式为 mode = exp(μ - σ²) = exp(-σ_I²) < 1。
    #           由于 σ_I² > 0，mode 总是小于均值 ⟨I⟩ = 1，这体现了对数正态分布
    #           的正偏态（右偏）特性：概率质量集中在左侧，右侧有长尾。
    # 预期行为：PDF 最大值对应的光强位置 I_mode < 1.0
    # -------------------------------------------------------------------------
    def test_mode_at_less_than_one(self):
        I = np.linspace(0.01, 3.0, 500)
        pdf = lognormal_pdf(I, 0.3)
        idx_max = np.argmax(pdf)
        assert I[idx_max] < 1.0


# =============================================================================
# 测试类：TestGammaGammaAlphaBeta
# 测试目的：验证 gamma_gamma_alpha_beta() 函数 —— Gamma-Gamma 分布参数计算
# 测试原理：Gamma-Gamma 湍流模型将光强起伏建模为两个独立 Gamma 随机过程的乘积：
#           大尺度闪烁（由 α 参数描述）和小尺度闪烁（由 β 参数描述）。
#           参数 α 和 β 由 Rytov 方差 σ_R² 通过以下关系式计算：
#               α = [exp(0.49σ_R² / (1 + 1.11σ_R^{12/5})^{7/6}) - 1]^{-1}
#               β = [exp(0.51σ_R² / (1 + 0.69σ_R^{12/5})^{5/6}) - 1]^{-1}
#           该模型适用于中等到强湍流条件（σ_R² ~ 1 至 25）。
# 预期行为：α > 0, β > 0 对所有合法 σ_R² 成立；β 随 σ_R² 增大而单调递减；
#           非法参数（σ_R² ≤ 0）抛出 ValueError。
# =============================================================================
class TestGammaGammaAlphaBeta:
    """Tests for gamma_gamma_alpha_beta() — Gamma-Gamma parameters."""

    # -------------------------------------------------------------------------
    # 测试目的：验证在中等湍流下计算得到的 α 和 β 均为正数
    # 测试原理：α 和 β 是 Gamma-Gamma 分布的形状参数，物理上必须为正。
    #           使用 σ_R² = 2.0（中等湍流）进行验证。
    # 预期行为：alpha > 0 且 beta > 0
    # -------------------------------------------------------------------------
    def test_both_positive(self):
        alpha, beta = gamma_gamma_alpha_beta(2.0)
        assert alpha > 0
        assert beta > 0

    # -------------------------------------------------------------------------
    # 测试目的：验证在强湍流（高 σ_R²）下参数仍然保持有效正值
    # 测试原理：Gamma-Gamma 模型在 σ_R² 较大时（如 10.0, 15.0, 25.0）
    #           应仍然产生合法的正参数，不会出现数值溢出或失效。
    # 预期行为：对所有测试的高 σ_R² 值，alpha > 0 且 beta > 0
    # -------------------------------------------------------------------------
    def test_params_remain_valid_at_high_sigma(self):
        for sr2 in [10.0, 15.0, 25.0]:
            alpha, beta = gamma_gamma_alpha_beta(sr2)
            assert alpha > 0
            assert beta > 0

    # -------------------------------------------------------------------------
    # 测试目的：验证 β 参数随 σ_R² 增大而单调递减
    # 测试原理：随着湍流强度增强，小尺度闪烁参数 β 应减小，
    #           表示闪烁更加剧烈。从公式可看出 β 随 σ_R² 增大而递减。
    # 预期行为：σ_R² = 10.0 时的 β 值小于 σ_R² = 1.0 时的 β 值
    # -------------------------------------------------------------------------
    def test_beta_decreases_with_sigma(self):
        a1, b1 = gamma_gamma_alpha_beta(1.0)
        a2, b2 = gamma_gamma_alpha_beta(10.0)
        assert b2 < b1

    # -------------------------------------------------------------------------
    # 测试目的：验证在各种湍流强度下参数计算均正确
    # 测试原理：使用参数化测试框架，覆盖从弱湍流到极强湍流的完整范围
    #           （σ_R² = 0.1, 0.5, 1.0, 5.0, 10.0, 25.0）。
    # 预期行为：对所有测试值，alpha > 0 且 beta > 0
    # -------------------------------------------------------------------------
    @pytest.mark.parametrize("sigma_R2", [0.1, 0.5, 1.0, 5.0, 10.0, 25.0])
    def test_params_for_various_regimes(self, sigma_R2):
        alpha, beta = gamma_gamma_alpha_beta(sigma_R2)
        assert alpha > 0
        assert beta > 0

    # -------------------------------------------------------------------------
    # 测试目的：验证 σ_R² = 0 时抛出 ValueError
    # 测试原理：σ_R² = 0 表示无湍流，Gamma-Gamma 模型在此边界下
    #           参数计算公式出现除零，应拒绝此输入。
    # 预期行为：抛出 ValueError，异常信息包含 "sigma_R2"
    # -------------------------------------------------------------------------
    def test_value_error_zero(self):
        with pytest.raises(ValueError, match="sigma_R2"):
            gamma_gamma_alpha_beta(0.0)

    # -------------------------------------------------------------------------
    # 测试目的：验证 σ_R² < 0 时抛出 ValueError
    # 测试原理：Rytov 方差为物理量，必须为正数。负输入非法。
    # 预期行为：抛出 ValueError，异常信息包含 "sigma_R2"
    # -------------------------------------------------------------------------
    def test_value_error_negative(self):
        with pytest.raises(ValueError, match="sigma_R2"):
            gamma_gamma_alpha_beta(-1.0)


# =============================================================================
# 测试类：TestGammaGammaPDF
# 测试目的：验证 gamma_gamma_pdf() 函数 —— 中等到强湍流条件下的光强概率密度分布
# 测试原理：Gamma-Gamma 分布的概率密度函数为：
#               p(I) = (2(αβ)^{(α+β)/2} / Γ(α)Γ(β)) · I^{(α+β)/2 - 1}
#                      · K_{α-β}(2√(αβI))
#           其中 Γ(·) 为 Gamma 函数，K_{ν}(·) 为 ν 阶第二类修正 Bessel 函数。
#           此模型由 Andrews 和 Phillips 提出，是中强湍流 FSO 信道建模的标准模型。
#           参数 α 和 β 通过 gamma_gamma_alpha_beta() 由 σ_R² 计算得出。
# 预期行为：PDF 值非负、积分归一、非物理输入返回 0、支持向量化计算。
# =============================================================================
class TestGammaGammaPDF:
    """Tests for gamma_gamma_pdf() — moderate-to-strong turbulence distribution."""

    # -------------------------------------------------------------------------
    # 测试目的：验证 Gamma-Gamma PDF 在所有光强值上均非负
    # 测试原理：以 σ_R² = 2.0（中等湍流）为例，计算参数 α、β，
    #           然后在 [0.01, 3.0] 范围内采样验证 PDF 非负性。
    # 预期行为：所有采样点的 PDF 值 ≥ 0
    # -------------------------------------------------------------------------
    def test_non_negative_values(self):
        alpha, beta = gamma_gamma_alpha_beta(2.0)
        I = np.linspace(0.01, 3.0, 100)
        pdf = gamma_gamma_pdf(I, alpha, beta)
        assert np.all(pdf >= 0)

    # -------------------------------------------------------------------------
    # 测试目的：验证 Gamma-Gamma PDF 的归一化性质
    # 测试原理：PDF 在 [0, ∞) 上的积分必须为 1。使用数值梯形积分
    #           在 [0.01, 5.0] 上近似计算。由于截断和离散误差，
    #           允许相对较大的容差 ±0.1。
    # 预期行为：∫ p(I) dI ≈ 1.0，容差 ±0.1
    # -------------------------------------------------------------------------
    def test_approximate_normalization(self):
        alpha, beta = gamma_gamma_alpha_beta(2.0)
        I = np.linspace(0.01, 5.0, 1000)
        pdf = gamma_gamma_pdf(I, alpha, beta)
        integral = np.trapezoid(pdf, I)
        assert integral == pytest.approx(1.0, abs=0.1)

    # -------------------------------------------------------------------------
    # 测试目的：验证光强 I = 0 时 Gamma-Gamma PDF 返回 0
    # 测试原理：对于 α > 1 且 β > 1 的情况，p(0) = 0（因为 Bessel 函数
    #           在自变量趋于 0 时有界，而 I^{(α+β)/2 - 1} 项趋于 0）。
    # 预期行为：gamma_gamma_pdf(0) = 0.0
    # -------------------------------------------------------------------------
    def test_zero_returns_zero(self):
        alpha, beta = gamma_gamma_alpha_beta(2.0)
        result = gamma_gamma_pdf(np.array([0.0]), alpha, beta)
        assert result[0] == 0.0

    # -------------------------------------------------------------------------
    # 测试目的：验证负光强输入时 Gamma-Gamma PDF 返回 0
    # 测试原理：负光强无物理意义，函数应安全处理非物理输入。
    # 预期行为：gamma_gamma_pdf(-1.0) = 0.0
    # -------------------------------------------------------------------------
    def test_negative_returns_zero(self):
        alpha, beta = gamma_gamma_alpha_beta(2.0)
        result = gamma_gamma_pdf(np.array([-1.0]), alpha, beta)
        assert result[0] == 0.0

    # -------------------------------------------------------------------------
    # 测试目的：验证 Gamma-Gamma PDF 支持向量化输入
    # 测试原理：输入多个光强值的数组，验证输出形状与输入一致。
    # 预期行为：输入形状 (5,) 的数组，输出形状也为 (5,)
    # -------------------------------------------------------------------------
    def test_vectorized_input(self):
        alpha, beta = gamma_gamma_alpha_beta(2.0)
        I = np.array([0.1, 0.5, 1.0, 2.0, 3.0])
        pdf = gamma_gamma_pdf(I, alpha, beta)
        assert pdf.shape == (5,)

    # -------------------------------------------------------------------------
    # 测试目的：验证 Gamma-Gamma PDF 在各种湍流强度下的有效性
    # 测试原理：遍历从 σ_R² = 1.0 到 25.0 的多种湍流条件，
    #           分别计算 α、β 和 PDF，验证 PDF 值非负且存在正值。
    # 预期行为：所有条件下 PDF 值 ≥ 0，且 PDF 不全为 0（存在正概率密度）
    # -------------------------------------------------------------------------
    def test_various_regimes(self):
        for sr2 in [1.0, 2.0, 5.0, 10.0, 25.0]:
            alpha, beta = gamma_gamma_alpha_beta(sr2)
            I = np.linspace(0.01, 5.0, 500)
            pdf = gamma_gamma_pdf(I, alpha, beta)
            assert np.all(pdf >= 0)
            assert np.any(pdf > 0)


# =============================================================================
# 测试类：TestNegativeExponentialPDF
# 测试目的：验证 negative_exponential_pdf() 函数 —— 饱和湍流条件下的光强分布
# 测试原理：在强湍流（饱和区，σ_R² → ∞）条件下，光强 I 的起伏服从
#           负指数分布（即均值为 1 的指数分布）：
#               p(I) = exp(-I),  I ≥ 0
#           这对应于 Gamma-Gamma 模型在 α → ∞、β → 1 时的极限情况，
#           也等价于充分发展的散斑（fully developed speckle）理论。
#           此时光强相干时间极短，接收光场表现为大量独立散射元的非相干叠加。
# 预期行为：p(I) = exp(-I)、p(0) = 1、负输入返回 0、积分归一化、
#           均值 E[I] = 1、单调递减、支持向量化。
# =============================================================================
class TestNegativeExponentialPDF:
    """Tests for negative_exponential_pdf() — saturated turbulence distribution."""

    # -------------------------------------------------------------------------
    # 测试目的：验证负指数 PDF 的解析形式与标准指数分布一致
    # 测试原理：负指数分布的定义为 p(I) = exp(-I)。函数值应直接匹配
    #           numpy.exp(-I)。这是该分布最基本的正确性检验。
    # 预期行为：negative_exponential_pdf(I) ≈ exp(-I)
    # -------------------------------------------------------------------------
    def test_standard_exponential(self):
        I = np.array([0.5, 1.0, 2.0])
        pdf = negative_exponential_pdf(I)
        expected = np.exp(-I)
        assert pdf == pytest.approx(expected)

    # -------------------------------------------------------------------------
    # 测试目的：验证 I = 0 时 PDF 值为 1
    # 测试原理：对于指数分布 p(I) = exp(-I)，p(0) = exp(0) = 1。
    #           这是指数分布的一个基本性质。
    # 预期行为：negative_exponential_pdf(0) = 1.0
    # -------------------------------------------------------------------------
    def test_zero_intensity(self):
        result = negative_exponential_pdf(np.array([0.0]))
        assert result[0] == pytest.approx(1.0)

    # -------------------------------------------------------------------------
    # 测试目的：验证负光强输入时 PDF 返回 0
    # 测试原理：负指数分布的定义域为 I ≥ 0，负输入应安全地返回 0。
    # 预期行为：negative_exponential_pdf(-0.5) = 0.0
    # -------------------------------------------------------------------------
    def test_negative_intensity_zero(self):
        result = negative_exponential_pdf(np.array([-0.5]))
        assert result[0] == 0.0

    # -------------------------------------------------------------------------
    # 测试目的：验证负指数 PDF 的归一化性质
    # 测试原理：∫₀^∞ exp(-I) dI = 1，此为指数分布的解析积分结果。
    #           使用数值梯形积分在 [0, 10] 上验证。
    # 预期行为：∫ exp(-I) dI ≈ 1.0，容差 ±0.01
    # -------------------------------------------------------------------------
    def test_normalization(self):
        I = np.linspace(0, 10, 2000)
        pdf = negative_exponential_pdf(I)
        integral = np.trapezoid(pdf, I)
        assert integral == pytest.approx(1.0, abs=0.01)

    # -------------------------------------------------------------------------
    # 测试目的：验证负指数分布的均值为 1
    # 测试原理：标准指数分布 Exp(λ) 的均值为 1/λ。此处 λ = 1，
    #           故 E[I] = ∫ I · exp(-I) dI = 1。通过数值积分验证。
    # 预期行为：E[I] ≈ 1.0，容差 ±0.01
    # -------------------------------------------------------------------------
    def test_mean_is_one(self):
        I = np.linspace(0, 10, 2000)
        pdf = negative_exponential_pdf(I)
        mean = np.trapezoid(I * pdf, I)
        assert mean == pytest.approx(1.0, abs=0.01)

    # -------------------------------------------------------------------------
    # 测试目的：验证负指数 PDF 支持向量化输入
    # 测试原理：测试函数对数组输入的兼容性。
    # 预期行为：输入形状 (5,) 的数组，输出形状也为 (5,)
    # -------------------------------------------------------------------------
    def test_vectorized(self):
        I = np.array([0.0, 0.5, 1.0, 2.0, 5.0])
        pdf = negative_exponential_pdf(I)
        assert pdf.shape == (5,)

    # -------------------------------------------------------------------------
    # 测试目的：验证负指数 PDF 的单调递减性质
    # 测试原理：指数分布 p(I) = exp(-I) 的导数为 -exp(-I) < 0，
    #           因此函数严格单调递减。验证每相邻两点之间递减关系。
    # 预期行为：对任意 I₁ < I₂，有 p(I₁) ≥ p(I₂)（允许数值舍入误差）
    # -------------------------------------------------------------------------
    def test_monotonic_decreasing(self):
        I = np.linspace(0, 10, 100)
        pdf = negative_exponential_pdf(I)
        for i in range(len(pdf) - 1):
            assert pdf[i + 1] <= pdf[i] + 1e-12


# =============================================================================
# 测试类：TestSelectDistribution
# 测试目的：验证 select_distribution() 函数 —— 根据湍流强度自动选择概率分布模型
# 测试原理：FSO 湍流信道中，不同湍流强度采用不同的光强分布模型：
#           • σ_R² ∈ [0, 1)   → 对数正态分布（弱湍流）
#           • σ_R² ∈ [1, 25]  → Gamma-Gamma 分布（中强湍流）
#           • σ_R² ∈ (25, ∞)  → 负指数分布（饱和湍流）
#           函数应返回（分布名称, PDF 函数, 参数字典）三元组。
# 预期行为：根据 σ_R² 值正确映射到对应的分布模型、返回正确的 PDF 函数引用、
#           非法 σ_R²（负值）抛出 ValueError。
# =============================================================================
class TestSelectDistribution:
    """Tests for select_distribution() — automatic distribution selection."""

    # -------------------------------------------------------------------------
    # 测试目的：全面验证各湍流区间的分布选择逻辑
    # 测试原理：使用参数化测试覆盖三种湍流状态的所有边界：
    #           • [0.0, 0.99] → 对数正态分布
    #           • [1.0, 25.0] → Gamma-Gamma 分布
    #           • (25.0, ∞)   → 负指数分布
    #           同时验证返回的参数字典包含正确的键名。
    # 预期行为：分布名称匹配、参数键存在、PDF 函数不为 None
    # -------------------------------------------------------------------------
    @pytest.mark.parametrize("sigma_R2, expected_name, expected_params_key", [
        (0.0, "对数正态分布", "sigma_R2"),
        (0.1, "对数正态分布", "sigma_R2"),
        (0.5, "对数正态分布", "sigma_R2"),
        (0.99, "对数正态分布", "sigma_R2"),
        (1.0, "Gamma-Gamma分布", "alpha"),
        (5.0, "Gamma-Gamma分布", "alpha"),
        (10.0, "Gamma-Gamma分布", "alpha"),
        (25.0, "Gamma-Gamma分布", "alpha"),
        (25.01, "负指数分布", None),
        (50.0, "负指数分布", None),
        (100.0, "负指数分布", None),
    ])
    def test_distribution_selection(self, sigma_R2, expected_name, expected_params_key):
        name, pdf_func, params = select_distribution(sigma_R2)
        assert name == expected_name
        if expected_params_key is not None:
            assert expected_params_key in params
        assert pdf_func is not None

    # -------------------------------------------------------------------------
    # 测试目的：验证负 σ_R² 输入时抛出 ValueError
    # 测试原理：Rytov 方差必须为正，负值非法。测试多种负值情况。
    # 预期行为：抛出 ValueError，异常信息包含 "sigma_R2"
    # -------------------------------------------------------------------------
    @pytest.mark.parametrize("sigma_R2", [-0.1, -1.0, -10.0])
    def test_value_error_negative(self, sigma_R2):
        with pytest.raises(ValueError, match="sigma_R2"):
            select_distribution(sigma_R2)

    # -------------------------------------------------------------------------
    # 测试目的：验证弱湍流时正确返回 lognormal_pdf 函数引用
    # 测试原理：σ_R² = 0.1 属于弱湍流区间，应映射到对数正态分布。
    #           同时验证参数字典中含有 σ_R² 键且值正确传递。
    # 预期行为：函数引用 == lognormal_pdf，params["sigma_R2"] == 0.1
    # -------------------------------------------------------------------------
    def test_lognormal_func_matches(self):
        name, pdf_func, params = select_distribution(0.1)
        assert pdf_func == lognormal_pdf
        assert params["sigma_R2"] == 0.1

    # -------------------------------------------------------------------------
    # 测试目的：验证中强湍流时正确返回 gamma_gamma_pdf 函数引用
    # 测试原理：σ_R² = 5.0 属于 Gamma-Gamma 分布区间。
    #           验证参数字典中包含 α 和 β 两个形状参数。
    # 预期行为：函数引用 == gamma_gamma_pdf，params 包含 "alpha" 和 "beta"
    # -------------------------------------------------------------------------
    def test_gamma_gamma_func_matches(self):
        name, pdf_func, params = select_distribution(5.0)
        assert pdf_func == gamma_gamma_pdf
        assert "alpha" in params
        assert "beta" in params

    # -------------------------------------------------------------------------
    # 测试目的：验证饱和湍流时正确返回 negative_exponential_pdf 函数引用
    # 测试原理：σ_R² = 50.0 属于饱和湍流区间，应映射到负指数分布。
    #           负指数分布无额外参数，参数字典应为空。
    # 预期行为：函数引用 == negative_exponential_pdf，params == {}
    # -------------------------------------------------------------------------
    def test_neg_exp_func_matches(self):
        name, pdf_func, params = select_distribution(50.0)
        assert pdf_func == negative_exponential_pdf
        assert params == {}
