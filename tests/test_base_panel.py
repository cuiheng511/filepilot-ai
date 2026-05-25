"""Tests for filepilot.ui.base_panel — shared panel base class"""

from PySide6.QtWidgets import QLabel

from filepilot.ui.base_panel import BasePanel


def test_base_panel_signals(qtbot):
    panel = BasePanel()
    qtbot.addWidget(panel)

    assert hasattr(panel, "progress_updated")
    assert hasattr(panel, "progress_text")
    assert hasattr(panel, "status_message")


def test_base_panel_make_stat_card(qtbot):
    panel = BasePanel()
    qtbot.addWidget(panel)

    card = panel._make_stat_card("Files", "42")
    assert card is not None
    # Card should contain both title and value labels
    labels = card.findChildren(QLabel)
    texts = [lb.text() for lb in labels]
    assert "Files" in texts
    assert "42" in texts


def test_base_panel_update_stat(qtbot):
    panel = BasePanel()
    qtbot.addWidget(panel)

    card = panel._make_stat_card("Files", "0")
    panel._update_stat("Files", "99")
    labels = card.findChildren(QLabel)
    values = [lb for lb in labels if lb.text() == "99"]
    assert len(values) >= 1


def test_base_panel_cancel_tracking(qtbot):
    panel = BasePanel()
    qtbot.addWidget(panel)

    panel._cancelled = False
    assert not panel._cancelled
    panel._cancelled = True
    assert panel._cancelled


def test_base_panel_default_state(qtbot):
    panel = BasePanel()
    qtbot.addWidget(panel)
    assert hasattr(panel, "_cancelled")
    assert panel._cancelled is False
    assert hasattr(panel, "btn_cancel")
    assert not panel.btn_cancel.isVisible()
