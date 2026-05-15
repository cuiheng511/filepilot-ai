"""Tests for shortcut editor."""

import os
import sys
from unittest import TestCase

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

from filepilot.ui.shortcut_editor import DEFAULT_SHORTCUTS, ShortcutEditor  # noqa: E402


class TestShortcutEditorDefaults(TestCase):
    def test_default_shortcuts_count(self):
        self.assertGreaterEqual(len(DEFAULT_SHORTCUTS), 7)

    def test_default_shortcuts_unique(self):
        values = list(DEFAULT_SHORTCUTS.values())
        self.assertEqual(len(values), len(set(values)))

    def test_default_shortcuts_include_all_panels(self):
        self.assertIn("File Browser", DEFAULT_SHORTCUTS)
        self.assertIn("File Search", DEFAULT_SHORTCUTS)
        self.assertIn("Favorites", DEFAULT_SHORTCUTS)


class TestShortcutEditorWidget(TestCase):
    def test_get_overrides_empty_by_default(self):
        editor = ShortcutEditor()
        overrides = editor.get_overrides()
        self.assertEqual({}, overrides)

    def test_get_overrides_with_custom(self):
        custom = {"File Browser": "Ctrl+B"}
        editor = ShortcutEditor(overrides=custom)
        overrides = editor.get_overrides()
        self.assertEqual({"File Browser": "Ctrl+B"}, overrides)

    def test_reset_defaults_clears_overrides(self):
        custom = {"File Browser": "Ctrl+B", "File Search": "Ctrl+S"}
        editor = ShortcutEditor(overrides=custom)
        editor._reset_defaults()
        self.assertEqual({}, editor.get_overrides())

    def test_shortcuts_changed_signal_emitted_on_reset(self):
        editor = ShortcutEditor(overrides={"File Browser": "Ctrl+B"})
        signal_received = []
        editor.shortcuts_changed.connect(lambda d: signal_received.append(d))
        editor._reset_defaults()
        self.assertEqual(1, len(signal_received))
        self.assertEqual({}, signal_received[0])
