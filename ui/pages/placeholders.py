from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

class BasePage(QWidget):
    def __init__(self, title_text):
        super().__init__()
        layout = QVBoxLayout()
        title = QLabel(title_text)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)
        
        info = QLabel(f"{title_text} implementation pending...")
        layout.addWidget(info)
        layout.addStretch()
        self.setLayout(layout)

class StockAnalysisPage(BasePage):
    def __init__(self):
        super().__init__("Stock Analysis")

class DecisionPage(BasePage):
    def __init__(self):
        super().__init__("Decision Agent Output")


class TAReportPage(BasePage):
    def __init__(self):
        super().__init__("TradingAgents Report")

class BacktestPage(BasePage):
    def __init__(self):
        super().__init__("Backtest")
