"""System Tray unit tests — pause/resume, file events, notifications"""

from unittest.mock import MagicMock, NonCallableMock, patch

import pytest


class TestTrayPauseResume:
    @pytest.fixture(autouse=True)
    def _setup(self):
        mw = MagicMock()
        mi = MagicMock()
        mt = MagicMock()
        with (
            patch("filepilot.ui.tray.QSystemTrayIcon"),
            patch("filepilot.ui.tray.QMenu"),
            patch("filepilot.ui.tray.QAction"),
            patch("filepilot.ui.tray.QIcon"),
            patch("filepilot.ui.tray.QApplication"),
            patch("filepilot.ui.tray.Signal"),
            patch("filepilot.ui.tray.FileWatcher", return_value=mw),
            patch("filepilot.ui.tray.FileIndexer", return_value=mi),
            patch("filepilot.ui.tray.NotificationToast", return_value=mt),
            patch("filepilot.ui.tray.t", lambda key: key),
        ):
            from filepilot.ui.tray import SystemTrayManager as TrayCls

        self.tray = TrayCls.__new__(TrayCls)
        self.tray._main_window = None
        self.tray._services = {"watcher": mw, "indexer": mi, "toast": mt}
        self.tray._watcher = mw
        self.tray._indexer = mi
        self.tray._toast = mt
        self.tray._tray_icon = MagicMock()
        self.tray._watched_dirs = []
        self.tray._paused_dirs = []
        self.mw = mw
        self.mt = mt

    def test_pause_stores_and_unwatches(self):
        self.tray._watched_dirs = ["/dir/a", "/dir/b"]
        self.tray._on_toggle_watching(paused=True)
        assert self.tray._paused_dirs == ["/dir/a", "/dir/b"]
        self.mw.unwatch_all.assert_called_once()

    def test_pause_shows_toast(self):
        self.tray._watched_dirs = ["/dir/a"]
        self.tray._on_toggle_watching(paused=True)
        self.mt.assert_called_with(
            "\u23f8\ufe0f Background watching paused",
            "warning",
            2000,
        )

    def test_resume_rewatches_and_clears(self):
        self.tray._paused_dirs = ["/dir/a", "/dir/b"]
        self.tray._watched_dirs = []
        self.tray._on_toggle_watching(paused=False)
        assert self.mw.watch.call_count == 2
        assert self.tray._paused_dirs == []

    def test_resume_shows_toast(self):
        self.tray._paused_dirs = ["/dir/a"]
        self.tray._watched_dirs = []
        self.tray._on_toggle_watching(paused=False)
        self.mt.assert_called_with(
            "\u25b6\ufe0f Background watching resumed",
            "info",
            2000,
        )

    def test_roundtrip(self):
        self.tray._watched_dirs = ["/x", "/y"]
        self.tray._on_toggle_watching(paused=True)
        assert self.tray._paused_dirs == ["/x", "/y"]
        self.tray._on_toggle_watching(paused=False)
        assert self.tray._watched_dirs == ["/x", "/y"]

    def test_pause_empty_safe(self):
        self.tray._on_toggle_watching(paused=True)
        assert self.tray._paused_dirs == []

    def test_resume_empty_safe(self):
        self.tray._on_toggle_watching(paused=False)
        self.mw.watch.assert_not_called()


class TestTrayFileEvents:
    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        mw = MagicMock()
        mi = MagicMock()
        mt = MagicMock()
        with (
            patch("filepilot.ui.tray.QSystemTrayIcon"),
            patch("filepilot.ui.tray.QMenu"),
            patch("filepilot.ui.tray.QAction"),
            patch("filepilot.ui.tray.QIcon"),
            patch("filepilot.ui.tray.QApplication"),
            patch("filepilot.ui.tray.Signal"),
            patch("filepilot.ui.tray.FileWatcher", return_value=mw),
            patch("filepilot.ui.tray.FileIndexer", return_value=mi),
            patch("filepilot.ui.tray.NotificationToast", return_value=mt),
            patch("filepilot.ui.tray.t", lambda key: key),
        ):
            from filepilot.ui.tray import SystemTrayManager as TrayCls

        self.tray = TrayCls.__new__(TrayCls)
        self.tray._main_window = None
        self.tray._services = {"watcher": mw, "indexer": mi, "toast": mt}
        self.tray._watcher = mw
        self.tray._indexer = mi
        self.tray._toast = mt
        self.tray._tray_icon = MagicMock()
        self.tray._watched_dirs = []
        self.tray._paused_dirs = []
        self.mi = mi
        self.mt = mt
        self.tmp_path = tmp_path

    def test_event_indexes_file(self):
        f = self.tmp_path / "doc.py"
        f.write_text("x = 1")
        self.tray._on_file_event(str(f))
        assert self.mi.index_files.call_count == 1
        info = self.mi.index_files.call_args[0][0][0]
        assert info.name == "doc.py"
        assert info.extension == ".py"
        assert info.size_bytes == 5
        assert info.category.value[0] == "Code"

    def test_no_indexer_safe(self):
        self.tray._indexer = None
        self.tray._on_file_event(str(self.tmp_path / "test.py"))

    def test_delete_calls_remove(self):
        f = self.tmp_path / "test.py"
        f.write_text("x")
        self.tray._on_file_deleted(str(f))
        self.mi.remove_from_index.assert_called_once_with(str(f))

    def test_delete_no_indexer_safe(self):
        self.tray._indexer = None
        f = self.tmp_path / "test.py"
        f.write_text("x")
        self.tray._on_file_deleted(str(f))

    def test_event_shows_toast(self):
        f = self.tmp_path / "doc.py"
        f.write_text("x = 1")
        self.tray._on_file_event(str(f))
        self.mt.assert_called_with("\U0001f4c4 Indexed: doc.py", "info", 1500)


