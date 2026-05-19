"""Update checker tests."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from filepilot.updater import UpdateChecker


def _asset(name: str, size: int = 123) -> dict:
    return {
        "name": name,
        "size": size,
        "browser_download_url": f"https://example.test/{name}",
    }


def test_select_download_asset_windows(monkeypatch):
    monkeypatch.setattr("filepilot.updater.sys.platform", "win32")

    url, size = UpdateChecker._select_download_asset(
        [
            _asset("FilePilot-0.4.0-x86_64.AppImage"),
            _asset("FilePilot-0.4.0.dmg"),
            _asset("FilePilot-AI-Setup-0.4.0.exe", 456),
        ]
    )

    assert url == "https://example.test/FilePilot-AI-Setup-0.4.0.exe"
    assert size == 456


def test_select_download_asset_macos(monkeypatch):
    monkeypatch.setattr("filepilot.updater.sys.platform", "darwin")

    url, _ = UpdateChecker._select_download_asset(
        [
            _asset("FilePilot-0.4.0-x86_64.AppImage"),
            _asset("FilePilot-0.4.0.dmg"),
            _asset("FilePilot-AI-Setup-0.4.0.exe"),
        ]
    )

    assert url == "https://example.test/FilePilot-0.4.0.dmg"


def test_select_download_asset_linux_prefers_matching_arch(monkeypatch):
    monkeypatch.setattr("filepilot.updater.sys.platform", "linux")
    monkeypatch.setattr("filepilot.updater.platform.machine", lambda: "x86_64")

    url, _ = UpdateChecker._select_download_asset(
        [
            _asset("FilePilot-0.4.0-aarch64.AppImage"),
            _asset("FilePilot-0.4.0-x86_64.AppImage"),
        ]
    )

    assert url == "https://example.test/FilePilot-0.4.0-x86_64.AppImage"


def test_compare_versions_pads_missing_parts():
    assert UpdateChecker._compare_versions("0.4", "0.3.9") > 0
    assert UpdateChecker._compare_versions("0.4.0", "0.4") == 0


class TestDownloadInstall:
    """Tests for download() and install() methods."""

    def test_download_streams_to_file(self, tmp_path):
        dest = tmp_path / "installer.exe"
        fake_content = b"fake installer content"
        fake_resp = MagicMock()
        fake_resp.headers = {"content-length": str(len(fake_content))}
        fake_resp.iter_content.return_value = [fake_content]
        fake_resp.__enter__.return_value = fake_resp

        with patch("filepilot.updater.requests.get", return_value=fake_resp):
            result = UpdateChecker().download("https://example.test/pkg.exe", dest)

        assert result == dest
        assert dest.read_bytes() == fake_content

    def test_download_reports_progress(self, tmp_path):
        dest = tmp_path / "pkg.exe"
        chunks = [b"hello", b" ", b"world"]
        total_len = sum(len(c) for c in chunks)
        fake_resp = MagicMock()
        fake_resp.headers = {"content-length": str(total_len)}
        fake_resp.iter_content.return_value = chunks
        fake_resp.__enter__.return_value = fake_resp

        progress_log: list[int] = []

        def on_progress(pct: int):
            progress_log.append(pct)

        with patch("filepilot.updater.requests.get", return_value=fake_resp):
            UpdateChecker().download("https://example.test/pkg.exe", dest, on_progress)

        assert progress_log[-1] == 100  # final progress is 100%

    def test_download_raises_on_http_error(self, tmp_path):
        fake_resp = MagicMock()
        fake_resp.raise_for_status.side_effect = Exception("HTTP 404")
        fake_resp.__enter__.return_value = fake_resp

        with (
            patch("filepilot.updater.requests.get", return_value=fake_resp),
            pytest.raises(Exception, match="HTTP 404"),
        ):
            UpdateChecker().download("https://example.test/bad.exe", tmp_path / "bad.exe")

    def test_install_launches_subprocess_windows(self, tmp_path, monkeypatch):
        monkeypatch.setattr("filepilot.updater.sys.platform", "win32")
        installer = tmp_path / "FilePilot-AI-Setup-0.4.0.exe"
        installer.write_text("dummy")
        with patch("filepilot.updater.subprocess.Popen") as mock_popen:
            UpdateChecker().install(installer)
            mock_popen.assert_called_once_with([str(installer), "/S"], shell=False)

    def test_install_opens_dmg_macos(self, tmp_path, monkeypatch):
        monkeypatch.setattr("filepilot.updater.sys.platform", "darwin")
        dmg = tmp_path / "FilePilot-0.4.0.dmg"
        dmg.write_text("dummy")
        with patch("filepilot.updater.subprocess.Popen") as mock_popen:
            UpdateChecker().install(dmg)
            mock_popen.assert_called_once_with(["open", str(dmg)], shell=False)

    @pytest.mark.skipif(
        sys.platform.startswith("win"), reason="chmod bit check not meaningful on Windows"
    )
    def test_install_makes_appimage_executable(self, tmp_path, monkeypatch):
        monkeypatch.setattr("filepilot.updater.sys.platform", "linux")
        appimage = tmp_path / "FilePilot-0.4.0-x86_64.AppImage"
        appimage.write_text("dummy")
        with patch("filepilot.updater.subprocess.Popen") as mock_popen:
            UpdateChecker().install(appimage)
            assert appimage.stat().st_mode & 0o111  # executable bit set
            mock_popen.assert_called_once_with([str(appimage)], shell=False)
