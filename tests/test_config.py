"""Config module unit tests — load/save/keyring round-trip"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from filepilot.core import config


@pytest.fixture
def tmp_settings_dir(tmp_path: Path) -> Path:
    """Provide a temporary settings directory."""
    d = tmp_path / ".filepilot"
    d.mkdir()
    return d


@pytest.fixture(autouse=True)
def _patch_dirs(tmp_settings_dir):
    """Patch SETTINGS_DIR and SETTINGS_FILE to use temp paths."""
    with (
        patch.object(config, "SETTINGS_DIR", tmp_settings_dir),
        patch.object(config, "SETTINGS_FILE", tmp_settings_dir / "settings.json"),
    ):
        yield


def _make_json(settings_dict: dict, path: Path):
    """Write a JSON settings file at the given path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings_dict, ensure_ascii=False, indent=2), encoding="utf-8")


# ── load() ──────────────────────────────────────────────────────────────


class TestLoad:
    def test_no_file_returns_defaults(self):
        result = config.load()
        assert result == config.DEFAULTS

    def test_loads_existing_file(self):
        overrides = {"ai_provider": "openai", "theme": "light"}
        _make_json(overrides, config.SETTINGS_FILE)

        result = config.load()
        assert result["ai_provider"] == "openai"
        assert result["theme"] == "light"
        assert result["ai_mode"] == "local"
        assert result["language"] == "en"

    def test_corrupt_json_returns_defaults(self):
        config.SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        config.SETTINGS_FILE.write_text("{{not json", encoding="utf-8")

        result = config.load()
        assert result == config.DEFAULTS

    def test_empty_file_returns_defaults(self):
        config.SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        config.SETTINGS_FILE.write_text("")

        result = config.load()
        assert result == config.DEFAULTS

    def test_io_error_during_parse_returns_defaults(self):
        _make_json({"ai_provider": "openai"}, config.SETTINGS_FILE)

        with patch("filepilot.core.config.json") as mock_json:
            mock_json.loads.side_effect = OSError("disk error")
            result = config.load()

        assert result == config.DEFAULTS


# ── load() + keyring ────────────────────────────────────────────────────


class TestLoadWithKeyring:
    def test_keyring_key_overrides_file_value(self):
        _make_json({"ai_api_key": "old_value"}, config.SETTINGS_FILE)

        with patch.object(config, "_get_keyring_key", return_value="keyring_secret"):
            result = config.load()

        assert result["ai_api_key"] == "keyring_secret"

    def test_empty_keyring_keeps_file_value(self):
        _make_json({"ai_api_key": "file_value"}, config.SETTINGS_FILE)

        with patch.object(config, "_get_keyring_key", return_value=""):
            result = config.load()

        assert result["ai_api_key"] == "file_value"

    def test_keyring_empty_migrates_file_value_to_keyring(self):
        _make_json({"ai_api_key": "migrate_me"}, config.SETTINGS_FILE)

        with (
            patch.object(config, "_get_keyring_key", return_value=""),
            patch.object(config, "_save_keyring_key", return_value=True) as mock_save,
        ):
            result = config.load()

        assert result["ai_api_key"] == "migrate_me"
        mock_save.assert_called_once_with("migrate_me")

    def test_both_empty_no_api_key(self):
        _make_json({"ai_api_key": ""}, config.SETTINGS_FILE)

        with (
            patch.object(config, "_get_keyring_key", return_value=""),
            patch.object(config, "_save_keyring_key", return_value=True) as mock_save,
        ):
            result = config.load()

        assert result["ai_api_key"] == ""
        mock_save.assert_not_called()


# ── _get_keyring_key() ────────────────────────────────────────────────


class TestGetKeyringKey:
    def test_returns_key_when_present(self):
        mock_kr = MagicMock()
        mock_kr.get_password.return_value = "mykey"
        with patch.dict("sys.modules", {"keyring": mock_kr}):
            result = config._get_keyring_key()
        assert result == "mykey"
        mock_kr.get_password.assert_called_once_with(
            config.KEYRING_SERVICE,
            config.KEYRING_KEY,
        )

    def test_returns_empty_on_exception(self):
        mock_kr = MagicMock()
        mock_kr.get_password.side_effect = Exception("keyring broken")
        # Use a mock encrypted key file that doesn't exist
        mock_file = MagicMock()
        mock_file.exists.return_value = False
        with (
            patch.dict("sys.modules", {"keyring": mock_kr}),
            patch.object(config, "ENCRYPTED_KEY_FILE", mock_file),
        ):
            result = config._get_keyring_key()
        assert result == ""


# ── _save_keyring_key() ────────────────────────────────────────────────


