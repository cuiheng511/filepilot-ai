"""Notification Toast — Non-blocking error/warning/info overlay widget"""

from PySide6.QtCore import Property, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QVBoxLayout, QWidget


class NotificationToast(QWidget):
    """Floating notification toast that auto-dismisses after a timeout"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setObjectName("notificationToast")

        self._opacity = 0.0
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._bg_color = QColor("#2d2d2d")
        self._auto_dismiss_timer = QTimer(self)
        self._auto_dismiss_timer.setSingleShot(True)
        self._auto_dismiss_timer.timeout.connect(self._start_fade_out)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        self._label = QLabel()
        self._label.setWordWrap(True)
        self._label.setStyleSheet("color: #e0e0e0; font-size: 13px;")
        layout.addWidget(self._label)

        self.setLayout(layout)
        self.adjustSize()

    def _get_opacity(self):
        return self._opacity

    def _set_opacity(self, value):
        self._opacity = value
        self._opacity_effect.setOpacity(value)

    opacity = Property(float, _get_opacity, _set_opacity)

    def show_message(self, text: str, level: str = "info", duration_ms: int = 3000):
        self._label.setText(text)

        if level == "error":
            self._bg_color = QColor("#5c1a1a")
        elif level == "warning":
            self._bg_color = QColor("#5c4a1a")
        else:
            self._bg_color = QColor("#1a3a5c")

        self.setStyleSheet(
            f"#notificationToast {{ background: {self._bg_color.name()}; "
            f"border: 1px solid {self._bg_color.lighter(130).name()}; "
            f"border-radius: 6px; }}"
        )
        self.adjustSize()
        self._position()
        self._start_fade_in(duration_ms)

    def _position(self):
        parent = self.parent()
        if parent:
            pr = parent.rect()
            x = pr.right() - self.width() - 20
            y = pr.top() + 20
            self.setGeometry(x, y, min(self.width(), 400), self.height())

    def _start_fade_in(self, duration_ms):
        self._opacity_effect.setOpacity(0.0)
        self.raise_()
        self.show()
        self.anim = QPropertyAnimation(self, b"opacity", self)
        self.anim.setDuration(200)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.finished.connect(lambda: self._auto_dismiss_timer.start(duration_ms))
        self.anim.start()

    def _start_fade_out(self):
        self.anim = QPropertyAnimation(self, b"opacity", self)
        self.anim.setDuration(300)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.finished.connect(self.hide)
        self.anim.start()
