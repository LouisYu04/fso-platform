"""Tests for physical constants and unit conversion functions."""

import pytest
import numpy as np
from fso_platform.utils.constants import (
    C, K_B, Q_E, H, PI,
    LAMBDA_850, LAMBDA_1064, LAMBDA_1550, LAMBDA_REF_NM,
    wavelength_to_wavenumber,
    wavelength_to_frequency,
    dbm_to_watt,
    watt_to_dbm,
    db_to_linear,
    linear_to_db,
)


# =============================================================================
# 测试类：TestPhysicalConstants
# 测试目的：验证模块中定义的物理常数是否与国际标准值（CODATA 2018）一致。
# 测试原理：FSO 链路计算依赖于精确的物理常数（光速、玻尔兹曼常数、元电荷、
#           普朗克常数等），这些常数由国际科学数据委员会（CODATA）定期推荐。
#           本测试将模块中的常量与 CODATA 2018 推荐值进行精确比对。
# 预期行为：所有物理常数应以高精度匹配 CODATA 2018 标准值，确保后续模型计算
#           的基准正确性。
# =============================================================================
class TestPhysicalConstants:
    """Verify standard physical constants match CODATA 2018 values."""

    # -------------------------------------------------------------------------
    # 测试方法：test_speed_of_light
    # 测试目的：验证真空光速 C 是否为 299,792,458 m/s（精确定义值）。
    # 测试原理：光速是国际单位制（SI）中米的定义基准，自 1983 年起被定义为
    #           299,792,458 m/s 的精确值，无测量不确定度。
    # 预期行为：C == 299792458.0（精确相等）。
    # -------------------------------------------------------------------------
    def test_speed_of_light(self):
        assert C == pytest.approx(299792458.0)

    # -------------------------------------------------------------------------
    # 测试方法：test_boltzmann_constant
    # 测试目的：验证玻尔兹曼常数 K_B 是否为 1.380649 × 10⁻²³ J/K。
    # 测试原理：玻尔兹曼常数将热力学温度与微观粒子动能联系起来，是 SI 单位制
    #           中温度单位开尔文（K）的定义基准。在 FSO 系统中，它用于计算
    #           接收端的热噪声功率谱密度。
    # 预期行为：K_B == 1.380649e-23（精确值）。
    # -------------------------------------------------------------------------
    def test_boltzmann_constant(self):
        assert K_B == pytest.approx(1.380649e-23)

    # -------------------------------------------------------------------------
    # 测试方法：test_elementary_charge
    # 测试目的：验证元电荷 Q_E 是否为 1.602176634 × 10⁻¹⁹ C。
    # 测试原理：元电荷是单个质子的电荷量，也是 SI 单位制中电流单位安培（A）
    #           的定义基准。在 FSO 接收机模型中，它用于计算 PIN 光电二极管和
    #           APD 雪崩光电二极管的散粒噪声电流。
    # 预期行为：Q_E == 1.602176634e-19（精确值）。
    # -------------------------------------------------------------------------
    def test_elementary_charge(self):
        assert Q_E == pytest.approx(1.602176634e-19)

    # -------------------------------------------------------------------------
    # 测试方法：test_planck_constant
    # 测试目的：验证普朗克常数 H 是否为 6.62607015 × 10⁻³⁴ J·Hz⁻¹。
    # 测试原理：普朗克常数是量子力学的基本常数，描述光子能量与频率之间的比例
    #           关系（E = h·f），也是 SI 单位制中千克（kg）的定义基准。
    #           在 FSO 系统中，它用于计算光子能量和量子效率相关的参数。
    # 预期行为：H == 6.62607015e-34（精确值）。
    # -------------------------------------------------------------------------
    def test_planck_constant(self):
        assert H == pytest.approx(6.62607015e-34)

    # -------------------------------------------------------------------------
    # 测试方法：test_pi
    # 测试目的：验证圆周率 PI 是否与 NumPy 内置的 π 值一致。
    # 测试原理：圆周率 π 是圆周长与直径之比，在 FSO 模型中广泛用于波数计算
    #           （k = 2π/λ）、高斯光束传播、天线孔径面积等几何与波动光学公式中。
    # 预期行为：PI == np.pi（与 NumPy 标准值一致）。
    # -------------------------------------------------------------------------
    def test_pi(self):
        assert PI == pytest.approx(np.pi)

    # -------------------------------------------------------------------------
    # 测试方法：test_reference_wavelengths_not_none
    # 测试目的：验证 FSO 常用的三个激光波长常量（850 nm、1064 nm、1550 nm）
    #           以及参考波长（550 nm）的值是否正确。
    # 测试原理：850 nm（VCSEL 激光器，短距室内 FSO）、1064 nm（Nd:YAG 激光器，
    #           中距自由空间链路）、1550 nm（掺铒光纤放大器兼容，人眼安全，
    #           长距 FSO 常用）是 FSO 系统的三个标准波长窗口。550 nm 为可见光
    #           参考波长（对应人眼最敏感的绿光区域），用于大气能见度计算。
    # 预期行为：各波长常量应精确对应其纳米值换算为米（×10⁻⁹）的结果。
    # -------------------------------------------------------------------------
    def test_reference_wavelengths_not_none(self):
        assert LAMBDA_850 == 850e-9
        assert LAMBDA_1064 == 1064e-9
        assert LAMBDA_1550 == 1550e-9
        assert LAMBDA_REF_NM == 550