class TestSaveKeyringKey:
    def test_empty_key_returns_true_without_calling_keyring(self):
        mock_kr = MagicMock()
        with patch.dict("sys.modules", {"keyring": mock_kr}):
            result = config._save_keyring_key("")
        assert result is True
        mock_kr.set_password.assert_not_called()

    def test_nonempty_key_calls_keyring(self):
        mock_kr = MagicMock()
        with patch.dict("sys.modules", {"keyring": mock_kr}):
            result = config._save_keyring_key("secret123")
        assert result is True
        mock_kr.set_password.assert_called_once_with(
            config.KEYRING_SERVICE,
            config.KEYRING_KEY,
            "secret123",
        )

    def test_keyring_exception_returns_false(self):
        mock_kr = MagicMock()
        mock_kr.set_password.side_effect = Exception("no backend")
        # Also make the encrypted file fallback fail
        mock_file = MagicMock()
        mock_file.write_bytes.side_effect = OSError("disk full")
        mock_file.parent = MagicMock()
        with (
            patch.dict("sys.modules", {"keyring": mock_kr}),
            patch.object(config, "ENCRYPTED_KEY_FILE", mock_file),
        ):
            result = config._save_keyring_key("secret")
        assert result is False


# ── save() ──────────────────────────────────────────────────────────────


class TestSave:
    def test_creates_settings_dir(self, tmp_settings_dir):
        target_dir = tmp_settings_dir / "sub" / "deep"
        target_file = target_dir / "settings.json"
        with (
            patch.object(config, "SETTINGS_DIR", target_dir),
            patch.object(config, "SETTINGS_FILE", target_file),
        ):
            config.save(dict(config.DEFAULTS))

        assert target_dir.is_dir()
        assert target_file.exists()

    def test_saves_all_defaults(self):
        config.save(dict(config.DEFAULTS))

        data = json.loads(config.SETTINGS_FILE.read_text(encoding="utf-8"))
        for key, value in config.DEFAULTS.items():
            if key == "ai_api_key":
                continue
            assert data[key] == value

    def test_api_key_not_in_json(self):
        """api_key must never be written to the JSON file."""
        settings = dict(config.DEFAULTS)
        settings["ai_api_key"] = "super_secret"

        with patch.object(config, "_save_keyring_key", return_value=True) as mock_kr:
            config.save(settings)

        data = json.loads(config.SETTINGS_FILE.read_text(encoding="utf-8"))
        assert "ai_api_key" not in data
        mock_kr.assert_called_once_with("super_secret")

    def test_caller_dict_not_mutated(self):
        """save() must not mutate the caller's dict (regression test)."""
        original = dict(config.DEFAULTS)
        original["ai_api_key"] = "temp_key"
        original["theme"] = "light"
        original_ref = original.copy()

        with patch.object(config, "_save_keyring_key", return_value=True):
            config.save(original)

        assert original == original_ref, "save() mutated the caller's dict"
        assert original["ai_api_key"] == "temp_key"
        assert original["theme"] == "light"

    def test_empty_api_key_not_saved_to_keyring(self):
        settings = dict(config.DEFAULTS)
        settings["ai_api_key"] = ""

        with patch.object(config, "_save_keyring_key", return_value=True) as mock_kr:
            config.save(settings)

        mock_kr.assert_not_called()

    def test_io_error_logged_not_raised(self):
        """save() should not raise even if disk write fails."""
        settings = dict(config.DEFAULTS)
        settings["ai_api_key"] = ""

        with patch.object(
            config.SETTINGS_FILE.__class__, "write_text", side_effect=OSError("disk full")
        ):
            config.save(settings)


# ── Round-trip ──────────────────────────────────────────────────────────


class TestSaveLoadRoundtrip:
    def test_roundtrip_preserves_values(self):
        original = dict(config.DEFAULTS)
        original["ai_provider"] = "openai"
        original["theme"] = "light"
        original["language"] = "fr"
        original["recent_dirs"] = ["/home/user/projects"]

        with patch.object(config, "_save_keyring_key", return_value=True):
            config.save(original)

        result = config.load()
        assert result["ai_provider"] == "openai"
        assert result["theme"] == "light"
        assert result["language"] == "fr"
        assert result["recent_dirs"] == ["/home/user/projects"]

    def test_roundtrip_api_key(self):
        """API key survives save→load via keyring."""
        original = dict(config.DEFAULTS)
        original["ai_api_key"] = "sk-roundtrip-test"

        with (
            patch.object(config, "_save_keyring_key", return_value=True) as mock_save,
            patch.object(config, "_get_keyring_key", return_value="sk-roundtrip-test") as mock_get,
        ):
            config.save(original)
            result = config.load()

        mock_save.assert_called_once_with("sk-roundtrip-test")
        mock_get.assert_called_once()
        assert result["ai_api_key"] == "sk-roundtrip-test"
