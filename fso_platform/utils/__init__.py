"""
工具层 — 物理常量、单位转换、字体配置、验证报告

导出:
    9 个物理/光学常量           — C, K_B, Q_E, H, PI, LAMBDA_* (4 个)
    6 个单位转换函数            — wavelength_to_*, dbm_to_watt, watt_to_dbm, db_to_linear, linear_to_db
    3 个字体配置常量            — FONT_FAMILY, FONT_MONO, MPL_CJK_FONTS
    2 个验证报告 CLI 函数       — run_all, generate_markdown
"""

from fso_platform.utils.constants import (
    C,
    K_B,
    Q_E,
    H,
    PI,
    LAMBDA_850,
    LAMBDA_1064,
    LAMBDA_1550,
    LAMBDA_REF_NM,
    wavelength_to_wavenumber,
    wavelength_to_frequency,
    dbm_to_watt,
    watt_to_dbm,
    db_to_linear,
    linear_to_db,
)

from fso_platform.utils.fonts import (
    FONT_FAMILY,
    FONT_MONO,
    MPL_CJK_FONTS,
)

from fso_platform.utils.validation_report import (
    run_all,
    generate_markdown,
)

__all__ = [
    # Physical / optical constants (9)
    "C",
    "K_B",
    "Q_E",
    "H",
    "PI",
    "LAMBDA_850",
    "LAMBDA_1064",
    "LAMBDA_1550",
    "LAMBDA_REF_NM",
    # Conversion functions (6)
    "wavelength_to_wavenumber",
    "wavelength_to_frequency",
    "dbm_to_watt",
    "watt_to_dbm",
    "db_to_linear",
    "linear_to_db",
    # Font constants (3)
    "FONT_FAMILY",
    "FONT_MONO",
    "MPL_CJK_FONTS",
    # Validation CLI (2)
    "run_all",
    "generate_markdown",
]
