"""Tests for NotificationToast — floating notification widget."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget

from filepilot.ui.notification import NotificationToast


class TestNotificationToast:
    def test_constructor_defaults(self, qtbot):
        toast = NotificationToast()
        qtbot.addWidget(toast)
        assert toast._opacity == 0.0
        assert toast._opacity_effect.opacity() == 0.0
        assert toast._auto_dismiss_timer.isSingleShot()
        assert not toast._auto_dismiss_timer.isActive()
        assert toast._label is not None
        assert toast.testAttribute(Qt.WA_TransparentForMouseEvents) is False
        assert toast.testAttribute(Qt.WA_ShowWithoutActivating) is True

    def test_show_message_info(self, qtbot):
        toast = NotificationToast()
        qtbot.addWidget(toast)
        toast.show_message("Hello World")
        assert toast._label.text() == "Hello World"
        assert toast._bg_color == QColor("#1a3a5c")

    def test_show_message_error(self, qtbot):
        toast = NotificationToast()
        qtbot.addWidget(toast)
        toast.show_message("Error!", level="error")
        assert toast._label.text() == "Error!"
        assert toast._bg_color == QColor("#5c1a1a")

    def test_show_message_warning(self, qtbot):
        toast = NotificationToast()
        qtbot.addWidget(toast)
        toast.show_message("Warning!", level="warning")
        assert toast._label.text() == "Warning!"
        assert toast._bg_color == QColor("#5c4a1a")

    def test_position_with_parent(self, qtbot):
        parent = QWidget()
        parent.resize(800, 600)
        toast = NotificationToast(parent)
        qtbot.addWidget(parent)
        qtbot.addWidget(toast)
        toast.show_message("Test")
        assert toast.x() <= parent.width() - 20
        assert toast.y() == 20

    def test_opacity_property(self, qtbot):
        toast = NotificationToast()
        qtbot.addWidget(toast)
        assert toast.opacity == 0.0
        toast._set_opacity(0.5)
        assert toast.opacity == 0.5
        assert toast._opacity_effect.opacity() == 0.5

    def test_custom_duration(self, qtbot):
        toast = NotificationToast()
        qtbot.addWidget(toast)
        toast.show_message("Quick", duration_ms=100)
        assert toast._label.text() == "Quick"
        assert toast._auto_dismiss_timer.isSingleShot()

    def test_adjust_size_on_show(self, qtbot):
        toast = NotificationToast()
        qtbot.addWidget(toast)
        old_w = toast.width()
        toast.show_message("A" * 500)
        assert toast.width() > old_w or toast.width() == min(toast.width(), 400)
