# -*- coding: utf-8 -*-
"""
KRONOS X - 回測頁面
支援 SMA 交叉、Kronos Signal、TimesFM Signal、Fusion Signal 四種策略。
顯示 6 張 KPI 卡片、累積報酬主圖、回撤子圖，全部使用深色主題。
"""

import warnings
import numpy as np
import pandas as pd

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QLineEdit, QPushButton, QComboBox, QDoubleSpinBox,
    QAbstractSpinBox, QApplication,
)
from PyQt6.QtCore import Qt

import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from backtest.engine import BacktestEngine, BacktestResult
from ui.theme import COLORS, get_matplotlib_style


# ======================================================================
# KPI 卡片 (同 dashboard 風格)
# ======================================================================

class _BTKPICard(QFrame):
    """回測用 KPI 摘要卡片"""

    def __init__(self, accent_color: str, label_text: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(100)
        self.setMinimumWidth(140)
        self.setObjectName("btkpi")
        self.setStyleSheet(f"""
            QFrame#btkpi {{
                background-color: {COLORS['BG_CARD']};
                border: 1px solid {COLORS['BORDER']};
                border-radius: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 8)
        layout.setSpacing(2)

        # 頂部強調條
        bar = QFrame()
        bar.setFixedHeight(4)
        bar.setStyleSheet(f"background-color: {accent_color}; border: none; border-radius: 2px;")
        layout.addWidget(bar)

        self.value_label = QLabel("--")
        self.value_label.setStyleSheet(f"""
            font-size: 22px; font-weight: bold;
            color: {COLORS['TEXT_PRIMARY']};
            background: transparent;
        """)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.value_label)

        desc = QLabel(label_text)
        desc.setStyleSheet(f"""
            font-size: 10px;
            color: {COLORS['TEXT_SECONDARY']};
            background: transparent;
        """)
        desc.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(desc)

    def set_value(self, text: str):
        self.value_label.setText(text)


# ======================================================================
# BacktestPage
# ======================================================================

class BacktestPage(QWidget):
    def __init__(self):
        super().__init__()
        self.engine = BacktestEngine()
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        # ---- 頁面標題 ----
        title = QLabel("Backtest Performance")
        title.setStyleSheet(f"""
            font-size: 20px; font-weight: bold;
            color: {COLORS['TEXT_PRIMARY']};
        """)
        root.addWidget(title)

        # ---- 控制列 ----
        ctrl_frame = QFrame()
        ctrl_frame.setObjectName("btCtrl")
        ctrl_frame.setStyleSheet(f"""
            QFrame#btCtrl {{
                background-color: {COLORS['BG_CARD']};
                border: 1px solid {COLORS['BORDER']};
                border-radius: 8px;
            }}
        """)
        ctrl = QHBoxLayout(ctrl_frame)
        ctrl.setContentsMargins(12, 8, 12, 8)
        ctrl.setSpacing(8)

        ctrl.addWidget(self._lbl("Ticker:"))
        self.ticker_input = QLineEdit()
        self.ticker_input.setPlaceholderText("e.g. 2330.TW")
        self.ticker_input.setFixedWidth(140)
        ctrl.addWidget(self.ticker_input)

        ctrl.addWidget(self._lbl("Interval:"))
        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["1d", "1h", "15m", "5m"])
        self.interval_combo.setFixedWidth(70)
        ctrl.addWidget(self.interval_combo)

        ctrl.addWidget(self._lbl("Strategy:"))
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            "SMA Crossover",
            "Kronos Signal",
            "TimesFM Signal",
            "Fusion Signal",
        ])
        self.strategy_combo.setFixedWidth(140)
        ctrl.addWidget(self.strategy_combo)

        ctrl.addWidget(self._lbl("Threshold:"))
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0, 100)
        self.threshold_spin.setValue(15.0)
        self.threshold_spin.setSingleStep(1.0)
        self.threshold_spin.setFixedWidth(70)
        self.threshold_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        ctrl.addWidget(self.threshold_spin)

        self.run_btn = QPushButton("Run Backtest")
        self.run_btn.setFixedWidth(120)
        self.run_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['ACCENT_PURPLE']};
                color: white; padding: 6px 14px;
                font-weight: bold; border-radius: 6px; border: none;
            }}
            QPushButton:hover {{ background-color: #a371f7; }}
        """)
        self.run_btn.clicked.connect(self.run_backtest)
        ctrl.addWidget(self.run_btn)
        ctrl.addStretch()

        root.addWidget(ctrl_frame)

        # ---- KPI 卡片列 ----
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(8)

        self.kpi_total = _BTKPICard(COLORS["ACCENT_GREEN"], "Total Return")
        self.kpi_market = _BTKPICard(COLORS["ACCENT_BLUE"], "Market Return")
        self.kpi_drawdown = _BTKPICard(COLORS["ACCENT_RED"], "Max Drawdown")
        self.kpi_sharpe = _BTKPICard(COLORS["ACCENT_ORANGE"], "Sharpe Ratio")
        self.kpi_winrate = _BTKPICard(COLORS["ACCENT_PURPLE"], "Win Rate")
        self.kpi_pf = _BTKPICard(COLORS["ACCENT_BLUE"], "Profit Factor")

        for card in [
            self.kpi_total, self.kpi_market, self.kpi_drawdown,
            self.kpi_sharpe, self.kpi_winrate, self.kpi_pf,
        ]:
            kpi_row.addWidget(card, stretch=1)

        root.addLayout(kpi_row)

        # ---- 狀態標籤 ----
        self.status_label = QLabel("Run a backtest to see results.")
        self.status_label.setStyleSheet(f"color: {COLORS['TEXT_SECONDARY']}; font-size: 12px;")
        root.addWidget(self.status_label)

        # ---- Matplotlib 圖表 ----
        plt.rcParams.update(get_matplotlib_style())
        self.figure = Figure(figsize=(10, 5))
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        root.addWidget(self.toolbar)
        root.addWidget(self.canvas, stretch=1)

    # ------------------------------------------------------------------
    # 回測執行
    # ------------------------------------------------------------------

    def run_backtest(self):
        ticker = self.ticker_input.text().strip().upper()
        if not ticker:
            self.status_label.setText("Please enter a ticker.")
            self.status_label.setStyleSheet(f"color: {COLORS['ACCENT_ORANGE']};")
            return

        interval = self.interval_combo.currentText()
        strategy = self.strategy_combo.currentText()
        threshold = self.threshold_spin.value()

        self.status_label.setText(f"Running {strategy} backtest for {ticker}...")
        self.status_label.setStyleSheet(f"color: {COLORS['ACCENT_BLUE']};")
        self.run_btn.setEnabled(False)
        QApplication.processEvents()

        try:
            result = None

            if strategy == "SMA Crossover":
                result = self.engine.run_sma_backtest(ticker, interval=interval)
            elif strategy == "Kronos Signal":
                result = self.engine.run_signal_backtest(
                    ticker, interval=interval,
                    signal_source="kronos", threshold=threshold,
                )
            elif strategy == "TimesFM Signal":
                result = self.engine.run_signal_backtest(
                    ticker, interval=interval,
                    signal_source="timesfm", threshold=threshold,
                )
            elif strategy == "Fusion Signal":
                result = self.engine.run_signal_backtest(
                    ticker, interval=interval,
                    signal_source="fusion", threshold=threshold,
                )

            if result is None:
                self.status_label.setText("Not enough data to run backtest.")
                self.status_label.setStyleSheet(f"color: {COLORS['ACCENT_RED']};")
                self._clear_charts()
                self._clear_kpi()
            else:
                self._update_kpi(result)
                self._draw_charts(result)
                if result.total_trades == 0 and strategy != "SMA Crossover":
                    self.status_label.setText(
                        f"Backtest complete: {result.strategy_name} | 0 trades. "
                        "提示：此策略依賴歷史預測數據。請確保您曾在此週期區間對該股票執行過預測/決策分析以累積訊號數據。"
                    )
                    self.status_label.setStyleSheet(f"color: {COLORS['ACCENT_ORANGE']};")
                else:
                    self.status_label.setText(
                        f"Backtest complete: {result.strategy_name} | "
                        f"{result.total_trades} trades"
                    )
                    self.status_label.setStyleSheet(f"color: {COLORS['ACCENT_GREEN']};")

        except Exception as e:
            self.status_label.setText(f"Error: {e}")
            self.status_label.setStyleSheet(f"color: {COLORS['ACCENT_RED']};")
            import traceback
            traceback.print_exc()

        self.run_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # KPI 更新
    # ------------------------------------------------------------------

    def _update_kpi(self, r: BacktestResult):
        self.kpi_total.set_value(f"{r.total_return:+.2f}%")
        self.kpi_market.set_value(f"{r.market_return:+.2f}%")
        self.kpi_drawdown.set_value(f"{r.max_drawdown:.2f}%")
        self.kpi_sharpe.set_value(f"{r.sharpe_ratio:.2f}")

        wr_text = f"{r.win_rate:.1f}%"
        self.kpi_winrate.set_value(wr_text)

        pf_text = (
            f"{r.profit_factor:.2f}"
            if r.profit_factor != float("inf") else "Inf"
        )
        self.kpi_pf.set_value(pf_text)

    def _clear_kpi(self):
        for card in [
            self.kpi_total, self.kpi_market, self.kpi_drawdown,
            self.kpi_sharpe, self.kpi_winrate, self.kpi_pf,
        ]:
            card.set_value("--")

    # ------------------------------------------------------------------
    # 繪圖
    # ------------------------------------------------------------------

    def _draw_charts(self, r: BacktestResult):
        self.figure.clear()

        df = r.prices_df
        if df is None or df.empty:
            self._clear_charts()
            return

        gs = self.figure.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.08)
        ax_main = self.figure.add_subplot(gs[0])
        ax_dd = self.figure.add_subplot(gs[1], sharex=ax_main)

        for ax in [ax_main, ax_dd]:
            ax.set_facecolor(COLORS["BG_DARK"])
            ax.tick_params(colors=COLORS["TEXT_SECONDARY"])
            ax.grid(True, color=COLORS["BORDER"], alpha=0.3, linestyle="--")

        # ---- 累積報酬主圖 ----
        ax_main.plot(
            df.index, df["Cum_Market"],
            label="Market (Buy & Hold)",
            color=COLORS["TEXT_SECONDARY"], linewidth=1.2, alpha=0.8,
        )
        ax_main.plot(
            df.index, df["Cum_Strategy"],
            label=f"Strategy: {r.strategy_name}",
            color=COLORS["ACCENT_BLUE"], linewidth=1.5,
        )
        ax_main.axhline(1.0, color=COLORS["BORDER"], linewidth=0.7, linestyle="-", alpha=0.4)
        ax_main.set_ylabel("Cumulative Return", fontsize=10, color=COLORS["TEXT_PRIMARY"])
        ax_main.set_title(
            f"Backtest: {r.ticker} - {r.strategy_name}",
            fontsize=12, color=COLORS["TEXT_PRIMARY"], pad=8,
        )
        ax_main.legend(
            loc="upper left", fontsize=9,
            facecolor=COLORS["BG_CARD"], edgecolor=COLORS["BORDER"],
            labelcolor=COLORS["TEXT_PRIMARY"],
        )
        plt.setp(ax_main.get_xticklabels(), visible=False)

        # ---- 回撤子圖 ----
        if "Drawdown" in df.columns:
            ax_dd.fill_between(
                df.index, df["Drawdown"] * 100, 0,
                color=COLORS["ACCENT_RED"], alpha=0.35,
            )
            ax_dd.plot(
                df.index, df["Drawdown"] * 100,
                color=COLORS["ACCENT_RED"], linewidth=0.8,
            )
        ax_dd.set_ylabel("Drawdown %", fontsize=9, color=COLORS["TEXT_PRIMARY"])
        ax_dd.set_xlabel("Date", fontsize=9, color=COLORS["TEXT_PRIMARY"])

        # X 軸日期格式
        self.figure.autofmt_xdate(rotation=25)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                self.figure.tight_layout(pad=1.0)
            except Exception:
                pass

        self.canvas.draw()

    def _clear_charts(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor(COLORS["BG_DARK"])
        ax.text(
            0.5, 0.5, "No backtest data",
            ha="center", va="center",
            color=COLORS["TEXT_SECONDARY"], fontsize=13,
        )
        self.canvas.draw()

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    @staticmethod
    def _lbl(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("background: transparent;")
        return lbl
