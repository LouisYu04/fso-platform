"""
大气衰减模型
适用范围: 近地水平路径 FSO（Free Space Optics，自由空间光通信）链路

物理背景:
    光波在大气中传播时，受气溶胶粒子（雾滴、雨滴、雪晶）和气体分子的散射与吸收，
    导致光功率沿传播方向指数衰减，即 Beer-Lambert 定律。
    衰减量取决于波长、能见度（气溶胶浓度代理量）、天气类型及传播距离。

单位约定:
    - Naperian 消光系数 σ: 单位 km⁻¹，基于自然对数底 e，用于 Beer-Lambert 透过率计算
    - dB 衰减量: 单位 dB 或 dB/km，基于常用对数底 10，用于链路预算加法运算
    - 换算关系: L_dB = 4.343 × σ(Naperian km⁻¹) × L(km)，其中 4.343 = 10/ln(10)

包含模型:
    1. Beer-Lambert 大气衰减定律 (式4.1)
       ——将消光系数和距离转换为透过率或 dB 衰减
    2. Kim 模型: 能见度 → 衰减系数 (式4.3, 4.5)
       ——适用于能见度 V > 0.5 km 的通用天气条件
    3. Naboulsi 平流雾/辐射雾模型 (开题报告式2.14, 2.15)
       ——针对浓雾（V < 0.5 km）精度优于 Kim 模型
    4. 雨天附加衰减经验模型 (Carbonneau 公式)
       ——基于幂律关系 α = a·R^b 拟合实测数据
    5. 雪天附加衰减经验模型
       ——区分干雪/湿雪，湿雪因含水率高衰减更严重

参考文献:
    - Kim I I et al., "Wireless optical transmission of fast Ethernet, FDDI, ATM,
      and ESCON protocol data using the TerraLink laser communication system",
      Optical Engineering, 1998.
    - Naboulsi M A et al., "Fog attenuation prediction for optical and infrared waves",
      Optical Engineering, 2004.
    - Carbonneau T H, Karafolas N, "Optical free space links in railway environments",
      Proc. SPIE, 1998.
"""

import numpy as np


def kim_p(visibility_km):
    """
    Kim 模型中的粒径分布系数 p
    根据能见度 V 确定大气气溶胶粒径分布特征 (教材式4.4)

    物理意义:
        p 是 Mie 散射理论中的粒径分布指数。
        p 值越大，表示大气粒子尺寸分布越窄、粒径越均匀（偏向大粒子），
        衰减对波长的依赖性越强（短波衰减远大于长波，即"蓝天散射"效应）；
        p 值越小（趋近于0），表示粒子粒径分布宽泛，散射近似波长无关（灰散射），
        多见于极浓雾/霾条件。

    分段规则与对应天气类型:
        V > 50 km     → p = 1.6   晴天，能见度极好，大粒子主导，波长依赖强
        6 < V ≤ 50 km → p = 1.3   薄雾/霾，能见度良好
        1 < V ≤ 6 km  → p = 0.16V + 0.34   中等雾霾，线性插值过渡区
        0.5 < V ≤ 1 km→ p = V - 0.5        浓雾，粒径分布趋向宽泛
        V ≤ 0.5 km    → p = 0.0   极浓雾，灰散射，衰减与波长无关

    实现说明:
        使用 np.where 向量化条件赋值，支持标量和数组输入，
        避免 Python 循环以提升批量计算性能。

    参数:
        visibility_km (float 或 np.ndarray): 大气能见度 (km)，支持向量化输入，必须 > 0
    返回:
        p (float 或 np.ndarray): 粒径分布系数，与输入形状一致
    异常:
        ValueError: visibility_km <= 0
    """
    V = np.asarray(visibility_km, dtype=float)
    if np.any(V <= 0):
        raise ValueError(f"visibility_km 必须 > 0，当前最小值: {float(np.min(V))}")

    # 初始化为全零数组，后续逐段用 np.where 覆盖对应区间的值
    p = np.zeros_like(V)

    # 按能见度分段赋值（从高到低覆盖，后面的条件优先级更高）
    p = np.where(V > 50,               1.6,             p)   # 晴天
    p = np.where((V > 6) & (V <= 50),  1.3,             p)   # 薄雾/霾
    p = np.where((V > 1) & (V <= 6),   0.16 * V + 0.34, p)   # 中等雾霾（线性插值）
    p = np.where((V > 0.5) & (V <= 1), V - 0.5,         p)   # 浓雾
    p = np.where(V <= 0.5,             0.0,              p)   # 极浓雾（灰散射）

    # 标量输入时返回 Python float，保持接口与非向量化调用兼容
    return float(p) if p.ndim == 0 else p


