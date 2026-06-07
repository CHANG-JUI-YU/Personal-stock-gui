# -*- coding: utf-8 -*-
"""
KRONOS X - 儀表板頁面
KPI 摘要卡片 + 資料庫存貨表格 + 最近 AI 決策表格，
搭配資料擷取控制列、刪除功能以及深色主題配色。
"""

import json
import re

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QPushButton, QDateEdit, QComboBox,
    QApplication, QMessageBox, QScrollArea,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QBrush, QFont

from data.database import Database
from data.collector import DataCollector
from ui.theme import COLORS


# ======================================================================
# KPI 卡片元件
# ======================================================================

class _KPICard(QFrame):
    """KPI summary card."""

    def __init__(self, accent_color: str, label_text: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        self.setMinimumWidth(160)
        self.setStyleSheet(f"""
            QFrame#kpicard {{
                background-color: {COLORS['BG_CARD']};
                border: 1px solid {COLORS['BORDER']};
                border-radius: 4px;
            }}
        """)
        self.setObjectName("kpicard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        # Label first (small, above value)
        desc = QLabel(label_text.upper())
        desc.setStyleSheet(f"""
            font-size: 10px; letter-spacing: 1px;
            color: {COLORS['TEXT_SECONDARY']};
            background: transparent;
        """)
        desc.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(desc)

        # Value
        self.value_label = QLabel("--")
        self.value_label.setStyleSheet(f"""
            font-size: 20px; font-weight: 600;
            color: {COLORS['TEXT_PRIMARY']};
            background: transparent;
        """)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.value_label)

    def set_value(self, text: str):
        self.value_label.setText(text)


# ======================================================================
# Dashboard 頁面
# ======================================================================

class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()
        self.refresh_data()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_data()

    # ------------------------------------------------------------------
    # UI 建構
    # ------------------------------------------------------------------

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(12)

        # ---------- 頂部: KPI 卡片列 ----------
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)

        self.card_tracked = _KPICard(COLORS["ACCENT_BLUE"], "Tracked Stocks")
        self.card_updated = _KPICard(COLORS["ACCENT_PURPLE"], "Last Updated")

        for card in [self.card_tracked, self.card_updated]:
            kpi_row.addWidget(card, stretch=1)
        kpi_row.addStretch(2)

        root.addLayout(kpi_row)

        # ---------- 中段: 資料擷取控制列 ----------
        fetch_frame = QFrame()
        fetch_frame.setObjectName("fetchFrame")
        fetch_frame.setStyleSheet(f"""
            QFrame#fetchFrame {{
                background-color: {COLORS['BG_CARD']};
                border: 1px solid {COLORS['BORDER']};
                border-radius: 8px;
            }}
        """)
        fetch_layout = QHBoxLayout(fetch_frame)
        fetch_layout.setContentsMargins(12, 8, 12, 8)
        fetch_layout.setSpacing(8)

        self.ticker_input = QLineEdit()
        self.ticker_input.setPlaceholderText("Ticker (e.g. 2330.TW)")
        self.ticker_input.setFixedWidth(160)

        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["1d", "1h", "15m", "5m"])
        self.interval_combo.setFixedWidth(70)

        self.start_date_input = QDateEdit()
        self.start_date_input.setCalendarPopup(True)
        self.start_date_input.setDate(QDate.currentDate().addDays(-365))

        self.end_date_input = QDateEdit()
        self.end_date_input.setCalendarPopup(True)
        self.end_date_input.setDate(QDate.currentDate())

        self.fetch_btn = QPushButton("Fetch Data")
        self.fetch_btn.setFixedWidth(100)
        self.fetch_btn.clicked.connect(self.fetch_data)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {COLORS['TEXT_SECONDARY']}; background: transparent;")

        for w, lbl in [
            (self.ticker_input, "Ticker:"),
            (self.interval_combo, "Interval:"),
            (self.start_date_input, "Start:"),
            (self.end_date_input, "End:"),
        ]:
            _l = QLabel(lbl)
            _l.setStyleSheet("background: transparent;")
            fetch_layout.addWidget(_l)
            fetch_layout.addWidget(w)

        fetch_layout.addWidget(self.fetch_btn)
        fetch_layout.addWidget(self.status_label)
        fetch_layout.addStretch()
        root.addWidget(fetch_frame)

        # ---------- 資料庫存貨表格 ----------
        data_header = self._make_section_header(
            "Data Inventory", "delete_data"
        )
        root.addLayout(data_header)

        self.data_table = QTableWidget()
        self.data_table.setColumnCount(5)
        self.data_table.setHorizontalHeaderLabels(
            ["Ticker", "Interval", "First Date", "Last Date", "Total Rows"]
        )
        self.data_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.data_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.data_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.data_table.setAlternatingRowColors(True)
        root.addWidget(self.data_table, stretch=1)

        # ---------- 最近 AI 決策表格 ----------
        dec_header = self._make_section_header(
            "Recent AI Decisions", "delete_decision"
        )
        root.addLayout(dec_header)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Decision Date", "Ticker", "Interval", "Final Score", "Weights (K/TFM/TA)", "Action"]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        root.addWidget(self.table, stretch=1)

    # ------------------------------------------------------------------
    # 小元件工廠
    # ------------------------------------------------------------------

    def _make_section_header(self, title_text: str, delete_id: str) -> QHBoxLayout:
        """建立區段標題 + 刪除按鈕"""
        row = QHBoxLayout()
        lbl = QLabel(title_text)
        lbl.setStyleSheet(f"""
            font-size: 15px; font-weight: bold;
            color: {COLORS['TEXT_PRIMARY']};
        """)

        btn = QPushButton("Delete Selected")
        btn.setFixedWidth(120)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['ACCENT_RED']};
                color: white; border: none;
                padding: 4px 10px; border-radius: 5px;
                font-weight: bold; font-size: 11px;
            }}
            QPushButton:hover {{ background-color: #da3633; }}
        """)
        if delete_id == "delete_data":
            btn.clicked.connect(self.delete_selected_data)
            self.delete_data_btn = btn
        else:
            btn.clicked.connect(self.delete_selected_decision)
            self.delete_decision_btn = btn

        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(btn)
        return row

    # ------------------------------------------------------------------
    # 資料刷新
    # ------------------------------------------------------------------

    def refresh_data(self):
        db = Database()
        conn = db._get_connection()
        try:
            cursor = conn.cursor()

            # ---- 更新資料庫存貨 ----
            cursor.execute(
                "SELECT ticker, interval, MIN(date), MAX(date), COUNT(*) "
                "FROM prices GROUP BY ticker, interval"
            )
            data_rows = cursor.fetchall()
            self.data_table.setRowCount(len(data_rows))
            for r, row in enumerate(data_rows):
                for c, val in enumerate(row):
                    self.data_table.setItem(r, c, QTableWidgetItem(str(val)))

            # ---- 更新決策表格 ----
            cursor.execute(
                "SELECT date, ticker, interval, final_score, json_data, action "
                "FROM decisions ORDER BY date DESC LIMIT 50"
            )
            dec_rows = cursor.fetchall()
            self.table.setRowCount(len(dec_rows))

            buy_count = 0
            confidence_vals = []
            latest_date = ""

            for r, row in enumerate(dec_rows):
                date, ticker, interval, final_score, json_data, action = row

                if r == 0 and date:
                    latest_date = str(date)
                if action == "BUY":
                    buy_count += 1
                if final_score is not None:
                    confidence_vals.append(abs(final_score))

                # 解析 K/TFM/TA 權重
                k_wt = 0.35
                tfm_wt = 0.30
                ta_wt = 0.35
                if json_data:
                    try:
                        data = json.loads(json_data)
                        contribs = data.get("contributions", {})
                        k_wt = contribs.get("kronos", {}).get("weight", 0.35)
                        tfm_wt = contribs.get("timesfm", {}).get("weight", 0.30)
                        ta_wt = contribs.get("trading_agents", {}).get("weight", 0.35)
                    except Exception:
                        pass

                ratio_str = f"{int(k_wt * 100)}%/{int(tfm_wt * 100)}%/{int(ta_wt * 100)}%"
                display = [
                    date, ticker, interval,
                    f"{final_score:+.2f}" if final_score is not None else "N/A",
                    ratio_str, action,
                ]

                for c, val in enumerate(display):
                    item = QTableWidgetItem(str(val))
                    # 動作欄位上色
                    if c == 5:
                        if val == "BUY":
                            item.setForeground(QBrush(QColor(COLORS["ACCENT_GREEN"])))
                            f = item.font()
                            f.setBold(True)
                            item.setFont(f)
                        elif val == "SELL":
                            item.setForeground(QBrush(QColor(COLORS["ACCENT_RED"])))
                            f = item.font()
                            f.setBold(True)
                            item.setFont(f)
                        elif val == "HOLD":
                            item.setForeground(QBrush(QColor(COLORS["ACCENT_ORANGE"])))
                    self.table.setItem(r, c, item)

            # ---- 更新 KPI 卡片 ----
            # 觀察清單追蹤數
            cursor.execute("SELECT COUNT(DISTINCT ticker) FROM watchlist")
            wl_row = cursor.fetchone()
            tracked = wl_row[0] if wl_row else 0
            self.card_tracked.set_value(str(tracked))

            self.card_updated.set_value(latest_date[:10] if latest_date else "N/A")

        except Exception as e:
            print(f"DB Error in Dashboard: {e}")
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # 擷取資料
    # ------------------------------------------------------------------

    def fetch_data(self):
        ticker = self.ticker_input.text().strip().upper()
        if not ticker:
            self.status_label.setText("Please enter a ticker.")
            self.status_label.setStyleSheet(f"color: {COLORS['ACCENT_ORANGE']}; background: transparent;")
            return

        interval = self.interval_combo.currentText()
        start = self.start_date_input.date().toString("yyyy-MM-dd")
        end = self.end_date_input.date().toString("yyyy-MM-dd")

        self.status_label.setStyleSheet(f"color: {COLORS['ACCENT_BLUE']}; background: transparent;")
        self.status_label.setText(f"Fetching {interval} data for {ticker}...")
        self.fetch_btn.setEnabled(False)
        QApplication.processEvents()

        try:
            collector = DataCollector()
            success = collector.fetch_historical_data(
                ticker, interval=interval, start_date=start, end_date=end,
            )
            if success:
                self.status_label.setStyleSheet(f"color: {COLORS['ACCENT_GREEN']}; background: transparent;")
                self.status_label.setText(f"Successfully fetched {interval} data for {ticker}.")
                self.refresh_data()
            else:
                self.status_label.setStyleSheet(f"color: {COLORS['ACCENT_RED']}; background: transparent;")
                self.status_label.setText(f"Failed to fetch data for {ticker}.")
        except Exception as e:
            self.status_label.setStyleSheet(f"color: {COLORS['ACCENT_RED']}; background: transparent;")
            self.status_label.setText(f"Error: {e}")

        self.fetch_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # 刪除
    # ------------------------------------------------------------------

    def delete_selected_data(self):
        selected = self.data_table.selectedItems()
        if not selected:
            self.status_label.setStyleSheet(f"color: {COLORS['ACCENT_RED']}; background: transparent;")
            self.status_label.setText("Please select a row from Inventory to delete.")
            return

        row = selected[0].row()
        ticker = self.data_table.item(row, 0).text()
        interval = self.data_table.item(row, 1).text()

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete all {interval} data for {ticker}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            db = Database()
            if db.delete_prices(ticker, interval):
                self.status_label.setStyleSheet(f"color: {COLORS['ACCENT_GREEN']}; background: transparent;")
                self.status_label.setText(f"Deleted {interval} data for {ticker}.")
                self.refresh_data()
            else:
                self.status_label.setStyleSheet(f"color: {COLORS['ACCENT_RED']}; background: transparent;")
                self.status_label.setText(f"Failed to delete data.")

    def delete_selected_decision(self):
        selected = self.table.selectedItems()
        if not selected:
            self.status_label.setStyleSheet(f"color: {COLORS['ACCENT_RED']}; background: transparent;")
            self.status_label.setText("Please select a decision row to delete.")
            return

        row = selected[0].row()
        date = self.table.item(row, 0).text()
        ticker = self.table.item(row, 1).text()
        interval = self.table.item(row, 2).text()

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete decision for {ticker} ({interval}) on {date}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            db = Database()
            conn = db._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM decisions WHERE ticker=? AND interval=? AND date=?",
                    (ticker, interval, date),
                )
                conn.commit()
                self.status_label.setStyleSheet(f"color: {COLORS['ACCENT_GREEN']}; background: transparent;")
                self.status_label.setText(f"Deleted decision for {ticker}.")
                self.refresh_data()
            except Exception as e:
                self.status_label.setStyleSheet(f"color: {COLORS['ACCENT_RED']}; background: transparent;")
                self.status_label.setText(f"Failed: {e}")
            finally:
                conn.close()
