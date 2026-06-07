import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QWidget, QVBoxLayout

class ContributionBar(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        self.figure = Figure(figsize=(5, 3))
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas)
        self.ax = self.figure.add_subplot(111)
        self.set_data(0, 0, 0)
        
    def set_data(self, kronos_contrib, tfm_contrib, ta_contrib):
        self.ax.clear()
        
        labels = ['Kronos', 'TimesFM', 'TradingAgents']
        values = [kronos_contrib, tfm_contrib, ta_contrib]
        colors = ['#3498db' if v >= 0 else '#e74c3c' for v in values]
        
        self.ax.barh(labels, values, color=colors)
        self.ax.axvline(0, color='black', linewidth=1)
        self.ax.set_xlim(-100, 100)
        self.ax.set_xlabel("Model Score (-100 to +100)")
        self.ax.set_title("Individual Model Scores")
        
        for i, v in enumerate(values):
            self.ax.text(v + (2 if v >= 0 else -10), i, f"{v:.1f}", va='center')
            
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            try:
                self.figure.tight_layout(pad=1.5)
            except Exception:
                pass
        self.canvas.draw()
