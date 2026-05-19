"""Tests for AppState — centralized application state with signal emission."""

from unittest.mock import patch

from PySide6.QtCore import QObject

from filepilot.core.app_state import AppState, _get_dict, _get_list


class TestAppState:
    def test_default_settings(self):
        state = AppState()
        assert state.get("theme") == "dark"
        assert state.get("language") == "en"
        assert state.get("ai_mode") == "local"

    def test_init_with_custom_settings(self):
        state = AppState(settings={"theme": "light", "language": "zh"})
        assert state.get("theme") == "light"
        assert state.get("language") == "zh"
        assert state.get("ai_mode") == "local"

    def test_get_with_default(self):
        state = AppState()
        assert state.get("nonexistent") is None
        assert state.get("nonexistent", "fallback") == "fallback"

    def test_set(self):
        state = AppState()
        state.set("custom_key", "custom_value")
        assert state.get("custom_key") == "custom_value"

    def test_update(self):
        state = AppState()
        state.update({"theme": "light", "custom": 42})
        assert state.get("theme") == "light"
        assert state.get("custom") == 42

    def test_raw_is_mutable(self):
        state = AppState()
        state.raw["custom"] = "direct"
        assert state.get("custom") == "direct"

    def test_theme_changed(self, qtbot):
        state = AppState()
        with qtbot.waitSignal(state.theme_changed) as blocker:
            state.theme = "light"
        assert blocker.args == ["light"]
        assert state.theme == "light"

    def test_current_dir_changed(self, qtbot):
        state = AppState()
        with qtbot.waitSignal(state.current_dir_changed) as blocker:
            state.current_dir = "/some/path"
        assert blocker.args == ["/some/path"]
        assert state.current_dir == "/some/path"

    def test_current_dir_none_does_not_emit(self, qtbot):
        state = AppState()
        state.current_dir = "/test"
        signals = []

        state.current_dir_changed.connect(lambda p: signals.append(p))
        state.current_dir = None
        assert signals == []
        assert state.current_dir is None

    def test_recent_dirs(self, qtbot):
        state = AppState()
        assert state.recent_dirs == []

        with qtbot.waitSignal(state.recent_dirs_changed) as blocker:
            state.add_recent_dir("/first")
        assert blocker.args == [["/first"]]

        state.add_recent_dir("/second")
        assert state.recent_dirs == ["/second", "/first"]

    def test_recent_dirs_dedup(self, qtbot):
        state = AppState()
        state.add_recent_dir("/a")
        state.add_recent_dir("/b")
        state.add_recent_dir("/a")
        assert state.recent_dirs == ["/a", "/b"]

    def test_recent_dirs_max_entries(self):
        state = AppState()
        for i in range(5):
            state.add_recent_dir(f"/dir{i}", max_entries=3)
        assert state.recent_dirs == ["/dir4", "/dir3", "/dir2"]

    def test_recent_files_alias(self, qtbot):
        state = AppState()
        assert state.recent_files is not None
        assert isinstance(state.recent_files, list)

    def test_favorite_dirs(self, qtbot):
        state = AppState()
        assert state.favorite_dirs == []

        with qtbot.waitSignal(state.favorite_dirs_changed):
            state.set_favorite_dirs(["/fav1", "/fav2"])
        assert state.favorite_dirs == ["/fav1", "/fav2"]

    def test_search_history(self, qtbot):
        state = AppState()
        assert state.search_history == []

        with qtbot.waitSignal(state.search_history_changed) as blocker:
            state.add_search_history("hello")
        assert blocker.args == [["hello"]]

        state.add_search_history("world")
        assert state.search_history == ["world", "hello"]

    def test_search_history_dedup(self):
        state = AppState()
        state.add_search_history("test")
        state.add_search_history("test")
        assert state.search_history == ["test"]

    def test_file_tags(self):
        state = AppState()
        assert state.file_tags == {}
        state.set_file_tags({"key": "val"})
        assert state.file_tags == {"key": "val"}

    def test_file_browser_columns(self):
        state = AppState()
        assert isinstance(state.file_browser_columns, list)
        state.set_file_browser_columns(["name", "size"])
        assert state.file_browser_columns == ["name", "size"]

    def test_saved_searches(self):
        state = AppState()
        assert state.saved_searches == []
        searches = [{"name": "test", "query": "hello"}]
        state.set_saved_searches(searches)
        assert state.saved_searches == searches

    def test_tag_automation_rules(self):
        state = AppState()
        assert state.tag_automation_rules == []
        rules = [{"name": "rule1", "conditions": {}, "tags": ["tag1"]}]
        state.set_tag_automation_rules(rules)
        assert state.tag_automation_rules == rules

    def test_shortcuts_sets_settings_changed(self, qtbot):
        state = AppState()
        with qtbot.waitSignal(state.settings_changed) as blocker:
            state.set_shortcuts({"Ctrl+K": "search"})
        assert "shortcuts" in blocker.args[0]

    def test_save(self, qtbot):
        state = AppState()
        with patch("filepilot.core.config.save") as mock_save:
            with qtbot.waitSignal(state.settings_changed):
                state.save()
            mock_save.assert_called_once()

    def test_reload(self, qtbot):
        state = AppState()
        state.set("custom", "before")
        with patch("filepilot.core.config.load", return_value={"theme": "light"}) as mock_load:
            with qtbot.waitSignal(state.settings_changed):
                state.reload()
            mock_load.assert_called_once()
        assert state.theme == "light"
        assert state.get("custom") is None

    def test_parent(self):
        parent = QObject()
        state = AppState(parent=parent)
        assert state.parent() == parent

    def test_helpers_get_list(self):
        assert _get_list({"key": [1, 2]}, "key") == [1, 2]
        assert _get_list({}, "key") == []
        assert _get_list({"key": None}, "key") == []

    def test_helpers_get_dict(self):
        assert _get_dict({"key": {"a": 1}}, "key") == {"a": 1}
        assert _get_dict({}, "key") == {}
        assert _get_dict({"key": None}, "key") == {}
