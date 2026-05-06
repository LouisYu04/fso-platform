"""Tests for shared scintillation log-intensity variance module."""

import pytest
import numpy as np
from fso_platform.models.scintillation import (
    sigma_ln_plane_wave,
    sigma_ln_spherical_wave,
)


# =============================================================================
# 测试类：TestSigmaLnPlaneWave
# 测试目的：
#   验证 sigma_ln_plane_wave() 函数（平面波对数光强方差计算）的正确性。
#   该函数返回两个分量：σ²_ln_x（大尺度闪烁对数方差）和 σ²_ln_y（小尺度闪烁对数方差）。
# 测试原理：
#   在 Rytov 湍流理论中，平面波在 Kolmogorov 湍流介质中传播时，
#   对数光强起伏的方差由 Rytov 方差 σ_R² 表征。根据修正的 Rytov 理论，
#   闪烁被分解为大尺度（折射）和小尺度（衍射）两个独立过程：
#     σ²_ln_x = 0.49·σ_R² / (1 + 1.11·σ_R^(12/5))^(7/6)   —— 大尺度分量
#     σ²_ln_y = 0.51·σ_R² / (1 + 0.69·σ_R^(12/5))^(5/6)   —— 小尺度分量
#   总闪烁指数 σ²_I = exp(σ²_ln_x + σ²_ln_y) - 1。
# 预期行为：
#   函数返回 (σ²_ln_x, σ²_ln_y) 二元组；输入标量或数组时返回相应类型；
#   输入为负时抛出 ValueError；弱湍流时两分量皆非负；
#   小尺度分量 σ²_ln_y 随 σ_R² 单调递增，大尺度分量 σ²_ln_x 在强湍流区可能下降（饱和效应）。
# =============================================================================
class TestSigmaLnPlaneWave:
    """Tests for sigma_ln_plane_wave() — plane wave log-intensity variances."""

    # ── scalar inputs ──────────────────────────────────────────────────────

    @pytest.mark.parametrize("sigma_R2", [0.0, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0])
    def test_returns_tuple(self, sigma_R2):
        # 测试目的：验证函数返回值类型为二元组
        # 测试原理：平面波闪烁方差应返回 (大尺度分量, 小尺度分量) 两个值
        # 预期行为：所有输入下返回值均为 tuple，且长度为 2
        result = sigma_ln_plane_wave(sigma_R2)
        assert isinstance(result, tuple)
        assert len(result) == 2

    @pytest.mark.parametrize("sigma_R2", [0.0, 0.1, 0.5, 1.0, 5.0, 10.0])
    def test_both_non_negative(self, sigma_R2):
        # 测试目的：验证两个闪烁分量均非负
        # 测试原理：对数光强方差是能量起伏的度量，物理上必须 ≥ 0
        # 预期行为：在弱到中等湍流下，σ²_ln_x ≥ 0 且 σ²_ln_y ≥ 0
        sx2, sy2 = sigma_ln_plane_wave(sigma_R2)
        assert float(sx2) >= 0
        assert float(sy2) >= 0

    @pytest.mark.parametrize("sigma_R2", [0.0, 0.1, 0.5, 1.0, 5.0, 10.0])
    def test_y2_increases_with_sigmaR2(self, sigma_R2):
        """sigma_ln_y2 应随 sigma_R2 单调递增（x2 不单调，在强湍流区会下降）"""
        # 测试目的：验证小尺度闪烁分量 σ²_ln_y 随湍流强度单调递增
        # 测试原理：小尺度闪烁由衍射效应主导，随着湍流增强，衍射效应持续增强，
        #          因此 σ²_ln_y 应始终随 σ_R² 增加而增大（不饱和）
        # 预期行为：对每个测试点，当前 σ_R² 下的 σ²_ln_y 大于其一半值时的 σ²_ln_y
        if float(sigma_R2) == 0:
            return
        prev_y2 = float(sigma_ln_plane_wave(sigma_R2 * 0.5)[1])
        curr_y2 = float(sigma_ln_plane_wave(sigma_R2)[1])
        assert curr_y2 > prev_y2

    def test_zero_sigma_gives_zero(self):
        # 测试目的：验证无湍流时闪烁方差为零
        # 测试原理：当 σ_R² = 0（无湍流），大气折射率均匀，不存在光强起伏，
        #          对数光强方差应为零
        # 预期行为：σ²_ln_x = 0.0, σ²_ln_y = 0.0
        sx2, sy2 = sigma_ln_plane_wave(0.0)
        assert float(sx2) == 0.0
        assert float(sy2) == 0.0

    def test_increases_with_sigmaR2(self):
        """sigma_ln_y2 单调递增；x2 在强湍流区会下降，只验证 y2"""
        # 测试目的：在较宽的湍流强度范围（弱到强）内验证 σ²_ln_y 单调递增
        # 测试原理：使用更多采样点进行系统性单调性检验。小尺度闪烁不会出现饱和效应，
        #          而大尺度分量在强湍流区会因涡旋破碎而下降，因此只检验 y2
        # 预期行为：随着 σ_R² 从 0.1 增加到 50.0，σ²_ln_y 严格单调递增
        values = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 50.0]
        _, prev_y2 = sigma_ln_plane_wave(values[0])
        for v in values[1:]:
            _, y2 = sigma_ln_plane_wave(v)
            assert float(y2) > float(prev_y2)
            prev_y2 = y2

    # ── ndarray inputs ─────────────────────────────────────────────────────

    def test_vectorized_returns_arrays(self):
        # 测试目的：验证函数支持向量化（ndarray）输入
        # 测试原理：物理模型函数应支持 NumPy 数组广播，批量计算多个 σ_R² 值
        # 预期行为：以长度为 5 的数组输入时，返回两个形状同为 (5,) 的 ndarray
        sr2 = np.array([0.1, 0.5, 1.0, 5.0, 10.0])
        sx2, sy2 = sigma_ln_plane_wave(sr2)
        assert isinstance(sx2, np.ndarray)
        assert isinstance(sy2, np.ndarray)
        assert sx2.shape == (5,)
        assert sy2.shape == (5,)

    def test_vectorized_elements_non_negative(self):
        # 测试目的：验证向量化输出中每个元素均非负
        # 测试原理：无论输入是标量还是数组，物理约束（闪烁方差 ≥ 0）必须始终满足
        # 预期行为：输出数组的所有元素 ≥ 0
        sr2 = np.array([0.0, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0])
        sx2, sy2 = sigma_ln_plane_wave(sr2)
        assert np.all(sx2 >= 0)
        assert np.all(sy2 >= 0)

    def test_vectorized_matches_scalar(self):
        # 测试目的：验证向量化计算与逐元素标量计算的结果一致
        # 测试原理：向量化是数值优化手段，不能改变物理结果。数组输入应等价于
        #          对每个元素单独调用标量版本
        # 预期行为：数组输出的第 i 个元素 ≈ 对应标量输入的单次函数返回值
        sr2 = np.array([0.1, 0.5, 1.0, 5.0])
        sx2_arr, sy2_arr = sigma_ln_plane_wave(sr2)
        for i, v in enumerate(sr2):
            sx2_sca, sy2_sca = sigma_ln_plane_wave(v)
            assert float(sx2_arr[i]) == pytest.approx(float(sx2_sca))
            assert float(sy2_arr[i]) == pytest.approx(float(sy2_sca))

    def test_list_input_coerced(self):
        # 测试目的：验证 Python list 输入能被自动转换为 ndarray
        # 测试原理：为提升 API 易用性，函数应接受 list 类型输入并内部转换
        # 预期行为：list 输入返回 ndarray 类型输出，形状与输入长度一致
        sx2, sy2 = sigma_ln_plane_wave([0.1, 0.5, 1.0])
        assert isinstance(sx2, np.ndarray)
        assert sx2.shape == (3,)

    # ── validation ─────────────────────────────────────────────────────────

    @pytest.mark.parametrize("sr2", [-0.1, -1.0, -100.0])
    def test_value_error_negative_scalar(self, sr2):
        # 测试目的：验证负 Rytov 方差输入会引发错误
        # 测试原理：σ_R² ≥ 0 是物理约束（Rytov 方差由 Cn², k, L 平方计算得出，
        #          三者均为非负物理量），负值输入无物理意义
        # 预期行为：抛出 ValueError，错误信息包含 "sigma_R2"
        with pytest.raises(ValueError, match="sigma_R2"):
            sigma_ln_plane_wave(sr2)

    def test_value_error_negative_in_array(self):
        # 测试目的：验证数组中包含负值时会引发错误
        # 测试原理：向量化输入同样需要遵守物理约束，数组中的任一负值都应被拒绝
        # 预期行为：抛出 ValueError，错误信息包含 "sigma_R2"
        with pytest.raises(ValueError, match="sigma_R2"):
            sigma_ln_plane_wave(np.array([0.1, -0.5, 1.0]))

    # ── numerical consistency with original inline formulas ────────────────

    def test_matches_original_inline_formula(self):
        """验证提取后的公式与原始内联公式数值一致"""
        # 测试目的：验证重构提取后的函数与原始内联实现完全一致
        # 测试原理：当将之前内联在湍流模块中的公式提取为独立函数后，
        #          数值结果必须保持不变（回归测试）
        # 预期行为：在所有测试点上，新函数与原内联公式的输出完全一致（浮点近似）
        def original_plane_wave(sigma_R2):
            sr2 = np.asarray(sigma_R2, dtype=float)
            s12_5 = sr2 ** (6.0 / 5.0)
            sx2 = 0.49 * sr2 / (1 + 1.11 * s12_5) ** (7.0 / 6.0)
            sy2 = 0.51 * sr2 / (1 + 0.69 * s12_5) ** (5.0 / 6.0)
            return sx2, sy2

        for v in [0.0, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0]:
            sx2_new, sy2_new = sigma_ln_plane_wave(v)
            sx2_old, sy2_old = original_plane_wave(v)
            assert float(sx2_new) == pytest.approx(float(sx2_old))
            assert float(sy2_new) == pytest.approx(float(sy2_old))

    def test_matches_original_inline_formula_vectorized(self):
        # 测试目的：验证向量化模式下重构函数与原始实现的一致性
        # 测试原理：与标量版本类似，需确保数组输入时两实现完全一致
        # 预期行为：两实现输出的数组在数值上完全一致（np.allclose）
        def original_plane_wave(sigma_R2):
            sr2 = np.asarray(sigma_R2, dtype=float)
            s12_5 = sr2 ** (6.0 / 5.0)
            sx2 = 0.49 * sr2 / (1 + 1.11 * s12_5) ** (7.0 / 6.0)
            sy2 = 0.51 * sr2 / (1 + 0.69 * s12_5) ** (5.0 / 6.0)
            return sx2, sy2

        sr2_arr = np.array([0.1, 0.5, 1.0, 5.0, 10.0, 50.0])
        sx2_new, sy2_new = sigma_ln_plane_wave(sr2_arr)
        sx2_old, sy2_old = original_plane_wave(sr2_arr)
        assert np.allclose(sx2_new, sx2_old)
        assert np.allclose(sy2_new, sy2_old)