def attenuation_coefficient(visibility_km, wavelength_nm=1550):
    """
    大气消光系数（Kim 模型）
    σ(λ) = (3.91 / V) · (λ / 550)^(-p)   (教材式4.3)

    公式推导背景:
        常数 3.91 来源于 Koschmieder 定律：
            能见度 V 定义为对比度降至 2%（即 e^{-σV} = 0.02）时的距离，
            由此得 σ = -ln(0.02) / V ≈ 3.912 / V，取近似值 3.91。
        参考波长 550 nm 是人眼亮度响应峰值波长，也是气象能见度标定的基准波长。
        幂律项 (λ/550)^(-p) 描述消光系数随波长的变化关系：
            波长越长（如 1550 nm）相对 550 nm 衰减越小，这是 FSO 优先选用近红外波段的原因。

    适用范围与局限:
        - Kim 模型适用于能见度 V > 0.5 km 的一般天气条件
        - 浓雾（V < 0.5 km）时精度下降，推荐改用 Naboulsi 模型
        - 该模型主要针对 Mie 散射（气溶胶粒子），未单独区分分子吸收

    单位说明:
        返回值为 Naperian（自然对数底）消光系数，单位 km⁻¹。
        若需 dB/km 单位，须乘以换算因子 4.343 = 10/ln(10)，
        见函数 atmospheric_attenuation_db()。

    参数:
        visibility_km (float): 大气能见度 (km)，必须 > 0
        wavelength_nm (float): 工作波长 (nm)，默认 1550 nm（C 波段常用）
    返回:
        sigma (float): 消光系数，Naperian km⁻¹（自然对数底）

    注意: 返回值为 Naperian 单位 (km⁻¹), 不是 dB/km。
          转换关系: L_atm(dB) = 4.343 × sigma(Naperian km⁻¹) × L(km)
          其中 4.343 = 10 / ln(10)，见 atmospheric_attenuation_db()。
    """
    V = float(visibility_km)
    if V <= 0:
        raise ValueError(f"visibility_km 必须 > 0，当前值: {V}")
    p = kim_p(V)
    # σ = (3.91/V) × (λ/550)^(-p)
    # 其中 3.91 ≈ -ln(0.02)（Koschmieder 常数），550 nm 为参考波长
    sigma = (3.91 / V) * (wavelength_nm / 550.0) ** (-p)
    return sigma


def beer_lambert(sigma_naperian_per_km, distance_km):
    """
    Beer-Lambert 大气透过率 (教材式4.1)
    τ(λ, L) = exp(-σ · L)

    物理意义:
        Beer-Lambert 定律描述光在均匀吸收/散射介质中传播时的强度衰减规律：
        每经过单位路径长度，光强按比例 exp(-σ) 衰减，总透过率为 exp(-σL)。
        σ 为体消光系数，包含两个分量：
            σ = σ_scatter（散射损耗） + σ_absorb（吸收损耗）
        在 FSO 近红外波段，气溶胶 Mie 散射是主要贡献，分子吸收相对较小。

    适用前提:
        1. 均匀大气假设：σ 沿路径不随位置变化（水平近地路径近似成立）
        2. 单色光：σ 对特定波长成立（宽带光源需积分）
        3. 线性光学区：不考虑非线性效应（FSO 功率范围内成立）

    参数:
        sigma_naperian_per_km (float): 体消光系数 βa，Naperian km⁻¹（由 attenuation_coefficient() 返回）
        distance_km (float): 传播路径长度 (km)
    返回:
        tau (float): 大气透过率，范围 (0, 1]；tau=1 表示无衰减，tau→0 表示近乎全衰减
    """
    return np.exp(-sigma_naperian_per_km * distance_km)


def atmospheric_attenuation_db(sigma_naperian_per_km, distance_km):
    """
    大气衰减量（dB）
    L_atm(dB) = 4.343 × βa(Naperian km⁻¹) × L(km)   (教材式4.16)

    公式推导:
        透过率 τ = exp(-σL)
        转换为 dB:
            L_dB = -10 × log10(τ)
                 = -10 × log10(exp(-σL))
                 = -10 × (-σL) × log10(e)
                 = 10 × σL × log10(e)
                 = 10 × σL / ln(10)
                 = 4.343 × σ × L
        其中换算因子 4.343 = 10 / ln(10) ≈ 10 / 2.3026

    与 beer_lambert() 的等价关系:
        atmospheric_attenuation_db(σ, L) == -10 * log10(beer_lambert(σ, L))
        即 dB 衰减量与透过率互为等价表示，链路预算中常用 dB 进行加法运算。

    参数:
        sigma_naperian_per_km (float): 消光系数 βa，Naperian km⁻¹（由 attenuation_coefficient() 返回）
        distance_km (float): 传播路径长度 (km)
    返回:
        attenuation_db (float): 总大气衰减量 (dB)，正值表示衰减（功率损失）
    """
    # 换算因子 4.343 = 10 / ln(10)，将 Naperian 消光系数转换为 dB 单位
    return 4.343 * sigma_naperian_per_km * distance_km


