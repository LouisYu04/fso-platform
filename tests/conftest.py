"""
FSO 平台测试共享夹具（fixtures）模块。

该模块为整个测试套件提供可复用的 fixture，包括：
  - textbook_params：教材 Table 4.6 参考系统参数（发射/接收孔径、功率、灵敏度等）
  - reference_wavelengths：FSO 典型工作波长（850 nm / 1064 nm / 1550 nm）
  - visibility_test_cases：Kim 大气衰减模型能见度测试用例
  - turbulence_regimes：Rytov 方差湍流强度分区边界值
  - rng：可复现随机数生成器

这些 fixture 自动被 test_models.py 等测试文件通过参数注入使用，
无需在每个测试文件中重复定义。
"""

import pytest
import numpy as np


# ── Textbook Table 4.6 reference parameters ──────────────────────────────────
#  教材表 4.6 参考系统参数：
#    接收孔径 d_R = 8 cm，发射孔径 d_T = 2.5 cm
#    光束发散角 θ = 2 mrad，调制方式 OOK @ 155 Mb/s
#    发射功率 P_T = 14 dBm，接收灵敏度 = -30 dBm
#    工作波长 λ = 850 nm


@pytest.fixture
def textbook_params():
    """
    教材 Table 4.6 参考系统参数字典。

    该 fixture 返回一组典型的近地无线光通信（FSO）链路参数，
    可用于几何损耗、链路预算、信噪比等模型的单元测试。

    返回的字典包含以下物理量：

    发射/接收光学参数：
      - D_T_m（发射孔径直径）       : 0.025 m  (2.5 cm)
      - D_R_m（接收孔径直径）       : 0.08 m   (8 cm)
      - theta_div_rad（光束全角发散角）: 2e-3 rad (2 mrad)

    功率与灵敏度：
      - P_T_dbm（发射光功率）       : 14 dBm  (约 25 mW)
      - sensitivity_dbm（接收灵敏度）: -30 dBm (约 1 μW)

    波长：
      - wavelength_nm（以纳米为单位）: 850 nm
      - wavelength_m（以米为单位）   : 850e-9 m
        （双单位并存，避免测试中重复换算）

    通信参数：
      - data_rate_bps（数据速率）    : 155e6 bps (155 Mbps)

    探测器与电路参数（用于信噪比 / 噪声计算）：
      - R_p（光电探测器响应度）      : 0.5 A/W
           每入射 1 瓦特光功率产生 0.5 安培光电流
      - T_K（系统等效噪声温度）      : 300 K (常温)
      - R_L_ohm（负载电阻）          : 50 Ω
    """
    return {
        "D_T_m": 0.025,          # 发射孔径直径 [m] —— 2.5 cm
        "D_R_m": 0.08,            # 接收孔径直径 [m] —— 8 cm
        "theta_div_rad": 2e-3,    # 光束全角发散角 [rad] —— 2 mrad
        "P_T_dbm": 14,            # 发射光功率 [dBm] —— 14 dBm
        "sensitivity_dbm": -30,   # 接收灵敏度 [dBm] —— -30 dBm
        "wavelength_nm": 850,     # 工作波长 [nm] —— 850 nm
        "wavelength_m": 850e-9,
        "data_rate_bps": 155e6,   # 数据速率 [bps] —— 155 Mbps
        "R_p": 0.5,               # 探测器响应度 [A/W]
        "T_K": 300,               # 系统等效噪声温度 [K]
        "R_L_ohm": 50,            # 负载电阻 [Ω]
    }


@pytest.fixture
def reference_wavelengths():
    """
    FSO 系统常用的三个典型工作波长（以米为单位）。

    包含：
      - 850 nm  ：短波长窗口，适用于低成本 Si 探测器
      - 1064 nm ：Nd:YAG 激光器波长，适用于近地链路
      - 1550 nm ：长波长窗口，人眼安全阈值高，适用于长距离链路

    这些波长在衰减系数计算、湍流强度评估等场景中作为测试输入。
    """
    return {
        "850nm": 850e-9,
        "1064nm": 1064e-9,
        "1550nm": 1550e-9,
    }


