# -*- coding: utf-8 -*-
"""
KRONOS X - 股票分析頁面
專業 K 線圖 (candlestick) 搭配成交量、SMA 移動平均線、RSI 技術指標。
優先使用 mplfinance 繪製，若不可用則以 matplotlib 手動繪製 OHLC。
"""

import json
import warnings
import numpy as np
import pandas as pd

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QAbstractSpinBox,
)
from PyQt6.QtCore import Qt

import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from data.database import Database
from ui.theme import COLORS, get_matplotlib_style

# 嘗試匯入 mplfinance
try:
    import mplfinance as mpf
    HAS_MPLFINANCE = True
except ImportError:
    HAS_MPLFINANCE = False


class StockAnalysisPage(QWidget):
    """股票分析頁面 - K 線 + Volume + SMA + RSI"""

    def __init__(self):
        super().__init__()
        self._init_ui()
        self.refresh_tickers()
        self.load_data()

    # ------------------------------------------------------------------
    # UI 初始化
    # ------------------------------------------------------------------

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # ---- 控制列 ----
        ctrl = QHBoxLayout()

        ctrl.addWidget(QLabel("Ticker:"))
        self.ticker_input = QComboBox()
        self.ticker_input.setEditable(True)
        self.ticker_input.setFixedWidth(130)
        ctrl.addWidget(self.ticker_input)

        ctrl.addWidget(QLabel("Interval:"))
        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["1d", "1h", "15m", "5m"])
        self.interval_combo.setFixedWidth(70)
        ctrl.addWidget(self.interval_combo)

        ctrl.addWidget(QLabel("Lookback:"))
        self.lookback_spin = QSpinBox()
        self.lookback_spin.setRange(30, 5000)
        self.lookback_spin.setValue(120)
        self.lookback_spin.setSuffix(" bars")
        self.lookback_spin.setFixedWidth(100)
        self.lookback_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        ctrl.addWidget(self.lookback_spin)

        search_btn = QPushButton("Analyze")
        search_btn.setFixedWidth(90)
        search_btn.clicked.connect(self.load_data)
        ctrl.addWidget(search_btn)

        # 技術指標控制項
        from PyQt6.QtWidgets import QCheckBox
        
        ctrl.addWidget(QLabel("Overlays:"))
        self.sma10_cb = QCheckBox("SMA10")
        self.sma10_cb.setChecked(True)
        self.sma10_cb.stateChanged.connect(self.load_data)
        ctrl.addWidget(self.sma10_cb)

        self.sma50_cb = QCheckBox("SMA50")
        self.sma50_cb.setChecked(True)
        self.sma50_cb.stateChanged.connect(self.load_data)
        ctrl.addWidget(self.sma50_cb)

        self.bb_cb = QCheckBox("BB")
        self.bb_cb.setChecked(False)
        self.bb_cb.stateChanged.connect(self.load_data)
        ctrl.addWidget(self.bb_cb)

        ctrl.addWidget(QLabel("Subplot:"))
        self.sub_combo = QComboBox()
        self.sub_combo.addItems(["RSI", "MACD", "KD", "None"])
        self.sub_combo.setFixedWidth(75)
        self.sub_combo.currentTextChanged.connect(self.load_data)
        ctrl.addWidget(self.sub_combo)

        ctrl.addStretch()
        layout.addLayout(ctrl)

        # ---- Matplotlib 畫布 ----
        plt.rcParams.update(get_matplotlib_style())
        self.figure = Figure(figsize=(10, 7))
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, stretch=1)

    # ------------------------------------------------------------------
    # 事件
    # ------------------------------------------------------------------

    def showEvent(self, event):
        """頁面切換至前景時更新 ticker 清單"""
        super().showEvent(event)
        self.refresh_tickers()

    def refresh_tickers(self):
        current = self.ticker_input.currentText()
        db = Database()
        tickers = db.get_all_tickers()
        self.ticker_input.clear()
        if tickers:
            self.ticker_input.addItems(tickers)
        idx = self.ticker_input.findText(current)
        if idx >= 0:
            self.ticker_input.setCurrentIndex(idx)
        elif current:
            self.ticker_input.setCurrentText(current)

    # ------------------------------------------------------------------
    # 資料載入與繪圖
    # ------------------------------------------------------------------

    def load_data(self):
        ticker = self.ticker_input.currentText().strip().upper()
        if not ticker:
            return

        interval = self.interval_combo.currentText()
        lookback = self.lookback_spin.value()

        db = Database()
        df = db.get_prices(ticker, interval)

        # 取得最新決策動作
        latest_action = ""
        try:
            conn = db._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT action FROM decisions WHERE ticker=? ORDER BY date DESC LIMIT 1",
                (ticker,),
            )
            row = cursor.fetchone()
            if row:
                latest_action = row[0]
            conn.close()
        except Exception:
            pass

        self.figure.clear()

        if df is None or df.empty:
            ax = self.figure.add_subplot(111)
            ax.set_facecolor(COLORS["BG_DARK"])
            ax.text(
                0.5, 0.5, f"No data for {ticker}",
                ha="center", va="center",
                color=COLORS["TEXT_SECONDARY"], fontsize=14,
            )
            self.canvas.draw()
            return

        # 限制資料筆數
        if len(df) > lookback:
            df = df.iloc[-lookback:]

        # 計算 SMA
        df["SMA10"] = df["Close"].rolling(window=10).mean()
        df["SMA50"] = df["Close"].rolling(window=50).mean()

        # 計算 RSI(14)
        df["RSI"] = self._calc_rsi(df["Close"], period=14)

        # 計算布林通道 (20, 2)
        df["BB_Mid"] = df["Close"].rolling(window=20).mean()
        df["BB_Std"] = df["Close"].rolling(window=20).std()
        df["BB_Upper"] = df["BB_Mid"] + 2 * df["BB_Std"]
        df["BB_Lower"] = df["BB_Mid"] - 2 * df["BB_Std"]

        # 計算 MACD (12, 26, 9)
        df["MACD_DIF"], df["MACD_DEA"], df["MACD_Hist"] = self._calc_macd(df["Close"])

        # 計算 KD (9, 3, 3)
        df["KD_K"], df["KD_D"] = self._calc_kd(df)

        # 標題文字
        title_text = f"{ticker} ({interval})"
        if latest_action:
            title_text += f"  |  Latest Decision: {latest_action}"

        if HAS_MPLFINANCE:
            self._plot_with_mplfinance(df, title_text)
        else:
            self._plot_manual(df, title_text)

        self.canvas.draw()

    # ------------------------------------------------------------------
    # 使用 mplfinance 繪製
    # ------------------------------------------------------------------

    def _plot_with_mplfinance(self, df: pd.DataFrame, title: str):
        """使用 mplfinance 繪製專業 K 線圖"""
        # 建立自訂深色風格
        mc = mpf.make_marketcolors(
            up=COLORS["ACCENT_GREEN"],
            down=COLORS["ACCENT_RED"],
            edge={"up": COLORS["ACCENT_GREEN"], "down": COLORS["ACCENT_RED"]},
            wick={"up": COLORS["ACCENT_GREEN"], "down": COLORS["ACCENT_RED"]},
            volume={"up": COLORS["ACCENT_GREEN"], "down": COLORS["ACCENT_RED"]},
        )
        style = mpf.make_mpf_style(
            marketcolors=mc,
            facecolor=COLORS["BG_DARK"],
            figcolor=COLORS["BG_CARD"],
            gridcolor=COLORS["BORDER"],
            gridstyle="--",
            gridaxis="both",
            edgecolor=COLORS["BORDER"],
            rc={
                "axes.labelcolor": COLORS["TEXT_PRIMARY"],
                "xtick.color": COLORS["TEXT_SECONDARY"],
                "ytick.color": COLORS["TEXT_SECONDARY"],
            },
        )

        # 準備附加線條
        add_plots = []

        # 1. 依勾選狀態加入主圖指標 (SMA10, SMA50, BB)
        if self.sma10_cb.isChecked() and df["SMA10"].notna().any():
            add_plots.append(
                mpf.make_addplot(
                    df["SMA10"], panel=0, color=COLORS["ACCENT_BLUE"],
                    width=1.0, linestyle="-",
                )
            )
        if self.sma50_cb.isChecked() and df["SMA50"].notna().any():
            add_plots.append(
                mpf.make_addplot(
                    df["SMA50"], panel=0, color=COLORS["ACCENT_ORANGE"],
                    width=1.0, linestyle="-",
                )
            )
        if self.bb_cb.isChecked() and df["BB_Upper"].notna().any() and df["BB_Lower"].notna().any():
            add_plots.append(
                mpf.make_addplot(
                    df["BB_Upper"], panel=0, color="#20B2AA",
                    width=0.8, linestyle="--",
                )
            )
            add_plots.append(
                mpf.make_addplot(
                    df["BB_Lower"], panel=0, color="#20B2AA",
                    width=0.8, linestyle="--",
                )
            )
            if df["BB_Mid"].notna().any():
                add_plots.append(
                    mpf.make_addplot(
                        df["BB_Mid"], panel=0, color="#20B2AA",
                        width=0.6, linestyle=":",
                    )
                )

        # 2. 依下拉選單決定副圖指標 (RSI, MACD, KD, None)
        sub_type = self.sub_combo.currentText()
        has_sub = False

        if sub_type == "RSI" and df["RSI"].notna().any():
            add_plots.append(
                mpf.make_addplot(
                    df["RSI"], panel=2, color=COLORS["ACCENT_PURPLE"],
                    ylabel="RSI(14)", width=1.0,
                )
            )
            has_sub = True
        elif sub_type == "MACD" and df["MACD_DIF"].notna().any():
            add_plots.append(
                mpf.make_addplot(
                    df["MACD_DIF"], panel=2, color=COLORS["ACCENT_BLUE"],
                    ylabel="MACD", width=1.0,
                )
            )
            add_plots.append(
                mpf.make_addplot(
                    df["MACD_DEA"], panel=2, color=COLORS["ACCENT_ORANGE"],
                    width=1.0,
                )
            )
            hist_colors = ["#2ec4b6" if v >= 0 else "#e71d36" for v in df["MACD_Hist"]]
            add_plots.append(
                mpf.make_addplot(
                    df["MACD_Hist"], type="bar", panel=2, color=hist_colors,
                    width=0.7,
                )
            )
            has_sub = True
        elif sub_type == "KD" and df["KD_K"].notna().any():
            add_plots.append(
                mpf.make_addplot(
                    df["KD_K"], panel=2, color=COLORS["ACCENT_BLUE"],
                    ylabel="KD(9,3,3)", width=1.0,
                )
            )
            add_plots.append(
                mpf.make_addplot(
                    df["KD_D"], panel=2, color=COLORS["ACCENT_ORANGE"],
                    width=1.0,
                )
            )
            has_sub = True

        ratios = (4, 1, 2) if has_sub else (4, 1)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mpf.plot(
                df,
                type="candle",
                style=style,
                title=title,
                volume=True,
                addplot=add_plots if add_plots else None,
                panel_ratios=ratios,
                figsize=(10, 7),
                returnfig=False,
                ax=None,
                # 直接繪製到 self.figure
                fig=self.figure,
            )

        # mplfinance 的 fig 參數並不可靠，改用備用方案:
        # 重新繪製到自己的 figure 上
        try:
            self.figure.clear()
            fig_tmp, axes_tmp = mpf.plot(
                df,
                type="candle",
                style=style,
                title=title,
                volume=True,
                addplot=add_plots if add_plots else None,
                panel_ratios=ratios,
                figsize=(10, 7),
                returnfig=True,
            )
            # 將暫存 figure 的內容複製到 self.figure
            self.figure.clear()
            for tmp_ax in fig_tmp.axes:
                new_ax = self.figure.add_subplot(
                    len(fig_tmp.axes), 1, fig_tmp.axes.index(tmp_ax) + 1
                )
            # 直接使用暫存 figure 替換
            self.figure = fig_tmp
            self.canvas.figure = self.figure
            plt.close(fig_tmp)
        except Exception:
            # 若 mplfinance returnfig 出問題，退回手動繪圖
            self.figure.clear()
            self._plot_manual(df, title)

    # ------------------------------------------------------------------
    # 手動 matplotlib 繪圖 (fallback)
    # ------------------------------------------------------------------

    def _plot_manual(self, df: pd.DataFrame, title: str):
        """不依賴 mplfinance 的手動 K 線繪圖"""
        # 決定是否顯示副圖
        sub_type = self.sub_combo.currentText()
        has_sub = sub_type in ("RSI", "MACD", "KD")

        if has_sub:
            gs = self.figure.add_gridspec(
                3, 1, height_ratios=[4, 1, 2], hspace=0.05,
            )
        else:
            gs = self.figure.add_gridspec(2, 1, height_ratios=[4, 1], hspace=0.05)

        ax_price = self.figure.add_subplot(gs[0])
        ax_vol = self.figure.add_subplot(gs[1], sharex=ax_price)
        ax_sub = self.figure.add_subplot(gs[2], sharex=ax_price) if has_sub else None

        # 設定背景色
        for ax in [ax_price, ax_vol, ax_sub]:
            if ax is not None:
                ax.set_facecolor(COLORS["BG_DARK"])
                ax.tick_params(colors=COLORS["TEXT_SECONDARY"])
                ax.grid(True, color=COLORS["BORDER"], alpha=0.4, linestyle="--")

        # ---- 主圖: 收盤線 + SMA (簡化版 K 線用漲跌色的 bar 表示) ----
        x = np.arange(len(df))
        opens = df["Open"].values
        closes = df["Close"].values
        highs = df["High"].values
        lows = df["Low"].values

        # 漲跌判定
        up = closes >= opens
        down = ~up

        # 繪製 K 線實體 (bar) 與影線 (vlines)
        body_width = 0.6
        ax_price.bar(
            x[up], (closes - opens)[up], body_width,
            bottom=opens[up], color=COLORS["ACCENT_GREEN"], edgecolor=COLORS["ACCENT_GREEN"],
        )
        ax_price.bar(
            x[down], (opens - closes)[down], body_width,
            bottom=closes[down], color=COLORS["ACCENT_RED"], edgecolor=COLORS["ACCENT_RED"],
        )

        # 影線
        ax_price.vlines(
            x[up], lows[up], highs[up],
            color=COLORS["ACCENT_GREEN"], linewidth=0.8,
        )
        ax_price.vlines(
            x[down], lows[down], highs[down],
            color=COLORS["ACCENT_RED"], linewidth=0.8,
        )

        # SMA 10 疊加
        if self.sma10_cb.isChecked() and df["SMA10"].notna().any():
            ax_price.plot(
                x, df["SMA10"].values,
                color=COLORS["ACCENT_BLUE"], linewidth=1.0, label="SMA10",
            )
        # SMA 50 疊加
        if self.sma50_cb.isChecked() and df["SMA50"].notna().any():
            ax_price.plot(
                x, df["SMA50"].values,
                color=COLORS["ACCENT_ORANGE"], linewidth=1.0, label="SMA50",
            )
        # Bollinger Bands 疊加
        if self.bb_cb.isChecked() and df["BB_Upper"].notna().any() and df["BB_Lower"].notna().any():
            ax_price.plot(
                x, df["BB_Upper"].values, color="#20B2AA",
                linewidth=0.8, linestyle="--", label="BB Upper",
            )
            ax_price.plot(
                x, df["BB_Lower"].values, color="#20B2AA",
                linewidth=0.8, linestyle="--", label="BB Lower",
            )
            ax_price.plot(
                x, df["BB_Mid"].values, color="#20B2AA",
                linewidth=0.6, linestyle=":", label="BB Mid",
            )
            ax_price.fill_between(
                x, df["BB_Lower"].values, df["BB_Upper"].values,
                color="#20B2AA", alpha=0.05,
            )

        ax_price.legend(
            loc="upper left", fontsize=9,
            facecolor=COLORS["BG_CARD"], edgecolor=COLORS["BORDER"],
            labelcolor=COLORS["TEXT_PRIMARY"],
        )
        ax_price.set_title(title, color=COLORS["TEXT_PRIMARY"], fontsize=13, pad=8)
        ax_price.set_ylabel("Price", color=COLORS["TEXT_PRIMARY"])
        plt.setp(ax_price.get_xticklabels(), visible=False)

        # ---- 成交量子圖 ----
        volumes = df["Volume"].values.astype(float)
        vol_colors = [
            COLORS["ACCENT_GREEN"] if c >= o else COLORS["ACCENT_RED"]
            for c, o in zip(closes, opens)
        ]
        ax_vol.bar(x, volumes, body_width, color=vol_colors, alpha=0.7)
        ax_vol.set_ylabel("Volume", color=COLORS["TEXT_PRIMARY"], fontsize=9)
        if ax_sub is None:
            self._set_x_labels(ax_vol, df, x)
        else:
            plt.setp(ax_vol.get_xticklabels(), visible=False)

        # ---- 副圖繪製 (RSI, MACD, KD) ----
        if ax_sub is not None:
            if sub_type == "RSI" and df["RSI"].notna().any():
                ax_sub.plot(x, df["RSI"].values, color=COLORS["ACCENT_PURPLE"], linewidth=1.0)
                ax_sub.axhline(70, color=COLORS["ACCENT_RED"], linewidth=0.7, linestyle="--", alpha=0.6)
                ax_sub.axhline(30, color=COLORS["ACCENT_GREEN"], linewidth=0.7, linestyle="--", alpha=0.6)
                ax_sub.fill_between(x, 30, 70, color=COLORS["BORDER"], alpha=0.15)
                ax_sub.set_ylabel("RSI(14)", color=COLORS["TEXT_PRIMARY"], fontsize=9)
                ax_sub.set_ylim(0, 100)
            elif sub_type == "MACD" and df["MACD_DIF"].notna().any():
                ax_sub.plot(x, df["MACD_DIF"].values, color=COLORS["ACCENT_BLUE"], linewidth=1.0, label="DIF")
                ax_sub.plot(x, df["MACD_DEA"].values, color=COLORS["ACCENT_ORANGE"], linewidth=1.0, label="DEA")
                hist = df["MACD_Hist"].values
                hist_colors = [COLORS["ACCENT_GREEN"] if v >= 0 else COLORS["ACCENT_RED"] for v in hist]
                ax_sub.bar(x, hist, width=0.6, color=hist_colors, alpha=0.6, label="Hist")
                ax_sub.legend(
                    loc="upper left", fontsize=8,
                    facecolor=COLORS["BG_CARD"], edgecolor=COLORS["BORDER"],
                    labelcolor=COLORS["TEXT_PRIMARY"],
                )
                ax_sub.set_ylabel("MACD", color=COLORS["TEXT_PRIMARY"], fontsize=9)
            elif sub_type == "KD" and df["KD_K"].notna().any():
                ax_sub.plot(x, df["KD_K"].values, color=COLORS["ACCENT_BLUE"], linewidth=1.0, label="K")
                ax_sub.plot(x, df["KD_D"].values, color=COLORS["ACCENT_ORANGE"], linewidth=1.0, label="D")
                ax_sub.axhline(80, color=COLORS["ACCENT_RED"], linewidth=0.7, linestyle="--", alpha=0.6)
                ax_sub.axhline(20, color=COLORS["ACCENT_GREEN"], linewidth=0.7, linestyle="--", alpha=0.6)
                ax_sub.legend(
                    loc="upper left", fontsize=8,
                    facecolor=COLORS["BG_CARD"], edgecolor=COLORS["BORDER"],
                    labelcolor=COLORS["TEXT_PRIMARY"],
                )
                ax_sub.set_ylabel("KD(9,3,3)", color=COLORS["TEXT_PRIMARY"], fontsize=9)
                ax_sub.set_ylim(0, 100)

            self._set_x_labels(ax_sub, df, x)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            try:
                self.figure.tight_layout(pad=1.0)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """計算 RSI 指標"""
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def _calc_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        """計算 MACD 指標"""
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False).mean()
        hist = (dif - dea) * 2
        return dif, dea, hist

    @staticmethod
    def _calc_kd(df: pd.DataFrame, period: int = 9):
        """計算 KD (9, 3, 3) 指標"""
        low_min = df["Low"].rolling(window=period).min()
        high_max = df["High"].rolling(window=period).max()
        rsv = (df["Close"] - low_min) / (high_max - low_min).replace(0, np.nan) * 100

        k = rsv.copy()
        k.iloc[:period] = 50.0
        for i in range(period, len(df)):
            k.iloc[i] = k.iloc[i-1] * (2.0/3.0) + rsv.iloc[i] * (1.0/3.0)

        d = k.copy()
        d.iloc[:period] = 50.0
        for i in range(period, len(df)):
            d.iloc[i] = d.iloc[i-1] * (2.0/3.0) + k.iloc[i] * (1.0/3.0)

        return k, d

    @staticmethod
    def _set_x_labels(ax, df: pd.DataFrame, x: np.ndarray):
        """在 X 軸上放置日期標籤 (間隔取樣避免密集)"""
        n = len(x)
        step = max(1, n // 8)
        tick_positions = x[::step]
        tick_labels = [
            df.index[i].strftime("%m-%d") if hasattr(df.index[i], "strftime") else str(df.index[i])[:10]
            for i in range(0, n, step)
        ]
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, rotation=30, fontsize=8)
