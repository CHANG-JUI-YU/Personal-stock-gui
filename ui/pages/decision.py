# -*- coding: utf-8 -*-
"""
KRONOS X - 決策代理頁面
雷達圖 (Radar Chart) + 儀錶圖 (Gauge Chart) + 歷史決策趨勢折線圖，
搭配證據面板與完整的分析流程控制列。
"""

import json
import warnings
import numpy as np
import pandas as pd

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QDateEdit, QComboBox, QSpinBox, QFrame,
    QAbstractSpinBox, QApplication, QSplitter,
    QDoubleSpinBox
)
from PyQt6.QtCore import Qt, QDate

import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from data.database import Database
from ui.theme import COLORS, get_matplotlib_style


class DecisionPage(QWidget):
    """決策代理頁面 - Radar / Gauge / Trend / Evidence"""

    def __init__(self):
        super().__init__()
        self.db = Database()
        self._init_ui()
        self.refresh_data(None, None)
        self.refresh_tickers()

    # ------------------------------------------------------------------
    # UI 建構
    # ------------------------------------------------------------------

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        # ---- 頁面標題 ----
        title = QLabel("Decision Agent")
        title.setStyleSheet(f"""
            font-size: 20px; font-weight: bold;
            color: {COLORS['TEXT_PRIMARY']};
        """)
        root.addWidget(title)

        # ---- 控制列 ----
        ctrl = QHBoxLayout()
        ctrl.setSpacing(6)

        ctrl.addWidget(self._lbl("Ticker:"))
        self.ticker_input = QComboBox()
        self.ticker_input.setEditable(True)
        self.ticker_input.setFixedWidth(130)
        ctrl.addWidget(self.ticker_input)

        ctrl.addWidget(self._lbl("Interval:"))
        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["1d", "1h", "15m", "5m"])
        self.interval_combo.setFixedWidth(65)
        ctrl.addWidget(self.interval_combo)

        ctrl.addWidget(self._lbl("Date:"))
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        ctrl.addWidget(self.date_input)

        ctrl.addWidget(self._lbl("Lookback:"))
        self.lookback_spin = QSpinBox()
        self.lookback_spin.setRange(30, 1024)
        self.lookback_spin.setValue(252)
        self.lookback_spin.setFixedWidth(70)
        self.lookback_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        ctrl.addWidget(self.lookback_spin)

        ctrl.addWidget(self._lbl("Pred Len:"))
        self.pred_len_spin = QSpinBox()
        self.pred_len_spin.setRange(5, 60)
        self.pred_len_spin.setValue(20)
        self.pred_len_spin.setFixedWidth(60)
        self.pred_len_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        ctrl.addWidget(self.pred_len_spin)
        ctrl.addWidget(self._lbl("W_Kronos:"))
        self.w_k_spin = QDoubleSpinBox()
        self.w_k_spin.setRange(0.0, 1.0)
        self.w_k_spin.setSingleStep(0.05)
        self.w_k_spin.setValue(0.35)
        self.w_k_spin.setFixedWidth(55)
        self.w_k_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        ctrl.addWidget(self.w_k_spin)

        ctrl.addWidget(self._lbl("W_TFM:"))
        self.w_tfm_spin = QDoubleSpinBox()
        self.w_tfm_spin.setRange(0.0, 1.0)
        self.w_tfm_spin.setSingleStep(0.05)
        self.w_tfm_spin.setValue(0.30)
        self.w_tfm_spin.setFixedWidth(55)
        self.w_tfm_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        ctrl.addWidget(self.w_tfm_spin)

        ctrl.addWidget(self._lbl("W_TA:"))
        self.w_ta_spin = QDoubleSpinBox()
        self.w_ta_spin.setRange(0.0, 1.0)
        self.w_ta_spin.setSingleStep(0.05)
        self.w_ta_spin.setValue(0.35)
        self.w_ta_spin.setFixedWidth(55)
        self.w_ta_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        ctrl.addWidget(self.w_ta_spin)


        self.run_btn = QPushButton("Run Analysis")
        self.run_btn.setFixedWidth(120)
        self.run_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['ACCENT_ORANGE']};
                color: white; padding: 6px 14px;
                font-weight: bold; border-radius: 6px; border: none;
            }}
            QPushButton:hover {{ background-color: #b8860b; }}
        """)
        self.run_btn.clicked.connect(self.run_analysis)
        ctrl.addWidget(self.run_btn)
        ctrl.addStretch()

        root.addLayout(ctrl)

        # ---- 狀態列 ----
        self.result_label = QLabel("Click 'Run Analysis' to start.")
        self.result_label.setStyleSheet(f"color: {COLORS['TEXT_SECONDARY']}; font-size: 13px;")
        self.result_label.setWordWrap(True)
        root.addWidget(self.result_label)

        # ---- 圖表與證據分裂面板 ----
        plt.rcParams.update(get_matplotlib_style())

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setStyleSheet(
            f"QSplitter::handle {{ background-color: {COLORS['BORDER']}; height: 2px; }}"
        )

        # 上半部 (三個指標區: Model Scores 40%, Final Score 30%, Risk Environment 30%)
        top_frame = QFrame()
        top_layout = QHBoxLayout(top_frame)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)

        # 1. Model Scores (40% 寬度)
        self.radar_figure = Figure(figsize=(4, 3))
        self.radar_canvas = FigureCanvasQTAgg(self.radar_figure)
        top_layout.addWidget(self.radar_canvas, stretch=4)

        # 2. Final Score (30% 寬度)
        self.gauge_figure = Figure(figsize=(4, 3))
        self.gauge_canvas = FigureCanvasQTAgg(self.gauge_figure)
        top_layout.addWidget(self.gauge_canvas, stretch=3)

        # 3. Risk Environment Panel (30% 寬度)
        self.risk_panel = QFrame()
        self.risk_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['BG_CARD']};
                border: 1px solid {COLORS['BORDER']};
                border-radius: 4px;
            }}
        """)
        risk_layout = QVBoxLayout(self.risk_panel)
        risk_layout.setContentsMargins(12, 10, 12, 10)
        risk_layout.setSpacing(4)

        risk_title = QLabel("RISK ENVIRONMENT")
        risk_title.setStyleSheet(f"""
            font-size: 11px; font-weight: bold; letter-spacing: 1px;
            color: {COLORS['TEXT_SECONDARY']}; border: none; background: transparent;
        """)
        risk_layout.addWidget(risk_title, alignment=Qt.AlignmentFlag.AlignTop)

        self.risk_level_val = QLabel("UNKNOWN")
        self.risk_level_val.setStyleSheet(f"""
            font-size: 24px; font-weight: bold;
            color: {COLORS['TEXT_PRIMARY']}; border: none; background: transparent;
        """)
        risk_layout.addWidget(self.risk_level_val, alignment=Qt.AlignmentFlag.AlignTop)

        self.risk_details = QTextEdit()
        self.risk_details.setReadOnly(True)
        self.risk_details.setStyleSheet(f"""
            background-color: {COLORS['BG_DARK']}; color: {COLORS['TEXT_PRIMARY']};
            border: 1px solid {COLORS['BORDER']}; border-radius: 4px; font-family: Consolas, monospace;
            font-size: 11px;
        """)
        risk_layout.addWidget(self.risk_details)

        top_layout.addWidget(self.risk_panel, stretch=3)

        splitter.addWidget(top_frame)

        # 證據面板 (下半部)
        bottom_frame = QFrame()
        bottom_layout = QVBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(6)

        ev_label = QLabel("Evidence")
        ev_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {COLORS['TEXT_SECONDARY']};")
        bottom_layout.addWidget(ev_label)

        self.evidence_text = QTextEdit()
        self.evidence_text.setReadOnly(True)
        self.evidence_text.setStyleSheet(
            f"background-color: {COLORS['BG_DARK']}; color: {COLORS['TEXT_PRIMARY']}; "
            f"border: 1px solid {COLORS['BORDER']}; border-radius: 4px; font-family: Consolas, monospace;"
        )
        bottom_layout.addWidget(self.evidence_text)

        splitter.addWidget(bottom_frame)

        # 設定初始高度比例
        splitter.setSizes([280, 400])

        root.addWidget(splitter, stretch=1)



    # ------------------------------------------------------------------
    # 事件
    # ------------------------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_tickers()

    def refresh_tickers(self):
        current = self.ticker_input.currentText()
        tickers = self.db.get_all_tickers()
        self.ticker_input.clear()
        if tickers:
            self.ticker_input.addItems(tickers)
        idx = self.ticker_input.findText(current)
        if idx >= 0:
            self.ticker_input.setCurrentIndex(idx)
        elif current:
            self.ticker_input.setCurrentText(current)

    # ------------------------------------------------------------------
    # 分析執行
    # ------------------------------------------------------------------

    def run_analysis(self):
        ticker = self.ticker_input.currentText().strip().upper()
        if not ticker:
            self.result_label.setText("Please enter a ticker to analyze.")
            return

        date_str = self.date_input.date().toString("yyyy-MM-dd")
        interval = self.interval_combo.currentText()
        lookback = self.lookback_spin.value()
        pred_len = self.pred_len_spin.value()

        self.result_label.setText(
            f"Running analysis for {ticker} on {date_str} "
            f"(Interval: {interval}, Lookback: {lookback}, Pred Len: {pred_len})..."
        )
        self.result_label.setStyleSheet(f"color: {COLORS['ACCENT_BLUE']}; font-size: 14px; font-weight: bold;")
        self.run_btn.setEnabled(False)
        QApplication.processEvents()

        try:
            from kronos.service import KronosService
            from kronos.timesfm_service import TimesFMService
            from decision.agent import DecisionAgentV1

            # Step 1: Kronos
            self.result_label.setText(f"Step 1: Running Kronos for {ticker}...")
            QApplication.processEvents()
            k_service = KronosService()
            k_success = k_service.predict(
                ticker, date=date_str, interval=interval,
                lookback=lookback, pred_len=pred_len,
            )
            if not k_success:
                self.result_label.setText("Kronos prediction failed.")
                self.result_label.setStyleSheet(
                    f"color: {COLORS['ACCENT_RED']}; font-size: 14px; font-weight: bold;"
                )
                self.run_btn.setEnabled(True)
                return

            # Step 2: TimesFM
            self.result_label.setText(f"Step 2: Running TimesFM for {ticker}...")
            QApplication.processEvents()
            t_service = TimesFMService()
            t_service.predict(
                ticker, date=date_str, interval=interval,
                lookback=lookback, pred_len=pred_len,
            )

            # Step 3: Decision Agent
            self.result_label.setText("Step 3: Running Decision Agent...")
            QApplication.processEvents()
            w_k = self.w_k_spin.value()
            w_tfm = self.w_tfm_spin.value()
            w_ta = self.w_ta_spin.value()
            agent = DecisionAgentV1()
            res = agent.get_decision(
                ticker, date_str, interval=interval,
                w_kronos=w_k, w_timesfm=w_tfm, w_ta=w_ta
            )

            if res:
                self.refresh_data(ticker, interval)
            else:
                self.result_label.setText("Decision Agent failed.")
                self.result_label.setStyleSheet(
                    f"color: {COLORS['ACCENT_RED']}; font-size: 14px; font-weight: bold;"
                )

        except Exception as e:
            self.result_label.setText(f"Error: {e}")
            self.result_label.setStyleSheet(
                f"color: {COLORS['ACCENT_RED']}; font-size: 14px; font-weight: bold;"
            )
            import traceback
            traceback.print_exc()

        self.run_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # 資料刷新與繪圖
    # ------------------------------------------------------------------

    def refresh_data(self, ticker=None, interval=None):
        if not ticker:
            ticker = self.ticker_input.currentText().strip().upper()
        if not interval:
            interval = self.interval_combo.currentText()

        decisions = self.db.get_decisions(ticker, interval=interval, limit=1)

        if decisions is None or decisions.empty:
            self.result_label.setText("No analysis found. Click 'Run Analysis'.")
            self.result_label.setStyleSheet(f"color: {COLORS['TEXT_SECONDARY']}; font-size: 13px;")
            self.evidence_text.setText("")
            self.risk_level_val.setText("UNKNOWN")
            self.risk_level_val.setStyleSheet(
                f"font-size: 24px; font-weight: bold; color: {COLORS['TEXT_PRIMARY']}; border: none; background: transparent;"
            )
            self.risk_details.setText("")
            self._draw_bar_chart(0, 0, 0)
            self._draw_gauge(0)
            return

        latest = decisions.iloc[0]
        json_data = latest["data"]

        kc = 0.0
        tfmc = 0.0
        tc = 0.0
        final_score = 0.0

        if json_data:
            try:
                data = json.loads(json_data)
                kc = data.get("scores", {}).get("kronos", {}).get("score", 0.0)
                tfmc = data.get("scores", {}).get("timesfm", {}).get("score", 0.0)
                tc = data.get("scores", {}).get("trading_agents", {}).get("score", 0.0)
                final_score = data.get("final_score", 0.0)

                evidence = data.get("evidence", [])
                self.evidence_text.setMarkdown("\n\n".join(evidence))
                self.result_label.setText(f"Analysis Complete for {ticker}")
                self.result_label.setStyleSheet(
                    f"color: {COLORS['ACCENT_GREEN']}; font-size: 14px; font-weight: bold;"
                )

                # 風險環境與旗標更新
                risk_level = data.get("risk_level", "NORMAL").upper()
                risk_flags = data.get("risk_flags", [])

                # 根據 risk_flags 的存在與嚴重程度決定環境風險大字
                has_critical = any(f.get("severity") == "CRITICAL" for f in risk_flags)
                has_warning = any(f.get("severity") == "WARNING" for f in risk_flags)

                if has_critical:
                    env_status = "危險"
                    status_color = COLORS["ACCENT_RED"]
                elif has_warning:
                    env_status = "警告"
                    status_color = COLORS["ACCENT_ORANGE"]
                else:
                    env_status = "正常"
                    status_color = COLORS["ACCENT_GREEN"]

                self.risk_level_val.setText(env_status)
                self.risk_level_val.setStyleSheet(f"""
                    font-size: 24px; font-weight: bold;
                    color: {status_color}; border: none; background: transparent;
                """)

                # 對照字典
                level_map = {
                    "LOW": "低",
                    "MEDIUM": "中",
                    "HIGH": "高",
                    "NORMAL": "正常",
                    "WARNING": "警告",
                    "CRITICAL": "危險",
                    "HIGH_VOLATILITY": "高波動度",
                    "CONSECUTIVE_SIGNALS": "連續同向信號",
                    "HIGH_VIX": "高恐慌指數 (VIX)"
                }

                risk_level_zh = level_map.get(risk_level, risk_level)

                risk_md = []
                risk_md.append(f"**模型不確定性**: {risk_level_zh}")
                risk_md.append("")
                risk_md.append("---")

                if not risk_flags:
                    risk_md.append("[通過] 未觸發任何風險旗標。")
                    risk_md.append("市場波動度與 VIX 恐慌指數均處於正常區間。")
                else:
                    for flag in risk_flags:
                        name = flag.get("name", "UNKNOWN_FLAG")
                        desc = flag.get("description", "")
                        sev = flag.get("severity", "WARNING")
                        
                        name_zh = level_map.get(name, name)
                        sev_zh = level_map.get(sev, sev)
                        
                        risk_md.append(f"* [{name_zh}] ({sev_zh})")
                        risk_md.append(f"  {desc}")
                self.risk_details.setMarkdown("\n".join(risk_md))

            except Exception as e:
                self.evidence_text.setText(f"Error parsing JSON: {e}\n\n{json_data}")
        else:
            self.evidence_text.setText("No JSON evidence found.")

        self._draw_bar_chart(kc, tfmc, tc)
        self._draw_gauge(final_score)

    # ------------------------------------------------------------------
    # Model Scores Comparison Chart (水平橫條圖)
    # ------------------------------------------------------------------

    def _draw_bar_chart(self, kronos: float, timesfm: float, trading_agent: float):
        self.radar_figure.clear()
        ax = self.radar_figure.add_subplot(111)

        labels = ["TradingAgent", "TimesFM", "Kronos"]  # 由下往上畫
        values = [trading_agent, timesfm, kronos]

        # 設定背景
        ax.set_facecolor(COLORS["BG_DARK"])
        self.radar_figure.patch.set_facecolor(COLORS["BG_CARD"])

        # 繪製橫條
        y_pos = np.arange(len(labels))
        bar_colors = [COLORS["ACCENT_GREEN"] if v >= 0 else COLORS["ACCENT_RED"] for v in values]
        
        bars = ax.barh(y_pos, values, color=bar_colors, height=0.45, align='center', alpha=0.8)

        # 在 0 畫一條垂直線
        ax.axvline(0, color=COLORS["BORDER"], linewidth=1, linestyle="-", alpha=0.8)

        # 標記數值
        for bar, val in zip(bars, values):
            width = bar.get_width()
            if val >= 0:
                ax.text(
                    width + 5, bar.get_y() + bar.get_height() / 2.0,
                    f"{val:+.1f}",
                    ha='left', va='center', fontsize=9, fontweight='bold',
                    color=COLORS["ACCENT_GREEN"]
                )
            else:
                ax.text(
                    width - 5, bar.get_y() + bar.get_height() / 2.0,
                    f"{val:+.1f}",
                    ha='right', va='center', fontsize=9, fontweight='bold',
                    color=COLORS["ACCENT_RED"]
                )

        # 調整軸與外觀
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=10, fontweight='bold', color=COLORS["TEXT_PRIMARY"])

        ax.set_xlim(-115, 115)
        ax.set_xticks([-100, -50, 0, 50, 100])
        ax.set_xticklabels(["-100", "-50", "0", "50", "100"], fontsize=8, color=COLORS["TEXT_SECONDARY"])

        # 隱藏外框
        for spine in ["top", "right", "left", "bottom"]:
            ax.spines[spine].set_visible(False)

        ax.grid(axis='x', color=COLORS["BORDER"], alpha=0.3, linestyle="--")
        ax.set_title("Model Scores Comparison", pad=15, fontsize=11, fontweight="bold", color=COLORS["TEXT_PRIMARY"])

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                self.radar_figure.tight_layout(pad=1.0)
            except Exception:
                pass
        self.radar_canvas.draw()

    # ------------------------------------------------------------------
    # Gauge Chart (半圓儀錶圖)
    # ------------------------------------------------------------------

    def _draw_gauge(self, final_score: float):
        self.gauge_figure.clear()
        ax = self.gauge_figure.add_subplot(111)
        ax.set_aspect("equal")
        ax.set_facecolor(COLORS["BG_CARD"])
        self.gauge_figure.patch.set_facecolor(COLORS["BG_CARD"])
        ax.set_xlim(-1.3, 1.3)
        ax.set_ylim(-0.3, 1.3)
        ax.axis("off")

        # 繪製半圓弧: SELL(紅) | HOLD(黃) | BUY(綠)
        # 角度範圍: 0 (左, -100) 到 180 (右, +100)
        # SELL: -100 ~ -15  -> 0 ~ 74.25 度
        # HOLD: -15 ~ +15   -> 74.25 ~ 105.75 度
        # BUY:  +15 ~ +100  -> 105.75 ~ 180 度
        zones = [
            (0, 74.25, COLORS["ACCENT_RED"], 0.4),
            (74.25, 105.75, COLORS["ACCENT_ORANGE"], 0.4),
            (105.75, 180, COLORS["ACCENT_GREEN"], 0.4),
        ]

        for start_deg, end_deg, color, alpha in zones:
            theta1 = np.radians(start_deg)
            theta2 = np.radians(end_deg)
            thetas = np.linspace(theta1, theta2, 50)

            # 外弧
            r_outer = 1.0
            r_inner = 0.7
            xs = np.concatenate([
                r_outer * np.cos(thetas),
                r_inner * np.cos(thetas[::-1]),
            ])
            ys = np.concatenate([
                r_outer * np.sin(thetas),
                r_inner * np.sin(thetas[::-1]),
            ])
            ax.fill(xs, ys, color=color, alpha=alpha)

        # 區域標籤
        for lbl, angle_deg, col in [
            ("SELL", 37, COLORS["ACCENT_RED"]),
            ("HOLD", 90, COLORS["ACCENT_ORANGE"]),
            ("BUY", 143, COLORS["ACCENT_GREEN"]),
        ]:
            rad = np.radians(angle_deg)
            ax.text(
                1.15 * np.cos(rad), 1.15 * np.sin(rad), lbl,
                ha="center", va="center", fontsize=9, fontweight="bold",
                color=col,
            )

        # 刻度
        for val in [-100, -50, -15, 0, 15, 50, 100]:
            angle_deg = (val + 100) / 200 * 180
            rad = np.radians(angle_deg)
            x1, y1 = 1.02 * np.cos(rad), 1.02 * np.sin(rad)
            x2, y2 = 1.08 * np.cos(rad), 1.08 * np.sin(rad)
            ax.plot([x1, x2], [y1, y2], color=COLORS["TEXT_SECONDARY"], linewidth=1)
            ax.text(
                1.15 * np.cos(rad), 1.15 * np.sin(rad) - 0.08,
                str(val), ha="center", va="top",
                fontsize=7, color=COLORS["TEXT_SECONDARY"],
            )

        # 指針
        clamped = max(-100, min(100, final_score))
        needle_deg = (clamped + 100) / 200 * 180
        needle_rad = np.radians(needle_deg)
        needle_len = 0.82
        ax.annotate(
            "",
            xy=(needle_len * np.cos(needle_rad), needle_len * np.sin(needle_rad)),
            xytext=(0, 0),
            arrowprops=dict(
                arrowstyle="-|>",
                color=COLORS["TEXT_PRIMARY"],
                lw=2.5,
            ),
        )
        # 圓心裝飾
        circle = plt.Circle((0, 0), 0.06, color=COLORS["TEXT_PRIMARY"], zorder=5)
        ax.add_patch(circle)

        # 分數顯示
        if final_score > 15:
            score_color = COLORS["ACCENT_GREEN"]
        elif final_score < -15:
            score_color = COLORS["ACCENT_RED"]
        else:
            score_color = COLORS["ACCENT_ORANGE"]

        ax.text(
            0, -0.2, f"{final_score:+.1f}",
            ha="center", va="center",
            fontsize=22, fontweight="bold", color=score_color,
        )
        ax.set_title("Final Score", pad=8, fontsize=11, color=COLORS["TEXT_PRIMARY"])

        self.gauge_canvas.draw()



    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    @staticmethod
    def _lbl(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("background: transparent;")
        return lbl
