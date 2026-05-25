"""Tests for filepilot.ui.preview_panel — async file preview"""

from filepilot.ui.preview_panel import PreviewPanel


def test_preview_panel_init(qtbot):
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    assert panel is not None


def test_preview_starts_empty(qtbot):
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    assert panel._current_preview_path is None


def test_clear_preview(qtbot):
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    panel.clear()
    assert panel._current_preview_path is None
