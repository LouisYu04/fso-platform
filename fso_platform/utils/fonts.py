"""
跨平台字体配置
根据操作系统自动选择合适的中文字体和等宽字体
"""

import platform

_sys = platform.system()

if _sys == "Darwin":  # macOS
    FONT_FAMILY = "PingFang SC"
    FONT_MONO = "Menlo"
    # macOS 保持原始字号不变
    FONT_SIZE_APP = 10
    FONT_SIZE_XS = 11
    FONT_SIZE_SM = 12
    FONT_SIZE_MD = 13
    FONT_SIZE_LG = 14
    FONT_SIZE_XL = 16
    FONT_SIZE_TITLE = 20
elif _sys == "Windows":  # Windows
    FONT_FAMILY = "Microsoft YaHei"
    FONT_MONO = "Consolas"
    FONT_SIZE_APP = 13          # Windows needs larger base font
    FONT_SIZE_XS = 12
    FONT_SIZE_SM = 13
    FONT_SIZE_MD = 14
    FONT_SIZE_LG = 15
    FONT_SIZE_XL = 17
    FONT_SIZE_TITLE = 22
else:  # Linux / other
    FONT_FAMILY = "Noto Sans CJK SC"
    FONT_MONO = "DejaVu Sans Mono"
    FONT_SIZE_APP = 11
    FONT_SIZE_XS = 11
    FONT_SIZE_SM = 12
    FONT_SIZE_MD = 13
    FONT_SIZE_LG = 14
    FONT_SIZE_XL = 16
    FONT_SIZE_TITLE = 20

# Matplotlib CJK 字体列表 (按优先级排列)
MPL_CJK_FONTS = [
    "Arial Unicode MS",  # macOS (广泛 Unicode 覆盖)
    "PingFang SC",  # macOS 系统字体
    "SimHei",  # Windows 黑体
    "Microsoft YaHei",  # Windows 微软雅黑
    "Noto Sans CJK SC",  # Linux
    "DejaVu Sans",  # 通用 fallback
]
