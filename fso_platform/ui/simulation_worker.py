"""
仿真工作线程
将纯计算逻辑从 SimulationPanel 中提取，在独立线程中运行

信号:
    progress(int)           -- 进度 0-100
    log_line(str)           -- 日志行文本（面板会再转换为 HTML）
    result_update(str, object, str) -- (key, value, fmt) 指标增量更新
    simulation_done(dict)   -- 完整结果字典，供图表和报告面板使用
    error_occurred(str)     -- 异常信息

设计说明:
    Worker 不直接操作任何 QWidget。Qt 要求 GUI 控件只能在主线程更新，
    因此本类只通过信号把“进度、日志、指标、最终结果”发回 MainWindow
    和 SimulationPanel。这样既避免界面卡顿，也减少跨线程 UI 崩溃风险。
"""

import threading
import time
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal

from ..models.atmosphere import (
    attenuation_coefficient,
    total_channel_loss_db,
    rain_attenuation,
    snow_attenuation,
)
from ..models.turbulence import (
    rytov_variance,
    turbulence_regime,
    scintillation_index_plane_wave,
)
from ..models.distributions import (
    lognormal_pdf,
    gamma_gamma_pdf,
    gamma_gamma_alpha_beta,
    negative_exponential_pdf,
    select_distribution,
)
from ..models.geometric import (
    beam_diameter_at_distance,
    geometric_loss,
    geometric_loss_db,
    pointing_error_loss_simple,
    transmitter_gain,
)
from ..models.link_budget import (
    received_power,
    snr_pin,
    snr_apd,
    noise_thermal,
    noise_shot,
    link_margin,
    bandwidth_from_datarate,
)
from ..models.ber import (
    ber_ook,
    ber_ppm,
    ber_ppm_photon,
    ber_sim_bpsk,
    ber_ook_turbulence,
    ber_ppm_turbulence,
    ber_sim_turbulence,
    ber_vs_snr,
)
from ..utils.constants import watt_to_dbm, H, C, Q_E


