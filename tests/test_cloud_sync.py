"""Tests for cloud sync provider detection."""

from filepilot.core import cloud_sync


def test_detect_cloud_providers_deduplicates_paths(tmp_path, monkeypatch):
    root = tmp_path / "OneDrive"
    root.mkdir()
    monkeypatch.setattr(
        cloud_sync,
        "_PROVIDER_PATHS",
        {"OneDrive": [str(root), str(root)], "Dropbox": [str(tmp_path / "missing")]},
    )

    providers = cloud_sync.detect_cloud_providers()

    assert len(providers) == 1
    assert providers[0].name == "OneDrive"
    assert providers[0].root_path == root


def test_get_cloud_status_batch_matches_relative_files(tmp_path, monkeypatch):
    root = tmp_path / "Dropbox"
    nested = root / "folder"
    nested.mkdir(parents=True)
    file_path = nested / "doc.txt"
    file_path.write_text("hello", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("nope", encoding="utf-8")
    monkeypatch.setattr(cloud_sync, "_PROVIDER_PATHS", {"Dropbox": [str(root)]})

    results = cloud_sync.get_cloud_status_batch([file_path, outside])

    assert results[str(file_path)].name == "Dropbox"
    assert results[str(outside)] is None


def test_onedrive_status_unknown_off_windows(monkeypatch):
    monkeypatch.setattr(cloud_sync.sys, "platform", "linux")

    assert cloud_sync.get_onedrive_file_status("/tmp/file.txt") == "unknown"
