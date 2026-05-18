"""Tests for plugin system."""

import tempfile
from pathlib import Path
from unittest import TestCase

from filepilot.core.plugin_system import BaseFileExtractor, PluginManager


class DummyExtractor(BaseFileExtractor):
    display_name = "Dummy"
    description = "Test extractor"
    version = "1.0.0"

    def supports(self, extension: str) -> bool:
        return extension == ".dummy"

    def extract_text(self, file_path: Path) -> str | None:
        return "dummy text"

    def extract_metadata(self, file_path: Path) -> dict:
        return {"key": "value"}


class TestBaseFileExtractor(TestCase):
    def test_supports(self):
        ext = DummyExtractor()
        self.assertTrue(ext.supports(".dummy"))
        self.assertFalse(ext.supports(".txt"))

    def test_extract_text(self):
        ext = DummyExtractor()
        with tempfile.NamedTemporaryFile(suffix=".dummy", delete=False) as f:
            f.write(b"test")
            path = Path(f.name)
        result = ext.extract_text(path)
        self.assertEqual("dummy text", result)
        path.unlink()

    def test_extract_metadata(self):
        ext = DummyExtractor()
        with tempfile.NamedTemporaryFile(suffix=".dummy", delete=False) as f:
            path = Path(f.name)
        meta = ext.extract_metadata(path)
        self.assertEqual({"key": "value"}, meta)
        path.unlink()

    def test_properties(self):
        ext = DummyExtractor()
        self.assertEqual("DummyExtractor", ext.name)
        self.assertEqual("Dummy", ext.display_name)
        self.assertEqual("1.0.0", ext.version)
        self.assertEqual("Test extractor", ext.description)

    def test_collect_extractors(self):
        class InlineExtractor(BaseFileExtractor):
            display_name = "Inline"

            def supports(self, extension: str) -> bool:
                return extension == ".xyz"

            def extract_text(self, file_path: Path) -> str | None:
                return "inline"

        result = PluginManager._collect_extractors(
            type("mod", (), {"InlineExtractor": InlineExtractor})()
        )
        self.assertEqual(1, len(result))
        self.assertIsInstance(result[0], InlineExtractor)

    def test_no_extractors_from_empty_module(self):
        result = PluginManager._collect_extractors(type("mod", (), {})())
        self.assertEqual([], result)

    def test_plugin_manager_no_dir(self):
        pm = PluginManager("/nonexistent/plugins")
        self.assertEqual([], pm.discover())


class TestPluginManager(TestCase):
    def test_plugins_dir_default(self):
        pm = PluginManager()
        self.assertTrue(str(pm.plugins_dir).endswith("plugins"))

    def test_discover_empty_dir(self):
        with tempfile.TemporaryDirectory() as d:
            pm = PluginManager(d)
            result = pm.discover()
            self.assertEqual([], result)

    def test_install_sample_plugin(self):
        with tempfile.TemporaryDirectory() as d:
            import filepilot.core.plugin_system as ps

            orig_dir = ps.PLUGINS_DIR
            ps.PLUGINS_DIR = Path(d)
            try:
                pm = PluginManager(d)
                path = PluginManager.install_sample_plugin()
                self.assertTrue(path.exists())
                result = pm.discover()
                self.assertGreaterEqual(len(result), 1)
            finally:
                ps.PLUGINS_DIR = orig_dir