# =============================================================================
# 测试类：TestWavelengthConversions
# 测试目的：验证波长-波数转换和波长-频率转换函数的正确性。
# 测试原理：波数 k = 2π/λ 表示单位长度内波的相位变化量（角波数），是波动
#           光学中描述光波空间振荡频率的物理量。频率 f = c/λ 表示单位时间内
#           光波的振动次数。两者通过色散关系 ω = c·k 联系（其中 ω = 2πf）。
#           对于自由空间光通信，波数用于计算大气湍流中的空间相干长度等参数，
#           频率用于计算光子能量和量子效率。
# 预期行为：转换函数应在不同波长输入下精确返回对应的波数/频率值，且波数与
#           频率之间满足 k = 2πf/c 的关系。
# =============================================================================
class TestWavelengthConversions:
    """Tests for wavelength-to-wavenumber and wavelength-to-frequency."""

    # -------------------------------------------------------------------------
    # 测试方法：test_wavelength_to_wavenumber（参数化）
    # 测试目的：验证 wavelength_to_wavenumber 函数在多个典型波长下能否正确
    #           将波长转换为角波数。
    # 测试原理：角波数 k 的定义为 k = 2π/λ，单位为 rad/m。测试覆盖 850 nm、
    #           1064 nm、1550 nm 三个 FSO 标准波长，以及 1 μm 和 500 nm
    #           两个边界波长。
    # 预期行为：对每组输入，返回值与 2π/λ 的理论值在相对误差 1e-10 内一致。
    # -------------------------------------------------------------------------
    @pytest.mark.parametrize("wavelength_m, expected_k", [
        (850e-9, 2 * np.pi / 850e-9),
        (1064e-9, 2 * np.pi / 1064e-9),
        (1550e-9, 2 * np.pi / 1550e-9),
        (1e-6, 2 * np.pi / 1e-6),
        (500e-9, 2 * np.pi / 500e-9),
    ])
    def test_wavelength_to_wavenumber(self, wavelength_m, expected_k):
        result = wavelength_to_wavenumber(wavelength_m)
        assert result == pytest.approx(expected_k, rel=1e-10)

    # -------------------------------------------------------------------------
    # 测试方法：test_wavelength_to_wavenumber_identity
    # 测试目的：通过 1550 nm 单点验证波数转换的恒等关系，确保函数对特定
    #           常用波长的计算结果稳定可靠。
    # 测试原理：取 FSO 中最常用的 1550 nm 波长进行直接计算验证，确认
    #           wavelength_to_wavenumber(1550e-9) == 2π/1550e-9。
    # 预期行为：单点返回值与理论值一致。
    # -------------------------------------------------------------------------
    def test_wavelength_to_wavenumber_identity(self):
        k = 2 * np.pi / 1550e-9
        assert wavelength_to_wavenumber(1550e-9) == pytest.approx(k)

    # -------------------------------------------------------------------------
    # 测试方法：test_wavelength_to_frequency（参数化）
    # 测试目的：验证 wavelength_to_frequency 函数在多个波长下能否正确将
    #           波长转换为光波频率。
    # 测试原理：光波频率 f = c/λ，其中 c 为真空光速。测试覆盖 850 nm、
    #           1064 nm、1550 nm 和 1 μm 四个波长点。频率是计算光子能量
    #           （E = hf）和接收机量子效率的基础。
    # 预期行为：对每组输入，返回值与 c/λ 的理论值在相对误差 1e-10 内一致。
    # -------------------------------------------------------------------------
    @pytest.mark.parametrize("wavelength_m, expected_f", [
        (850e-9, C / 850e-9),
        (1064e-9, C / 1064e-9),
        (1550e-9, C / 1550e-9),
        (1e-6, C / 1e-6),
    ])
    def test_wavelength_to_frequency(self, wavelength_m, expected_f):
        result = wavelength_to_frequency(wavelength_m)
        assert result == pytest.approx(expected_f, rel=1e-10)

    # -------------------------------------------------------------------------
    # 测试方法：test_wavenumber_frequency_relation
    # 测试目的：验证角波数 k 和频率 f 之间是否满足电磁波的色散关系。
    # 测试原理：对于在自由空间传播的电磁波，角频率 ω = 2πf 与角波数 k
    #           之间满足 ω = c·k，即 2πf = c·k。等价变形为 k = 2πf/c。
    #           此关系是麦克斯韦方程组在真空中的直接推论。
    # 预期行为：对 850 nm 和 1550 nm 两个典型波长，k 与 2πf/c 的差值在
    #           相对误差 1e-10 内一致。
    # -------------------------------------------------------------------------
    def test_wavenumber_frequency_relation(self):
        for wl in (850e-9, 1550e-9):
            k = wavelength_to_wavenumber(wl)
            f = wavelength_to_frequency(wl)
            assert k == pytest.approx(2 * np.pi * f / C, rel=1e-10)


