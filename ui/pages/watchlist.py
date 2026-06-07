"""
Watchlist Page - 觀察清單頁面
顯示使用者追蹤的股票清單，並自動載入最新預測與決策資料。
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox
)
from PyQt6.QtGui import QColor, QBrush, QFont
from PyQt6.QtCore import Qt
from data.database import Database


class WatchlistPage(QWidget):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # 標題
        title = QLabel("Watchlist - Portfolio Monitor")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2C3E50;")
        layout.addWidget(title)

        # 上方工具列
        toolbar = QHBoxLayout()

        # Ticker 輸入 (可編輯的 QComboBox，用於同步)
        self.ticker_input = QComboBox()
        self.ticker_input.setEditable(True)
        self.ticker_input.setPlaceholderText("輸入股票代碼 (e.g. 2330.TW)")
        self.ticker_input.setFixedWidth(200)
        self.ticker_input.setStyleSheet(
            "padding: 6px; font-size: 14px; border: 1px solid #BDC3C7; border-radius: 4px;"
        )

        # Interval 選擇 (用於同步)
        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["1d", "1h", "15m", "5m"])
        self.interval_combo.setFixedWidth(80)

        # 加入觀察清單按鈕
        self.add_btn = QPushButton("Add to Watchlist")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60; color: white; padding: 8px 16px;
                font-weight: bold; border-radius: 4px; border: none;
            }
            QPushButton:hover { background-color: #2ECC71; }
        """)
        self.add_btn.clicked.connect(self._on_add_clicked)

        # 移除選取按鈕
        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #C0392B; color: white; padding: 8px 16px;
                font-weight: bold; border-radius: 4px; border: none;
            }
            QPushButton:hover { background-color: #E74C3C; }
        """)
        self.remove_btn.clicked.connect(self._on_remove_clicked)

        # 狀態標籤
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: gray; font-size: 12px;")

        toolbar.addWidget(QLabel("Ticker:"))
        toolbar.addWidget(self.ticker_input)
        toolbar.addWidget(QLabel("Interval:"))
        toolbar.addWidget(self.interval_combo)
        toolbar.addWidget(self.add_btn)
        toolbar.addWidget(self.remove_btn)
        toolbar.addWidget(self.status_label)
        toolbar.addStretch()

        layout.addLayout(toolbar)

        # 主表格
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Ticker", "Latest Close", "Kronos Score",
            "TimesFM Score", "TA Score", "Final Action",
            "Last Updated", "Notes"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #D5D8DC;
                font-size: 13px;
            }
            QTableWidget::item:selected {
                background-color: #AED6F1;
            }
        """)
        layout.addWidget(self.table)

    # ------------------------------------------------------------------
    # 事件處理
    # ------------------------------------------------------------------

    def showEvent(self, event):
        """頁面顯示時自動重新載入資料。"""
        super().showEvent(event)
        self._refresh_table()

    def _on_add_clicked(self):
        """加入股票到觀察清單。"""
        ticker = self.ticker_input.currentText().strip().upper()
        if not ticker:
            self.status_label.setStyleSheet("color: red;")
            self.status_label.setText("請輸入股票代碼")
            return

        if self.db.is_in_watchlist(ticker):
            self.status_label.setStyleSheet("color: orange;")
            self.status_label.setText(f"{ticker} 已在觀察清單中")
            return

        success = self.db.add_to_watchlist(ticker)
        if success:
            self.status_label.setStyleSheet("color: green;")
            self.status_label.setText(f"已加入 {ticker}")
            self._refresh_table()
        else:
            self.status_label.setStyleSheet("color: red;")
            self.status_label.setText(f"加入 {ticker} 失敗")

    def _on_remove_clicked(self):
        """從觀察清單移除選取的股票。"""
        selected = self.table.selectedItems()
        if not selected:
            self.status_label.setStyleSheet("color: red;")
            self.status_label.setText("請先選取要移除的項目")
            return

        row = selected[0].row()
        ticker = self.table.item(row, 0).text()

        reply = QMessageBox.question(
            self, "確認移除",
            f"確定要從觀察清單移除 {ticker} 嗎?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            success = self.db.remove_from_watchlist(ticker)
            if success:
                self.status_label.setStyleSheet("color: green;")
                self.status_label.setText(f"已移除 {ticker}")
                self._refresh_table()

    # ------------------------------------------------------------------
    # 資料載入
    # ------------------------------------------------------------------

    def _refresh_table(self):
        """重新從資料庫載入觀察清單與各項分數。"""
        watchlist = self.db.get_watchlist()
        interval = self.interval_combo.currentText()

        self.table.setRowCount(len(watchlist))

        for row_idx, item in enumerate(watchlist):
            ticker = item["ticker"]
            notes = item.get("notes", "")

            # 取得最新收盤價
            latest_close = self._get_latest_close(ticker, interval)

            # 取得 Kronos 分數 (predictions 表, 不含 _tfm 後綴)
            kronos_score = self._get_latest_prediction_score(ticker, interval)

            # 取得 TimesFM 分數 (predictions 表, 帶 _tfm 後綴)
            tfm_interval = interval + "_tfm"
            timesfm_score = self._get_latest_prediction_score(ticker, tfm_interval)

            # 取得決策資料
            decision_data = self._get_latest_decision(ticker, interval)
            ta_score = decision_data.get("ta_contrib", None)
            final_action = decision_data.get("action", "N/A")
            last_updated = decision_data.get("date", "N/A")

            # 填入表格
            values = [
                ticker,
                f"{latest_close:.2f}" if latest_close is not None else "N/A",
                f"{kronos_score:+.1f}" if kronos_score is not None else "N/A",
                f"{timesfm_score:+.1f}" if timesfm_score is not None else "N/A",
                f"{ta_score:+.1f}" if ta_score is not None else "N/A",
                final_action,
                last_updated,
                notes or ""
            ]

            for col_idx, val in enumerate(values):
                table_item = QTableWidgetItem(str(val))
                table_item.setFlags(table_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                # Final Action 欄位以顏色區分
                if col_idx == 5:
                    bold_font = QFont()
                    bold_font.setBold(True)
                    table_item.setFont(bold_font)
                    if val == "BUY":
                        table_item.setForeground(QBrush(QColor("#27AE60")))
                    elif val == "SELL":
                        table_item.setForeground(QBrush(QColor("#C0392B")))
                    elif val == "HOLD":
                        table_item.setForeground(QBrush(QColor("#E67E22")))

                self.table.setItem(row_idx, col_idx, table_item)

    # ------------------------------------------------------------------
    # 資料庫查詢輔助方法
    # ------------------------------------------------------------------

    def _get_latest_close(self, ticker: str, interval: str):
        """取得該股票最新收盤價。"""
        try:
            prices_df = self.db.get_prices(ticker, interval)
            if prices_df is not None and not prices_df.empty:
                return float(prices_df['Close'].iloc[-1])
        except Exception:
            pass
        return None

    def _get_latest_prediction_score(self, ticker: str, interval: str):
        """從 predictions 表取得最新的 score_k。"""
        try:
            with self.db._get_connection() as conn:
                import sqlite3
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT score_k FROM predictions "
                    "WHERE ticker = ? AND interval = ? "
                    "ORDER BY date DESC LIMIT 1",
                    (ticker, interval)
                )
                row = cursor.fetchone()
                if row:
                    return float(row["score_k"])
        except Exception:
            pass
        return None

    def _get_latest_decision(self, ticker: str, interval: str) -> dict:
        """從 decisions 表取得最新決策。"""
        try:
            df = self.db.get_decisions(ticker, interval, limit=1)
            if df is not None and not df.empty:
                row = df.iloc[0]
                return {
                    "action": row.get("action", "N/A"),
                    "final_score": row.get("final_score", None),
                    "ta_contrib": row.get("ta_contrib", None),
                    "date": row.get("date", "N/A"),
                }
        except Exception:
            pass
        return {"action": "N/A", "final_score": None, "ta_contrib": None, "date": "N/A"}
