"""Update checker tests."""

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
