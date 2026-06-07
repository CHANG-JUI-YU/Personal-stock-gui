import numpy as np
import pandas as pd
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QHBoxLayout,
                               QPushButton, QComboBox, QGroupBox, QGridLayout)
from PyQt6.QtCore import Qt
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from data.database import Database
from kronos.calibration import CalibrationAnalyzer


# 深色主題配色
DARK_BG = '#1e1e2e'
DARK_SURFACE = '#2d2d3f'
DARK_TEXT = '#cdd6f4'
ACCENT_BLUE = '#89b4fa'
ACCENT_GREEN = '#a6e3a1'
ACCENT_RED = '#f38ba8'
ACCENT_YELLOW = '#f9e2af'
ACCENT_ORANGE = '#fab387'
GRID_COLOR = '#45475a'


class CalibrationPage(QWidget):
    """
    校準分析頁面。
    顯示模型預測機率與實際結果之間的校準程度，
    包含校準圖（支援 Kronos 與 TimesFM 雙模型比較）、
    信賴度直方圖及關鍵指標。
    """

    def __init__(self, db_path="data/stock_advisor.db"):
        super().__init__()
        self.db = Database(db_path)
        self.analyzer = CalibrationAnalyzer(db_path)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        # 標題
        header = QLabel("Model Calibration Analysis")
        header.setStyleSheet(
            f"font-size: 24px; font-weight: bold; color: {DARK_TEXT};"
        )
        layout.addWidget(header)

        # 控制列
        control_layout = QHBoxLayout()

        # Ticker 輸入 (可編輯 QComboBox)
        self.ticker_input = QComboBox()
        self.ticker_input.setEditable(True)
        self.ticker_input.setFixedWidth(140)
        self.ticker_input.addItems(self._get_available_tickers())

        # Interval 選擇
        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["1d", "1h", "15m", "5m"])

        # Bins 數量選擇
        self.bins_combo = QComboBox()
        self.bins_combo.addItems(["5", "10", "15", "20"])
        self.bins_combo.setCurrentText("10")

        # 執行按鈕
        self.run_btn = QPushButton("Run Calibration")
        self.run_btn.setStyleSheet(
            f"background-color: {ACCENT_GREEN}; color: #1e1e2e; "
            f"font-weight: bold; padding: 6px 16px; border-radius: 4px;"
        )
        self.run_btn.clicked.connect(self.run_calibration)

        ticker_label = QLabel("Ticker:")
        ticker_label.setStyleSheet(f"color: {DARK_TEXT};")
        interval_label = QLabel("Interval:")
        interval_label.setStyleSheet(f"color: {DARK_TEXT};")
        bins_label = QLabel("Bins:")
        bins_label.setStyleSheet(f"color: {DARK_TEXT};")

        control_layout.addWidget(ticker_label)
        control_layout.addWidget(self.ticker_input)
        control_layout.addWidget(interval_label)
        control_layout.addWidget(self.interval_combo)
        control_layout.addWidget(bins_label)
        control_layout.addWidget(self.bins_combo)
        control_layout.addWidget(self.run_btn)
        control_layout.addStretch()
        layout.addLayout(control_layout)

        # 指標面板
        metrics_group = QGroupBox("校準評估指標 (Calibration Metrics)")
        metrics_group.setStyleSheet(
            f"QGroupBox {{ font-weight: bold; color: {DARK_TEXT}; "
            f"border: 1px solid {GRID_COLOR}; border-radius: 6px; "
            f"margin-top: 8px; padding-top: 16px; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; left: 12px; }}"
        )
        metrics_layout = QGridLayout()

        self.brier_label = QLabel("Brier 分數: --")
        self.brier_label.setStyleSheet(f"font-size: 14px; color: {DARK_TEXT};")
        self.ece_label = QLabel("期待校準誤差 (ECE): --")
        self.ece_label.setStyleSheet(f"font-size: 14px; color: {DARK_TEXT};")
        self.total_label = QLabel("預測總筆數: --")
        self.total_label.setStyleSheet(f"font-size: 14px; color: {DARK_TEXT};")
        self.quality_label = QLabel("校準品質判定: --")
        self.quality_label.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {DARK_TEXT};"
        )
        # 新增導引提示
        self.tip_label = QLabel("提示：校準分析需要預測日期後已擁有實際價格結果的數據。若僅有最新幾天（如週末）的預測，由於未來價格尚未發生，將無法進行校準分析。")
        self.tip_label.setStyleSheet(f"font-size: 11px; color: {ACCENT_ORANGE};")
        self.tip_label.setWordWrap(True)

        metrics_layout.addWidget(self.brier_label, 0, 0)
        metrics_layout.addWidget(self.ece_label, 0, 1)
        metrics_layout.addWidget(self.total_label, 0, 2)
        metrics_layout.addWidget(self.quality_label, 0, 3)
        metrics_layout.addWidget(self.tip_label, 1, 0, 1, 4)
        metrics_group.setLayout(metrics_layout)
        layout.addWidget(metrics_group)

        # 圖表區域 - 兩張並排（深色主題）
        self.figure = Figure(figsize=(12, 5), facecolor=DARK_BG)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, stretch=1)

        # 初始化雙子圖
        self.ax_cal = self.figure.add_subplot(121)
        self.ax_hist = self.figure.add_subplot(122)
        self._apply_dark_theme_axes(self.ax_cal)
        self._apply_dark_theme_axes(self.ax_hist)
        self._draw_empty_charts()

    def _apply_dark_theme_axes(self, ax):
        """將深色主題套用到 matplotlib axes。"""
        ax.set_facecolor(DARK_SURFACE)
        ax.tick_params(colors=DARK_TEXT, which='both')
        ax.xaxis.label.set_color(DARK_TEXT)
        ax.yaxis.label.set_color(DARK_TEXT)
        ax.title.set_color(DARK_TEXT)
        for spine in ax.spines.values():
            spine.set_color(GRID_COLOR)

    def _get_available_tickers(self):
        """取得資料庫中可用的標的清單。"""
        try:
            tickers = self.db.get_all_tickers()
            return tickers if tickers else ["2330.TW"]
        except Exception:
            return ["2330.TW"]

    def showEvent(self, event):
        """頁面顯示時刷新標的清單。"""
        super().showEvent(event)
        self._refresh_tickers()

    def _refresh_tickers(self):
        """重新載入標的清單。"""
        current = self.ticker_input.currentText()
        tickers = self._get_available_tickers()

        self.ticker_input.blockSignals(True)
        self.ticker_input.clear()
        self.ticker_input.addItems(tickers)

        idx = self.ticker_input.findText(current)
        if idx >= 0:
            self.ticker_input.setCurrentIndex(idx)
        elif current:
            self.ticker_input.setCurrentText(current)
        self.ticker_input.blockSignals(False)

    def run_calibration(self):
        """執行校準分析，收集預測結果並繪製校準圖。"""
        ticker = self.ticker_input.currentText().strip().upper()
        if not ticker:
            return

        interval = self.interval_combo.currentText()
        n_bins = int(self.bins_combo.currentText())

        self.run_btn.setEnabled(False)
        self.run_btn.setText("Analyzing...")

        try:
            # 收集包含 model_type 的預測結果
            all_pred_df = self.analyzer.collect_prediction_outcomes(ticker, interval)

            if all_pred_df.empty:
                self._show_no_data(ticker, interval)
                return

            # 分離 Kronos 與 TimesFM 預測
            kronos_df = all_pred_df[all_pred_df['model_type'] == 'kronos']
            tfm_df = all_pred_df[all_pred_df['model_type'] == 'timesfm']

            # 計算整體校準指標（使用所有預測）
            cal_overall = self.analyzer.compute_calibration(all_pred_df, n_bins)

            # 分別計算各模型校準
            cal_kronos = None
            cal_tfm = None
            if not kronos_df.empty:
                cal_kronos = self.analyzer.compute_calibration(kronos_df, n_bins)
            if not tfm_df.empty:
                cal_tfm = self.analyzer.compute_calibration(tfm_df, n_bins)

            # 更新指標顯示
            self._update_metrics(cal_overall)

            # 繪製圖表（支援雙模型）
            self._plot_calibration(cal_kronos, cal_tfm, cal_overall, ticker, interval)

        except Exception as e:
            self.quality_label.setText(f"Error: {str(e)}")
        finally:
            self.run_btn.setEnabled(True)
            self.run_btn.setText("Run Calibration")

    def _update_metrics(self, cal_result: dict):
        """更新指標面板顯示。"""
        brier = cal_result.get('brier_score')
        ece = cal_result.get('ece')
        total = cal_result.get('total_predictions', 0)

        if brier is not None:
            self.brier_label.setText(f"Brier 分數: {brier:.4f}")
        else:
            self.brier_label.setText("Brier 分數: N/A")

        if ece is not None:
            self.ece_label.setText(f"期待校準誤差 (ECE): {ece:.4f}")
        else:
            self.ece_label.setText("期待校準誤差 (ECE): N/A")

        self.total_label.setText(f"預測總筆數: {total}")

        # 校準品質判定
        if ece is not None:
            if ece < 0.05:
                quality = "極佳 (Excellent)"
                color = ACCENT_GREEN
            elif ece < 0.10:
                quality = "良好 (Good)"
                color = ACCENT_BLUE
            elif ece < 0.20:
                quality = "尚可 (Fair)"
                color = ACCENT_YELLOW
            else:
                quality = "較差 (Poor)"
                color = ACCENT_RED
            self.quality_label.setText(f"校準品質判定: {quality}")
            self.quality_label.setStyleSheet(
                f"font-size: 14px; font-weight: bold; color: {color};"
            )
        else:
            self.quality_label.setText("校準品質判定: --")

    def _plot_calibration(self, cal_kronos: dict, cal_tfm: dict,
                          cal_overall: dict, ticker: str, interval: str):
        """
        繪製校準圖與信賴度直方圖。
        支援同時顯示 Kronos 與 TimesFM 兩條校準曲線。
        """
        self.ax_cal.clear()
        self.ax_hist.clear()
        self._apply_dark_theme_axes(self.ax_cal)
        self._apply_dark_theme_axes(self.ax_hist)

        # === 校準圖 (左) ===
        # 對角線 - 完美校準參考線
        self.ax_cal.plot([0, 1], [0, 1], '--', color=DARK_TEXT, alpha=0.5,
                         label='完美校準參考線', linewidth=1)

        # 繪製 Kronos 校準曲線
        if cal_kronos is not None:
            self._plot_single_calibration_curve(
                self.ax_cal, cal_kronos, ACCENT_BLUE, 'Kronos'
            )

        # 繪製 TimesFM 校準曲線
        if cal_tfm is not None:
            self._plot_single_calibration_curve(
                self.ax_cal, cal_tfm, ACCENT_ORANGE, 'TimesFM'
            )

        # 若兩者皆無，則使用整體資料
        if cal_kronos is None and cal_tfm is None and cal_overall is not None:
            self._plot_single_calibration_curve(
                self.ax_cal, cal_overall, ACCENT_BLUE, 'Model'
            )

        self.ax_cal.set_xlabel('預測上漲機率 (Predicted Probability)')
        self.ax_cal.set_ylabel('實際發生頻率 (Observed Frequency)')
        self.ax_cal.set_title(f'{ticker} ({interval}) - 校準曲線')
        self.ax_cal.set_xlim([0, 1])
        self.ax_cal.set_ylim([0, 1])
        self.ax_cal.legend(loc='lower right', facecolor=DARK_SURFACE,
                           edgecolor=GRID_COLOR, labelcolor=DARK_TEXT)
        self.ax_cal.grid(True, alpha=0.2, color=GRID_COLOR)
        self.ax_cal.set_aspect('equal')

        # === 信賴度直方圖 (右) ===
        bin_centers = cal_overall['bin_centers']
        bin_counts = cal_overall['bin_counts']

        if bin_centers:
            bar_width = 1.0 / len(bin_centers) * 0.8
            colors = [ACCENT_BLUE if c > 0 else GRID_COLOR for c in bin_counts]
            self.ax_hist.bar(bin_centers, bin_counts, width=bar_width,
                             color=colors, edgecolor=DARK_SURFACE, alpha=0.85)

            # 在直方圖上方標註數量
            for c, count in zip(bin_centers, bin_counts):
                if count > 0:
                    self.ax_hist.text(c, count + 0.3, str(count),
                                     ha='center', va='bottom', fontsize=8,
                                     color=DARK_TEXT)

        self.ax_hist.set_xlabel('預測上漲機率 (Predicted Probability)')
        self.ax_hist.set_ylabel('預測次數 (Count)')
        self.ax_hist.set_title(f'{ticker} ({interval}) - 信賴度直方圖')
        self.ax_hist.set_xlim([0, 1])
        self.ax_hist.grid(True, alpha=0.2, color=GRID_COLOR, axis='y')

        self.figure.tight_layout()
        self.canvas.draw()

    def _plot_single_calibration_curve(self, ax, cal_result: dict,
                                       color: str, label: str):
        """繪製單一模型的校準曲線。"""
        bin_centers = cal_result['bin_centers']
        bin_accuracies = cal_result['bin_accuracies']

        valid_centers = []
        valid_accs = []
        for c, a in zip(bin_centers, bin_accuracies):
            if a is not None:
                valid_centers.append(c)
                valid_accs.append(a)

        if valid_centers:
            ax.plot(valid_centers, valid_accs, 'o-', color=color,
                    markersize=7, linewidth=2, label=label)

            # 填充校準誤差區域
            ax.fill_between(valid_centers,
                            valid_centers,
                            valid_accs,
                            alpha=0.1, color=color)

    def _show_no_data(self, ticker: str, interval: str):
        """當沒有足夠資料時顯示提示。"""
        self.ax_cal.clear()
        self.ax_hist.clear()
        self._apply_dark_theme_axes(self.ax_cal)
        self._apply_dark_theme_axes(self.ax_hist)

        self.ax_cal.text(0.5, 0.5,
                         f"此標的無可用的校準數據\n標的: {ticker} ({interval})",
                         ha='center', va='center', fontsize=12,
                         color=DARK_TEXT,
                         transform=self.ax_cal.transAxes)
        self.ax_hist.text(0.5, 0.5,
                          "需要至少 20 天前的歷史預測紀錄\n且有對應的未來價格以供比對",
                          ha='center', va='center', fontsize=12,
                          color=DARK_TEXT,
                          transform=self.ax_hist.transAxes)

        self.brier_label.setText("Brier 分數: N/A")
        self.ece_label.setText("期待校準誤差 (ECE): N/A")
        self.total_label.setText("預測總筆數: 0")
        self.quality_label.setText("校準品質判定: --")
        self.quality_label.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {DARK_TEXT};"
        )

        self.figure.tight_layout()
        self.canvas.draw()

    def _draw_empty_charts(self):
        """繪製初始空白圖表。"""
        self.ax_cal.set_xlabel('預測上漲機率 (Predicted Probability)')
        self.ax_cal.set_ylabel('實際發生頻率 (Observed Frequency)')
        self.ax_cal.set_title('校準曲線 (Calibration Curve)')
        self.ax_cal.plot([0, 1], [0, 1], '--', color=DARK_TEXT, alpha=0.5)
        self.ax_cal.set_xlim([0, 1])
        self.ax_cal.set_ylim([0, 1])
        self.ax_cal.grid(True, alpha=0.2, color=GRID_COLOR)
        self.ax_cal.set_aspect('equal')

        self.ax_hist.set_xlabel('預測上漲機率 (Predicted Probability)')
        self.ax_hist.set_ylabel('預測次數 (Count)')
        self.ax_hist.set_title('信賴度直方圖 (Reliability Histogram)')
        self.ax_hist.set_xlim([0, 1])
        self.ax_hist.grid(True, alpha=0.2, color=GRID_COLOR, axis='y')

        self.figure.tight_layout()
        self.canvas.draw()