class SimulationWorker(QObject):
    """
    单次仿真的后台执行器。

    params 由 ParameterPanel.get_params() 生成，已经把界面单位转换为模型
    所需单位，例如 mW -> W、km -> m、mrad -> rad。Worker 内部只消费
    params，不再访问界面控件。
    """

    # 这些信号是 worker 和 UI 的唯一通信通道。新增展示字段时，优先扩展
    # results 字典或 result_update，而不是让 worker 持有面板引用。
    progress = pyqtSignal(int)
    log_line = pyqtSignal(str)
    result_update = pyqtSignal(str, object, str)
    simulation_done = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, params: dict):
        super().__init__()
        # 参数字典在仿真期间视为只读。若后续支持运行中修改参数，应该创建
        # 新 worker，而不是原地修改这里的 dict。
        self._params = params
        # threading.Event 是线程安全的取消标记，主线程可调用 cancel() 设置，
        # worker 在各阶段边界通过 _check_cancelled() 主动检查。
        self._cancelled = threading.Event()

    def cancel(self):
        """请求取消仿真。实际中断点取决于 _check_cancelled() 调用位置。"""
        self._cancelled.set()

    def _check_cancelled(self, section: str = None):
        """
        在阶段边界检查取消标记。

        这里使用异常跳出计算流程，可以避免在每个调用点写重复的 if/return。
        注意：长时间数值积分内部不会自动检查取消，若要提升取消响应速度，
        需要在曲线生成循环中增加更多检查点。
        """
        if self._cancelled.is_set():
            if section:
                self.log_line.emit(f"\n[取消] {section} 被中断")
            raise InterruptedError("仿真已取消")

    def run(self):
        """
        QThread.started 连接到的入口函数。

        不把异常抛出到 Qt 事件循环，而是转换成 error_occurred 信号交给
        MainWindow 显示。InterruptedError 代表用户主动取消，不按错误弹窗处理。
        """
        try:
            self._run_simulation()
        except InterruptedError:
            pass
        except Exception as e:
            self.error_occurred.emit(str(e))

    def _run_simulation(self):
        """
        执行完整链路仿真。

        results 字典是本方法的核心产物，包含三类数据：
            1. 标量指标：接收功率、SNR、BER、链路余量等；
            2. 状态文本：湍流强度、光强分布名称等；
            3. 曲线数组：供 PlotPanel 绘制距离曲线、BER 曲线和 PDF 曲线。

        计算流程按日志中的 1/6 到 6/6 分段，便于 UI 展示和后续定位问题。
        """
        params = self._params
        t_start = time.time()
        results = {}

        self.log_line.emit("=" * 50)
        self.log_line.emit("  开始仿真 — 近地大气FSO链路特性计算")
        self.log_line.emit("=" * 50)

        # ===== 1. 大气衰减 =====
        # 先使用 Kim 模型计算基础消光系数 sigma，用于日志展示；总大气损耗
        # 通过 total_channel_loss_db 汇总雾/霾、雨、雪等天气效应。
        self._check_cancelled("大气衰减")
        self.progress.emit(10)
        self.log_line.emit("\n[1/6] 计算大气衰减...")

        sigma = attenuation_coefficient(
            params["visibility_km"], params["wavelength_nm"]
        )
        atm_loss_db = total_channel_loss_db(
            params["visibility_km"],
            params["distance_km"],
            params["wavelength_nm"],
            params["rainfall_rate"],
            params["snowfall_rate"],
            params["snow_type"],
            params.get("fog_model", "kim"),
        )
        tau_atm = 10 ** (-atm_loss_db / 10)

        results["sigma_atm"] = sigma
        results["atm_loss_db"] = atm_loss_db
        results["tau_atm"] = tau_atm

        self.log_line.emit(f"  雾/霾模型 = {params.get('fog_model', 'kim')}")
        self.log_line.emit(f"  Kim 衰减系数 σ = {sigma:.4f} Np/km")
        self.log_line.emit(f"  大气衰减 = {atm_loss_db:.4f} dB")
        self.log_line.emit(f"  透过率 τ = {tau_atm:.6f}")
        self.result_update.emit("atm_loss", atm_loss_db, "{:.2f}")

        # ===== 2. 几何损耗 =====
        # 几何损耗描述接收孔径能截获多少扩展后的光斑功率。这里使用简化远场
        # 光斑直径模型 D_beam = D_T + divergence * distance。
        self._check_cancelled("几何损耗")
        self.progress.emit(25)
        self.log_line.emit("\n[2/6] 计算几何损耗...")

        D_beam = beam_diameter_at_distance(
            params["D_T_m"], params["divergence_rad"], params["distance_m"]
        )
        L_geo = geometric_loss(params["D_R_m"], D_beam)
        L_geo_db = geometric_loss_db(params["D_R_m"], D_beam)

        results["D_beam"] = D_beam
        results["L_geo"] = L_geo
        results["L_geo_db"] = L_geo_db

        self.log_line.emit(f"  接收面光斑直径 = {D_beam * 100:.2f} cm")
        self.log_line.emit(f"  几何损耗 = {L_geo_db:.2f} dB")
        self.result_update.emit("geo_loss", L_geo_db, "{:.2f}")

        # 指向误差是独立于几何扩展的额外功率损耗。界面允许设置 0，表示
        # 不考虑抖动，此时保持 L_point=1 以免引入数值误差。
        jitter_rad = params.get("pointing_jitter_rad", 0.0)
        if jitter_rad > 0:
            L_point = pointing_error_loss_simple(
                jitter_rad, params["divergence_rad"]
            )
        else:
            L_point = 1.0
        L_point_db = -10 * np.log10(L_point) if L_point > 0 else 0.0

        results["L_point"] = L_point
        results["L_point_db"] = L_point_db
        self.log_line.emit(f"  指向抖动 = {params.get('pointing_jitter_urad', 0):.1f} μrad")
        self.log_line.emit(f"  指向误差损耗 = {L_point_db:.2f} dB")

        # ===== 3. 链路预算 =====
        # received_power 在功率线性域计算最终接收功率；total_loss 在 dB 域
        # 汇总用于展示。两者应保持等价，但一个适合后续 SNR 计算，一个适合
        # 工程链路预算阅读。
        self._check_cancelled("链路预算")
        self.progress.emit(40)
        self.log_line.emit("\n[3/6] 链路预算计算...")

        P_R = received_power(
            params["power_w"],
            0,
            0,
            tau_atm,
            L_geo,
            L_point=L_point,
            mu_T=params["mu_T"],
            mu_R=params["mu_R"],
        )
        P_R_dbm = watt_to_dbm(P_R) if P_R > 0 else -999

        total_loss = atm_loss_db + abs(L_geo_db)
        opt_loss = -10 * np.log10(params["mu_T"] * params["mu_R"])
        total_loss += opt_loss
        total_loss += L_point_db

        results["P_R_w"] = P_R
        results["P_R_dbm"] = P_R_dbm
        results["total_loss_db"] = total_loss
        results["opt_loss_db"] = opt_loss

        self.log_line.emit(
            f"  发射功率 = {params['power_mw']:.2f} mW "
            f"({watt_to_dbm(params['power_w']):.2f} dBm)"
        )
        self.log_line.emit(f"  光学效率损耗 = {opt_loss:.2f} dB")
        self.log_line.emit(f"  总链路损耗 = {total_loss:.2f} dB")
        self.log_line.emit(f"  接收功率 = {P_R_dbm:.2f} dBm ({P_R * 1e6:.4f} μW)")
        self.result_update.emit("P_R", P_R_dbm, "{:.2f}")
        self.result_update.emit("total_loss", total_loss, "{:.2f}")

        # ===== 4. SNR =====
        # 带宽由调制方式决定：PPM 为获得功率效率会牺牲带宽，因此 B 与 M_ppm
        # 有关。探测器类型决定使用 PIN 还是 APD 噪声模型。
        self._check_cancelled("SNR")
        self.progress.emit(55)
        self.log_line.emit("\n[4/6] 信噪比计算...")

        modulation = params["modulation"]
        B = bandwidth_from_datarate(params["data_rate_bps"], modulation, params.get("M_ppm", 4))
        detector_type = params.get("detector_type", "PIN")
        M_apd = params.get("M_apd", 50.0)
        F_apd = params.get("F_apd", 3.0)
        if detector_type == "APD":
            snr = snr_apd(
                P_R,
                params["R_p"],
                M_apd,
                F_apd,
                1.0,
                params["temperature"],
                B,
                params["R_L"],
                params["P_B_w"],
            )
        else:
            snr = snr_pin(
                P_R,
                params["R_p"],
                1.0,
                params["temperature"],
                B,
                params["R_L"],
                params["P_B_w"],
            )
        snr_db = 10 * np.log10(snr) if snr > 0 else -999

        results["bandwidth"] = B
        results["snr"] = snr
        results["snr_db"] = snr_db

        n_th = noise_thermal(params["temperature"], B, params["R_L"])
        n_sh = noise_shot(params["R_p"], P_R, params["P_B_w"], B)
        results["noise_thermal"] = n_th
        results["noise_shot"] = n_sh

        _apd_extra = f"  (M={M_apd:.0f}, F={F_apd:.1f})" if detector_type == "APD" else ""
        self.log_line.emit(f"  探测器类型 = {detector_type}{_apd_extra}")
        self.log_line.emit(f"  电带宽 B = {B / 1e6:.1f} MHz")
        self.log_line.emit(f"  热噪声 = {n_th:.2e} A²")
        self.log_line.emit(f"  散粒噪声 = {n_sh:.2e} A²")
        self.log_line.emit(f"  SNR = {snr_db:.2f} dB")
        self.result_update.emit("snr", snr_db, "{:.2f}")

        # ===== 5. 大气湍流 =====
        # Rytov 方差是后续湍流强度分类、闪烁指数和光强分布选择的公共输入。
        self._check_cancelled("大气湍流")
        self.progress.emit(70)
        self.log_line.emit("\n[5/6] 大气湍流分析...")

        sigma_R2 = rytov_variance(
            params["Cn2"], params["wavelength_m"], params["distance_m"]
        )
        regime = turbulence_regime(sigma_R2)
        sigma_I2 = scintillation_index_plane_wave(sigma_R2)

        dist_name, _, dist_params = select_distribution(sigma_R2)

        results["sigma_R2"] = sigma_R2
        results["regime"] = regime
        results["sigma_I2"] = sigma_I2
        results["dist_name"] = dist_name
        results["dist_params"] = dist_params

        self.log_line.emit(f"  Cn² = {params['Cn2']:.2e} m⁻²/³")
        self.log_line.emit(f"  Rytov方差 σ_R² = {sigma_R2:.6f}")
        self.log_line.emit(f"  湍流强度: {regime}")
        self.log_line.emit(f"  闪烁指数 σ_I² = {sigma_I2:.6f}")
        self.log_line.emit(f"  光强分布: {dist_name}")
        if "alpha" in dist_params:
            self.log_line.emit(
                f"    α = {dist_params['alpha']:.4f}, β = {dist_params['beta']:.4f}"
            )
        self.result_update.emit("sigma_R2", sigma_R2, "{:.6f}")
        self.result_update.emit("regime", regime, None)
        self.result_update.emit("sigma_I2", sigma_I2, "{:.6f}")

        # ===== 6. BER =====
        # 同时计算 AWGN 和湍流信道下的 BER，方便结果面板直接对比。若 SNR<=0
        # 或 sigma_R2=0，则湍流结果退化为 AWGN/默认最差值。
        self._check_cancelled("BER")
        self.progress.emit(85)
        self.log_line.emit("\n[6/6] 误码率计算...")

        M_ppm = params.get("M_ppm", 4)
        eta_q = params["R_p"] * H * C / (Q_E * params["wavelength_m"])
        eta_q = float(np.clip(eta_q, 0.0, 1.0))
        ppm_gain = M_apd if detector_type == "APD" else 1.0
        ppm_noise_factor = F_apd if detector_type == "APD" else 1.0

        ber_ook_awgn = ber_ook(snr) if snr > 0 else 1.0
        ber_ppm_awgn = (
            ber_ppm_photon(
                P_R,
                params["P_B_w"],
                params["wavelength_m"],
                params["data_rate_bps"],
                M_ppm,
                eta_q,
                ppm_gain,
                ppm_noise_factor,
                params["temperature"],
                params["R_L"],
            )
            if P_R > 0
            else 1.0
        )
        ber_sim_awgn = ber_sim_bpsk(snr) if snr > 0 else 1.0

        if snr > 0 and sigma_R2 > 0:
            ber_ook_val = ber_ook_turbulence(snr, sigma_R2)
            ber_ppm_val = ber_ppm_turbulence(snr, sigma_R2, M_ppm)
            ber_sim_val = ber_sim_turbulence(snr, sigma_R2)
        else:
            ber_ook_val = ber_ook_awgn
            ber_ppm_val = ber_ppm_awgn
            ber_sim_val = ber_sim_awgn

        results["ber_ook_awgn"] = ber_ook_awgn
        results["ber_ppm_awgn"] = ber_ppm_awgn
        results["ber_sim_awgn"] = ber_sim_awgn
        results["ber_ook"] = ber_ook_val
        results["ber_ppm"] = ber_ppm_val
        results["ber_sim"] = ber_sim_val
        results["M_ppm"] = M_ppm

        self.log_line.emit(f"\n  {'':15} {'AWGN':>12}  {'湍流信道':>12}")
        self.log_line.emit(f"  {'OOK':15} {ber_ook_awgn:12.4e}  {ber_ook_val:12.4e}")
        self.log_line.emit(f"  {f'{M_ppm}-PPM':15} {ber_ppm_awgn:12.4e}  {ber_ppm_val:12.4e}")
        self.log_line.emit(f"  {'SIM-BPSK':15} {ber_sim_awgn:12.4e}  {ber_sim_val:12.4e}")

        self.result_update.emit("ber_ook", ber_ook_val, None)
        self.result_update.emit("ber_ppm", ber_ppm_val, None)
        self.result_update.emit("ber_sim", ber_sim_val, None)

        # 链路余量 = 接收功率 - 接收灵敏度。它比单独看 BER 更直观，适合在
        # 状态栏和结果摘要里给出“可用/不可用”的工程判断。
        margin = link_margin(P_R_dbm, params["sensitivity_dbm"])
        results["margin"] = margin
        self.result_update.emit("margin", margin, "{:.2f}")

        # ===== 生成曲线数据 =====
        # PlotPanel 不再调用模型函数重新计算，而是只消费 results 中的曲线数组。
        # 这样一次仿真对应一组冻结数据，图表、表格和报告不会因为二次计算产生
        # 细微不一致。
        self._check_cancelled("可视化数据")
        self.log_line.emit("\n生成可视化数据...")

        # BER 曲线：无湍流曲线是向量化公式；有湍流曲线会逐点积分，属于本流程
        # 中最耗时的部分。后续若要优化响应速度，可从这里降低点数或增加缓存。
        snr_db_range = np.linspace(0, 40, 200)
        results["snr_db_range"] = snr_db_range
        results["ber_ook_curve"] = ber_vs_snr(snr_db_range, "OOK")
        results["ber_ppm_curve"] = ber_vs_snr(snr_db_range, "PPM", M_ppm=M_ppm)
        results["ber_sim_curve"] = ber_vs_snr(snr_db_range, "SIM")
        results["ber_ook_turb_curve"] = ber_vs_snr(snr_db_range, "OOK", sigma_R2)
        results["ber_ppm_turb_curve"] = ber_vs_snr(snr_db_range, "PPM", sigma_R2, M_ppm)
        results["ber_sim_turb_curve"] = ber_vs_snr(snr_db_range, "SIM", sigma_R2)

        # 距离曲线：横轴至少覆盖 5 km，也会覆盖当前链路距离的两倍，保证图中
        # 当前工作点不会贴在右边界。
        dist_range = np.linspace(0.01, max(params["distance_km"] * 2, 5), 200)
        dist_range_m = dist_range * 1000
        results["dist_range_km"] = dist_range

        # 大气衰减曲线使用每公里损耗乘距离，和单点计算保持同一组天气参数。
        results["atm_loss_curve"] = total_channel_loss_db(
            params["visibility_km"],
            dist_range,
            params["wavelength_nm"],
            params["rainfall_rate"],
            params["snowfall_rate"],
            params["snow_type"],
            params.get("fog_model", "kim"),
        )

        _sigma_R2_curve = rytov_variance(params["Cn2"], params["wavelength_m"], dist_range_m)
        results["sigma_I2_curve"] = scintillation_index_plane_wave(_sigma_R2_curve)

        # 接收功率曲线同时考虑大气透过率、几何截获比例、指向损耗和光学效率。
        # np.maximum(..., 1e-30) 避免极小功率取 log10 时出现 -inf，保持图表可画。
        _tau_curve = 10.0 ** (-results["atm_loss_curve"] / 10.0)
        _D_beam_curve = params["D_T_m"] + params["divergence_rad"] * dist_range_m
        _L_geo_curve = np.minimum((params["D_R_m"] / _D_beam_curve) ** 2, 1.0)
        _P_R_curve_w = (
            params["power_w"]
            * _tau_curve
            * _L_geo_curve
            * L_point
            * params["mu_T"]
            * params["mu_R"]
        )
        results["P_R_curve"] = np.where(
            _P_R_curve_w > 0,
            10.0 * np.log10(np.maximum(_P_R_curve_w, 1e-30) * 1000.0),
            -100.0,
        )

        # 光强 PDF 曲线用于同屏比较三种常见湍流强度分布。弱湍流下 Gamma-Gamma
        # 参数可能不稳定，因此 sigma_R2 很小时返回零曲线。
        I_range = np.linspace(0.01, 6.0, 500)
        results["I_range"] = I_range
        results["pdf_lognormal"] = lognormal_pdf(I_range, max(sigma_R2, 0.05))
        if sigma_R2 > 0.01:
            alpha, beta = gamma_gamma_alpha_beta(sigma_R2)
            results["pdf_gamma_gamma"] = gamma_gamma_pdf(I_range, alpha, beta)
            results["gg_alpha"] = alpha
            results["gg_beta"] = beta
        else:
            results["pdf_gamma_gamma"] = np.zeros_like(I_range)
            results["gg_alpha"] = 0
            results["gg_beta"] = 0
        results["pdf_neg_exp"] = negative_exponential_pdf(I_range)

        # 完成
        self.progress.emit(100)
        elapsed = time.time() - t_start
        self.log_line.emit(f"\n{'=' * 50}")
        self.log_line.emit(f"  仿真完成! 耗时 {elapsed:.2f} 秒")
        self.log_line.emit(f"{'=' * 50}")

        self.simulation_done.emit(results)