def naboulsi_advection_fog(visibility_km, wavelength_nm=1550):
    """
    Naboulsi 平流雾衰减系数 (文献式4.5a)
    α_Advection = (0.11478·λ + 3.8367) / V   [dB/km]

    严格按《近地无线光通信》式(4.5a)后的单位说明实现:
    λ 为波长（nm），V 为能见度（m）。函数接口仍接收 km，
    内部只在代入公式前转换为 m。

    平流雾的物理机制:
        平流雾由暖湿气流流经较冷下垫面（海面、湖面、河谷）时，
        水汽冷却凝结形成。其特点是：
        - 雾滴粒径较大（典型直径 10~20 μm），远大于近红外波长
        - 属于几何光学散射区（Mie 散射极限），散射截面近似等于几何截面
        - 多见于沿海城市、海雾区（如旧金山、上海沿海）
        - 持续时间长，能见度可低至 0.05 km 以下

    与 Kim 模型的对比:
        - Kim 模型: 适用范围广（V > 0.5 km），但在极浓雾（V < 0.5 km）精度下降
        - Naboulsi 模型: 专门针对浓雾条件拟合，在 V < 0.5 km 时精度更高
        经验系数 (0.11478, 3.8367) 由实测平流雾数据统计回归得到。

    单位说明:
        本函数直接返回 dB/km，与 Kim 模型的 Naperian km⁻¹ 不同。
        调用方使用时乘以距离 (km) 即得 dB，无需再乘以 4.343。

    参数:
        visibility_km (float): 大气能见度 (km)，推荐用于 0.05~1 km 的浓雾场景，必须 > 0
        wavelength_nm (float): 工作波长 (nm)，默认 1550 nm
    返回:
        alpha_db_per_km (float): 平流雾衰减系数 (dB/km)
    异常:
        ValueError: visibility_km <= 0
    """
    V = float(visibility_km)
    if V <= 0:
        raise ValueError(f"visibility_km 必须 > 0，当前值: {V}")
    V_m = V * 1000.0
    alpha = (0.11478 * wavelength_nm + 3.8367) / V_m
    return alpha


def naboulsi_radiation_fog(visibility_km, wavelength_nm=1550):
    """
    Naboulsi 辐射雾衰减系数 (文献式4.5b)
    α_Radiation = (0.18126·λ² + 0.13709·λ + 3.7502) / V   [dB/km]

    严格按《近地无线光通信》式(4.5b)后的单位说明实现:
    λ 为波长（nm），V 为能见度（m）。函数接口仍接收 km，
    内部只在代入公式前转换为 m。

    辐射雾的物理机制:
        辐射雾由夜间地面长波辐射冷却形成，当地面温度降至露点以下时，
        近地层水汽凝结产生。其特点是：
        - 雾滴粒径较小（典型直径 1~10 μm），尺寸与近红外波长接近
        - 散射特征介于 Mie 散射和瑞利散射之间，对波长有一定依赖性
        - 多见于内陆盆地、河谷地区的秋冬清晨（如成都盆地、伦敦"雾都"）
        - 通常在日出后随温度升高而消散

    与平流雾的衰减差异:
        辐射雾的经验公式为二次多项式（λ² 项），反映其粒径较小、
        散射对波长更敏感的特性。在相同能见度下，两种雾对 FSO 的衰减量相近，
        但辐射雾的波长依赖性略强。

    单位说明:
        本函数直接返回 dB/km，调用方无需再乘以 4.343。
        使用时乘以传输距离 (km) 即得总衰减 (dB)。

    参数:
        visibility_km (float): 大气能见度 (km)，推荐用于 V < 1 km 的浓雾场景，必须 > 0
        wavelength_nm (float): 工作波长 (nm)，默认 1550 nm
    返回:
        alpha_db_per_km (float): 辐射雾衰减系数 (dB/km)
    异常:
        ValueError: visibility_km <= 0
    """
    V = float(visibility_km)
    if V <= 0:
        raise ValueError(f"visibility_km 必须 > 0，当前值: {V}")
    V_m = V * 1000.0
    alpha = (0.18126 * wavelength_nm**2 + 0.13709 * wavelength_nm + 3.7502) / V_m
    return alpha


