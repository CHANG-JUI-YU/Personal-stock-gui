# -*- coding: utf-8 -*-
"""
KRONOS X - 深色主題系統
提供全域深色主題的色彩定義、QSS 樣式表、以及 matplotlib 繪圖風格設定。
"""

# ---------------------------------------------------------------------------
# 色彩常數
# ---------------------------------------------------------------------------
COLORS = {
    # 背景
    "BG_DARK":      "#0f1318",
    "BG_CARD":      "#181d24",
    "BG_SIDEBAR":   "#0b0e12",
    "BG_INPUT":     "#1e242c",
    # 邊框
    "BORDER":       "#2a3038",
    # 文字
    "TEXT_PRIMARY":  "#d1d5db",
    "TEXT_SECONDARY":"#6b7280",
    # 語義色 (低飽和度)
    "ACCENT_BLUE":   "#6b8aaf",
    "ACCENT_GREEN":  "#5a9e6f",
    "ACCENT_RED":    "#c25550",
    "ACCENT_ORANGE": "#b8943e",
    "ACCENT_PURPLE": "#7c8594",
}

# 建立便捷別名
_C = COLORS


def get_app_stylesheet() -> str:
    """
    回傳涵蓋所有 PyQt6 元件類型的完整 QSS 樣式表字串。
    """
    return f"""
    /* ========================================================= */
    /*  全域設定                                                  */
    /* ========================================================= */
    * {{
        font-family: "Microsoft JhengHei", "Segoe UI", "Noto Sans TC", sans-serif;
        font-size: 13px;
        color: {_C['TEXT_PRIMARY']};
    }}

    /* ========================================================= */
    /*  QMainWindow / QWidget                                     */
    /* ========================================================= */
    QMainWindow {{
        background-color: {_C['BG_DARK']};
    }}
    QWidget {{
        background-color: {_C['BG_DARK']};
        color: {_C['TEXT_PRIMARY']};
    }}

    /* ========================================================= */
    /*  QLabel                                                    */
    /* ========================================================= */
    QLabel {{
        color: {_C['TEXT_PRIMARY']};
        background-color: transparent;
    }}

    /* ========================================================= */
    /*  QPushButton                                               */
    /* ========================================================= */
    QPushButton {{
        background-color: {_C['BG_INPUT']};
        color: {_C['TEXT_PRIMARY']};
        border: 1px solid {_C['BORDER']};
        border-radius: 6px;
        padding: 6px 16px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {_C['BORDER']};
        border-color: {_C['ACCENT_BLUE']};
    }}
    QPushButton:pressed {{
        background-color: {_C['BG_SIDEBAR']};
    }}
    QPushButton:disabled {{
        color: {_C['TEXT_SECONDARY']};
        background-color: {_C['BG_CARD']};
        border-color: {_C['BORDER']};
    }}

    /* ========================================================= */
    /*  QComboBox                                                 */
    /* ========================================================= */
    QComboBox {{
        background-color: {_C['BG_INPUT']};
        color: {_C['TEXT_PRIMARY']};
        border: 1px solid {_C['BORDER']};
        border-radius: 6px;
        padding: 5px 10px;
        min-height: 22px;
    }}
    QComboBox:hover {{
        border-color: {_C['ACCENT_BLUE']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid {_C['TEXT_SECONDARY']};
        margin-right: 6px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {_C['BG_CARD']};
        color: {_C['TEXT_PRIMARY']};
        border: 1px solid {_C['BORDER']};
        selection-background-color: {_C['BG_INPUT']};
        selection-color: {_C['ACCENT_BLUE']};
        outline: none;
    }}

    /* ========================================================= */
    /*  QLineEdit                                                 */
    /* ========================================================= */
    QLineEdit {{
        background-color: {_C['BG_INPUT']};
        color: {_C['TEXT_PRIMARY']};
        border: 1px solid {_C['BORDER']};
        border-radius: 6px;
        padding: 5px 10px;
        selection-background-color: {_C['ACCENT_BLUE']};
        selection-color: {_C['BG_DARK']};
    }}
    QLineEdit:focus {{
        border-color: {_C['ACCENT_BLUE']};
    }}

    /* ========================================================= */
    /*  QSpinBox / QDoubleSpinBox                                 */
    /* ========================================================= */
    QSpinBox, QDoubleSpinBox {{
        background-color: {_C['BG_INPUT']};
        color: {_C['TEXT_PRIMARY']};
        border: 1px solid {_C['BORDER']};
        border-radius: 6px;
        padding: 4px 8px;
    }}
    QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {_C['ACCENT_BLUE']};
    }}
    QSpinBox::up-button, QDoubleSpinBox::up-button,
    QSpinBox::down-button, QDoubleSpinBox::down-button {{
        background-color: {_C['BG_INPUT']};
        border: none;
        width: 16px;
    }}
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-bottom: 5px solid {_C['TEXT_SECONDARY']};
    }}
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {_C['TEXT_SECONDARY']};
    }}

    /* ========================================================= */
    /*  QDateEdit                                                 */
    /* ========================================================= */
    QDateEdit {{
        background-color: {_C['BG_INPUT']};
        color: {_C['TEXT_PRIMARY']};
        border: 1px solid {_C['BORDER']};
        border-radius: 6px;
        padding: 4px 8px;
    }}
    QDateEdit:focus {{
        border-color: {_C['ACCENT_BLUE']};
    }}
    QDateEdit::drop-down {{
        border: none;
        width: 24px;
    }}
    QDateEdit::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid {_C['TEXT_SECONDARY']};
        margin-right: 6px;
    }}
    QCalendarWidget {{
        background-color: {_C['BG_CARD']};
        color: {_C['TEXT_PRIMARY']};
    }}

    /* ========================================================= */
    /*  QTableWidget / QTableView                                 */
    /* ========================================================= */
    QTableWidget, QTableView {{
        background-color: {_C['BG_CARD']};
        alternate-background-color: {_C['BG_DARK']};
        color: {_C['TEXT_PRIMARY']};
        border: 1px solid {_C['BORDER']};
        border-radius: 6px;
        gridline-color: {_C['BORDER']};
        selection-background-color: rgba(88, 166, 255, 0.15);
        selection-color: {_C['ACCENT_BLUE']};
        outline: none;
    }}
    QTableWidget::item:hover, QTableView::item:hover {{
        background-color: rgba(88, 166, 255, 0.08);
    }}
    QTableWidget::item:selected, QTableView::item:selected {{
        background-color: rgba(88, 166, 255, 0.18);
        color: {_C['ACCENT_BLUE']};
    }}

    /* ========================================================= */
    /*  QHeaderView                                               */
    /* ========================================================= */
    QHeaderView {{
        background-color: {_C['BG_DARK']};
    }}
    QHeaderView::section {{
        background-color: {_C['BG_DARK']};
        color: {_C['TEXT_SECONDARY']};
        border: none;
        border-bottom: 1px solid {_C['BORDER']};
        border-right: 1px solid {_C['BORDER']};
        padding: 6px 8px;
        font-weight: 600;
        font-size: 12px;
        text-transform: uppercase;
    }}
    QHeaderView::section:hover {{
        color: {_C['TEXT_PRIMARY']};
    }}

    /* ========================================================= */
    /*  QScrollArea                                               */
    /* ========================================================= */
    QScrollArea {{
        background-color: {_C['BG_DARK']};
        border: none;
    }}

    /* ========================================================= */
    /*  QFrame                                                    */
    /* ========================================================= */
    QFrame {{
        border: none;
    }}

    /* ========================================================= */
    /*  QTextEdit / QPlainTextEdit                                */
    /* ========================================================= */
    QTextEdit, QPlainTextEdit {{
        background-color: {_C['BG_INPUT']};
        color: {_C['TEXT_PRIMARY']};
        border: 1px solid {_C['BORDER']};
        border-radius: 6px;
        padding: 6px;
        selection-background-color: {_C['ACCENT_BLUE']};
        selection-color: {_C['BG_DARK']};
    }}
    QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {_C['ACCENT_BLUE']};
    }}

    /* ========================================================= */
    /*  QCheckBox                                                 */
    /* ========================================================= */
    QCheckBox {{
        spacing: 8px;
        color: {_C['TEXT_PRIMARY']};
        background-color: transparent;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {_C['BORDER']};
        border-radius: 3px;
        background-color: {_C['BG_INPUT']};
    }}
    QCheckBox::indicator:checked {{
        background-color: {_C['ACCENT_BLUE']};
        border-color: {_C['ACCENT_BLUE']};
    }}
    QCheckBox::indicator:hover {{
        border-color: {_C['ACCENT_BLUE']};
    }}

    /* ========================================================= */
    /*  QRadioButton                                              */
    /* ========================================================= */
    QRadioButton {{
        spacing: 8px;
        color: {_C['TEXT_PRIMARY']};
        background-color: transparent;
    }}
    QRadioButton::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {_C['BORDER']};
        border-radius: 8px;
        background-color: {_C['BG_INPUT']};
    }}
    QRadioButton::indicator:checked {{
        background-color: {_C['ACCENT_BLUE']};
        border-color: {_C['ACCENT_BLUE']};
    }}

    /* ========================================================= */
    /*  QListWidget / QListView                                   */
    /* ========================================================= */
    QListWidget, QListView {{
        background-color: {_C['BG_CARD']};
        color: {_C['TEXT_PRIMARY']};
        border: 1px solid {_C['BORDER']};
        border-radius: 6px;
        outline: none;
    }}
    QListWidget::item:hover, QListView::item:hover {{
        background-color: rgba(88, 166, 255, 0.08);
    }}
    QListWidget::item:selected, QListView::item:selected {{
        background-color: rgba(88, 166, 255, 0.18);
        color: {_C['ACCENT_BLUE']};
    }}

    /* ========================================================= */
    /*  QSplitter                                                 */
    /* ========================================================= */
    QSplitter::handle {{
        background-color: {_C['BORDER']};
    }}
    QSplitter::handle:horizontal {{
        width: 2px;
    }}
    QSplitter::handle:vertical {{
        height: 2px;
    }}

    /* ========================================================= */
    /*  QTabWidget / QTabBar                                      */
    /* ========================================================= */
    QTabWidget::pane {{
        border: 1px solid {_C['BORDER']};
        border-radius: 6px;
        background-color: {_C['BG_CARD']};
        top: -1px;
    }}
    QTabBar::tab {{
        background-color: {_C['BG_DARK']};
        color: {_C['TEXT_SECONDARY']};
        border: 1px solid {_C['BORDER']};
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        padding: 8px 18px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background-color: {_C['BG_CARD']};
        color: {_C['ACCENT_BLUE']};
        border-bottom: 2px solid {_C['ACCENT_BLUE']};
    }}
    QTabBar::tab:hover:!selected {{
        color: {_C['TEXT_PRIMARY']};
        background-color: {_C['BG_INPUT']};
    }}

    /* ========================================================= */
    /*  QProgressBar                                              */
    /* ========================================================= */
    QProgressBar {{
        background-color: {_C['BG_INPUT']};
        border: 1px solid {_C['BORDER']};
        border-radius: 4px;
        text-align: center;
        color: {_C['TEXT_PRIMARY']};
        min-height: 18px;
    }}
    QProgressBar::chunk {{
        background-color: {_C['ACCENT_BLUE']};
        border-radius: 3px;
    }}

    /* ========================================================= */
    /*  QToolBar                                                  */
    /* ========================================================= */
    QToolBar {{
        background-color: {_C['BG_CARD']};
        border-bottom: 1px solid {_C['BORDER']};
        spacing: 4px;
        padding: 2px;
    }}
    QToolBar::separator {{
        background-color: {_C['BORDER']};
        width: 1px;
        margin: 4px 6px;
    }}

    /* ========================================================= */
    /*  QMenuBar / QMenu                                          */
    /* ========================================================= */
    QMenuBar {{
        background-color: {_C['BG_CARD']};
        color: {_C['TEXT_PRIMARY']};
        border-bottom: 1px solid {_C['BORDER']};
    }}
    QMenuBar::item:selected {{
        background-color: {_C['BG_INPUT']};
        color: {_C['ACCENT_BLUE']};
    }}
    QMenu {{
        background-color: {_C['BG_CARD']};
        color: {_C['TEXT_PRIMARY']};
        border: 1px solid {_C['BORDER']};
        border-radius: 6px;
        padding: 4px 0;
    }}
    QMenu::item {{
        padding: 6px 24px;
    }}
    QMenu::item:selected {{
        background-color: {_C['BG_INPUT']};
        color: {_C['ACCENT_BLUE']};
    }}
    QMenu::separator {{
        height: 1px;
        background-color: {_C['BORDER']};
        margin: 4px 8px;
    }}

    /* ========================================================= */
    /*  QStatusBar                                                */
    /* ========================================================= */
    QStatusBar {{
        background-color: {_C['BG_CARD']};
        color: {_C['TEXT_SECONDARY']};
        border-top: 1px solid {_C['BORDER']};
    }}

    /* ========================================================= */
    /*  QMessageBox                                               */
    /* ========================================================= */
    QMessageBox {{
        background-color: {_C['BG_CARD']};
    }}
    QMessageBox QLabel {{
        color: {_C['TEXT_PRIMARY']};
    }}

    /* ========================================================= */
    /*  QScrollBar - 細窄深色滾動條                                */
    /* ========================================================= */
    QScrollBar:vertical {{
        background-color: {_C['BG_DARK']};
        width: 8px;
        margin: 0;
        border: none;
    }}
    QScrollBar::handle:vertical {{
        background-color: {_C['BORDER']};
        min-height: 30px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {_C['TEXT_SECONDARY']};
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {{
        background: none;
    }}

    QScrollBar:horizontal {{
        background-color: {_C['BG_DARK']};
        height: 8px;
        margin: 0;
        border: none;
    }}
    QScrollBar::handle:horizontal {{
        background-color: {_C['BORDER']};
        min-width: 30px;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background-color: {_C['TEXT_SECONDARY']};
    }}
    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
    QScrollBar::add-page:horizontal,
    QScrollBar::sub-page:horizontal {{
        background: none;
    }}

    /* ========================================================= */
    /*  QToolTip                                                  */
    /* ========================================================= */
    QToolTip {{
        background-color: {_C['BG_CARD']};
        color: {_C['TEXT_PRIMARY']};
        border: 1px solid {_C['BORDER']};
        border-radius: 4px;
        padding: 6px 10px;
        font-size: 12px;
    }}

    /* ========================================================= */
    /*  QGroupBox                                                 */
    /* ========================================================= */
    QGroupBox {{
        border: 1px solid {_C['BORDER']};
        border-radius: 6px;
        margin-top: 12px;
        padding-top: 16px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        color: {_C['TEXT_SECONDARY']};
    }}

    /* ========================================================= */
    /*  QDialog                                                   */
    /* ========================================================= */
    QDialog {{
        background-color: {_C['BG_CARD']};
    }}
    """


