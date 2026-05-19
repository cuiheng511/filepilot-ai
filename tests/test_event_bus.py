"""Tests for EventBus — signal emission and connection."""

from PySide6.QtCore import QObject

from filepilot.core.event_bus import EventBus


class TestEventBus:
    def test_signals_exist(self):
        bus = EventBus()
        assert hasattr(bus, "open_folder_requested")
        assert hasattr(bus, "open_file_requested")
        assert hasattr(bus, "switch_panel_requested")
        assert hasattr(bus, "global_search_requested")
        assert hasattr(bus, "file_tagged")
        assert hasattr(bus, "file_untagged")
        assert hasattr(bus, "files_deleted")
        assert hasattr(bus, "files_moved")
        assert hasattr(bus, "files_copied")
        assert hasattr(bus, "scan_requested")
        assert hasattr(bus, "index_requested")
        assert hasattr(bus, "scan_completed")
        assert hasattr(bus, "index_completed")
        assert hasattr(bus, "theme_toggled")
        assert hasattr(bus, "settings_applied")
        assert hasattr(bus, "dashboard_refresh_requested")

    def test_open_folder_requested(self, qtbot):
        bus = EventBus()
        with qtbot.waitSignal(bus.open_folder_requested) as blocker:
            bus.open_folder_requested.emit("/test/path")
        assert blocker.args == ["/test/path"]

    def test_open_file_requested(self, qtbot):
        bus = EventBus()
        with qtbot.waitSignal(bus.open_file_requested) as blocker:
            bus.open_file_requested.emit("/test/file.txt")
        assert blocker.args == ["/test/file.txt"]

    def test_switch_panel_requested(self, qtbot):
        bus = EventBus()
        with qtbot.waitSignal(bus.switch_panel_requested) as blocker:
            bus.switch_panel_requested.emit("browse")
        assert blocker.args == ["browse"]

    def test_global_search_requested(self, qtbot):
        bus = EventBus()
        with qtbot.waitSignal(bus.global_search_requested):
            bus.global_search_requested.emit()

    def test_file_tagged(self, qtbot):
        bus = EventBus()
        with qtbot.waitSignal(bus.file_tagged) as blocker:
            bus.file_tagged.emit("/path/to/file.py", ["important", "code"])
        assert blocker.args == ["/path/to/file.py", ["important", "code"]]

    def test_file_untagged(self, qtbot):
        bus = EventBus()
        with qtbot.waitSignal(bus.file_untagged) as blocker:
            bus.file_untagged.emit("/path/to/file.py", ["old_tag"])
        assert blocker.args == ["/path/to/file.py", ["old_tag"]]

    def test_files_deleted(self, qtbot):
        bus = EventBus()
        paths = ["/a.txt", "/b.txt"]
        with qtbot.waitSignal(bus.files_deleted) as blocker:
            bus.files_deleted.emit(paths)
        assert blocker.args == [paths]

    def test_files_moved(self, qtbot):
        bus = EventBus()
        paths = ["/a.txt", "/b.txt"]
        with qtbot.waitSignal(bus.files_moved) as blocker:
            bus.files_moved.emit(paths, "/dest")
        assert blocker.args == [paths, "/dest"]

    def test_files_copied(self, qtbot):
        bus = EventBus()
        paths = ["/a.txt"]
        with qtbot.waitSignal(bus.files_copied) as blocker:
            bus.files_copied.emit(paths, "/dest")
        assert blocker.args == [paths, "/dest"]

    def test_scan_requested_and_completed(self, qtbot):
        bus = EventBus()
        results = []

        def on_scan(path):
            results.append(f"scan:{path}")
            bus.scan_completed.emit(path)

        bus.scan_requested.connect(on_scan)
        with qtbot.waitSignal(bus.scan_completed) as blocker:
            bus.scan_requested.emit("/dir")
        assert results == ["scan:/dir"]
        assert blocker.args == ["/dir"]

    def test_index_requested_and_completed(self, qtbot):
        bus = EventBus()
        results = []

        def on_index(path):
            results.append(f"index:{path}")
            bus.index_completed.emit(path)

        bus.index_requested.connect(on_index)
        with qtbot.waitSignal(bus.index_completed) as blocker:
            bus.index_requested.emit("/dir")
        assert results == ["index:/dir"]
        assert blocker.args == ["/dir"]

    def test_theme_toggled(self, qtbot):
        bus = EventBus()
        with qtbot.waitSignal(bus.theme_toggled) as blocker:
            bus.theme_toggled.emit(True)
        assert blocker.args == [True]

        with qtbot.waitSignal(bus.theme_toggled) as blocker:
            bus.theme_toggled.emit(False)
        assert blocker.args == [False]

    def test_settings_applied(self, qtbot):
        bus = EventBus()
        data = {"theme": "dark", "language": "en"}
        with qtbot.waitSignal(bus.settings_applied) as blocker:
            bus.settings_applied.emit(data)
        assert blocker.args == [data]

    def test_dashboard_refresh_requested(self, qtbot):
        bus = EventBus()
        with qtbot.waitSignal(bus.dashboard_refresh_requested):
            bus.dashboard_refresh_requested.emit()

    def test_multiple_connections(self, qtbot):
        bus = EventBus()
        received = []

        def slot1(path):
            received.append(f"1:{path}")

        def slot2(path):
            received.append(f"2:{path}")

        bus.open_folder_requested.connect(slot1)
        bus.open_folder_requested.connect(slot2)
        bus.open_folder_requested.emit("/path")
        assert received == ["1:/path", "2:/path"]

    def test_parent(self):
        parent = QObject()
        bus = EventBus(parent=parent)
        assert bus.parent() == parent

    def test_no_unexpected_attrs(self):
        bus = EventBus()
        assert "connect" not in type(bus).__dict__
        assert "disconnect" not in type(bus).__dict__
