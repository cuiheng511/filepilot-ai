"""Tests for tag_rules — tag automation rule engine."""

from unittest.mock import patch

import pytest

from filepilot.core.tag_rules import (
    add_rule,
    apply_rules_to_directory,
    apply_rules_to_files,
    delete_rule,
    get_rules,
    rule_matches,
    save_rules,
    update_rule,
)

_store: dict = {}


def _fake_load():
    return _store


def _fake_save(s):
    pass


@pytest.fixture(autouse=True)
def mock_config():
    with (
        patch("filepilot.core.tag_rules.load", side_effect=_fake_load),
        patch("filepilot.core.tag_rules.save", side_effect=_fake_save),
    ):
        yield


@pytest.fixture(autouse=True)
def reset_store():
    _store.clear()
    return


class TestGetRules:
    def test_default_empty(self):
        assert get_rules() == []

    def test_returns_saved_rules(self):
        save_rules([{"name": "test", "conditions": {}, "tags": ["t1"]}])
        rules = get_rules()
        assert len(rules) == 1
        assert rules[0]["name"] == "test"


class TestSaveRules:
    def test_overwrites_existing(self):
        save_rules([{"name": "a"}])
        save_rules([{"name": "b"}])
        assert len(get_rules()) == 1
        assert get_rules()[0]["name"] == "b"


class TestAddRule:
    def test_adds_rule(self):
        rule = add_rule("My Rule", {"extensions": [".pdf"]}, ["pdf_tag"])
        assert rule["name"] == "My Rule"
        assert rule["conditions"]["extensions"] == [".pdf"]
        assert rule["tags"] == ["pdf_tag"]
        assert len(get_rules()) == 1

    def test_appends_multiple(self):
        add_rule("R1", {}, ["t1"])
        add_rule("R2", {}, ["t2"])
        assert len(get_rules()) == 2


class TestUpdateRule:
    def test_updates_existing(self):
        add_rule("Original", {"extensions": [".txt"]}, ["text"])
        updated = update_rule(0, "Updated", {"categories": ["Code"]}, ["code"])
        assert updated["name"] == "Updated"
        assert get_rules()[0]["name"] == "Updated"

    def test_invalid_index_returns_none(self):
        assert update_rule(0, "x", {}, ["x"]) is None
        add_rule("Only", {}, ["t"])
        assert update_rule(5, "x", {}, ["x"]) is None


class TestDeleteRule:
    def test_deletes_existing(self):
        add_rule("ToDelete", {}, ["t"])
        assert delete_rule(0) is True
        assert get_rules() == []

    def test_invalid_index(self):
        assert delete_rule(0) is False
        assert delete_rule(-1) is False


class TestRuleMatches:
    def test_empty_conditions_match_all(self, tmp_path):
        f = tmp_path / "any.txt"
        f.write_text("test")
        assert rule_matches(f, {}) is True

    def test_extension_match(self, tmp_path):
        f = tmp_path / "doc.pdf"
        f.write_text("test")
        assert rule_matches(f, {"extensions": [".pdf"]}) is True
        assert rule_matches(f, {"extensions": [".txt"]}) is False

    def test_extension_match_without_dot(self, tmp_path):
        f = tmp_path / "doc.pdf"
        f.write_text("test")
        assert rule_matches(f, {"extensions": ["pdf"]}) is True

    def test_extension_or_logic(self, tmp_path):
        f = tmp_path / "doc.pdf"
        f.write_text("test")
        assert rule_matches(f, {"extensions": [".txt", ".pdf"]}) is True

    def test_category_match(self, tmp_path):
        f = tmp_path / "script.py"
        f.write_text("x=1")
        assert rule_matches(f, {"categories": ["Code"]}) is True

    def test_category_mismatch(self, tmp_path):
        f = tmp_path / "script.py"
        f.write_text("x=1")
        assert rule_matches(f, {"categories": ["PDF"]}) is False

    def test_size_min(self, tmp_path):
        f = tmp_path / "small.txt"
        f.write_text("a" * 100)
        assert rule_matches(f, {"min_size_mb": 1}) is False

    def test_size_max(self, tmp_path):
        f = tmp_path / "huge.txt"
        f.write_text("a" * 2 * 1024 * 1024)  # 2MB
        assert rule_matches(f, {"max_size_mb": 1}) is False
        assert rule_matches(f, {"max_size_mb": 3}) is True

    def test_size_filter_nonexistent_file(self, tmp_path):
        f = tmp_path / "nonexistent.txt"
        assert rule_matches(f, {"min_size_mb": 1}) is False

    def test_age_filter_nonexistent_file(self, tmp_path):
        f = tmp_path / "nonexistent.txt"
        assert rule_matches(f, {"max_age_days": 7}) is False

    def test_age_filter_recent_file(self, tmp_path):
        f = tmp_path / "recent.txt"
        f.write_text("test")
        assert rule_matches(f, {"max_age_days": 9999}) is True

    def test_all_filters_together(self, tmp_path):
        f = tmp_path / "report.pdf"
        f.write_text("test content")
        conditions = {
            "extensions": [".pdf"],
            "categories": ["PDF"],
            "min_size_mb": 0,
            "max_size_mb": 100,
            "max_age_days": 9999,
        }
        assert rule_matches(f, conditions) is True


class TestApplyRulesToFiles:
    def test_tags_matching_file(self, tmp_path):
        add_rule("TagPDFs", {"extensions": [".pdf"]}, ["pdf_doc"])
        f = tmp_path / "doc.pdf"
        f.write_text("test")
        with patch("filepilot.core.tag_rules.TagManager") as mock_tm:
            tm = mock_tm.return_value
            count = apply_rules_to_files([f])
            assert count == 1
            tm.add_tag.assert_called_once_with(f, "pdf_doc")

    def test_skips_nonexistent_files(self, tmp_path):
        add_rule("TagAll", {}, ["tag"])
        f = tmp_path / "nonexistent.txt"
        count = apply_rules_to_files([f])
        assert count == 0

    def test_applies_first_matching_rule_only(self, tmp_path):
        add_rule("First", {"extensions": [".txt"]}, ["first"])
        add_rule("Second", {"extensions": [".txt"]}, ["second"])
        f = tmp_path / "doc.txt"
        f.write_text("test")
        with patch("filepilot.core.tag_rules.TagManager") as mock_tm:
            tm = mock_tm.return_value
            count = apply_rules_to_files([f])
            assert count == 1
            tm.add_tag.assert_called_once_with(f, "first")


class TestApplyRulesToDirectory:
    def test_tags_files_in_directory(self, tmp_path):
        add_rule("TagCode", {"extensions": [".py"]}, ["code"])
        (tmp_path / "a.py").write_text("x=1")
        (tmp_path / "b.py").write_text("y=2")
        (tmp_path / "c.txt").write_text("hello")
        with patch("filepilot.core.tag_rules.TagManager") as mock_tm:
            tm = mock_tm.return_value
            count = apply_rules_to_directory(tmp_path, tm=tm)
            assert count == 2

    def test_no_rules_returns_zero(self, tmp_path):
        (tmp_path / "a.py").write_text("x=1")
        count = apply_rules_to_directory(tmp_path)
        assert count == 0

    def test_uses_provided_tag_manager(self, tmp_path):
        add_rule("TagAll", {}, ["t"])
        (tmp_path / "f.txt").write_text("test")
        with patch("filepilot.core.tag_rules.TagManager") as mock_tm:
            tm = mock_tm.return_value
            count = apply_rules_to_directory(tmp_path, tm=tm)
            assert count == 1
