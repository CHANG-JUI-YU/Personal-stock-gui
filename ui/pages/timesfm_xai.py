import pandas as pd
import numpy as np
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QHBoxLayout,
                               QPushButton, QComboBox, QSpinBox, QCheckBox,
                               QFrame)
from PyQt6.QtCore import Qt
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from data.database import Database
from kronos.timesfm_service import TimesFMService

try:
    from ui.theme import COLORS
except ImportError:
    COLORS = {
        'BG_DARK': '#0d1117', 'BG_CARD': '#161b22', 'TEXT_PRIMARY': '#e6edf3',
        'TEXT_SECONDARY': '#8b949e', 'ACCENT_BLUE': '#58a6ff', 'ACCENT_GREEN': '#3fb950',
        'ACCENT_RED': '#f85149', 'ACCENT_ORANGE': '#d29922', 'ACCENT_PURPLE': '#bc8cff',
        'BORDER': '#30363d'
    }


class TimesFMXAIPage(QWidget):
    def __init__(self, db_path="data/stock_advisor.db"):
        super().__init__()
        self.db = Database(db_path)
        self.tfm_service = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        header = QLabel("TimesFM XAI - Uncertainty & XReg Covariate Analysis")
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
        self.lookback_spin.setRange(60, 2048)
        self.lookback_spin.setValue(512)
        control_layout.addWidget(QLabel("Lookback:"))
        control_layout.addWidget(self.lookback_spin)

        self.pred_len_spin = QSpinBox()
        self.pred_len_spin.setRange(5, 100)
        self.pred_len_spin.setValue(20)
        control_layout.addWidget(QLabel("Pred Len:"))
        control_layout.addWidget(self.pred_len_spin)

        self.analyze_btn = QPushButton("Run TimesFM Analysis")
        self.analyze_btn.setStyleSheet(
            f"background-color: {COLORS['ACCENT_GREEN']}; color: white; "
            f"font-weight: bold; padding: 6px 12px; border-radius: 4px; border: none;"
        )
        self.analyze_btn.clicked.connect(self.run_analysis)
        control_layout.addWidget(self.analyze_btn)

        self.show_ci_cb = QCheckBox("80% CI")
        self.show_ci_cb.setChecked(True)
        self.show_ci_cb.stateChanged.connect(self.replot)
        control_layout.addWidget(self.show_ci_cb)

        control_layout.addStretch()
        layout.addLayout(control_layout)

        # Summary Stats Bar (flat)
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
            ("up_prob", "Up Prob"),
            ("score_k", "Score"),
            ("uncertainty", "Uncertainty"),
            ("pred_vs_actual", "Pred vs Close"),
            ("model", "Model"),
        ]
        for key, title in stat_items:
            pair = QHBoxLayout()
            pair.setSpacing(6)

            title_label = QLabel(f"{title}:")
            title_label.setStyleSheet(
                f"font-size: 12px; color: {COLORS['TEXT_SECONDARY']}; background: transparent;"
            )

            default = "TimesFM 2.5" if key == "model" else "--"
            val_label = QLabel(default)
            val_label.setStyleSheet(
                f"font-size: 13px; font-weight: 600; color: {COLORS['TEXT_PRIMARY']}; background: transparent;"
            )

            pair.addWidget(title_label)
            pair.addWidget(val_label)
            stats_layout.addLayout(pair)
            self.stat_labels[key] = val_label

        stats_layout.addStretch()

        layout.addWidget(self.stats_frame)

        # Charts - 2 subplots
        self.figure = Figure(figsize=(12, 8))
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

        if not self.tfm_service:
            self.tfm_service = TimesFMService(db_path=self.db.db_path)

        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("Processing...")
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

        try:
            res = self.tfm_service.predict(
                ticker=ticker,
                interval=interval,
                lookback=lookback,
                pred_len=pred_len
            )
        except Exception as e:
            print(f"TimesFM XAI Error: {e}")
            res = None

        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Run TimesFM Analysis")

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
        mean_close = np.array(raw['pred_close'])
        upper = np.array(raw['upper_bound'])
        lower = np.array(raw['lower_bound'])
        last_actual = raw['last_actual_close']

        fg = COLORS['BG_DARK']
        tc = COLORS['TEXT_PRIMARY']
        gc = COLORS['BORDER']

        # -- Subplot 1: Price Prediction with Quantile Band --
        ax1 = self.figure.add_subplot(2, 1, 1)
        ax1.set_facecolor(fg)

        # Historical data
        df_hist = self.db.get_prices(ticker, interval=interval)
        last_date = pd.Timestamp.now()
        last_close = last_actual

        if df_hist is not None and not df_hist.empty:
            df_hist = df_hist.reset_index()
            df_hist['date'] = pd.to_datetime(df_hist['date']).dt.tz_localize(None)
            df_recent = df_hist.tail(80)
            ax1.plot(df_recent['date'], df_recent['Close'],
                     color=COLORS['ACCENT_BLUE'], linewidth=1.2, label=f"{ticker} Close")
            last_date = df_recent['date'].iloc[-1]
            last_close = df_recent['Close'].iloc[-1]

        # Future timestamps
        pred_len = len(mean_close)
        freq_map = {"1d": ("B", 1, "days"), "1h": ("h", 1, "hours"),
                    "15m": ("15min", 15, "minutes"), "5m": ("5min", 5, "minutes")}
        freq_info = freq_map.get(interval, ("B", 1, "days"))

        if interval == "1d":
            y_times = pd.bdate_range(start=last_date + pd.Timedelta(days=1), periods=pred_len)
        else:
            y_times = pd.date_range(
                start=last_date + pd.Timedelta(**{freq_info[2]: freq_info[1]}),
                periods=pred_len, freq=freq_info[0]
            )

        plot_dates = [last_date] + list(y_times)
        plot_mean = [last_close] + list(mean_close)
        plot_upper = [last_close] + list(upper)
        plot_lower = [last_close] + list(lower)

        ax1.plot(plot_dates, plot_mean, color=COLORS['ACCENT_GREEN'],
                 linestyle='--', linewidth=1.5, label='TimesFM Predicted Mean')

        if self.show_ci_cb.isChecked():
            ax1.fill_between(plot_dates, plot_lower, plot_upper,
                             color=COLORS['ACCENT_GREEN'], alpha=0.15,
                             label='80% Quantile Interval')

        # Reference line
        ax1.axhline(y=last_close, color=COLORS['ACCENT_ORANGE'],
                     linestyle=':', alpha=0.5, linewidth=1)

        uncertainty_pct = res.get('uncertainty_pct', 0) * 100
        up_prob = res.get('up_prob', 0) * 100

        ax1.set_title(
            f"{ticker} TimesFM XAI - Up Prob: {up_prob:.1f}%, Uncertainty: {uncertainty_pct:.1f}%",
            color=tc, fontsize=12, fontweight='bold'
        )
        ax1.set_ylabel("Price", color=tc)
        ax1.legend(fontsize=8, loc='upper left')
        ax1.grid(True, alpha=0.2, color=gc)
        ax1.tick_params(colors=tc)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))

        # -- Subplot 2: Prediction Spread (Upper - Lower band width) --
        ax2 = self.figure.add_subplot(2, 1, 2)
        ax2.set_facecolor(fg)

        spread = np.array(upper) - np.array(lower)
        spread_pct = spread / last_close * 100

        ax2.bar(range(len(spread_pct)), spread_pct,
                color=COLORS['ACCENT_PURPLE'], alpha=0.6, edgecolor=COLORS['ACCENT_PURPLE'])
        ax2.axhline(y=np.mean(spread_pct), color=COLORS['ACCENT_ORANGE'],
                     linestyle='--', linewidth=1, label=f'Mean Spread: {np.mean(spread_pct):.2f}%')

        ax2.set_title("Quantile Spread Width (Upper - Lower as % of Price)",
                       color=tc, fontsize=11, fontweight='bold')
        ax2.set_xlabel("Prediction Step", color=tc)
        ax2.set_ylabel("Spread %", color=tc)
        ax2.legend(fontsize=8)
        ax2.grid(True, alpha=0.2, color=gc)
        ax2.tick_params(colors=tc)

        self.figure.tight_layout(pad=2.0)
        self.canvas.draw()

        # Update stats
        self._update_stats(res, mean_close, last_close, upper, lower)

    def _update_stats(self, res, mean_close, last_close, upper, lower):
        """Update summary statistics cards."""
        up_prob = res.get('up_prob', 0.5)
        score_k = res.get('score_k', 0)
        uncertainty = res.get('uncertainty_pct', 0) * 100

        # Up Probability
        up_color = COLORS['ACCENT_GREEN'] if up_prob > 0.55 else (
            COLORS['ACCENT_RED'] if up_prob < 0.45 else COLORS['ACCENT_ORANGE']
        )
        self.stat_labels['up_prob'].setText(f"{up_prob*100:.1f}%")
        self.stat_labels['up_prob'].setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {up_color};"
        )

        # Score K
        sk_color = COLORS['ACCENT_GREEN'] if score_k > 15 else (
            COLORS['ACCENT_RED'] if score_k < -15 else COLORS['ACCENT_ORANGE']
        )
        self.stat_labels['score_k'].setText(f"{score_k:+.1f}")
        self.stat_labels['score_k'].setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {sk_color};"
        )

        # Uncertainty
        unc_color = COLORS['ACCENT_RED'] if uncertainty > 5 else (
            COLORS['ACCENT_ORANGE'] if uncertainty > 2 else COLORS['ACCENT_GREEN']
        )
        self.stat_labels['uncertainty'].setText(f"{uncertainty:.2f}%")
        self.stat_labels['uncertainty'].setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {unc_color};"
        )

        # Pred vs Close
        change_pct = (mean_close[-1] - last_close) / last_close * 100
        change_color = COLORS['ACCENT_GREEN'] if change_pct >= 0 else COLORS['ACCENT_RED']
        self.stat_labels['pred_vs_actual'].setText(f"{change_pct:+.2f}%")
        self.stat_labels['pred_vs_actual'].setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {change_color};"
        )

        # Model info
        model_name = res.get('raw_output', {}).get('model', 'TimesFM 2.5')
        self.stat_labels['model'].setText(model_name)
