"""
仿真工作线程
将纯计算逻辑从 SimulationPanel 中提取，在独立线程中运行

信号:
    progress(int)           -- 进度 0-100
    log_line(str)           -- 日志行文本（已渲染 HTML）
    result_update(str, object, str) -- (key, value, fmt) 指标更新
    simulation_done(dict)   -- 完整结果字典
    error_occurred(str)     -- 异常信息
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
    ber_sim_bpsk,
    ber_ook_turbulence,
    ber_ppm_turbulence,
    ber_sim_turbulence,
    ber_vs_snr,
)
from ..utils.constants import watt_to_dbm


class SimulationWorker(QObject):
    progress = pyqtSignal(int)
    log_line = pyqtSignal(str)
    result_update = pyqtSignal(str, object, str)
    simulation_done = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, params: dict):
        super().__init__()
        self._params = params
        self._cancelled = threading.Event()

    def cancel(self):
        self._cancelled.set()

    def _check_cancelled(self, section: str = None):
        if self._cancelled.is_set():
            if section:
                self.log_line.emit(f"\n[取消] {section} 被中断")
            raise InterruptedError("仿真已取消")

    def run(self):
        try:
            self._run_simulation()
        except InterruptedError:
            pass
        except Exception as e:
            self.error_occurred.emit(str(e))

    def _run_simulation(self):
        params = self._params
        t_start = time.time()
        results = {}

        self.log_line.emit("=" * 50)
        self.log_line.emit("  开始仿真 — 近地大气FSO链路特性计算")
        self.log_line.emit("=" * 50)

        # ===== 1. 大气衰减 =====
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
        )
        tau_atm = 10 ** (-atm_loss_db / 10)

        results["sigma_atm"] = sigma
        results["atm_loss_db"] = atm_loss_db
        results["tau_atm"] = tau_atm

        self.log_line.emit(f"  衰减系数 σ = {sigma:.4f} Np/km")
        self.log_line.emit(f"  大气衰减 = {atm_loss_db:.4f} dB")
        self.log_line.emit(f"  透过率 τ = {tau_atm:.6f}")
        self.result_update.emit("atm_loss", atm_loss_db, "{:.2f}")

        # ===== 2. 几何损耗 =====
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
        self._check_cancelled("BER")
        self.progress.emit(85)
        self.log_line.emit("\n[6/6] 误码率计算...")

        M_ppm = params.get("M_ppm", 4)

        ber_ook_awgn = ber_ook(snr) if snr > 0 else 1.0
        ber_ppm_awgn = ber_ppm(snr, M_ppm) if snr > 0 else 1.0
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

        # 链路余量
        margin = link_margin(P_R_dbm, params["sensitivity_dbm"])
        results["margin"] = margin
        self.result_update.emit("margin", margin, "{:.2f}")

        # ===== 生成曲线数据 =====
        self._check_cancelled("可视化数据")
        self.log_line.emit("\n生成可视化数据...")

        snr_db_range = np.linspace(0, 40, 200)
        results["snr_db_range"] = snr_db_range
        results["ber_ook_curve"] = ber_vs_snr(snr_db_range, "OOK")
        results["ber_ppm_curve"] = ber_vs_snr(snr_db_range, "PPM", M_ppm=M_ppm)
        results["ber_sim_curve"] = ber_vs_snr(snr_db_range, "SIM")
        results["ber_ook_turb_curve"] = ber_vs_snr(snr_db_range, "OOK", sigma_R2)
        results["ber_ppm_turb_curve"] = ber_vs_snr(snr_db_range, "PPM", sigma_R2, M_ppm)
        results["ber_sim_turb_curve"] = ber_vs_snr(snr_db_range, "SIM", sigma_R2)

        dist_range = np.linspace(0.01, max(params["distance_km"] * 2, 5), 200)
        dist_range_m = dist_range * 1000
        results["dist_range_km"] = dist_range

        _sigma_kim = attenuation_coefficient(params["visibility_km"], params["wavelength_nm"])
        _rain_per_km = rain_attenuation(params["rainfall_rate"]) if params["rainfall_rate"] > 0 else 0.0
        _snow_per_km = snow_attenuation(params["snowfall_rate"], params["snow_type"]) if params["snowfall_rate"] > 0 else 0.0
        _loss_per_km = 4.343 * _sigma_kim + _rain_per_km + _snow_per_km
        results["atm_loss_curve"] = _loss_per_km * dist_range

        _sigma_R2_curve = rytov_variance(params["Cn2"], params["wavelength_m"], dist_range_m)
        results["sigma_I2_curve"] = scintillation_index_plane_wave(_sigma_R2_curve)

        _tau_curve = 10.0 ** (-_loss_per_km * dist_range / 10.0)
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