def rain_attenuation(rainfall_rate_mm_h, wavelength_nm=1550):
    """
    雨天附加衰减系数（文献式4.5后文字）
    文献只给出锚点: 2.5 cm/h = 25 mm/h 降雨约 6 dB/km。
    为了在 UI 连续输入降雨率时仍能计算，这里采用通过原点和该锚点的
    线性插值: α_rain = 6 · R / 25。

    其中 R 为降雨量 (mm/h)。

    物理背景:
        雨滴直径典型范围 0.1~10 mm，远大于近红外波长（1~2 μm），
        属于几何光学散射区（Mie 散射的大粒子极限）：
        - 散射截面近似等于雨滴几何截面，与波长基本无关
        - 因此 wavelength_nm 参数在当前实现中未使用（预留扩展接口）
        - FSO 雨衰比同频段微波雨衰更小，因为光波波长远小于雨滴（几何区），
          而微波波长与雨滴尺寸接近（共振区），散射截面更大

    参数:
        rainfall_rate_mm_h (float): 降雨强度 (mm/h)，0 表示无雨
        wavelength_nm (float): 工作波长 (nm)，当前版本未使用（预留接口）
    返回:
        alpha_rain (float): 雨天衰减系数 (dB/km)；降雨量为 0 时返回 0.0
    """
    # 无降雨时直接返回零，避免对 0 取幂的无意义计算
    if rainfall_rate_mm_h <= 0:
        return 0.0
    return 6.0 * rainfall_rate_mm_h / 25.0


def snow_attenuation(snowfall_rate_mm_h, snow_type="wet"):
    """
    雪天附加衰减系数（文献式4.5后文字）

    文献给出的约束是“小雪至暴雪可能造成 3~30 dB/km 的衰减”，
    没有提供降雪率到衰减的闭式公式。为了严格围绕该区间建模，这里将
    UI 输入的 0~100 mm/h 映射到 3~30 dB/km；湿雪因含水率高采用更陡
    的斜率并在 30 dB/km 截断，干雪上限较低。

    干雪 vs 湿雪的物理差异:
        - **干雪**（气温 < -5°C）：雪晶为冰相，折射率接近冰（n≈1.31），
          与空气对比较小，散射效率低；指数 1.38 较小，
          衰减随降雪量增加相对缓慢；常数项 5.50 较大，
          反映干雪大雪晶的基础几何散射本底。
        - **湿雪**（气温 -5~0°C）：雪晶部分融化，表面包裹液态水膜，
          折射率趋近于水（n≈1.33），散射效率大幅增强；
          指数 3.79 远大于干雪，表明衰减随降雪量急剧非线性增加；
          常数项 0.23 较小，说明小降雪量时湿雪衰减并不严重，
          但大降雪量时远超干雪。

    参数:
        snowfall_rate_mm_h (float): 降雪强度，水当量 (mm/h)，0 表示无雪
        snow_type (str): 雪的类型，'dry'（干雪）或 'wet'（湿雪），默认 'wet'
    返回:
        alpha_snow (float): 雪天衰减系数 (dB/km)；降雪量为 0 时返回 0.0
    """
    # 无降雪时直接返回零
    if snowfall_rate_mm_h <= 0:
        return 0.0

    S = min(float(snowfall_rate_mm_h), 100.0)
    if snow_type == "dry":
        return min(25.0, 3.0 + 0.5 * S)
    return min(30.0, 3.0 + 0.7 * S)


