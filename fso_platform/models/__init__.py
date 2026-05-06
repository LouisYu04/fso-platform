"""
物理模型层 — FSO 链路核心物理模型 (50 个公共函数)

模块:
    atmosphere      — 10 个: 大气衰减 (Kim / Naboulsi / 雨/雪)
    geometric       —  7 个: 几何损耗、增益、指向误差
    turbulence      — 10 个: Rytov方差、闪烁指数、Fried参数、Cn²
    link_budget     —  9 个: 接收功率、SNR (PIN/APD)、噪声、链路余量
    ber             —  7 个: OOK/PPM/SIM-BPSK BER (AWGN + 湍流)
    distributions   —  5 个: 对数正态 / Gamma-Gamma / 负指数 PDF
    scintillation   —  2 个: 平面波/球面波对数闪烁方差
"""

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

from fso_platform.models.geometric import (
    beam_diameter_at_distance,
    geometric_loss,
    geometric_loss_db,
    transmitter_gain,
    receiver_gain,
    pointing_error_loss,
    pointing_error_loss_simple,
)

from fso_platform.models.turbulence import (
    rytov_variance,
    rytov_variance_spherical,
    turbulence_regime,
    scintillation_index_weak,
    scintillation_index_plane_wave,
    scintillation_index_spherical_wave,
    fried_parameter,
    long_term_beam_size,
    beam_wander_variance,
    cn2_typical,
)

from fso_platform.models.link_budget import (
    received_power,
    received_power_dbm,
    noise_thermal,
    noise_shot,
    snr_pin,
    snr_pin_db,
    snr_apd,
    link_margin,
    bandwidth_from_datarate,
)

from fso_platform.models.ber import (
    ber_ook,
    ber_ppm,
    ber_sim_bpsk,
    ber_ook_turbulence,
    ber_ppm_turbulence,
    ber_sim_turbulence,
    ber_vs_snr,
)

from fso_platform.models.distributions import (
    lognormal_pdf,
    gamma_gamma_alpha_beta,
    gamma_gamma_pdf,
    negative_exponential_pdf,
    select_distribution,
)

from fso_platform.models.scintillation import (
    sigma_ln_plane_wave,
    sigma_ln_spherical_wave,
)

__all__ = [
    # atmosphere (10)
    "kim_p",
    "attenuation_coefficient",
    "beer_lambert",
    "atmospheric_attenuation_db",
    "naboulsi_advection_fog",
    "naboulsi_radiation_fog",
    "rain_attenuation",
    "snow_attenuation",
    "total_channel_loss_db",
    "transmittance",
    # geometric (7)
    "beam_diameter_at_distance",
    "geometric_loss",
    "geometric_loss_db",
    "transmitter_gain",
    "receiver_gain",
    "pointing_error_loss",
    "pointing_error_loss_simple",
    # turbulence (10)
    "rytov_variance",
    "rytov_variance_spherical",
    "turbulence_regime",
    "scintillation_index_weak",
    "scintillation_index_plane_wave",
    "scintillation_index_spherical_wave",
    "fried_parameter",
    "long_term_beam_size",
    "beam_wander_variance",
    "cn2_typical",
    # link_budget (9)
    "received_power",
    "received_power_dbm",
    "noise_thermal",
    "noise_shot",
    "snr_pin",
    "snr_pin_db",
    "snr_apd",
    "link_margin",
    "bandwidth_from_datarate",
    # ber (7)
    "ber_ook",
    "ber_ppm",
    "ber_sim_bpsk",
    "ber_ook_turbulence",
    "ber_ppm_turbulence",
    "ber_sim_turbulence",
    "ber_vs_snr",
    # distributions (5)
    "lognormal_pdf",
    "gamma_gamma_alpha_beta",
    "gamma_gamma_pdf",
    "negative_exponential_pdf",
    "select_distribution",
    # scintillation (2)
    "sigma_ln_plane_wave",
    "sigma_ln_spherical_wave",
]
