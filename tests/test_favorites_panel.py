"""Tests for filepilot.ui.favorites_panel — Favorites CRUD with persistence"""

from filepilot.ui.favorites_panel import FavoritesPanel


def test_favorites_panel_init(qtbot):
    panel = FavoritesPanel()
    qtbot.addWidget(panel)
    assert panel is not None


def test_contains_path(qtbot):
    panel = FavoritesPanel()
    qtbot.addWidget(panel)
    assert not panel.contains_path("C:\\missing")
    # Add directly to favorites list (internal)
    panel.favorites.append({"path": "C:\\foo", "name": "foo"})
    assert panel.contains_path("C:\\foo")


def test_set_current_dir(qtbot):
    panel = FavoritesPanel()
    qtbot.addWidget(panel)
    panel.set_current_dir("C:\\some\\dir")
    assert panel._current_dir == "C:\\some\\dir"


def test_refresh_does_not_crash(qtbot):
    panel = FavoritesPanel()
    qtbot.addWidget(panel)
    panel.refresh()  # should not raise
