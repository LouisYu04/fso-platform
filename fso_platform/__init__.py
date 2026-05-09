"""
fso_platform — 无线光通信系统链路特性可视化平台

A PyQt5 + Matplotlib FSO (Free Space Optics) link simulation and
visualization platform with atmospheric attenuation, turbulence,
link budget, BER, and statistical distribution models.
"""

__version__ = "1.0.3"
__author__ = "FSO Team"

from fso_platform import models
from fso_platform import ui
from fso_platform import utils
from fso_platform import analysis

__all__ = [
    "models",
    "ui",
    "utils",
    "analysis",
]
