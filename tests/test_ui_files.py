#!/usr/bin/env python3
"""
测试所有 .ui 文件能否被 PyQt5 uic 加载
"""

from pathlib import Path
import pytest
from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow


@pytest.fixture(scope="module")
def qapp():
    """创建 QApplication 实例（模块级只创建一次）。"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


UI_DIR = Path(__file__).parent.parent / "fso_platform" / "ui"
UI_FILES = sorted(UI_DIR.glob("*.ui"))


@pytest.mark.parametrize("ui_file", UI_FILES, ids=lambda p: p.name)
def test_ui_file_loads(qapp, ui_file):
    """验证每个 .ui 文件可被 uic.loadUi 正确加载。"""
    if ui_file.name == "main_window.ui":
        widget = QMainWindow()
    else:
        widget = QWidget()

    uic.loadUi(str(ui_file), widget)
    assert widget is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