# =============================================================================
# 测试类：TestDbmWattRoundtrip
# 测试目的：验证 dBm 与瓦特（Watt）之间的双向转换函数的正确性和可逆性。
# 测试原理：dBm 是相对于 1 mW 的对数功率单位，定义为 P_dBm = 10·log₁₀(P/1mW)。
#           反向变换为 P(W) = 1mW × 10^(P_dBm/10)。双向转换必须满足
#           往返一致性：x → f(x) → f⁻¹(f(x)) = x。
# 预期行为：任意 dBm 值经 dbm_to_watt 转换后再经 watt_to_dbm 转换应回到
#           原值；反之亦然。特定已知点的转换值应等于理论预期值。
# =============================================================================
class TestDbmWattRoundtrip:
    """Roundtrip tests for dbm_to_watt and watt_to_dbm."""

    # -------------------------------------------------------------------------
    # 测试方法：test_dbm_watt_roundtrip（参数化）
    # 测试目的：验证从 dBm → W → dBm 的往返可逆性。
    # 测试原理：测试覆盖正 dBm 值（0, 10, 14, 20, 30）和负 dBm 值
    #           （-10, -20, -30, -40）。14 dBm（≈25 mW）是 FSO 系统中
    #           常见的激光器发射功率典型值。
    # 预期行为：对每个测试点，往返转换后的 dBm 值与原始值的相对误差 ≤ 1e-10。
    # -------------------------------------------------------------------------
    @pytest.mark.parametrize("dbm", [0, 10, 14, 20, 30, -10, -20, -30, -40])
    def test_dbm_watt_roundtrip(self, dbm):
        watt = dbm_to_watt(dbm)
        dbm_again = watt_to_dbm(watt)
        assert dbm_again == pytest.approx(dbm, rel=1e-10)

    # -------------------------------------------------------------------------
    # 测试方法：test_watt_dbm_roundtrip（参数化）
    # 测试目的：验证从 W → dBm → W 的往返可逆性。
    # 测试原理：测试覆盖从 1 mW 到 100 W 的功率范围，涵盖 FSO 系统发射端
    #           的典型功率区间（毫瓦级到瓦级）。
    # 预期行为：对每个测试点，往返转换后的瓦特值与原始值的相对误差 ≤ 1e-10。
    # -------------------------------------------------------------------------
    @pytest.mark.parametrize("watt", [1e-3, 1e-2, 0.1, 1.0, 10.0, 100.0])
    def test_watt_dbm_roundtrip(self, watt):
        dbm = watt_to_dbm(watt)
        watt_again = dbm_to_watt(dbm)
        assert watt_again == pytest.approx(watt, rel=1e-10)

    # -------------------------------------------------------------------------
    # 测试方法：test_dbm_to_watt_known_values
    # 测试目的：验证 dBm → W 转换在三个已知点上的正确性。
    # 测试原理：这些是 dBm 定义的基准点：0 dBm ≡ 1 mW = 0.001 W，
    #           10 dBm ≡ 10 mW = 0.01 W，30 dBm ≡ 1 W。每个 10 dB 的
    #           变化对应功率的 10 倍变化。
    # 预期行为：dbm_to_watt(0) == 0.001，dbm_to_watt(10) == 0.01，
    #           dbm_to_watt(30) == 1.0。
    # -------------------------------------------------------------------------
    def test_dbm_to_watt_known_values(self):
        assert dbm_to_watt(0) == pytest.approx(0.001)
        assert dbm_to_watt(10) == pytest.approx(0.01)
        assert dbm_to_watt(30) == pytest.approx(1.0)

    # -------------------------------------------------------------------------
    # 测试方法：test_watt_to_dbm_known_values
    # 测试目的：验证 W → dBm 转换在三个已知点上的正确性。
    # 测试原理：与 test_dbm_to_watt_known_values 互为逆变换的基准点验证。
    #           1 mW = 0 dBm，10 mW = 10 dBm，1 W = 30 dBm。
    # 预期行为：watt_to_dbm(0.001) == 0.0，watt_to_dbm(0.01) == 10.0，
    #           watt_to_dbm(1.0) == 30.0。
    # -------------------------------------------------------------------------
    def test_watt_to_dbm_known_values(self):
        assert watt_to_dbm(0.001) == pytest.approx(0.0)
        assert watt_to_dbm(0.01) == pytest.approx(10.0)
        assert watt_to_dbm(1.0) == pytest.approx(30.0)


