# -*- coding: utf-8 -*-
"""
MiroFish Simulation Page - Multi-agent simulation using pre-analyzed data.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QFrame, QSplitter,
    QTextEdit, QSpinBox, QMessageBox, QApplication,
    QLineEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from data.database import Database
import json

try:
    from ui.theme import COLORS
except ImportError:
    COLORS = {
        'BG_DARK': '#0f1318', 'BG_CARD': '#181d24', 'TEXT_PRIMARY': '#d1d5db',
        'TEXT_SECONDARY': '#6b7280', 'ACCENT_BLUE': '#6b8aaf', 'ACCENT_GREEN': '#5a9e6f',
        'ACCENT_RED': '#c25550', 'BORDER': '#2a3038',
    }

class SimWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, ticker, interval, date, debate_rounds, risk_rounds, db_path, what_if_event=None):
        super().__init__()
        self.ticker = ticker
        self.interval = interval
        self.date = date
        self.debate_rounds = debate_rounds
        self.risk_rounds = risk_rounds
        self.db_path = db_path
        self.what_if_event = what_if_event

    def run(self):
        try:
            from trading_agents.mirofish_runner import MiroFishRunner
            runner = MiroFishRunner(self.db_path)
            result = runner.run_simulation(
                self.ticker, self.interval, self.date,
                self.debate_rounds, self.risk_rounds,
                what_if_event=self.what_if_event
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class MiroFishSimPage(QWidget):
    def __init__(self, db_path="data/stock_advisor.db"):
        super().__init__()
        self.db = Database(db_path)
        self.worker = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = QLabel("WHAT IF SIMULATION")
        header.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {COLORS['TEXT_PRIMARY']};"
        )
        layout.addWidget(header)

        # Control Bar
        control_frame = QFrame()
        control_frame.setStyleSheet(
            f"background-color: {COLORS['BG_CARD']}; border: 1px solid {COLORS['BORDER']}; "
            f"border-radius: 6px; padding: 8px;"
        )
        control = QHBoxLayout(control_frame)

        self.ticker_input = QComboBox()
        self.ticker_input.setEditable(True)
        self.ticker_input.setFixedWidth(120)
        self.ticker_input.addItems(self._get_tickers())

        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["1d", "1h", "15m", "5m"])

        self.debate_spin = QSpinBox()
        self.debate_spin.setRange(1, 3)
        self.debate_spin.setValue(1)
        self.debate_spin.valueChanged.connect(self._update_cost)

        self.risk_spin = QSpinBox()
        self.risk_spin.setRange(1, 3)
        self.risk_spin.setValue(1)
        self.risk_spin.valueChanged.connect(self._update_cost)

        self.cost_label = QLabel("Est. Cost: ~$0.005")
        self.cost_label.setStyleSheet(f"color: {COLORS['TEXT_SECONDARY']}; font-weight: bold;")

        self.run_btn = QPushButton("Run Simulation")
        self.run_btn.setStyleSheet(
            f"background-color: {COLORS['ACCENT_BLUE']}; color: white; "
            f"font-weight: bold; padding: 6px 16px; border-radius: 4px;"
        )
        self.run_btn.clicked.connect(self._run_simulation)

        control.addWidget(QLabel("Ticker:"))
        control.addWidget(self.ticker_input)
        control.addWidget(QLabel("Interval:"))
        control.addWidget(self.interval_combo)
        control.addWidget(QLabel("Debate Rnds:"))
        control.addWidget(self.debate_spin)
        control.addWidget(QLabel("Risk Rnds:"))
        control.addWidget(self.risk_spin)
        control.addStretch()
        control.addWidget(self.cost_label)
        control.addWidget(self.run_btn)

        layout.addWidget(control_frame)

        # What-If Event Input Frame
        what_if_frame = QFrame()
        what_if_frame.setStyleSheet(
            f"background-color: {COLORS['BG_CARD']}; border: 1px solid {COLORS['BORDER']}; "
            f"border-radius: 6px; padding: 8px;"
        )
        what_if_layout = QHBoxLayout(what_if_frame)
        what_if_layout.setContentsMargins(8, 4, 8, 4)
        
        what_if_label = QLabel("What-If 黑天鵝事件 (選填):")
        what_if_label.setStyleSheet(f"color: {COLORS['TEXT_PRIMARY']}; font-weight: bold;")
        
        self.what_if_input = QLineEdit()
        self.what_if_input.setPlaceholderText("例如：美國總統被刺殺、台積電2nm產線大火、台海局勢升溫... (不填則使用正常狀態)")
        self.what_if_input.setStyleSheet(
            f"background-color: {COLORS['BG_DARK']}; color: {COLORS['TEXT_PRIMARY']}; "
            f"border: 1px solid {COLORS['BORDER']}; border-radius: 4px; padding: 6px;"
        )
        
        what_if_layout.addWidget(what_if_label)
        what_if_layout.addWidget(self.what_if_input)
        layout.addWidget(what_if_frame)

        # Splitter for Main Content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(
            f"QSplitter::handle {{ background-color: {COLORS['BORDER']}; width: 2px; }}"
        )

        # Left Panel (Input Summary)
        left_frame = QFrame()
        left_frame.setStyleSheet(
            f"background-color: {COLORS['BG_CARD']}; border: 1px solid {COLORS['BORDER']}; border-radius: 6px;"
        )
        left_layout = QVBoxLayout(left_frame)
        
        left_title = QLabel("Input Pre-Analysis Summary")
        left_title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {COLORS['TEXT_PRIMARY']};")
        left_layout.addWidget(left_title)

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setStyleSheet(
            f"background-color: {COLORS['BG_DARK']}; color: {COLORS['TEXT_PRIMARY']}; "
            f"border: 1px solid {COLORS['BORDER']}; border-radius: 4px; font-family: Consolas, monospace;"
        )
        left_layout.addWidget(self.summary_text)

        # Right Panel (Simulation Results)
        right_frame = QFrame()
        right_frame.setStyleSheet(
            f"background-color: {COLORS['BG_CARD']}; border: 1px solid {COLORS['BORDER']}; border-radius: 6px;"
        )
        right_layout = QVBoxLayout(right_frame)
        
        right_title = QLabel("Simulation Results")
        right_title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {COLORS['TEXT_PRIMARY']};")
        right_layout.addWidget(right_title)

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setStyleSheet(
            f"background-color: {COLORS['BG_DARK']}; color: {COLORS['TEXT_PRIMARY']}; "
            f"border: 1px solid {COLORS['BORDER']}; border-radius: 4px; font-family: Consolas, monospace;"
        )
        right_layout.addWidget(self.results_text)

        splitter.addWidget(left_frame)
        splitter.addWidget(right_frame)
        splitter.setSizes([300, 600])

        layout.addWidget(splitter, stretch=1)
        
        # Connect to load summary when ticker/interval changes
        self.ticker_input.currentTextChanged.connect(self._load_summary)
        self.interval_combo.currentTextChanged.connect(self._load_summary)

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
        self._load_summary()

    def _get_tickers(self):
        try:
            return self.db.get_all_tickers() or ["2330.TW"]
        except Exception:
            return ["2330.TW"]

    def _update_cost(self):
        # Base input tokens ~8000, Base output ~4000
        # DeepSeek v4-flash / v3: input $0.27/M, output $1.10/M
        base_cost = (8000 * 0.27 / 1e6) + (4000 * 1.10 / 1e6) # ~$0.0065
        
        # Each extra debate round adds ~2000 output tokens
        extra_debate = max(0, self.debate_spin.value() - 1)
        extra_risk = max(0, self.risk_spin.value() - 1)
        
        extra_cost = (extra_debate + extra_risk) * (2000 * 1.10 / 1e6)
        
        total_cost = base_cost + extra_cost
        self.cost_label.setText(f"Est. Cost: ~${total_cost:.4f}")

    def _load_summary(self):
        ticker = self.ticker_input.currentText().strip().upper()
        interval = self.interval_combo.currentText()
        if not ticker:
            return
            
        kronos_pred = self.db.get_latest_prediction(ticker, interval)
        tfm_pred = self.db.get_latest_prediction(ticker, f"{interval}_tfm")
        
        # Just display the context string that MiroFishRunner would generate
        lines = [
            f"KRONOS XAI PRE-ANALYSIS REPORT FOR {ticker}",
            f"Interval: {interval}",
            "-" * 40
        ]
        
        if kronos_pred:
            lines.append(f"Kronos Up Prob: {kronos_pred.get('up_prob', 0):.2%}")
        else:
            lines.append("Kronos: No Data")
            
        if tfm_pred:
            lines.append(f"TimesFM Up Prob: {tfm_pred.get('up_prob', 0):.2%}")
        else:
            lines.append("TimesFM: No Data")
            
        self.summary_text.setPlainText("\n".join(lines))
        self.results_text.setPlainText("Ready to run simulation.\nThis may take 1-3 minutes depending on rounds.")

    def _run_simulation(self):
        ticker = self.ticker_input.currentText().strip().upper()
        if not ticker:
            return

        interval = self.interval_combo.currentText()
        from datetime import datetime
        date = datetime.now().strftime("%Y-%m-%d")

        self.run_btn.setEnabled(False)
        self.run_btn.setText("Simulating...")
        self.results_text.setPlainText("Starting TradingAgents graph execution...\nInjecting KRONOS XAI pre-analysis into Context...\nWaiting for Agents to debate...")

        what_if_event = self.what_if_input.text().strip()
        if not what_if_event:
            what_if_event = None

        self.worker = SimWorker(
            ticker, interval, date,
            self.debate_spin.value(),
            self.risk_spin.value(),
            self.db.db_path,
            what_if_event=what_if_event
        )
        self.worker.finished.connect(self._on_sim_finished)
        self.worker.error.connect(self._on_sim_error)
        self.worker.start()

    def _on_sim_finished(self, result: dict):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Run Simulation")

        out = []
        action = result.get('action', 'N/A')
        conf = result.get('confidence', 0)
        
        out.append(f"=== FINAL DECISION ===")
        out.append(f"Action: {action}")
        out.append(f"Confidence: {conf:.2f}")
        out.append("")

        # Display the Portfolio Manager reasoning
        reports = result.get('reports', {})
        pm_reasoning = reports.get('Portfolio Manager', {}).get('reasoning', '')
        if pm_reasoning:
            out.append(f"Portfolio Manager Reasoning:\n{pm_reasoning}")
            out.append("")
        
        reports = result.get('reports', {})
        if reports:
            out.append("=== SUB-AGENT REPORTS ===")
            for agent, data in reports.items():
                if agent != "Portfolio Manager":
                    reasoning = data.get('reasoning', '')[:300] + '...'
                    out.append(f"[{agent}] -> {data.get('action')}")
                    out.append(f"{reasoning}\n")
                    
        debate = result.get('debate', {})
        if debate:
            out.append("=== DEBATE HIGHLIGHTS ===")
            if debate.get('judge'):
                out.append(f"[Judge]: {debate['judge']}\n")
                
        self.results_text.setPlainText("\n".join(out))

    def _on_sim_error(self, err: str):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Run Simulation")
        self.results_text.setPlainText(f"Simulation Error:\n{err}\n\nPlease check Settings for API Key.")

