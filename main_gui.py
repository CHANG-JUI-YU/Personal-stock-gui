# -*- coding: utf-8 -*-
"""
KRONOS X Agent - GUI 啟動入口
載入深色主題、matplotlib 風格並啟動主視窗。
"""

import sys
import os
import yfinance as yf  # ensure yfinance is available

from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.theme import get_app_stylesheet, get_matplotlib_style

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def main():
    app = QApplication(sys.argv)

    # 設定應用程式名稱
    app.setApplicationName("KRONOS X")

    # 套用深色主題樣式表
    app.setStyleSheet(get_app_stylesheet())

    # 套用 matplotlib 深色繪圖風格
    try:
        import matplotlib as mpl
        mpl.rcParams.update(get_matplotlib_style())
    except ImportError:
        pass

    window = MainWindow()
    window.setWindowTitle("KRONOS X - AI Trading Platform")
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