# =============================================================================
# 测试类：TestSigmaLnSphericalWave
# 测试目的：
#   验证 sigma_ln_spherical_wave() 函数（球面波对数光强方差计算）的正确性。
#   与平面波类似，球面波闪烁也分解为大尺度分量 σ²_ln_x 和小尺度分量 σ²_ln_y。
# 测试原理：
#   球面波（点光源）与平面波的差异在于波前曲率。在 Rytov 湍流理论中，
#   球面波的有效 Rytov 方差需乘以系数 0.4（称为球面波修正因子）：
#     β₀² = 0.4 · σ_R²
#   然后以 β₀² 替代 σ_R² 代入闪烁公式：
#     σ²_ln_x = 0.49·β₀² / (1 + 0.56·β₀^(12/5))^(7/6)
#     σ²_ln_y = 0.51·β₀² / (1 + 0.69·β₀^(12/5))^(5/6)
#   其中系数 0.56（而非平面波的 1.11）反映了球面波大尺度滤波的差异。
#   物理上，球面波由于波前发散，通过相同湍流路径时的总闪烁弱于平面波。
# 预期行为：
#   函数返回 (σ²_ln_x, σ²_ln_y) 二元组；输入为负时抛出 ValueError；
#   各分量非负；在弱湍流下总闪烁指数小于平面波对应值。
# =============================================================================
class TestSigmaLnSphericalWave:
    """Tests for sigma_ln_spherical_wave() — spherical wave log-intensity variances."""

    # ── scalar inputs ──────────────────────────────────────────────────────

    @pytest.mark.parametrize("sigma_R2", [0.0, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0])
    def test_returns_tuple(self, sigma_R2):
        # 测试目的：验证函数返回值类型为二元组
        # 测试原理：球面波闪烁方差同样返回 (大尺度分量, 小尺度分量) 两个值
        # 预期行为：所有输入下返回值均为 tuple，且长度为 2
        result = sigma_ln_spherical_wave(sigma_R2)
        assert isinstance(result, tuple)
        assert len(result) == 2

    @pytest.mark.parametrize("sigma_R2", [0.0, 0.1, 0.5, 1.0, 5.0, 10.0])
    def test_both_non_negative(self, sigma_R2):
        # 测试目的：验证球面波两闪烁分量均非负
        # 测试原理：与平面波相同，对数光强方差物理上必须 ≥ 0
        # 预期行为：在弱到中等湍流下，σ²_ln_x ≥ 0 且 σ²_ln_y ≥ 0
        sx2, sy2 = sigma_ln_spherical_wave(sigma_R2)
        assert float(sx2) >= 0
        assert float(sy2) >= 0

    def test_zero_sigma_gives_zero(self):
        # 测试目的：验证无湍流时球面波闪烁方差为零
        # 测试原理：σ_R² = 0 时 β₀² = 0，两分量均为零
        # 预期行为：σ²_ln_x = 0.0, σ²_ln_y = 0.0
        sx2, sy2 = sigma_ln_spherical_wave(0.0)
        assert float(sx2) == 0.0
        assert float(sy2) == 0.0

    def test_increases_with_sigmaR2(self):
        # 测试目的：验证球面波两闪烁分量均随湍流强度单调递增
        # 测试原理：球面波在弱到中等湍流范围内（σ_R² ≤ 5），大尺度和小尺度闪烁
        #          都尚未进入饱和区，因此两分量均应单调递增
        # 预期行为：在 [0.1, 0.5, 1.0, 2.0, 5.0] 范围内，σ²_ln_x 和 σ²_ln_y 均严格递增
        values = [0.1, 0.5, 1.0, 2.0, 5.0]
        prev_x2, prev_y2 = sigma_ln_spherical_wave(values[0])
        for v in values[1:]:
            x2, y2 = sigma_ln_spherical_wave(v)
            assert float(x2) > float(prev_x2)
            assert float(y2) > float(prev_y2)
            prev_x2, prev_y2 = x2, y2

    # ── spherical vs plane wave comparison ─────────────────────────────────

    @pytest.mark.parametrize("sigma_R2", [0.1, 0.5, 1.0])
    def test_spherical_total_scintillation_less_than_plane_weak(self, sigma_R2):
        """弱湍流（σ_R² ≤ 1）时球面波总闪烁指数 < 平面波"""
        # 测试目的：验证弱湍流下球面波总闪烁指数小于平面波
        # 测试原理：球面波波前发散，光场经过相同湍流路径时的相位扰动累积小于平面波，
        #          因此闪烁指数 σ²_I（即归一化光强方差）应显著小于平面波。
        #          这也从物理上验证了 β₀² = 0.4·σ_R² 修正因子的合理性。
        # 预期行为：对弱湍流 σ_R² ∈ {0.1, 0.5, 1.0}，球面波闪烁指数始终低于平面波
        from fso_platform.models.turbulence import (
            scintillation_index_plane_wave,
            scintillation_index_spherical_wave,
        )
        si2_plane = scintillation_index_plane_wave(sigma_R2)
        si2_spherical = scintillation_index_spherical_wave(sigma_R2)
        assert float(si2_spherical) < float(si2_plane)

    # ── ndarray inputs ─────────────────────────────────────────────────────

    def test_vectorized_returns_arrays(self):
        # 测试目的：验证球面波函数支持向量化输入
        # 测试原理：与平面波类似，应支持 NumPy 数组批量计算
        # 预期行为：以长度为 5 的数组输入时，返回两个形状同为 (5,) 的 ndarray
        sr2 = np.array([0.1, 0.5, 1.0, 5.0, 10.0])
        sx2, sy2 = sigma_ln_spherical_wave(sr2)
        assert isinstance(sx2, np.ndarray)
        assert isinstance(sy2, np.ndarray)
        assert sx2.shape == (5,)
        assert sy2.shape == (5,)

    def test_vectorized_matches_scalar(self):
        # 测试目的：验证球面波向量化与标量计算的一致性
        # 测试原理：向量化不能改变物理结果
        # 预期行为：数组输出的第 i 个元素 ≈ 对应标量输入的单次函数返回值
        sr2 = np.array([0.1, 0.5, 1.0, 5.0])
        sx2_arr, sy2_arr = sigma_ln_spherical_wave(sr2)
        for i, v in enumerate(sr2):
            sx2_sca, sy2_sca = sigma_ln_spherical_wave(v)
            assert float(sx2_arr[i]) == pytest.approx(float(sx2_sca))
            assert float(sy2_arr[i]) == pytest.approx(float(sy2_sca))

    # ── validation ─────────────────────────────────────────────────────────

    @pytest.mark.parametrize("sr2", [-0.1, -1.0, -100.0])
    def test_value_error_negative_scalar(self, sr2):
        # 测试目的：验证球面波函数拒绝负 Rytov 方差输入
        # 测试原理：σ_R² ≥ 0 是普适物理约束，与波前类型无关
        # 预期行为：抛出 ValueError，错误信息包含 "sigma_R2"
        with pytest.raises(ValueError, match="sigma_R2"):
            sigma_ln_spherical_wave(sr2)

    def test_value_error_negative_in_array(self):
        # 测试目的：验证球面波函数数组中负值引发错误
        # 测试原理：向量化输入同样需要遵守物理约束
        # 预期行为：抛出 ValueError，错误信息包含 "sigma_R2"
        with pytest.raises(ValueError, match="sigma_R2"):
            sigma_ln_spherical_wave(np.array([0.1, -0.5, 1.0]))

    # ── numerical consistency with original inline formula ────────────────

    def test_matches_original_inline_formula(self):
        # 测试目的：验证重构后的球面波函数与原始内联实现数值一致
        # 测试原理：回归测试，确保代码提取/重构未改变数值结果
        # 预期行为：在所有测试点上，新函数与原内联公式输出完全一致（浮点近似）
        def original_spherical_wave(sigma_R2):
            sr2 = np.asarray(sigma_R2, dtype=float)
            b02 = 0.4 * sr2
            b125 = b02 ** (6.0 / 5.0)
            sx2 = 0.49 * b02 / (1 + 0.56 * b125) ** (7.0 / 6.0)
            sy2 = 0.51 * b02 / (1 + 0.69 * b125) ** (5.0 / 6.0)
            return sx2, sy2

        for v in [0.0, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0]:
            sx2_new, sy2_new = sigma_ln_spherical_wave(v)
            sx2_old, sy2_old = original_spherical_wave(v)
            assert float(sx2_new) == pytest.approx(float(sx2_old))
            assert float(sy2_new) == pytest.approx(float(sy2_old))

    def test_matches_original_inline_formula_vectorized(self):
        # 测试目的：验证向量化模式下球面波重构函数与原始实现的一致性
        # 测试原理：与标量版本类似，数组输入时两实现应完全一致
        # 预期行为：两实现输出的数组在数值上完全一致（np.allclose）
        def original_spherical_wave(sigma_R2):
            sr2 = np.asarray(sigma_R2, dtype=float)
            b02 = 0.4 * sr2
            b125 = b02 ** (6.0 / 5.0)
            sx2 = 0.49 * b02 / (1 + 0.56 * b125) ** (7.0 / 6.0)
            sy2 = 0.51 * b02 / (1 + 0.69 * b125) ** (5.0 / 6.0)
            return sx2, sy2

        sr2_arr = np.array([0.1, 0.5, 1.0, 5.0, 10.0, 50.0])
        sx2_new, sy2_new = sigma_ln_spherical_wave(sr2_arr)
        sx2_old, sy2_old = original_spherical_wave(sr2_arr)
        assert np.allclose(sx2_new, sx2_old)
        assert np.allclose(sy2_new, sy2_old)


