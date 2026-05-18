"""Tests for file tag system."""

import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from filepilot.core.tag_manager import DEFAULT_COLORS, TagManager


class TestTagManager(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file = Path(self.temp_dir.name) / "test.txt"
        self.test_file.write_text("test content")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _make_tm(self):
        tm = TagManager()
        mock_file = Path(tempfile.gettempdir()) / f"test_tags_{id(self)}.json"
        with patch.object(tm, "_load"), patch.object(tm, "_save"):
            tm._tags = {}
            return tm, mock_file

    def test_add_tag(self):
        tm = TagManager()
        with patch.object(tm, "_save"):
            tm.add_tag(self.test_file, "important")
        self.assertIn("important", tm.get_tags(self.test_file))

    def test_add_tag_with_color(self):
        tm = TagManager()
        with patch.object(tm, "_save"):
            tm.add_tag(self.test_file, "urgent", "#FF0000")
        self.assertEqual("#FF0000", tm.get_color(self.test_file))

    def test_remove_tag(self):
        tm = TagManager()
        with patch.object(tm, "_save"):
            tm.add_tag(self.test_file, "temp")
            tm.remove_tag(self.test_file, "temp")
        self.assertEqual([], tm.get_tags(self.test_file))

    def test_has_tag(self):
        tm = TagManager()
        with patch.object(tm, "_save"):
            tm.add_tag(self.test_file, "review")
        self.assertTrue(tm.has_tag(self.test_file, "review"))
        self.assertFalse(tm.has_tag(self.test_file, "other"))

    def test_find_by_tag(self):
        tm = TagManager()
        file1 = Path(self.temp_dir.name) / "file1.txt"
        file2 = Path(self.temp_dir.name) / "file2.txt"
        file1.write_text("1")
        file2.write_text("2")
        with patch.object(tm, "_save"):
            tm.add_tag(file1, "shared")
            tm.add_tag(file2, "shared")
        results = tm.find_by_tag("shared")
        self.assertEqual(2, len(results))

    def test_get_all_tags(self):
        tm = TagManager()
        file1 = Path(self.temp_dir.name) / "a.txt"
        file2 = Path(self.temp_dir.name) / "b.txt"
        file1.write_text("1")
        file2.write_text("2")
        with patch.object(tm, "_save"):
            tm.add_tag(file1, "alpha")
            tm.add_tag(file2, "beta")
        all_tags = tm.get_all_tags()
        self.assertIn("alpha", all_tags)
        self.assertIn("beta", all_tags)

    def test_remove_file(self):
        tm = TagManager()
        with patch.object(tm, "_save"):
            tm.add_tag(self.test_file, "tag1")
            tm.remove_file(self.test_file)
        self.assertEqual([], tm.get_tags(self.test_file))

    def test_cleanup_nonexistent(self):
        tm = TagManager()
        with patch.object(tm, "_save"):
            tm.add_tag(self.test_file, "valid")
            tm.add_tag(Path("/nonexistent/file.txt"), "orphan")
        removed = tm.cleanup_nonexistent()
        self.assertGreaterEqual(removed, 1)

    def test_default_colors(self):
        self.assertEqual(10, len(DEFAULT_COLORS))
        self.assertTrue(all(c.startswith("#") for c in DEFAULT_COLORS))
