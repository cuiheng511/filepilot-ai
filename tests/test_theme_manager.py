"""Tests for filepilot.styles.manager — ThemeManager"""

from filepilot.styles.manager import ThemeManager


def test_theme_manager_available_themes(tmp_path):
    (tmp_path / "dark.qss").write_text("")
    (tmp_path / "light.qss").write_text("")
    mgr = ThemeManager(tmp_path)
    themes = mgr.available_themes()
    assert "dark" in themes
    assert "light" in themes


def test_available_themes_empty_dir(tmp_path):
    mgr = ThemeManager(tmp_path)
    assert mgr.available_themes() == []


def test_available_themes_ignores_non_qss(tmp_path):
    (tmp_path / "dark.qss").write_text("")
    (tmp_path / "notes.txt").write_text("hello")
    mgr = ThemeManager(tmp_path)
    themes = mgr.available_themes()
    assert "dark" in themes
    assert "notes" not in themes


def test_current_theme_default(tmp_path):
    mgr = ThemeManager(tmp_path)
    assert mgr.current_theme is None or isinstance(mgr.current_theme, str)