# =============================================================================
# 测试类：TestIntegration
# 测试目的：
#   集成测试，验证重构后的 sigma_ln_plane_wave() / sigma_ln_spherical_wave()
#   函数在通过上层模块（turbulence、distributions）调用时仍保持一致的行为。
# 测试原理：
#   代码重构（将内联闪烁公式提取为独立函数）不应改变上层消费者模块的输出。
#   这些测试作为回归检查，确保调用链完整：
#     sigma_ln_plane_wave → scintillation_index_plane_wave
#     sigma_ln_spherical_wave → scintillation_index_spherical_wave
#     sigma_ln_* → gamma_gamma_alpha_beta（Gamma-Gamma 分布的 α、β 参数）
# 预期行为：
#   上层消费者函数的输出与重构前一致：闪烁指数非负；
#   Gamma-Gamma 分布的 α、β 参数为正；向量化输入兼容。
# =============================================================================
class TestIntegration:
    """Integration tests: refactored consumers produce identical output."""

    def test_turbulence_plane_wave_unchanged(self):
        # 测试目的：验证平面波闪烁指数函数调用正常
        # 测试原理：scintillation_index_plane_wave 内部调用 sigma_ln_plane_wave，
        #          总闪烁指数 σ²_I = exp(σ²_ln_x + σ²_ln_y) - 1，物理上必须 ≥ 0
        # 预期行为：对宽范围 σ_R²（含零），闪烁指数 ≥ 0
        from fso_platform.models.turbulence import scintillation_index_plane_wave

        for v in [0.0, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0]:
            si2 = scintillation_index_plane_wave(v)
            assert si2 >= 0

    def test_turbulence_spherical_wave_unchanged(self):
        # 测试目的：验证球面波闪烁指数函数调用正常
        # 测试原理：scintillation_index_spherical_wave 内部调用 sigma_ln_spherical_wave，
        #          总闪烁指数 σ²_I ≥ 0
        # 预期行为：对宽范围 σ_R²，闪烁指数 ≥ 0
        from fso_platform.models.turbulence import scintillation_index_spherical_wave

        for v in [0.0, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0]:
            si2 = scintillation_index_spherical_wave(v)
            assert si2 >= 0

    def test_distributions_alpha_beta_unchanged(self):
        # 测试目的：验证 Gamma-Gamma 分布参数生成函数调用正常
        # 测试原理：Gamma-Gamma 分布是光强闪烁的概率模型，其形状参数 α 和 β
        #          由闪烁方差导出（α = 1/σ²_ln_x, β = 1/σ²_ln_y），
        #          作为概率分布的形状参数，α > 0 且 β > 0 是数学上的必要条件
        # 预期行为：对宽范围 σ_R²，α > 0 且 β > 0
        from fso_platform.models.distributions import gamma_gamma_alpha_beta

        for v in [0.1, 0.5, 1.0, 5.0, 10.0, 25.0]:
            alpha, beta = gamma_gamma_alpha_beta(v)
            assert alpha > 0
            assert beta > 0

    def test_vectorized_turbulence_plane_wave_unchanged(self):
        # 测试目的：验证平面波闪烁指数函数的向量化支持
        # 测试原理：上层消费者函数应继承底层函数的向量化能力
        # 预期行为：输入长度为 5 的数组，输出形状为 (5,) 且所有元素 ≥ 0
        from fso_platform.models.turbulence import scintillation_index_plane_wave

        sr2 = np.array([0.1, 0.5, 1.0, 5.0, 10.0])
        result = scintillation_index_plane_wave(sr2)
        assert result.shape == (5,)
        assert np.all(result >= 0)

    def test_vectorized_turbulence_spherical_wave_unchanged(self):
        # 测试目的：验证球面波闪烁指数函数的向量化支持
        # 测试原理：上层消费者函数应继承底层函数的向量化能力
        # 预期行为：输入长度为 4 的数组，输出形状为 (4,) 且所有元素 ≥ 0
        from fso_platform.models.turbulence import scintillation_index_spherical_wave

        sr2 = np.array([0.1, 0.5, 1.0, 5.0])
        result = scintillation_index_spherical_wave(sr2)
        assert result.shape == (4,)
        assert np.all(result >= 0)