# =============================================================================
# 测试类：TestDbLinearRoundtrip
# 测试目的：验证 dB（对数）与线性比之间的双向转换函数的正确性和可逆性。
# 测试原理：dB 定义为 G_dB = 10·log₁₀(G_linear)（功率比），或更一般地
#           用于描述信号增益或衰减的对数比。线性比与 dB 的转换公式为：
#           G_linear = 10^(G_dB/10)，G_dB = 10·log₁₀(G_linear)。
#           在 FSO 系统中，dB 广泛用于描述大气衰减、几何损耗、链路裕量等。
#           特殊边界情况：负线性比（如 -1）在物理上无意义，应返回 NaN；
#           零线性比对应负无穷 dB（完全衰减）。
# 预期行为：正常值应满足往返一致性；边界情况应返回非有限值（NaN 或 -inf）。
# =============================================================================
class TestDbLinearRoundtrip:
    """Roundtrip tests for db_to_linear and linear_to_db."""

    # -------------------------------------------------------------------------
    # 测试方法：test_db_linear_roundtrip（参数化）
    # 测试目的：验证从 dB → 线性比 → dB 的往返可逆性。
    # 测试原理：测试覆盖从 -30 dB 到 +30 dB 的典型范围，包括 0 dB（增益为 1）
    #           和 ±3 dB（约对应 2 倍或 1/2 倍功率变化）。在 FSO 链路预算中，
    #           大气衰减通常在几 dB 到数十 dB 之间。
    # 预期行为：对每个测试点，往返转换后的 dB 值与原始值的相对误差 ≤ 1e-10。
    # -------------------------------------------------------------------------
    @pytest.mark.parametrize("db", [-30, -20, -10, -3, 0, 3, 10, 20, 30])
    def test_db_linear_roundtrip(self, db):
        linear = db_to_linear(db)
        db_again = linear_to_db(linear)
        assert db_again == pytest.approx(db, rel=1e-10)

    # -------------------------------------------------------------------------
    # 测试方法：test_linear_db_roundtrip（参数化）
    # 测试目的：验证从线性比 → dB → 线性比的往返可逆性。
    # 测试原理：测试覆盖从 0.001（-30 dB）到 1000（+30 dB）的宽动态范围，
    #           涵盖 FSO 系统中可能遇到的信号衰减和放大范围。
    # 预期行为：对每个测试点，往返转换后的线性值与原始值的相对误差 ≤ 1e-10。
    # -------------------------------------------------------------------------
    @pytest.mark.parametrize("linear", [0.001, 0.01, 0.1, 0.5, 1.0, 2.0, 10.0, 100.0, 1000.0])
    def test_linear_db_roundtrip(self, linear):
        db = linear_to_db(linear)
        linear_again = db_to_linear(db)
        assert linear_again == pytest.approx(linear, rel=1e-10)

    # -------------------------------------------------------------------------
    # 测试方法：test_db_to_linear_zero_db
    # 测试目的：验证 0 dB 对应线性比 1 的基准关系。
    # 测试原理：由定义，0 dB 表示功率比为 1（即没有增益也没有衰减）。
    #           这是 dB 标度的自然原点：10^(0/10) = 10^0 = 1。
    # 预期行为：db_to_linear(0) == 1.0。
    # -------------------------------------------------------------------------
    def test_db_to_linear_zero_db(self):
        assert db_to_linear(0) == pytest.approx(1.0)

    # -------------------------------------------------------------------------
    # 测试方法：test_linear_to_db_one
    # 测试目的：验证线性比 1 对应 0 dB 的逆基准关系。
    # 测试原理：与 test_db_to_linear_zero_db 对称，验证逆映射的正确性。
    #           10·log₁₀(1) = 0。
    # 预期行为：linear_to_db(1.0) == 0.0。
    # -------------------------------------------------------------------------
    def test_linear_to_db_one(self):
        assert linear_to_db(1.0) == pytest.approx(0.0)

    # -------------------------------------------------------------------------
    # 测试方法：test_linear_to_db_negative_returns_nan
    # 测试目的：验证对负数输入进行 dB 转换时返回 NaN。
    # 测试原理：dB 定义基于功率比的对数，而负数的对数在实数域无定义。
    #           线性功率比不可能为负值（功率是标量非负量），因此对负数
    #           输入应返回 NaN 以标志此物理上无意义的操作。
    # 预期行为：linear_to_db(-1.0) 的结果不是有限数（NaN 或 ±inf）。
    # -------------------------------------------------------------------------
    def test_linear_to_db_negative_returns_nan(self):
        result = linear_to_db(-1.0)
        assert not np.isfinite(result)

    # -------------------------------------------------------------------------
    # 测试方法：test_linear_to_db_zero_returns_neg_inf
    # 测试目的：验证对零输入进行 dB 转换时返回负无穷。
    # 测试原理：10·log₁₀(0) = -∞，表示信号完全衰减至零功率。在 FSO 链路
    #           预算中，这对应于信道完全阻塞的极端情况（如发射机关闭或
    #           光束完全被遮挡）。
    # 预期行为：linear_to_db(0.0) 的结果不是有限数，且为负值（-inf）。
    # -------------------------------------------------------------------------
    def test_linear_to_db_zero_returns_neg_inf(self):
        result = linear_to_db(0.0)
        assert not np.isfinite(result)
        assert result < 0