def total_channel_loss_db(
    visibility_km,
    distance_km,
    wavelength_nm=1550,
    rainfall_rate=0.0,
    snowfall_rate=0.0,
    snow_type="wet",
    fog_model="kim",
):
    """
    近地大气信道总衰减（dB）
    综合考虑：Mie 散射/吸收（雾/霾）+ 雨衰 + 雪衰

    衰减叠加原理:
        总衰减 = 大气散射衰减 + 雨衰 + 雪衰（dB 域线性叠加）
        dB 域相加等价于功率域（线性域）相乘，物理假设是：
        - 各天气效应相互独立，无耦合增强/屏蔽效应
        - 大气在传播路径上统计均匀（适用于近地水平链路）

    实际使用建议:
        - 雨、雪、雾在气象上通常互斥（不同天气类型），
          同时设置多个非零值时等效于"复合恶劣天气"的保守估计
        - fog_model 选择建议:
            * V > 1 km：使用默认 'kim'，公式简洁，精度足够
            * 0.05 < V < 1 km（浓雾）：推荐 'naboulsi_advection' 或 'naboulsi_radiation'
            * 沿海平流雾选 'naboulsi_advection'，内陆辐射雾选 'naboulsi_radiation'

    参数:
        visibility_km (float): 大气能见度 (km)
        distance_km (float): 传输距离 (km)
        wavelength_nm (float): 工作波长 (nm)，默认 1550 nm
        rainfall_rate (float): 降雨强度 (mm/h)，默认 0（无雨）
        snowfall_rate (float): 降雪强度，水当量 (mm/h)，默认 0（无雪）
        snow_type (str): 雪的类型，'dry'（干雪）或 'wet'（湿雪），默认 'wet'
        fog_model (str): 雾/霾衰减模型选择：
                         'kim'               — Kim 经验 Mie 散射模型（默认，通用）
                         'naboulsi_advection' — Naboulsi 平流雾模型（浓雾推荐）
                         'naboulsi_radiation' — Naboulsi 辐射雾模型（浓雾推荐）
    返回:
        total_loss_db (float): 总信道衰减 (dB)，正值，链路预算中直接从发射功率中扣除
    """
    # ── 第一项：大气散射/吸收衰减（根据所选雾衰减模型）──────────────────────────
    if fog_model == "naboulsi_advection":
        # Naboulsi 平流雾：直接返回 dB/km，乘以距离得总衰减 (dB)
        loss_atm = naboulsi_advection_fog(visibility_km, wavelength_nm) * distance_km
    elif fog_model == "naboulsi_radiation":
        # Naboulsi 辐射雾：直接返回 dB/km，乘以距离得总衰减 (dB)
        loss_atm = naboulsi_radiation_fog(visibility_km, wavelength_nm) * distance_km
    else:
        # 默认 Kim 模型：先求 Naperian 消光系数，再通过 4.343 因子转换为 dB
        sigma = attenuation_coefficient(visibility_km, wavelength_nm)
        loss_atm = atmospheric_attenuation_db(sigma, distance_km)

    # ── 第二项：雨天附加衰减 ──────────────────────────────────────────────────────
    # rain_attenuation() 返回 dB/km，乘以距离得总雨衰 (dB)
    loss_rain = rain_attenuation(rainfall_rate, wavelength_nm) * distance_km

    # ── 第三项：雪天附加衰减 ──────────────────────────────────────────────────────
    # snow_attenuation() 返回 dB/km，乘以距离得总雪衰 (dB)
    loss_snow = snow_attenuation(snowfall_rate, snow_type) * distance_km

    # 三项 dB 衰减直接相加（功率域等价于三个透过率相乘）
    return loss_atm + loss_rain + loss_snow


def transmittance(
    visibility_km,
    distance_km,
    wavelength_nm=1550,
    rainfall_rate=0.0,
    snowfall_rate=0.0,
    snow_type="wet",
    fog_model="kim",
):
    """
    近地大气信道总透过率
    τ_total = 10^(-L_total_dB / 10)

    透过率与衰减量的关系:
        dB 衰减量 L_dB 与线性透过率 τ 的互换公式：
            τ = 10^(-L_dB / 10)     （dB → 线性）
            L_dB = -10·log10(τ)    （线性 → dB）
        本函数调用 total_channel_loss_db() 获取总 dB 衰减，再转换为线性透过率。

    在链路预算中的位置:
        接收功率 P_r = P_t × η_T × τ_geometric × τ_atmosphere × η_R
        其中 τ_atmosphere 即本函数返回值，η_T/η_R 为发射/接收光学效率，
        τ_geometric 为几何损耗透过率（含衍射、指向误差等）。

    参数:
        visibility_km (float): 大气能见度 (km)
        distance_km (float): 传输距离 (km)
        wavelength_nm (float): 工作波长 (nm)，默认 1550 nm
        rainfall_rate (float): 降雨强度 (mm/h)，默认 0（无雨）
        snowfall_rate (float): 降雪强度，水当量 (mm/h)，默认 0（无雪）
        snow_type (str): 雪的类型，'dry'（干雪）或 'wet'（湿雪），默认 'wet'
        fog_model (str): 雾/霾衰减模型，'kim' / 'naboulsi_advection' / 'naboulsi_radiation'
    返回:
        tau (float): 大气总透过率，范围 (0, 1]；
                     tau=1 表示无衰减，tau→0 表示近乎全吸收
    """
    # 先计算总 dB 衰减，再转换为线性透过率
    total_loss = total_channel_loss_db(
        visibility_km,
        distance_km,
        wavelength_nm,
        rainfall_rate,
        snowfall_rate,
        snow_type,
        fog_model,
    )
    # 公式: τ = 10^(-L_dB / 10)
    return 10 ** (-total_loss / 10)
