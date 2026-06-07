import pandas as pd
import numpy as np
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QHBoxLayout,
                               QPushButton, QComboBox, QSpinBox, QCheckBox,
                               QFrame, QGridLayout)
from PyQt6.QtCore import Qt
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from data.database import Database
from kronos.service import KronosService

try:
    from ui.theme import COLORS
except ImportError:
    COLORS = {
        'BG_DARK': '#0d1117', 'BG_CARD': '#161b22', 'TEXT_PRIMARY': '#e6edf3',
        'TEXT_SECONDARY': '#8b949e', 'ACCENT_BLUE': '#58a6ff', 'ACCENT_GREEN': '#3fb950',
        'ACCENT_RED': '#f85149', 'ACCENT_ORANGE': '#d29922', 'ACCENT_PURPLE': '#bc8cff',
        'BORDER': '#30363d'
    }


class KronosXAIPage(QWidget):
    def __init__(self, db_path="data/stock_advisor.db"):
        super().__init__()
        self.db = Database(db_path)
        self.k_service = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Header
        header = QLabel("Kronos XAI - Uncertainty & Temporal Analysis")
        header.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(header)

        # Control Bar
        control_layout = QHBoxLayout()

        self.ticker_input = QComboBox()
        self.ticker_input.setEditable(True)
        self.ticker_input.setFixedWidth(120)
        self.ticker_input.addItems(self.get_available_tickers())

        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["1d", "1h", "15m", "5m"])

        control_layout.addWidget(QLabel("Ticker:"))
        control_layout.addWidget(self.ticker_input)
        control_layout.addWidget(QLabel("Interval:"))
        control_layout.addWidget(self.interval_combo)

        self.lookback_spin = QSpinBox()
        self.lookback_spin.setRange(20, 512)
        self.lookback_spin.setValue(60)
        control_layout.addWidget(QLabel("Lookback:"))
        control_layout.addWidget(self.lookback_spin)

        self.pred_len_spin = QSpinBox()
        self.pred_len_spin.setRange(5, 100)
        self.pred_len_spin.setValue(20)
        control_layout.addWidget(QLabel("Pred Len:"))
        control_layout.addWidget(self.pred_len_spin)

        self.samples_spin = QSpinBox()
        self.samples_spin.setRange(2, 50)
        self.samples_spin.setValue(5)
        control_layout.addWidget(QLabel("Samples:"))
        control_layout.addWidget(self.samples_spin)

        self.analyze_btn = QPushButton("Run XAI Analysis")
        self.analyze_btn.setStyleSheet(
            f"background-color: {COLORS['ACCENT_BLUE']}; color: white; "
            f"font-weight: bold; padding: 6px 12px; border-radius: 4px; border: none;"
        )
        self.analyze_btn.clicked.connect(self.run_analysis)
        control_layout.addWidget(self.analyze_btn)

        # Checkboxes
        self.show_ci_cb = QCheckBox("95% CI")
        self.show_ci_cb.setChecked(True)
        self.show_ci_cb.stateChanged.connect(self.replot)
        control_layout.addWidget(self.show_ci_cb)

        self.show_kw_cb = QCheckBox("Key Window")
        self.show_kw_cb.setChecked(True)
        self.show_kw_cb.stateChanged.connect(self.replot)
        control_layout.addWidget(self.show_kw_cb)

        self.show_fan_cb = QCheckBox("Fan Chart")
        self.show_fan_cb.setChecked(True)
        self.show_fan_cb.stateChanged.connect(self.replot)
        control_layout.addWidget(self.show_fan_cb)

        control_layout.addStretch()
        layout.addLayout(control_layout)

        # Summary Stats Bar (flat, minimal)
        self.stats_frame = QFrame()
        self.stats_frame.setStyleSheet(
            f"background-color: {COLORS['BG_CARD']}; border: 1px solid {COLORS['BORDER']}; "
            f"border-radius: 4px; padding: 6px 12px;"
        )
        stats_layout = QHBoxLayout(self.stats_frame)
        stats_layout.setSpacing(20)
        stats_layout.setContentsMargins(8, 4, 8, 4)

        self.stat_labels = {}
        stat_items = [
            ("mean_return", "Return"),
            ("max_uncertainty", "Uncertainty"),
            ("final_range", "Range"),
            ("up_prob", "Up Prob"),
            ("score_k", "Score"),
        ]
        for key, title in stat_items:
            pair = QHBoxLayout()
            pair.setSpacing(6)

            title_label = QLabel(f"{title}:")
            title_label.setStyleSheet(
                f"font-size: 12px; color: {COLORS['TEXT_SECONDARY']}; background: transparent;"
            )

            val_label = QLabel("--")
            val_label.setStyleSheet(
                f"font-size: 13px; font-weight: 600; color: {COLORS['TEXT_PRIMARY']}; background: transparent;"
            )

            pair.addWidget(title_label)
            pair.addWidget(val_label)
            stats_layout.addLayout(pair)
            self.stat_labels[key] = val_label

        stats_layout.addStretch()
        layout.addWidget(self.stats_frame)

        # Charts - 3 subplots
        self.figure = Figure(figsize=(12, 9))
        self.figure.set_facecolor(COLORS['BG_DARK'])
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, stretch=1)

        self.last_res = None
        self.last_ticker = None
        self.last_interval = None

    def get_available_tickers(self):
        try:
            return self.db.get_all_tickers() or ["2330.TW"]
        except Exception:
            return ["2330.TW"]

    def showEvent(self, event):
        super().showEvent(event)
        current = self.ticker_input.currentText()
        tickers = self.get_available_tickers()
        self.ticker_input.clear()
        self.ticker_input.addItems(tickers)
        idx = self.ticker_input.findText(current)
        if idx >= 0:
            self.ticker_input.setCurrentIndex(idx)
        elif current:
            self.ticker_input.setCurrentText(current)

    def run_analysis(self):
        ticker = self.ticker_input.currentText().strip().upper()
        if not ticker:
            return

        interval = self.interval_combo.currentText()
        lookback = self.lookback_spin.value()
        pred_len = self.pred_len_spin.value()
        samples = self.samples_spin.value()

        if not self.k_service:
            self.k_service = KronosService()

        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("Processing...")
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

        try:
            res = self.k_service.predict_with_uncertainty(
                ticker=ticker,
                interval=interval,
                lookback=lookback,
                pred_len=pred_len,
                n_samples=samples
            )
        except Exception as e:
            print(f"Kronos XAI Error: {e}")
            res = None

        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Run XAI Analysis")

        if not res:
            return

        self.last_res = res
        self.last_ticker = ticker
        self.last_interval = interval
        self.plot_results(res, ticker, interval)

    def replot(self):
        if self.last_res:
            self.plot_results(self.last_res, self.last_ticker, self.last_interval)

    def plot_results(self, res, ticker, interval):
        self.figure.clear()

        raw = res['raw_output']
        y_times = pd.to_datetime(raw['y_timestamps'])
        mean_close = np.array(raw['mean_close'])
        upper = np.array(raw['upper_bound'])
        lower = np.array(raw['lower_bound'])
        std_close = np.array(raw['std_close'])
        key_windows = raw['key_windows']
        all_samples = np.array(raw.get('all_samples', []))

        fg = COLORS['BG_DARK']
        tc = COLORS['TEXT_PRIMARY']
        gc = COLORS['BORDER']

        # -- Subplot 1: Price + CI + Key Windows --
        ax1 = self.figure.add_subplot(3, 1, 1)
        ax1.set_facecolor(fg)

        # Historical data
        df_hist = self.db.get_prices(ticker, interval=interval)
        last_date = pd.Timestamp.now()
        last_close = mean_close[0]

        if df_hist is not None and not df_hist.empty:
            df_hist = df_hist.reset_index()
            df_hist['date'] = pd.to_datetime(df_hist['date']).dt.tz_localize(None)
            df_recent = df_hist.tail(80)
            ax1.plot(df_recent['date'], df_recent['Close'],
                     color=COLORS['ACCENT_BLUE'], linewidth=1.2, label=f"{ticker} Close")
            last_date = df_recent['date'].iloc[-1]
            last_close = df_recent['Close'].iloc[-1]

        plot_dates = [last_date] + list(y_times)
        plot_mean = [last_close] + list(mean_close)
        plot_upper = [last_close] + list(upper)
        plot_lower = [last_close] + list(lower)

        ax1.plot(plot_dates, plot_mean, color=COLORS['ACCENT_ORANGE'],
                 linestyle='--', linewidth=1.5, label='Predicted Mean')

        if self.show_ci_cb.isChecked():
            ax1.fill_between(plot_dates, plot_lower, plot_upper,
                             color=COLORS['ACCENT_ORANGE'], alpha=0.2,
                             label='95% Confidence Interval')

        # Key windows
        if self.show_kw_cb.isChecked() and key_windows:
            td_map = {"1d": 12, "1h": 0.5, "15m": 0.125, "5m": 0.042}
            td = pd.Timedelta(hours=td_map.get(interval, 12))
            for i, kw in enumerate(key_windows):
                kd = pd.to_datetime(kw['date'])
                ax1.axvspan(kd - td, kd + td, color=COLORS['ACCENT_RED'], alpha=0.15,
                            label='Key Window' if i == 0 else "")

        ax1.set_title(f"{ticker} Kronos XAI - Prediction with Confidence Interval",
                      color=tc, fontsize=12, fontweight='bold')
        ax1.set_ylabel("Price", color=tc)
        ax1.legend(fontsize=8, loc='upper left')
        ax1.grid(True, alpha=0.2, color=gc)
        ax1.tick_params(colors=tc)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))

        # -- Subplot 2: Standard Deviation Timeline --
        ax2 = self.figure.add_subplot(3, 1, 2)
        ax2.set_facecolor(fg)

        ax2.fill_between(range(len(std_close)), std_close,
                         color=COLORS['ACCENT_PURPLE'], alpha=0.4)
        ax2.plot(range(len(std_close)), std_close,
                 color=COLORS['ACCENT_PURPLE'], linewidth=1.5)

        # Mark the top-3 uncertainty points
        if key_windows:
            for kw in key_windows:
                kw_std = kw.get('std', 0)
                idx_match = np.argmin(np.abs(std_close - kw_std))
                ax2.scatter(idx_match, std_close[idx_match],
                            color=COLORS['ACCENT_RED'], s=60, zorder=5,
                            edgecolors='white', linewidth=1)

        ax2.set_title("Prediction Uncertainty (Std Dev per Step)",
                       color=tc, fontsize=11, fontweight='bold')
        ax2.set_xlabel("Prediction Step", color=tc)
        ax2.set_ylabel("Std Dev", color=tc)
        ax2.grid(True, alpha=0.2, color=gc)
        ax2.tick_params(colors=tc)

        # -- Subplot 3: Fan Chart (sample paths) --
        ax3 = self.figure.add_subplot(3, 1, 3)
        ax3.set_facecolor(fg)

        if self.show_fan_cb.isChecked() and len(all_samples) > 0:
            # Plot each sample as a thin line
            for i, sample in enumerate(all_samples):
                ax3.plot(range(len(sample)), sample,
                         color=COLORS['ACCENT_BLUE'], alpha=0.3, linewidth=0.8)

            # Overlay mean and bounds
            ax3.plot(range(len(mean_close)), mean_close,
                     color=COLORS['ACCENT_ORANGE'], linewidth=2, label='Mean')
            ax3.fill_between(range(len(mean_close)), lower, upper,
                             color=COLORS['ACCENT_ORANGE'], alpha=0.15)

            # Horizontal line at last actual close
            ax3.axhline(y=last_close, color=COLORS['ACCENT_GREEN'],
                        linestyle=':', alpha=0.6, label=f'Last Close: {last_close:.1f}')
        else:
            ax3.text(0.5, 0.5, "Enable 'Fan Chart' checkbox to view sample paths",
                     ha='center', va='center', color=COLORS['TEXT_SECONDARY'],
                     fontsize=12, transform=ax3.transAxes)

        ax3.set_title("Fan Chart - All Sample Prediction Paths",
                       color=tc, fontsize=11, fontweight='bold')
        ax3.set_xlabel("Prediction Step", color=tc)
        ax3.set_ylabel("Predicted Price", color=tc)
        ax3.legend(fontsize=8, loc='upper left')
        ax3.grid(True, alpha=0.2, color=gc)
        ax3.tick_params(colors=tc)

        self.figure.tight_layout(pad=2.0)
        self.canvas.draw()

        # Update summary stats
        self._update_stats(res, mean_close, std_close, last_close, upper, lower)

    def _update_stats(self, res, mean_close, std_close, last_close, upper, lower):
        """Update the summary statistics cards."""
        # Mean Return
        mean_return = (mean_close[-1] - last_close) / last_close * 100
        color = COLORS['ACCENT_GREEN'] if mean_return >= 0 else COLORS['ACCENT_RED']
        self.stat_labels['mean_return'].setText(f"{mean_return:+.2f}%")
        self.stat_labels['mean_return'].setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {color};"
        )

        # Max Uncertainty
        max_unc = np.max(std_close)
        max_unc_pct = max_unc / last_close * 100
        self.stat_labels['max_uncertainty'].setText(f"{max_unc_pct:.2f}%")

        # Final Price Range
        final_low = lower[-1]
        final_high = upper[-1]
        self.stat_labels['final_range'].setText(f"{final_low:.1f} ~ {final_high:.1f}")

        # Up Probability (from raw output if available)
        raw = res.get('raw_output', {})
        price_change = (mean_close[-1] - last_close) / last_close
        p = 1 / (1 + np.exp(-price_change * 10.0))
        up_color = COLORS['ACCENT_GREEN'] if p > 0.55 else (
            COLORS['ACCENT_RED'] if p < 0.45 else COLORS['ACCENT_ORANGE']
        )
        self.stat_labels['up_prob'].setText(f"{p*100:.1f}%")
        self.stat_labels['up_prob'].setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {up_color};"
        )

        # Score K
        score_k = (p - 0.5) * 200
        sk_color = COLORS['ACCENT_GREEN'] if score_k > 15 else (
            COLORS['ACCENT_RED'] if score_k < -15 else COLORS['ACCENT_ORANGE']
        )
        self.stat_labels['score_k'].setText(f"{score_k:+.1f}")
        self.stat_labels['score_k'].setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {sk_color};"
        )
