"""
跨平台字体配置
根据操作系统自动选择合适的中文字体和等宽字体
"""

import platform

_sys = platform.system()

if _sys == "Darwin":  # macOS
    FONT_FAMILY = "PingFang SC"
    FONT_MONO = "Menlo"
elif _sys == "Windows":  # Windows
    FONT_FAMILY = "Microsoft YaHei"
    FONT_MONO = "Consolas"
else:  # Linux / other
    FONT_FAMILY = "Noto Sans CJK SC"
    FONT_MONO = "DejaVu Sans Mono"

# Matplotlib CJK 字体列表 (按优先级排列)
MPL_CJK_FONTS = [
    "Arial Unicode MS",  # macOS (广泛 Unicode 覆盖)
    "PingFang SC",  # macOS 系统字体
    "SimHei",  # Windows 黑体
    "Microsoft YaHei",  # Windows 微软雅黑
    "Noto Sans CJK SC",  # Linux
    "DejaVu Sans",  # 通用 fallback
]
