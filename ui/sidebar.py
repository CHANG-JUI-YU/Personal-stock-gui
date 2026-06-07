# -*- coding: utf-8 -*-
"""
KRONOS X - Side Navigation
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QFrame, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt
from ui.theme import COLORS

_C = COLORS


class _NavButton(QPushButton):
    """Simple text navigation button with active state indicator."""

    _STYLE_NORMAL = f"""
        QPushButton {{
            background-color: transparent;
            color: {_C['TEXT_SECONDARY']};
            text-align: left;
            padding: 9px 16px;
            border: none;
            border-left: 2px solid transparent;
            font-size: 13px;
        }}
        QPushButton:hover {{
            color: {_C['TEXT_PRIMARY']};
            background-color: rgba(255, 255, 255, 0.03);
        }}
    """

    _STYLE_ACTIVE = f"""
        QPushButton {{
            background-color: rgba(255, 255, 255, 0.05);
            color: {_C['TEXT_PRIMARY']};
            text-align: left;
            padding: 9px 16px;
            border: none;
            border-left: 2px solid {_C['TEXT_PRIMARY']};
            font-size: 13px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: rgba(255, 255, 255, 0.07);
        }}
    """

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.setText(label)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(36)
        self.set_active(False)

    def set_active(self, active: bool):
        self.setStyleSheet(self._STYLE_ACTIVE if active else self._STYLE_NORMAL)


# Navigation structure: list of (label, group_label_or_None)
# None entry = group separator
_NAV_GROUPS = [
    ("Overview", [
        "Dashboard",
        "Watchlist",
    ]),
    ("Analysis", [
        "Stock Analysis",
        "Kronos XAI",
        "TimesFM XAI",
        "Pred. Compare",
    ]),
    ("Decision", [
        "TA Report",
        "Decision",
        "What If",
    ]),
    ("Evaluation", [
        "Backtest",
        "Calibration",
    ]),
    ("System", [
        "Settings",
    ]),
]


class Sidebar(QWidget):
    nav = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setFixedWidth(180)
        self.setStyleSheet(f"background-color: {_C['BG_SIDEBAR']};")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Title
        title_container = QWidget()
        title_container.setStyleSheet(f"background-color: {_C['BG_SIDEBAR']};")
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(16, 20, 16, 16)
        title_layout.setSpacing(0)

        app_title = QLabel("STOCKS")
        app_title.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {_C['TEXT_PRIMARY']}; "
            f"letter-spacing: 3px; background-color: transparent;"
        )
        title_layout.addWidget(app_title)
        layout.addWidget(title_container)

        # Navigation buttons by group
        self.buttons: list[_NavButton] = []
        page_index = 0

        for group_name, items in _NAV_GROUPS:
            # Group label
            group_label = QLabel(group_name.upper())
            group_label.setStyleSheet(
                f"font-size: 10px; color: {_C['TEXT_SECONDARY']}; "
                f"padding: 12px 16px 4px 16px; background-color: transparent; "
                f"letter-spacing: 1px;"
            )
            layout.addWidget(group_label)

            for label in items:
                btn = _NavButton(label)
                idx = page_index
                btn.clicked.connect(lambda checked, i=idx: self._on_nav(i))
                self.buttons.append(btn)
                layout.addWidget(btn)
                page_index += 1

        layout.addStretch(1)

        # Version
        ver_label = QLabel("v2.0")
        ver_label.setStyleSheet(
            f"color: {_C['BORDER']}; font-size: 10px; "
            f"padding: 8px 16px; background-color: transparent;"
        )
        layout.addWidget(ver_label)

        if self.buttons:
            self.buttons[0].set_active(True)
            self._active_index = 0

    def _on_nav(self, index: int):
        for i, btn in enumerate(self.buttons):
            btn.set_active(i == index)
        self._active_index = index
        self.nav.emit(index)

    def set_active_page(self, index: int):
        if 0 <= index < len(self.buttons):
            self._on_nav(index)
