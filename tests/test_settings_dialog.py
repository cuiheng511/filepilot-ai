"""SettingsDialog unit tests — language switching, provider mapping, file size parsing.

Strategy: bypass Qt __init__, use simple state-tracking mocks to test logic.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QTabWidget

from filepilot.i18n import SUPPORTED_LANGUAGES
from filepilot.ui.settings_dialog import SettingsDialog


def _make_settings():
    return {
        "ai_mode": "local",
        "ai_provider": "ollama",
        "ai_model": "qwen2.5:7b",
        "ai_api_base": "http://localhost:11434",
        "ai_api_key": "",
        "index_dir": str(Path.home() / ".filepilot" / "index"),
        "max_file_size_mb": 500,
        "theme": "dark",
        "language": "en",
        "recent_dirs": [],
        "minimize_to_tray": True,
        "close_to_tray": True,
        "auto_start": False,
    }


class _ComboBox:
    """Lightweight mock of QComboBox that tracks currentIndex."""

    def __init__(self, initial_index=0):
        self._idx = initial_index

    def currentIndex(self):
        return self._idx

    def setCurrentIndex(self, idx):
        self._idx = idx

    def count(self):
        return 5

    def currentText(self):
        return f"mocked_text ({self._idx})"

    def itemText(self, idx):
        return f"Item {idx}"


def _make_dialog(settings_dict=None):
    """Create a SettingsDialog instance bypassing Qt __init__."""
    settings_dict = settings_dict or _make_settings()
    obj = SettingsDialog.__new__(SettingsDialog)
    obj._settings = settings_dict.copy()
    obj._current_lang = settings_dict.get("language", "en")
    obj.state = None
    obj.event_bus = None

    # Provider combo
    provider_map = {"ollama": 0, "llamacpp": 1, "openai": 2, "anthropic": 3, "custom": 4}
    obj.provider_combo = _ComboBox(provider_map.get(settings_dict.get("ai_provider", "ollama"), 0))

    # Model input
    obj.model_input = MagicMock()
    obj.model_input.currentText.return_value = settings_dict.get("ai_model", "qwen2.5:7b")

    # API base
    obj.api_base_input = MagicMock()
    obj.api_base_input.text.return_value = settings_dict.get(
        "ai_api_base", "http://localhost:11434"
    )

    # API key
    obj.api_key_input = MagicMock()
    obj.api_key_input.text.return_value = settings_dict.get("ai_api_key", "")

    # Max file size
    obj.max_file_size = MagicMock()
    obj.max_file_size.text.return_value = str(settings_dict.get("max_file_size_mb", 500))

    # Index dir
    obj.index_dir = MagicMock()
    obj.index_dir.text.return_value = settings_dict.get(
        "index_dir", str(Path.home() / ".filepilot" / "index")
    )

    # Language combo
    lang_keys = list(SUPPORTED_LANGUAGES.keys())
    default_lang_idx = lang_keys.index(settings_dict.get("language", "en"))
    obj.lang_combo = _ComboBox(default_lang_idx)

    # Tray / auto-start checkboxes
    obj.minimize_to_tray_cb = MagicMock()
    obj.minimize_to_tray_cb.isChecked.return_value = settings_dict.get("minimize_to_tray", True)
    obj.close_to_tray_cb = MagicMock()
    obj.close_to_tray_cb.isChecked.return_value = settings_dict.get("close_to_tray", True)
    obj.auto_start_cb = MagicMock()
    obj.auto_start_cb.isChecked.return_value = settings_dict.get("auto_start", False)

    return obj


# ── Language switching ──────────────────────────────────────────────


class TestLanguageSwitching:
    def test_language_change_calls_set_language(self):
        d = _make_dialog()
        # Set current lang to something different so the change is detected
        d._current_lang = "en"
        d.lang_combo.setCurrentIndex(2)  # Japanese
        mock_sl = MagicMock()
        with (
            patch("filepilot.ui.settings_dialog.set_language", mock_sl),
            patch("PySide6.QtWidgets.QDialog.accept", lambda self: None),
        ):
            d.accept()
        mock_sl.assert_called_once_with("ja")

    def test_no_language_change_skips_set_language(self):
        d = _make_dialog()
        d._current_lang = "en"
        # Don't change the lang combo — stays at English (index 0)
        mock_sl = MagicMock()
        with (
            patch("filepilot.ui.settings_dialog.set_language", mock_sl),
            patch("PySide6.QtWidgets.QDialog.accept", lambda self: None),
        ):
            d.accept()
        mock_sl.assert_not_called()

    def test_get_settings_reflects_language(self):
        d = _make_dialog()
        d.lang_combo.setCurrentIndex(2)
        r = d.get_settings()
        assert r["language"] == "ja"

    def test_initial_english_selected(self):
        d = _make_dialog()
        assert d.lang_combo.currentIndex() == 0


# ── Provider mapping ────────────────────────────────────────────────


class TestGetSettings:
    def test_all_keys_present(self):
        d = _make_dialog()
        r = d.get_settings()
        for k in (
            "ai_mode",
            "ai_provider",
            "ai_model",
            "ai_api_base",
            "ai_api_key",
            "index_dir",
            "max_file_size_mb",
            "language",
            "minimize_to_tray",
            "close_to_tray",
            "auto_start",
        ):
            assert k in r

    @pytest.mark.parametrize(
        ("idx", "provider", "mode"),
        [
            (0, "ollama", "local"),
            (1, "llamacpp", "local"),
            (2, "openai", "cloud"),
            (3, "anthropic", "cloud"),
            (4, "custom", "cloud"),
        ],
    )
    def test_provider_variations(self, idx, provider, mode):
        d = _make_dialog()
        d.provider_combo.setCurrentIndex(idx)
        r = d.get_settings()
        assert r["ai_provider"] == provider
        assert r["ai_mode"] == mode


class TestSettingsLayout:
    def test_updates_are_consolidated_into_general_tab(self, qtbot):
        dialog = SettingsDialog(settings=_make_settings())
        qtbot.addWidget(dialog)

        tabs = dialog.findChild(QTabWidget)
        tab_names = [tabs.tabText(i) for i in range(tabs.count())]

        assert tabs.count() == 4
        assert "Updates" not in tab_names
        assert dialog.check_update_btn.text() == "Check for Updates"


# ── File size parsing (pure logic) ──────────────────────────────────


class TestFileSizeParsing:
    def test_valid_number(self):
        d = _make_dialog()
        assert d._parse_file_size("100") == 100
        assert d._parse_file_size("500") == 500

    def test_empty_returns_default(self):
        d = _make_dialog()
        assert d._parse_file_size("") == 500
        assert d._parse_file_size("   ") == 500

    def test_negative_accepted(self):
        d = _make_dialog()
        assert d._parse_file_size("-50") == -50

    def test_invalid_returns_default(self):
        d = _make_dialog()
        assert d._parse_file_size("abc") == 500


# ── Update tab ───────────────────────────────────────────────────────


class TestUpdateTab:
    def test_check_updates_disables_button(self):
        """_on_check_updates should disable the check button and show status."""
        d = _make_dialog()
        d.check_update_btn = MagicMock()
        d.download_update_btn = MagicMock()
        d.update_status_label = MagicMock()
        d.update_version_label = MagicMock()
        d._update_checker = MagicMock()
        d._on_check_updates()
        d.check_update_btn.setEnabled.assert_called_with(False)
        d.update_status_label.setText.assert_called_with("Checking for updates...")

    def test_update_result_has_update_shows_download(self):
        from filepilot.updater import ReleaseInfo, UpdateCheckResult

        d = _make_dialog()
        d.check_update_btn = MagicMock()
        d.download_update_btn = MagicMock()
        d.update_status_label = MagicMock()
        d.update_version_label = MagicMock()

        release = ReleaseInfo(
            version="2.0.0",
            title="v2.0.0",
            body="Major update",
            published_at="2026-05-01",
            html_url="https://example.com",
            download_url="https://example.com/pkg.exe",
            download_size=5000000,
        )
        result = UpdateCheckResult(
            has_update=True,
            current_version="1.0.0",
            release=release,
        )
        d._on_update_result(result)
        d.download_update_btn.setVisible.assert_called_with(True)
        d.download_update_btn.setEnabled.assert_called_with(True)

    def test_update_result_up_to_date_hides_download(self):
        from filepilot.updater import UpdateCheckResult

        d = _make_dialog()
        d.check_update_btn = MagicMock()
        d.download_update_btn = MagicMock()
        d.update_status_label = MagicMock()
        d.update_version_label = MagicMock()

        result = UpdateCheckResult(
            has_update=False,
            current_version="1.0.0",
        )
        d._on_update_result(result)
        d.download_update_btn.setVisible.assert_called_with(False)

    def test_update_result_error_shows_warning(self):
        from filepilot.updater import UpdateCheckResult

        d = _make_dialog()
        d.check_update_btn = MagicMock()
        d.download_update_btn = MagicMock()
        d.update_status_label = MagicMock()
        d.update_version_label = MagicMock()

        result = UpdateCheckResult(
            has_update=False,
            current_version="1.0.0",
            error="Network error",
        )
        d._on_update_result(result)
        d.update_status_label.setText.assert_called_with("Check failed: Network error")
