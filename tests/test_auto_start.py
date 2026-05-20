"""Auto-start tests — platform detection and registry/file operations."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from filepilot.auto_start import is_auto_start_enabled, set_auto_start


class TestWindows:
    def test_is_enabled_winreg_key_exists(self):
        fake_winreg = MagicMock()
        fake_winreg.OpenKey.return_value.__enter__.return_value = MagicMock()
        fake_winreg.QueryValueEx.return_value = ("value", 1)
        with (
            patch("filepilot.auto_start.sys.platform", "win32"),
            patch("filepilot.auto_start._winreg", return_value=fake_winreg),
        ):
            assert is_auto_start_enabled() is True

    def test_is_enabled_winreg_key_missing(self):
        fake_winreg = MagicMock()
        fake_winreg.OpenKey.side_effect = FileNotFoundError
        with (
            patch("filepilot.auto_start.sys.platform", "win32"),
            patch("filepilot.auto_start._winreg", return_value=fake_winreg),
        ):
            assert is_auto_start_enabled() is False

    def test_set_enabled_writes_registry(self):
        fake_winreg = MagicMock()
        fake_winreg.CreateKeyEx.return_value.__enter__.return_value = MagicMock()
        with (
            patch("filepilot.auto_start.sys.platform", "win32"),
            patch("filepilot.auto_start._winreg", return_value=fake_winreg),
        ):
            set_auto_start(True)
            fake_winreg.SetValueEx.assert_called_once()

    def test_set_disabled_deletes_registry(self):
        fake_winreg = MagicMock()
        fake_winreg.CreateKeyEx.return_value.__enter__.return_value = MagicMock()
        with (
            patch("filepilot.auto_start.sys.platform", "win32"),
            patch("filepilot.auto_start._winreg", return_value=fake_winreg),
        ):
            set_auto_start(False)
            fake_winreg.DeleteValue.assert_called_once()


class TestLinux:
    def test_is_enabled_desktop_exists(self, tmp_path):
        desk = tmp_path / "filepilot-ai.desktop"
        desk.write_text("dummy")
        with (
            patch("filepilot.auto_start.sys.platform", "linux"),
            patch("filepilot.auto_start._LINUX_DESKTOP", desk),
        ):
            assert is_auto_start_enabled() is True

    def test_is_enabled_desktop_missing(self):
        with (
            patch("filepilot.auto_start.sys.platform", "linux"),
            patch("filepilot.auto_start._LINUX_DESKTOP", Path("/nonexistent/desktop")),
        ):
            assert is_auto_start_enabled() is False

    def test_set_enabled_creates_desktop(self, tmp_path):
        desk = tmp_path / "filepilot-ai.desktop"
        with (
            patch("filepilot.auto_start.sys.platform", "linux"),
            patch("filepilot.auto_start._LINUX_DESKTOP", desk),
            patch("filepilot.auto_start._get_executable", return_value="/usr/bin/filepilot"),
        ):
            set_auto_start(True)
            assert desk.exists()
            assert "Name=FilePilot AI" in desk.read_text()

    def test_set_disabled_removes_desktop(self, tmp_path):
        desk = tmp_path / "filepilot-ai.desktop"
        desk.write_text("dummy")
        with (
            patch("filepilot.auto_start.sys.platform", "linux"),
            patch("filepilot.auto_start._LINUX_DESKTOP", desk),
        ):
            set_auto_start(False)
            assert not desk.exists()


class TestMacOS:
    def test_is_enabled_plist_exists(self, tmp_path):
        plist = tmp_path / "com.filepilot-ai.plist"
        plist.write_text("dummy")
        with (
            patch("filepilot.auto_start.sys.platform", "darwin"),
            patch("filepilot.auto_start._MACOS_PLIST", plist),
        ):
            assert is_auto_start_enabled() is True

    def test_set_enabled_creates_plist(self, tmp_path):
        plist = tmp_path / "com.filepilot-ai.plist"
        with (
            patch("filepilot.auto_start.sys.platform", "darwin"),
            patch("filepilot.auto_start._MACOS_PLIST", plist),
            patch(
                "filepilot.auto_start._get_executable_args",
                return_value=["/usr/local/bin/python", "-m", "filepilot.main"],
            ),
        ):
            set_auto_start(True)
            assert plist.exists()
            text = plist.read_text()
            assert "com.filepilot-ai" in text
            assert "<string>/usr/local/bin/python</string>" in text
            assert "<string>-m</string>" in text
            assert "<string>filepilot.main</string>" in text

    def test_set_disabled_removes_plist(self, tmp_path):
        plist = tmp_path / "com.filepilot-ai.plist"
        plist.write_text("dummy")
        with (
            patch("filepilot.auto_start.sys.platform", "darwin"),
            patch("filepilot.auto_start._MACOS_PLIST", plist),
        ):
            set_auto_start(False)
            assert not plist.exists()


class TestGeneric:
    def test_non_windows_fallback(self):
        """Unknown platform should not crash — returns False."""
        with (
            patch("filepilot.auto_start.sys.platform", "unknown"),
            patch("filepilot.auto_start._linux_is_enabled", return_value=False),
        ):
            assert is_auto_start_enabled() is False

    def test_set_non_windows_noop(self):
        with (
            patch("filepilot.auto_start.sys.platform", "unknown"),
            patch("filepilot.auto_start._linux_is_enabled"),
            patch("filepilot.auto_start._macos_is_enabled"),
            patch("filepilot.auto_start._windows_is_enabled"),
        ):
            set_auto_start(True)  # should not raise