@pytest.fixture
def visibility_test_cases():
    """
    Kim 大气衰减模型的能见度测试用例集。

    每个用例为三元组 (能见度 V[km], 期望 Kim p 值, 场景标签)，
    覆盖从极浓雾到极晴的完整气象范围。

    Kim 模型中的 p 值（粒径分布因子）是能见度的分段函数：
      - p = 0.0  ：V < 0.5 km（极浓雾，散射粒子以雾滴为主）
      - p = V - 0.5 ：0.5 ≤ V < 1 km（过渡区）
      - p = 0.16 V + 0.34 ：1 ≤ V < 6 km（浓雾到中等雾霾）
      - p = 1.3  ：6 ≤ V < 50 km（薄雾到晴天，Mie 散射为主）
      - p = 1.6  ：V ≥ 50 km（极晴朗，接近 Rayleigh 散射）

    测试用例含义：
      (0.2,  0.0,  "极浓雾")      —— V=0.2 km，p=0，严重衰减
      (0.5,  0.0,  "浓雾边界")     —— V=0.5 km，p=0，能见度极低
      (0.8,  0.3,  "浓雾")         —— V=0.8 km，p=0.3，过渡区
      (2.0,  0.66, "中等雾霾")     —— V=2 km，p=0.66，中等衰减
      (6.0,  1.3,  "薄雾边界")     —— V=6 km，p=1.3，进入恒值区
      (10.0, 1.3,  "薄雾")         —— V=10 km，p=1.3，典型薄雾日
      (23.0, 1.3,  "晴天")         —— V=23 km，p=1.3，良好天气
      (50.0, 1.3,  "极晴边界")     —— V=50 km，p=1.3，恒值区上界
      (60.0, 1.6,  "极晴")         —— V=60 km，p=1.6，极晴朗
    """
    return [
        # (V_km, expected_p, label)
        (0.2, 0.0, "极浓雾"),       # 能见度 0.2 km，p=0，最恶劣场景
        (0.5, 0.0, "浓雾边界"),     # 能见度 0.5 km，p=0，p=0 区间的上界
        (0.8, 0.3, "浓雾"),         # 能见度 0.8 km，p=0.3，过渡区中点
        (2.0, 0.66, "中等雾霾"),    # 能见度 2 km，p=0.66，中等雾霾典型值
        (6.0, 1.3, "薄雾边界"),     # 能见度 6 km，p=1.3，进入 p=1.3 恒值区
        (10.0, 1.3, "薄雾"),        # 能见度 10 km，p=1.3，典型薄雾天气
        (23.0, 1.3, "晴天"),        # 能见度 23 km，p=1.3，晴朗天气
        (50.0, 1.3, "极晴边界"),    # 能见度 50 km，p=1.3，p=1.3 恒值区上界
        (60.0, 1.6, "极晴"),        # 能见度 60 km，p=1.6，极晴朗高能见度
    ]


@pytest.fixture
def turbulence_regimes():
    """
    大气湍流强度分区的 Rytov 方差参考值。

    Rytov 方差 σ²_R 是描述湍流强度的无量纲参数：
      - σ²_R < 0.3     ：弱湍流（weak）
            闪烁指数较小，可用对数正态分布近似
      - 0.3 ≤ σ²_R < 5 ：中等湍流（moderate）
            闪烁指数增大，Gamma-Gamma 分布适用
      - 5 ≤ σ²_R < 25  ：强湍流（strong）
            闪烁趋于饱和，Gamma-Gamma 仍可描述
      - σ²_R ≥ 25      ：饱和湍流（saturation）
            闪烁指数趋近于 1，负指数分布适用

    本 fixture 提供的边界值：
      weak            = 0.1     —— 弱湍流代表值
      weak_boundary   = 0.99    —— 弱→中 过渡边界（≈1）
      moderate        = 5.0     —— 中等湍流代表值
      moderate_boundary = 25.0  —— 中→强/饱和 过渡边界
      strong          = 50.0    —— 饱和湍流代表值
    """
    return {
        "weak": 0.1,              # 弱湍流：σ²_R = 0.1，对数正态近似有效
        "weak_boundary": 0.99,    # 弱→中湍流边界：σ²_R ≈ 1
        "moderate": 5.0,          # 中等湍流：σ²_R = 5.0
        "moderate_boundary": 25.0,# 中→强/饱和湍流边界：σ²_R = 25
        "strong": 50.0,           # 饱和湍流：σ²_R = 50.0，闪烁趋于饱和
    }


@pytest.fixture
def rng():
    """
    可复现的随机数生成器。

    使用固定种子（42）初始化 NumPy 默认生成器（PCG64 算法），
    确保每次运行测试时产生的随机序列完全相同。

    用途：
      - 蒙特卡洛仿真测试
      - 概率分布采样验证
      - 噪声生成测试
    固定种子避免了"flaky test"（因随机性导致的不稳定测试）。
    """
    return np.random.default_rng(42)
