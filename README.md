# 无线光通信系统链路特性可视化平台

## 项目概述

本项目是一个基于 PyQt5 + Matplotlib 的**近地无线光通信（FSO）系统链路特性仿真与可视化平台**，支持大气衰减、湍流闪烁、链路预算、误码率（BER）分析等核心物理模型的实时计算与图表展示。

## 核心功能

| 模块 | 功能 |
|------|------|
| **大气衰减模型** | Kim 模型、Naboulsi 平流/辐射雾模型、雨/雪衰减计算 |
| **几何损耗模型** | 光束扩展、几何损耗、指向误差损耗 |
| **湍流闪烁模型** | Rytov 方差、闪烁指数、Fried 参数、湍流强度判别 |
| **链路预算模型** | 接收功率、SNR（PIN/APD）、热噪声/散粒噪声分析 |
| **误码率模型** | OOK、PPM、SIM-BPSK，支持湍流信道平均 BER |
| **概率分布模型** | 对数正态、Gamma-Gamma、负指数分布 PDF |
| **可视化面板** | 7 种专业图表：衰减曲线、光斑扩展、闪烁指数、功率预算、BER 曲线、噪声饼图、光强分布 |

## 环境要求

- **Python**: >= 3.9（推荐 3.12）
- **操作系统**: Windows / macOS / Linux
- **GUI 显示后端**: Qt5（由 PyQt5 自带）
- **中文字体**: 系统需安装 `PingFang SC`(macOS) / `Microsoft YaHei`(Windows) / `Noto Sans CJK`(Linux)

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动程序

```bash
python main.py
```

### 3. 使用说明

1. **选择预设场景**：左侧下拉菜单可选择晴天、薄雾、浓雾、中雨、大雨、雪天等典型场景
2. **调整参数**：展开各参数分组，修改波长、距离、发射功率、能见度、湍流强度等
3. **开始仿真**：点击底部「开始仿真」按钮，等待计算完成
4. **查看结果**：右侧自动切换至结果面板，显示数值结果与图表

## 项目结构

```
.
├── main.py                          # 程序入口（兼容旧方式）
├── requirements.txt                 # Python 依赖清单
├── pyproject.toml                   # 项目元数据与构建配置
├── pytest.ini                       # 测试配置
├── MANIFEST.in                      # 源码分发文件清单
├── README.md                        # 本文件
├── UI_CONVERSION_REPORT.md          # UI 文件转换报告
├── build.py                         # 统一构建脚本
├── fso_platform_macos.spec          # PyInstaller macOS 配置
├── fso_platform_windows.spec        # PyInstaller Windows 配置
├── .gitignore                       # Git 忽略规则
├── fso_platform/                    # 主包
│   ├── __init__.py                  # 包初始化
│   ├── __main__.py                  # CLI 入口点 (python -m fso_platform)
│   ├── models/                      # 物理模型层
│   │   ├── atmosphere.py            # 大气衰减
│   │   ├── geometric.py             # 几何损耗
│   │   ├── turbulence.py            # 湍流闪烁
│   │   ├── scintillation.py         # 闪烁方差计算
│   │   ├── link_budget.py           # 链路预算与 SNR
│   │   ├── ber.py                   # 误码率计算
│   │   └── distributions.py         # 概率分布函数
│   ├── ui/                          # UI 层
│   │   ├── main_window.py / .ui     # 主窗口
│   │   ├── parameter_panel.py / .ui # 参数面板
│   │   ├── simulation_panel.py / .ui# 仿真控制面板
│   │   ├── plot_widgets.py / .ui    # 绘图组件
│   │   ├── result_panel.py / .ui    # 结果面板
│   │   ├── simulation_worker.py     # 仿真工作线程
│   │   └── theme.py                 # 全局主题样式
│   └── utils/                       # 工具层
│       ├── constants.py             # 物理常数与单位转换
│       ├── fonts.py                 # 跨平台字体配置
│       └── validation_report.py     # 参数验证报告生成器
├── tests/                           # 单元测试
│   ├── test_atmosphere.py           # 大气衰减模型测试
│   ├── test_ber.py                  # BER 模型测试
│   ├── test_constants.py            # 物理常量测试
│   ├── test_distributions.py        # 概率分布测试
│   ├── test_geometric.py            # 几何损耗测试
│   ├── test_link_budget.py          # 链路预算测试
│   ├── test_models.py               # 核心模型综合验证
│   ├── test_scintillation.py        # 闪烁方差测试
│   ├── test_turbulence.py           # 湍流模型测试
│   └── test_ui_files.py             # UI 文件加载测试
├── Matlab-Verify/                   # MATLAB 验证脚本
│   └── verify_python_fso.m          # 对标 Python 图表验证
└── 参考文献/                        # 文献资料
    ├── 任务书.md
    ├── 开题报告.md
    ├── 近地无线光通信.md
    └── 参考论文/                    # 参考论文 Markdown
```