# =============================================================================
# 测试类：TestVectorizedConstants
# 测试目的：验证所有转换函数是否支持 NumPy 数组的向量化输入。
# 测试原理：在 FSO 仿真中，常常需要一次性处理大量波长、功率值（如频谱扫描、
#           蒙特卡洛模拟）。如果函数仅支持标量输入，将导致性能瓶颈。向量化
#           实现可以利用 NumPy 的底层 C 循环批量计算，大幅提升效率。
# 预期行为：所有转换函数应接受 NumPy 数组作为输入，返回与输入形状相同的数组，
#           且元素值与对应的标量计算结果一致。
# =============================================================================
class TestVectorizedConstants:
    """Vectorized input tests for conversion functions."""

    # -------------------------------------------------------------------------
    # 测试方法：test_wavelength_to_wavenumber_vectorized
    # 测试目的：验证波数转换函数对数组输入的支持。
    # 测试原理：使用 np.array([850e-9, 1064e-9, 1550e-9]) 作为输入，
    #           预期输出为 2π/λ 的数组形式。同时验证返回数组的形状为 (3,)。
    # 预期行为：返回值与理论值的相对误差 ≤ 1e-10，且 shape == (3,)。
    # -------------------------------------------------------------------------
    def test_wavelength_to_wavenumber_vectorized(self):
        wavelengths = np.array([850e-9, 1064e-9, 1550e-9])
        result = wavelength_to_wavenumber(wavelengths)
        expected = 2 * PI / wavelengths
        assert result == pytest.approx(expected, rel=1e-10)
        assert result.shape == (3,)

    # -------------------------------------------------------------------------
    # 测试方法：test_dbm_to_watt_vectorized
    # 测试目的：验证 dBm → W 转换函数对数组输入的支持。
    # 测试原理：使用 np.array([0, 10, 20, 30]) dBm 作为输入，预期输出为
    #           [0.001, 0.01, 0.1, 1.0] W。同时验证返回数组形状为 (4,)。
    # 预期行为：返回值与理论值的相对误差 ≤ 1e-10，且 shape == (4,)。
    # -------------------------------------------------------------------------
    def test_dbm_to_watt_vectorized(self):
        dbm_vals = np.array([0, 10, 20, 30])
        result = dbm_to_watt(dbm_vals)
        expected = np.array([0.001, 0.01, 0.1, 1.0])
        assert result == pytest.approx(expected, rel=1e-10)
        assert result.shape == (4,)

    # -------------------------------------------------------------------------
    # 测试方法：test_watt_to_dbm_vectorized
    # 测试目的：验证 W → dBm 转换函数对数组输入的支持。
    # 测试原理：使用 np.array([0.001, 0.01, 0.1, 1.0]) W 作为输入，
    #           预期输出为 [0, 10, 20, 30] dBm。
    # 预期行为：返回值与理论值的相对误差 ≤ 1e-10。
    # -------------------------------------------------------------------------
    def test_watt_to_dbm_vectorized(self):
        watt_vals = np.array([0.001, 0.01, 0.1, 1.0])
        result = watt_to_dbm(watt_vals)
        expected = np.array([0, 10, 20, 30])
        assert result == pytest.approx(expected, rel=1e-10)

    # -------------------------------------------------------------------------
    # 测试方法：test_db_to_linear_vectorized
    # 测试目的：验证 dB → 线性比转换函数对数组输入的支持。
    # 测试原理：使用 np.array([-10, 0, 10, 20]) dB 作为输入，预期输出为
    #           [0.1, 1.0, 10.0, 100.0] 的线性比数组。
    # 预期行为：返回值与理论值的相对误差 ≤ 1e-10。
    # -------------------------------------------------------------------------
    def test_db_to_linear_vectorized(self):
        db_vals = np.array([-10, 0, 10, 20])
        result = db_to_linear(db_vals)
        expected = np.array([0.1, 1.0, 10.0, 100.0])
        assert result == pytest.approx(expected, rel=1e-10)

    # -------------------------------------------------------------------------
    # 测试方法：test_linear_to_db_vectorized
    # 测试目的：验证线性比 → dB 转换函数对数组输入的支持。
    # 测试原理：使用 np.array([0.1, 1.0, 10.0, 100.0]) 作为输入，预期输出为
    #           [-10, 0, 10, 20] dB。
    # 预期行为：返回值与理论值的相对误差 ≤ 1e-10。
    # -------------------------------------------------------------------------
    def test_linear_to_db_vectorized(self):
        lin_vals = np.array([0.1, 1.0, 10.0, 100.0])
        result = linear_to_db(lin_vals)
        expected = np.array([-10, 0, 10, 20])
        assert result == pytest.approx(expected, rel=1e-10)