class TestTrayFileEventsNoExt:
    """Tray does NOT filter by extension — all files get indexed."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        mw = MagicMock()
        mi = MagicMock()
        with (
            patch("filepilot.ui.tray.QSystemTrayIcon"),
            patch("filepilot.ui.tray.QMenu"),
            patch("filepilot.ui.tray.QAction"),
            patch("filepilot.ui.tray.QIcon"),
            patch("filepilot.ui.tray.QApplication"),
            patch("filepilot.ui.tray.Signal"),
            patch("filepilot.ui.tray.FileWatcher", return_value=mw),
            patch("filepilot.ui.tray.FileIndexer", return_value=mi),
            patch("filepilot.ui.tray.NotificationToast"),
            patch("filepilot.ui.tray.t", lambda key: key),
        ):
            from filepilot.ui.tray import SystemTrayManager as TrayCls

        self.tray = TrayCls.__new__(TrayCls)
        self.tray._main_window = None
        self.tray._services = {"watcher": mw, "indexer": mi}
        self.tray._watcher = mw
        self.tray._indexer = mi
        self.tray._toast = None
        self.tray._tray_icon = MagicMock()
        self.tray._watched_dirs = []
        self.tray._paused_dirs = []
        self.tmp_path = tmp_path

    def test_exe_also_indexed(self):
        f = self.tmp_path / "setup.exe"
        f.write_bytes(b"MZ\x90\x00")
        self.tray._on_file_event(str(f))
        self.tray._indexer.index_files.assert_called_once()

    def test_pdf_indexed(self):
        f = self.tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4 dummy")
        self.tray._on_file_event(str(f))
        self.tray._indexer.index_files.assert_called_once()

    def test_md_indexed(self):
        f = self.tmp_path / "readme.md"
        f.write_text("# Hello")
        self.tray._on_file_event(str(f))
        self.tray._indexer.index_files.assert_called_once()

    def test_stat_failure_safe(self):
        self.tray._on_file_event(str(self.tmp_path / "ghost.txt"))
        self.tray._indexer.index_files.assert_not_called()

    def test_directory_flag_set(self):
        d = self.tmp_path / "mydir"
        d.mkdir()
        self.tray._on_file_event(str(d))
        info = self.tray._indexer.index_files.call_args[0][0][0]
        assert info.is_directory is True


class TestTrayToastModes:
    @pytest.fixture(autouse=True)
    def _setup(self):
        mw = MagicMock()
        obj = NonCallableMock(spec=["show_message"])
        with (
            patch("filepilot.ui.tray.QSystemTrayIcon"),
            patch("filepilot.ui.tray.QMenu"),
            patch("filepilot.ui.tray.QAction"),
            patch("filepilot.ui.tray.QIcon"),
            patch("filepilot.ui.tray.QApplication"),
            patch("filepilot.ui.tray.Signal"),
            patch("filepilot.ui.tray.FileWatcher", return_value=mw),
            patch("filepilot.ui.tray.FileIndexer"),
            patch("filepilot.ui.tray.NotificationToast", return_value=obj),
            patch("filepilot.ui.tray.t", lambda key: key),
        ):
            from filepilot.ui.tray import SystemTrayManager as TrayCls

        self.tray = TrayCls.__new__(TrayCls)
        self.tray._main_window = None
        self.tray._services = {"watcher": mw, "indexer": MagicMock(), "toast": obj}
        self.tray._watcher = mw
        self.tray._indexer = MagicMock()
        self.tray._toast = obj
        self.tray._tray_icon = MagicMock()
        self.tray._watched_dirs = []
        self.tray._paused_dirs = []

    def test_show_message_called(self):
        self.tray._show_toast("Test", "warning", 2000)
        self.tray._toast.show_message.assert_called_once_with("Test", "warning", 2000)

    def test_none_toast_safe(self):
        self.tray._toast = None
        self.tray._show_toast("Test", "info", 1000)


class TestTraySetup:
    def _make_raw(self, services):
        with (
            patch("filepilot.ui.tray.QSystemTrayIcon"),
            patch("filepilot.ui.tray.QMenu"),
            patch("filepilot.ui.tray.QAction"),
            patch("filepilot.ui.tray.QIcon"),
            patch("filepilot.ui.tray.QApplication"),
            patch("filepilot.ui.tray.Signal"),
            patch("filepilot.ui.tray.FileWatcher"),
            patch("filepilot.ui.tray.FileIndexer"),
            patch("filepilot.ui.tray.NotificationToast"),
            patch("filepilot.ui.tray.t", lambda key: key),
        ):
            from filepilot.ui.tray import SystemTrayManager as TrayCls

        tray = TrayCls.__new__(TrayCls)
        tray._main_window = None
        tray._services = services
        tray._watcher = services.get("watcher")
        tray._indexer = services.get("indexer")
        tray._toast = services.get("toast")
        tray._tray_icon = MagicMock()
        tray._watched_dirs = []
        tray._paused_dirs = []
        return tray

    def test_signals_connected(self):
        mw = MagicMock()
        tray = self._make_raw({"watcher": mw, "indexer": MagicMock(), "toast": MagicMock()})
        tray._setup_watcher()
        mw.file_created.connect.assert_called_once()
        mw.file_modified.connect.assert_called_once()
        mw.file_deleted.connect.assert_called_once()
        mw.error_occurred.connect.assert_called_once()

    def test_no_watcher_no_crash(self):
        tray = self._make_raw({"watcher": None, "indexer": None, "toast": None})
        tray._setup_watcher()  # should not raise

    def test_toggle_watching_integration(self):
        """Full integration test: toggle from menu triggers unwatch/watch cycle"""
        mw = MagicMock()
        tray = self._make_raw({"watcher": mw, "indexer": MagicMock(), "toast": MagicMock()})

        # Simulate what happens when user clicks the pause toggle in the menu
        tray._watched_dirs = ["/project", "/data"]

        # Pause (as triggered by QAction.toggled.emit(True))
        tray._on_toggle_watching(paused=True)
        mw.unwatch_all.assert_called_once()
        assert tray._paused_dirs == ["/project", "/data"]
        assert tray._watched_dirs == []

        # Resume (as triggered by QAction.toggled.emit(False))
        tray._on_toggle_watching(paused=False)
        assert mw.watch.call_count == 2
        assert tray._watched_dirs == ["/project", "/data"]
        assert tray._paused_dirs == []


class TestTrayAutoStart:
    @pytest.fixture(autouse=True)
    def _setup(self):
        with (
            patch("filepilot.ui.tray.QSystemTrayIcon"),
            patch("filepilot.ui.tray.QMenu"),
            patch("filepilot.ui.tray.QAction"),
            patch("filepilot.ui.tray.QIcon"),
            patch("filepilot.ui.tray.QApplication"),
            patch("filepilot.ui.tray.Signal"),
            patch("filepilot.ui.tray.FileWatcher", return_value=MagicMock()),
            patch("filepilot.ui.tray.FileIndexer", return_value=MagicMock()),
            patch("filepilot.ui.tray.NotificationToast", return_value=MagicMock()),
            patch("filepilot.ui.tray.t", lambda key: key),
            patch("filepilot.ui.tray.is_auto_start_enabled", return_value=False),
        ):
            from filepilot.ui.tray import SystemTrayManager as TrayCls

        self.tray = TrayCls.__new__(TrayCls)
        self.tray._main_window = None
        self.tray._services = {}
        self.tray._watcher = MagicMock()
        self.tray._indexer = MagicMock()
        self.tray._toast = MagicMock()
        self.tray._tray_icon = MagicMock()
        self.tray._watched_dirs = []
        self.tray._paused_dirs = []
        self.tray._autostart_action = MagicMock()

    def test_toggle_autostart_enables(self):
        with patch("filepilot.ui.tray.set_auto_start") as mock_set:
            self.tray._on_toggle_autostart(True)
            mock_set.assert_called_once_with(True)

    def test_toggle_autostart_disables(self):
        with patch("filepilot.ui.tray.set_auto_start") as mock_set:
            self.tray._on_toggle_autostart(False)
            mock_set.assert_called_once_with(False)