def get_matplotlib_style() -> dict:
    """
    回傳可直接套用於 matplotlib.rcParams.update() 的深色繪圖風格字典。
    """
    return {
        # 畫布背景
        "figure.facecolor":   _C["BG_CARD"],
        "figure.edgecolor":   _C["BG_CARD"],
        # 繪圖區域背景
        "axes.facecolor":     _C["BG_DARK"],
        "axes.edgecolor":     _C["BORDER"],
        "axes.labelcolor":    _C["TEXT_PRIMARY"],
        "axes.titlecolor":    _C["TEXT_PRIMARY"],
        # 格線
        "axes.grid":          True,
        "grid.color":         _C["BORDER"],
        "grid.alpha":         0.4,
        "grid.linestyle":     "--",
        # 刻度
        "xtick.color":        _C["TEXT_SECONDARY"],
        "ytick.color":        _C["TEXT_SECONDARY"],
        "xtick.labelcolor":   _C["TEXT_SECONDARY"],
        "ytick.labelcolor":   _C["TEXT_SECONDARY"],
        # 文字
        "text.color":         _C["TEXT_PRIMARY"],
        # 圖例
        "legend.facecolor":   _C["BG_CARD"],
        "legend.edgecolor":   _C["BORDER"],
        "legend.labelcolor":  _C["TEXT_PRIMARY"],
        "legend.fontsize":    10,
        # 色彩循環 - 使用主題強調色
        "axes.prop_cycle":    __import__("cycler").cycler(
            color=[
                _C["ACCENT_BLUE"],
                _C["ACCENT_GREEN"],
                _C["ACCENT_RED"],
                _C["ACCENT_ORANGE"],
                _C["ACCENT_PURPLE"],
                "#8ba4bf",
                "#7ab88d",
                "#c9a455",
            ]
        ),
        # 線條
        "lines.linewidth":    1.5,
        # 儲存圖片預設背景
        "savefig.facecolor":  _C["BG_CARD"],
        "savefig.edgecolor":  _C["BG_CARD"],
        "savefig.transparent": False,
        # 字型
        "font.family":        "sans-serif",
        "font.sans-serif":    [
            "Microsoft JhengHei", "Segoe UI", "Noto Sans TC", "DejaVu Sans"
        ],
    }