# =============================================================================
# 测试类：TestConversionConsistency
# 测试目的：跨转换函数的一致性检查，验证不同单位体系之间的转换结果是否
#           相互自洽。
# 测试原理：FSO 链路预算分析中涉及多种物理量的单位转换（功率、波长、频率、
#           对数标度等）。这些转换函数虽然针对不同物理量，但在数学上存在
#           内在的一致性约束。例如：wavelength_to_wavenumber 和
#           wavelength_to_frequency 的输出必须满足波动方程的基本关系。
# 预期行为：所有跨函数一致性检查应通过，确保不同转换路径得到的结果自洽。
# =============================================================================
class TestConversionConsistency:
    """Cross-conversion consistency checks."""

    # -------------------------------------------------------------------------
    # 测试方法：test_dbm_and_db_consistency
    # 测试目的：验证 dBm 和 dB 单位体系之间的转换一致性。
    # 测试原理：选取 25 mW（0.025 W）作为典型 FSO 发射功率，先从 W → dBm
    #           再反向从 dBm → W，验证往返一致性。dBm 是相对于 1 mW 的
    #           绝对功率单位，与 dB（相对比值单位）不同，但其数学变换可逆性
    #           同样必须保持。
    # 预期行为：往返后的功率值与原始 25 mW 一致。
    # -------------------------------------------------------------------------
    def test_dbm_and_db_consistency(self):
        P_w = 0.025  # 25 mW
        dbm = watt_to_dbm(P_w)
        P_w_from_dbm = dbm_to_watt(dbm)
        assert P_w_from_dbm == pytest.approx(P_w)

    # -------------------------------------------------------------------------
    # 测试方法：test_cascade_wavelength_conversions
    # 测试目的：验证波长 → 波数和波长 → 频率两条转换路径在物理上是否满足
    #           电磁波的基本关系：c·k = 2πf。
    # 测试原理：由波动光学，真空光速 c、角波数 k、频率 f 之间的关系为
    #           ω = c·k（ω = 2πf）。整理得 c·k = 2πf。本测试对 1550 nm
    #           波长分别计算 k 和 f，然后验证该关系是否成立。这比单独验证
    #           每个转换函数更进一步，检验了函数间的物理一致性。
    # 预期行为：c·k 与 2πf 的相对误差 ≤ 1e-10。
    # -------------------------------------------------------------------------
    def test_cascade_wavelength_conversions(self):
        wl = 1550e-9
        k = wavelength_to_wavenumber(wl)
        f = wavelength_to_frequency(wl)
        assert C * k == pytest.approx(2 * np.pi * f, rel=1e-10)
