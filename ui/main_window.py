# -*- coding: utf-8 -*-
"""
KRONOS X - 主視窗
管理側邊欄導航與頁面堆疊切換，同步各頁面的股票代碼與時間區間設定。
"""

from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QStackedWidget
from ui.sidebar import Sidebar
from ui.pages.dashboard import DashboardPage
from ui.pages.ta_report import TAReportPage
from ui.pages.backtest import BacktestPage
from ui.pages.kronos_xai import KronosXAIPage
from ui.pages.timesfm_xai import TimesFMXAIPage
from ui.pages.decision import DecisionPage
from ui.pages.stock_analysis import StockAnalysisPage
from ui.pages.settings import SettingsPage
from ui.pages.mirofish_sim import MiroFishSimPage
from ui.pages.calibration_page import CalibrationPage
from ui.pages.watchlist import WatchlistPage
from ui.pages.prediction_compare import PredictionComparePage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KRONOS X - AI Trading Platform")
        self.resize(1280, 800)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.stack = QStackedWidget()

        layout.addWidget(self.sidebar)
        layout.addWidget(self.stack)

        # Page order must match sidebar nav button indices
        self.pages = [
            DashboardPage(),            # 0  Overview
            WatchlistPage(),            # 1
            StockAnalysisPage(),        # 2  Analysis
            KronosXAIPage(),            # 3
            TimesFMXAIPage(),           # 4
            PredictionComparePage(),    # 5
            TAReportPage(),             # 6  Decision
            DecisionPage(),             # 7
            MiroFishSimPage(),          # 8
            BacktestPage(),             # 9  Evaluation
            CalibrationPage(),          # 10
            SettingsPage(),             # 11 System
        ]

        for p in self.pages:
            self.stack.addWidget(p)

        self.sidebar.nav.connect(lambda i: self.stack.setCurrentIndex(i))

        self.setup_sync()

    def setup_sync(self):
        """收集具有 ticker_input 與 interval_combo 的頁面，並建立同步連線"""
        self.sync_pages = []
        for p in self.pages:
            if hasattr(p, 'ticker_input') and hasattr(p, 'interval_combo'):
                self.sync_pages.append(p)

        self.is_syncing = False

        for p in self.sync_pages:
            if hasattr(p.ticker_input, 'currentTextChanged'):
                p.ticker_input.currentTextChanged.connect(
                    lambda text, source=p: self.sync_ticker(text, source)
                )
            elif hasattr(p.ticker_input, 'textChanged'):
                p.ticker_input.textChanged.connect(
                    lambda text, source=p: self.sync_ticker(text, source)
                )

            p.interval_combo.currentTextChanged.connect(
                lambda text, source=p: self.sync_interval(text, source)
            )

    def sync_ticker(self, text, source):
        if self.is_syncing:
            return
        self.is_syncing = True
        try:
            for p in self.sync_pages:
                if p is not source:
                    if hasattr(p.ticker_input, 'setCurrentText'):
                        p.ticker_input.blockSignals(True)
                        p.ticker_input.setCurrentText(text)
                        p.ticker_input.blockSignals(False)
                    elif hasattr(p.ticker_input, 'setText'):
                        p.ticker_input.blockSignals(True)
                        p.ticker_input.setText(text)
                        p.ticker_input.blockSignals(False)
        finally:
            self.is_syncing = False

    def sync_interval(self, text, source):
        if self.is_syncing:
            return
        self.is_syncing = True
        try:
            for p in self.sync_pages:
                if p is not source:
                    p.interval_combo.blockSignals(True)
                    p.interval_combo.setCurrentText(text)
                    p.interval_combo.blockSignals(False)
        finally:
            self.is_syncing = False