## 验证与测试

### 运行单元测试

```bash
pytest
```

各模型均有独立测试文件，位于 `tests/` 目录：

| 测试文件 | 覆盖模块 | 说明 |
|----------|---------|------|
| `test_atmosphere.py` | `atmosphere` | 大气衰减各函数边界值测试 |
| `test_ber.py` | `ber` | BER 公式与调制方式测试 |
| `test_distributions.py` | `distributions` | 概率分布 PDF 正确性测试 |
| `test_geometric.py` | `geometric` | 几何损耗与指向误差测试 |
| `test_link_budget.py` | `link_budget` | 链路预算与 SNR 测试 |
| `test_turbulence.py` | `turbulence` | 湍流闪烁参数测试 |
| `test_scintillation.py` | `scintillation` | 闪烁方差计算测试 |
| `test_constants.py` | `constants` | 物理常量与单位转换测试 |
| `test_models.py` | 全部模型 | 核心模型综合数值验证 |
| `test_ui_files.py` | UI 文件 | `.ui` 文件加载完整性测试 |

### 生成参数验证报告

运行 `fso_platform/utils/validation_report.py` 可生成各模型的 Markdown 格式参数边界验证报告：

```bash
python fso_platform/utils/validation_report.py
```

## 打包与分发

### 安装构建工具

```bash
pip install build pyinstaller
```

### 1. 源码分发 (sdist + wheel)

```bash
python -m build
```

输出：
- `dist/fso_platform-1.0.0.tar.gz` — 源码压缩包
- `dist/fso_platform-1.0.0-py3-none-any.whl` — Python wheel（可直接 pip 安装）

安装 wheel：
```bash
pip install dist/fso_platform-1.0.0-py3-none-any.whl
fso-platform  # 启动程序
```

### 2. macOS 可执行文件 (.app)

```bash
pyinstaller fso_platform_macos.spec --clean --noconfirm
```

输出：`dist/FSOPlatform.app`

### 3. Windows 可执行文件 (.exe)

在 Windows 环境下：
```bash
pyinstaller fso_platform_windows.spec --clean --noconfirm
```

输出：`dist/FSOPlatform/FSOPlatform.exe`

**跨平台构建**: 项目包含 GitHub Actions 工作流 (`.github/workflows/build.yml`)，推送 `v*` 标签时自动构建 Windows 和 macOS 可执行文件并上传为 artifact。

### 统一构建脚本

```bash
python build.py --sdist     # 仅构建 sdist + wheel
python build.py --macos     # 仅构建 macOS .app（macOS 环境）
python build.py --windows   # 仅构建 Windows .exe（Windows 环境）
python build.py --all       # 构建当前平台适用的所有目标
```

## 技术栈

- **GUI 框架**: PyQt5 5.15.11
- **数值计算**: NumPy 2.4.4, SciPy 1.17.1
- **数据可视化**: Matplotlib 3.10.8（嵌入 Qt 后端）
- **打包工具**: PyInstaller 6.20, build 1.4

## 许可证

本项目为学术用途开发，仅供学习与研究使用。

## 联系方式

如有问题或建议，请联系项目开发者。
