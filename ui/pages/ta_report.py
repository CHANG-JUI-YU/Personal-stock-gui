from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QScrollArea, QFrame, 
                               QTextEdit, QSizePolicy, QComboBox, QSplitter,
                               QListWidget, QListWidgetItem, QMessageBox)
from PyQt6.QtCore import Qt
from data.database import Database
import json
import os

class TAReportPage(QWidget):
    def __init__(self, db_path="data/stock_advisor.db"):
        super().__init__()
        self.db = Database(db_path)
        self.init_ui()
        
    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_repository()
        self.refresh_tickers()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("TradingAgents Report Repository")
        header.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(header)
        
        # --- TOP PANEL: Run New Analysis ---
        top_layout = QHBoxLayout()
        self.ticker_input = QComboBox()
        self.ticker_input.setEditable(True)
        self.ticker_input.setMinimumWidth(150)
        self.ticker_input.setStyleSheet("padding: 8px; font-size: 14px; border: 1px solid #BDC3C7; border-radius: 4px;")
        
        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["1d", "1h", "15m", "5m"])
        self.interval_combo.setStyleSheet("padding: 8px; font-size: 14px; border: 1px solid #BDC3C7; border-radius: 4px;")
        
        self.run_btn = QPushButton("Run TA Analysis")
        self.run_btn.setStyleSheet("""
            QPushButton {
                background-color: #E67E22; color: white; padding: 8px 16px; 
                font-weight: bold; border-radius: 4px; border: none;
            }
            QPushButton:hover { background-color: #D35400; }
        """)
        self.run_btn.clicked.connect(self.run_analysis)
        
        top_layout.addWidget(self.ticker_input)
        top_layout.addWidget(self.interval_combo)
        top_layout.addWidget(self.run_btn)
        top_layout.addStretch()
        layout.addLayout(top_layout)
        
        # Splitter for Master-Detail view
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- LEFT PANEL: List of Reports ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        list_header = QLabel("Saved Reports")
        list_header.setStyleSheet("font-size: 16px; font-weight: bold;")
        left_layout.addWidget(list_header)
        
        self.report_list = QListWidget()
        self.report_list.setStyleSheet("""
            QListWidget {
                font-size: 14px; padding: 5px; border: 1px solid #BDC3C7; border-radius: 4px;
            }
            QListWidget::item {
                padding: 10px; border-bottom: 1px solid #ECF0F1;
            }
            QListWidget::item:selected {
                background-color: #3498DB; color: white;
            }
        """)
        self.report_list.itemClicked.connect(self.on_report_selected)
        left_layout.addWidget(self.report_list)
        
        # --- RIGHT PANEL: Report Detail ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; }")
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll.setWidget(self.content_widget)
        right_layout.addWidget(self.scroll)
        
        # Add widgets to splitter
        left_widget.setMaximumWidth(350)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        
        # Set stretch factor so right panel takes more space
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([250, 800])
        
        layout.addWidget(splitter, stretch=1)
        
    def refresh_repository(self):
        self.report_list.clear()
        reports = self.db.get_all_ta_reports()
        
        if not reports:
            item = QListWidgetItem("No reports found.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.report_list.addItem(item)
            return
            
        for rep in reports:
            ticker = rep.get('ticker')
            date = rep.get('date')
            interval = rep.get('interval')
            
            display_text = f"{ticker} | {date} ({interval})"
            item = QListWidgetItem(display_text)
            # Store the data in the item for retrieval
            item.setData(Qt.ItemDataRole.UserRole, rep)
            self.report_list.addItem(item)
            
    def on_report_selected(self, item):
        report_dict = item.data(Qt.ItemDataRole.UserRole)
        if not report_dict:
            return
            
        ticker = report_dict.get('ticker')
        date = report_dict.get('date')
        data = report_dict.get('data')
        
        self.render_report(date, data, ticker)

    def render_report(self, date, data, ticker):
        # clear previous
        for i in reversed(range(self.content_layout.count())): 
            widget = self.content_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
                
        ta_detail = data.get("agents", {})
        
        if not ta_detail:
            lbl = QLabel(f"No TradingAgents detail found in the report for {ticker}.")
            lbl.setStyleSheet("color: #7F8C8D; font-size: 16px;")
            self.content_layout.addWidget(lbl)
            return
            
        header_text = f"Analysis Report: {ticker} ({date})"
        date_lbl = QLabel(header_text)
        date_lbl.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        self.content_layout.addWidget(date_lbl)
        
        for agent_name, info in ta_detail.items():
            frame = QFrame()
            frame.setStyleSheet("""
                QFrame {
                    background-color: #ECF0F1; border-radius: 8px; margin-bottom: 15px;
                }
            """)
            flayout = QVBoxLayout(frame)
            
            # Agent Name & Action
            action = info.get("action", "UNKNOWN")
            conf = info.get("confidence", 0.0)
            
            color = "#27AE60" if action == "BUY" else "#C0392B" if action == "SELL" else "#F39C12"
            
            header_lbl = QLabel(f"{agent_name} | {action} (Conf: {conf:.2f})")
            header_lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {color}; background: transparent;")
            flayout.addWidget(header_lbl)
            
            # Reasoning
            reasoning = info.get("reasoning", "")
            reason_box = QTextEdit()
            reason_box.setReadOnly(True)
            reason_box.setMarkdown(reasoning) # Render as Markdown
            
            font = reason_box.font()
            font.setPointSize(11)
            reason_box.setFont(font)
            
            reason_box.setStyleSheet("background-color: white; color: black; border: 1px solid #BDC3C7; border-radius: 4px; padding: 10px;")
            reason_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
            reason_box.setMinimumHeight(250)
            
            flayout.addWidget(reason_box)
            self.content_layout.addWidget(frame)

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

    def run_analysis(self):
        ticker = self.ticker_input.currentText().strip().upper()
        if not ticker:
            return
            
        interval = self.interval_combo.currentText()
        import datetime
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Disable buttons
        self.run_btn.setEnabled(False)
        self.run_btn.setText("Generating...")
        
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        
        try:
            import os
            mock_ta = not bool(os.getenv("OPENAI_API_KEY"))
            
            if mock_ta:
                from trading_agents.adapter import MockTradingAgents
                ta = MockTradingAgents()
            else:
                from trading_agents.adapter import RealTradingAgents
                ta = RealTradingAgents()
                
            report_data = ta.analyze(ticker, date=date_str, interval=interval)
            
            if report_data:
                # Save to DB
                self.db.insert_ta_report(ticker, interval, date_str, report_data)
                
                # Render immediately
                self.render_report(date_str, report_data, ticker)
                
                # Refresh repository list
                self.refresh_repository()
        except Exception as e:
            lbl = QLabel(f"Error generating TA Report: {e}")
            lbl.setStyleSheet("color: red; font-size: 16px;")
            self.content_layout.addWidget(lbl)
            import traceback
            traceback.print_exc()
        finally:
            self.run_btn.setEnabled(True)
            self.run_btn.setText("Run TA Analysis")
