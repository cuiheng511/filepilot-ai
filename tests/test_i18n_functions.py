"""Tests for filepilot.i18n — t() fallback, set_language, interpolation"""

import pytest

from filepilot.i18n import get_language, set_language, t


def test_t_returns_translation():
    text = t("nav_search")
    assert isinstance(text, str)
    assert len(text) > 0


def test_t_fallback_key_returns_key_for_missing():
    result = t("__nonexistent_key_12345__")
    assert result == "__nonexistent_key_12345__"


def test_t_interpolation():
    result = t("confirm_delete_files", n=5)
    assert "{n}" not in result
    assert "5" in result


def test_set_and_get_language():
    prev = get_language()
    set_language("zh")
    assert get_language() == "zh"
    set_language(prev)
    assert get_language() == prev


def test_en_is_default():
    set_language("en")
    assert get_language() == "en"


def test_t_with_no_args():
    result = t("ready")
    assert isinstance(result, str)
    assert len(result) > 0


def test_switch_to_french():
    prev = get_language()
    set_language("fr")
    result = t("nav_search")
    assert isinstance(result, str)
    set_language(prev)


def test_all_known_keys_return_string():
    known_keys = [
        "app_name", "nav_search", "nav_browse", "nav_index", "nav_organize",
        "nav_duplicates", "nav_summary", "nav_tags", "nav_plugins_tip",
        "dashboard_title", "ready", "loading", "settings_title",
    ]
    for key in known_keys:
        val = t(key)
        assert isinstance(val, str), f"Key '{key}' returned non-string: {type(val)}"
        assert len(val) > 0, f"Key '{key}' returned empty string"
