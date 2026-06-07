# -*- coding: utf-8 -*-
"""
Prediction Compare - Kronos vs TimesFM side-by-side enlarged prediction view.
"""

import json
import numpy as np
import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QFrame, QSplitter
)
from PyQt6.QtCore import Qt
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from data.database import Database

try:
    from ui.theme import COLORS
except ImportError:
    COLORS = {
        'BG_DARK': '#0f1318', 'BG_CARD': '#181d24', 'TEXT_PRIMARY': '#d1d5db',
        'TEXT_SECONDARY': '#6b7280', 'ACCENT_BLUE': '#6b8aaf', 'ACCENT_GREEN': '#5a9e6f',
        'ACCENT_RED': '#c25550', 'ACCENT_ORANGE': '#b8943e', 'BORDER': '#2a3038',
    }


class _PredictionPanel(QFrame):
    """Single model prediction chart panel."""

    def __init__(self, model_name: str, accent_color: str, parent=None):
        super().__init__(parent)
        self.model_name = model_name
        self.accent_color = accent_color
        self.setStyleSheet(
            f"background-color: {COLORS['BG_CARD']}; "
            f"border: 1px solid {COLORS['BORDER']}; border-radius: 4px;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 4)
        layout.setSpacing(4)

        # Header with stats
        header_layout = QHBoxLayout()
        self.title_label = QLabel(model_name)
        self.title_label.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {COLORS['TEXT_PRIMARY']}; "
            f"background: transparent; border: none;"
        )
        header_layout.addWidget(self.title_label)

        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet(
            f"font-size: 12px; color: {COLORS['TEXT_SECONDARY']}; "
            f"background: transparent; border: none;"
        )
        header_layout.addStretch()
        header_layout.addWidget(self.stats_label)
        layout.addLayout(header_layout)

        # Chart
        self.figure = Figure(figsize=(8, 5))
        self.figure.set_facecolor(COLORS['BG_DARK'])
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.toolbar.setStyleSheet("border: none;")
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, stretch=1)

    def plot_prediction(self, db, ticker, interval, pred_data, pred_type):
        """Render the prediction chart.

        Args:
            db: Database instance
            ticker: stock ticker
            interval: data interval
            pred_data: prediction dict from DB (parsed raw_output)
            pred_type: 'kronos' or 'timesfm'
        """
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor(COLORS['BG_DARK'])

        fg = COLORS['BG_DARK']
        tc = COLORS['TEXT_PRIMARY']
        gc = COLORS['BORDER']

        # Load historical prices
        df_hist = db.get_prices(ticker, interval=interval)
        last_date = pd.Timestamp.now()
        last_close = 0

        if df_hist is not None and not df_hist.empty:
            df_hist = df_hist.reset_index()
            df_hist['date'] = pd.to_datetime(df_hist['date']).dt.tz_localize(None)
            df_recent = df_hist.tail(60)
            ax.plot(
                df_recent['date'], df_recent['Close'],
                color=COLORS['TEXT_SECONDARY'], linewidth=1, alpha=0.8,
                label='Historical'
            )
            last_date = df_recent['date'].iloc[-1]
            last_close = float(df_recent['Close'].iloc[-1])

        if not pred_data:
            ax.text(
                0.5, 0.5, f"No {self.model_name} prediction available",
                ha='center', va='center', color=COLORS['TEXT_SECONDARY'],
                fontsize=13, transform=ax.transAxes
            )
            self.stats_label.setText("")
            self.canvas.draw()
            return

        raw = pred_data.get('raw_output', {})

        # Extract prediction arrays based on model type
        if pred_type == 'kronos':
            mean_close = np.array(raw.get('mean_close', raw.get('pred_close', [])))
            upper = np.array(raw.get('upper_bound', []))
            lower = np.array(raw.get('lower_bound', []))
            ci_label = '95% CI'
        else:
            mean_close = np.array(raw.get('pred_close', []))
            upper = np.array(raw.get('upper_bound', []))
            lower = np.array(raw.get('lower_bound', []))
            ci_label = '80% Quantile'

        if len(mean_close) == 0:
            ax.text(
                0.5, 0.5, f"No prediction data in raw_output",
                ha='center', va='center', color=COLORS['TEXT_SECONDARY'],
                fontsize=13, transform=ax.transAxes
            )
            self.canvas.draw()
            return

        pred_len = len(mean_close)

        # Generate future timestamps
        if interval == "1d":
            y_times = pd.bdate_range(
                start=last_date + pd.Timedelta(days=1), periods=pred_len
            )
        elif interval == "1h":
            y_times = pd.date_range(
                start=last_date + pd.Timedelta(hours=1), periods=pred_len, freq='h'
            )
        elif interval == "15m":
            y_times = pd.date_range(
                start=last_date + pd.Timedelta(minutes=15), periods=pred_len, freq='15min'
            )
        else:
            y_times = pd.date_range(
                start=last_date + pd.Timedelta(minutes=5), periods=pred_len, freq='5min'
            )

        # Connect historical to prediction
        plot_dates = [last_date] + list(y_times)
        plot_mean = [last_close] + list(mean_close)

        # Plot prediction line
        ax.plot(
            plot_dates, plot_mean,
            color=self.accent_color, linewidth=1.8, linestyle='--',
            label=f'{self.model_name} Prediction'
        )

        # Plot CI band
        if len(upper) > 0 and len(lower) > 0:
            plot_upper = [last_close] + list(upper)
            plot_lower = [last_close] + list(lower)
            ax.fill_between(
                plot_dates, plot_lower, plot_upper,
                color=self.accent_color, alpha=0.12, label=ci_label
            )

        # Reference line at last close
        ax.axhline(
            y=last_close, color=COLORS['BORDER'],
            linestyle=':', alpha=0.6, linewidth=0.8
        )

        # Styling
        ax.set_title(
            f"{ticker} - {self.model_name} ({interval})",
            color=tc, fontsize=13, fontweight='bold', pad=10
        )
        ax.set_xlabel("", color=tc)
        ax.set_ylabel("Price", color=tc, fontsize=11)
        ax.legend(fontsize=9, loc='upper left')
        ax.grid(True, alpha=0.15, color=gc)
        ax.tick_params(colors=tc, labelsize=10)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))

        self.figure.autofmt_xdate()
        self.figure.tight_layout(pad=1.5)
        self.canvas.draw()

        # Update stats
        up_prob = pred_data.get('up_prob', 0.5)
        score_k = pred_data.get('score_k', 0)
        change_pct = (mean_close[-1] - last_close) / last_close * 100 if last_close > 0 else 0
        self.stats_label.setText(
            f"Up: {up_prob*100:.1f}%  |  Score: {score_k:+.1f}  |  Change: {change_pct:+.2f}%"
        )

    def clear_chart(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor(COLORS['BG_DARK'])
        ax.text(
            0.5, 0.5, f"Run analysis to view {self.model_name} prediction",
            ha='center', va='center', color=COLORS['TEXT_SECONDARY'],
            fontsize=12, transform=ax.transAxes
        )
        self.canvas.draw()
        self.stats_label.setText("")


class PredictionComparePage(QWidget):
    def __init__(self, db_path="data/stock_advisor.db"):
        super().__init__()
        self.db = Database(db_path)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Control bar
        control = QHBoxLayout()
        control.setSpacing(10)

        self.ticker_input = QComboBox()
        self.ticker_input.setEditable(True)
        self.ticker_input.setFixedWidth(120)
        self.ticker_input.addItems(self._get_tickers())

        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["1d", "1h", "15m", "5m"])

        self.load_btn = QPushButton("Load Predictions")
        self.load_btn.setFixedWidth(140)
        self.load_btn.clicked.connect(self._load_predictions)

        control.addWidget(QLabel("Ticker:"))
        control.addWidget(self.ticker_input)
        control.addWidget(QLabel("Interval:"))
        control.addWidget(self.interval_combo)
        control.addWidget(self.load_btn)
        control.addStretch()

        layout.addLayout(control)

        # Two panels side by side via QSplitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(
            f"QSplitter::handle {{ background-color: {COLORS['BORDER']}; width: 2px; }}"
        )

        self.kronos_panel = _PredictionPanel("Kronos", COLORS['ACCENT_BLUE'])
        self.timesfm_panel = _PredictionPanel("TimesFM", COLORS['ACCENT_GREEN'])

        splitter.addWidget(self.kronos_panel)
        splitter.addWidget(self.timesfm_panel)
        splitter.setSizes([500, 500])

        layout.addWidget(splitter, stretch=1)

        # Initial state
        self.kronos_panel.clear_chart()
        self.timesfm_panel.clear_chart()

    def _get_tickers(self):
        try:
            return self.db.get_all_tickers() or ["2330.TW"]
        except Exception:
            return ["2330.TW"]

    def showEvent(self, event):
        super().showEvent(event)
        current = self.ticker_input.currentText()
        tickers = self._get_tickers()
        self.ticker_input.blockSignals(True)
        self.ticker_input.clear()
        self.ticker_input.addItems(tickers)
        idx = self.ticker_input.findText(current)
        if idx >= 0:
            self.ticker_input.setCurrentIndex(idx)
        elif current:
            self.ticker_input.setCurrentText(current)
        self.ticker_input.blockSignals(False)

    def _load_predictions(self):
        """Load latest Kronos and TimesFM predictions from DB and render."""
        ticker = self.ticker_input.currentText().strip().upper()
        if not ticker:
            return
        interval = self.interval_combo.currentText()

        # Kronos prediction
        kronos_pred = self.db.get_latest_prediction(ticker, interval)
        if kronos_pred:
            raw_str = kronos_pred.get('raw_output', '{}')
            if isinstance(raw_str, str):
                try:
                    kronos_pred['raw_output'] = json.loads(raw_str)
                except (json.JSONDecodeError, TypeError):
                    kronos_pred['raw_output'] = {}
            self.kronos_panel.plot_prediction(
                self.db, ticker, interval, kronos_pred, 'kronos'
            )
        else:
            self.kronos_panel.clear_chart()

        # TimesFM prediction
        tfm_interval = interval + "_tfm"
        tfm_pred = self.db.get_latest_prediction(ticker, tfm_interval)
        if tfm_pred:
            raw_str = tfm_pred.get('raw_output', '{}')
            if isinstance(raw_str, str):
                try:
                    tfm_pred['raw_output'] = json.loads(raw_str)
                except (json.JSONDecodeError, TypeError):
                    tfm_pred['raw_output'] = {}
            self.timesfm_panel.plot_prediction(
                self.db, ticker, interval, tfm_pred, 'timesfm'
            )
        else:
            self.timesfm_panel.clear_chart()
