"""FileWatcher integration tests — signal emission with real watchdog"""

import os
import time

import pytest
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from filepilot.core.file_watcher import FileWatcher


@pytest.fixture
def watcher():
    """Create and return a FileWatcher instance."""
    return FileWatcher()


@pytest.fixture
def watched_dir(tmp_path):
    """Return a temporary directory to watch."""
    d = tmp_path / "watch_me"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture(autouse=True)
def _setup_watcher(watcher, watched_dir):
    """Auto-watch the temp directory for every test and clean up after."""
    watcher.watch(str(watched_dir))
    yield
    watcher.unwatch_all()


class _SignalCollector:
    """Collect signal emissions for verification, with event-loop pumping."""

    def __init__(self, watcher: FileWatcher, app: QApplication):
        self.created: list[str] = []
        self.deleted: list[str] = []
        self.modified: list[str] = []
        self.moved: list[tuple[str, str]] = []
        self.errors: list[str] = []
        self._app = app
        self._created_done = False
        self._deleted_done = False
        self._modified_done = False

        watcher.file_created.connect(self._on_created)
        watcher.file_deleted.connect(self._on_deleted)
        watcher.file_modified.connect(self._on_modified)
        watcher.file_moved.connect(self._on_moved)
        watcher.error_occurred.connect(self._on_error)

    def _on_created(self, path: str):
        self.created.append(path)
        self._created_done = True

    def _on_deleted(self, path: str):
        self.deleted.append(path)
        self._deleted_done = True

    def _on_modified(self, path: str):
        self.modified.append(path)
        self._modified_done = True

    def _on_moved(self, src: str, dest: str):
        self.moved.append((src, dest))

    def _on_error(self, msg: str):
        self.errors.append(msg)

    def _pump(self, timeout=5):
        """Pump Qt event loop until timeout."""
        loop = QEventLoop()
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)
        timer.start(timeout * 1000)
        loop.exec()

    def wait_created(self, timeout=5):
        self._pump(timeout)

    def wait_deleted(self, timeout=5):
        self._pump(timeout)

    def wait_modified(self, timeout=5):
        self._pump(timeout)

    @property
    def app(self):
        return self._app


@pytest.fixture
def qt_app():
    """Ensure QApplication exists for signal delivery."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestFileWatcherIntegration:
    def test_file_created_signal(self, watcher, watched_dir, qt_app):
        """Watching a directory emits file_created when a file appears."""
        collector = _SignalCollector(watcher, qt_app)
        time.sleep(0.2)

        target = watched_dir / "new_file.txt"
        target.write_text("hello watcher", encoding="utf-8")
        collector.wait_created()

        assert len(collector.created) >= 1
        names = [os.path.basename(p) for p in collector.created]
        assert "new_file.txt" in names

    def test_file_modified_signal(self, watcher, watched_dir, qt_app):
        """Modifying an existing file triggers file_modified."""
        target = watched_dir / "data.txt"
        target.write_text("initial", encoding="utf-8")
        time.sleep(0.2)

        collector = _SignalCollector(watcher, qt_app)
        time.sleep(0.2)

        target.write_text("modified content", encoding="utf-8")
        collector.wait_modified()

        assert len(collector.modified) >= 1

    def test_file_deleted_signal(self, watcher, watched_dir, qt_app):
        """Deleting a file triggers file_deleted."""
        target = watched_dir / "to_delete.txt"
        target.write_text("bye", encoding="utf-8")
        time.sleep(0.2)

        collector = _SignalCollector(watcher, qt_app)
        time.sleep(0.2)

        target.unlink()
        collector.wait_deleted()

        assert len(collector.deleted) >= 1

    def test_unwatch_stops_emissions(self, watcher, watched_dir, qt_app):
        """After unwatch, no more signals should fire."""
        watcher.unwatch_all()
        collector = _SignalCollector(watcher, qt_app)

        target = watched_dir / "late.txt"
        target.write_text("after unmount", encoding="utf-8")
        time.sleep(0.5)

        assert len(collector.created) == 0

    def test_is_available(self, watcher):
        """is_available returns True when watchdog is importable."""
        assert watcher.is_available is True

    def test_repeated_watch_ignored(self, watcher, watched_dir):
        """Calling watch() twice for same dir is a no-op (second returns early)."""
        # _setup_watcher already called once
        watcher.watch(str(watched_dir))
        assert len(watcher._watched_dirs) == 1

    def test_stop_is_alias_for_unwatch_all(self, watcher, watched_dir):
        """stop() clears all watchers."""
        watcher.stop()
        assert len(watcher._watched_dirs) == 0

    def test_nonexistent_dir_emits_error(self, watcher, qt_app):
        """Watching a nonexistent directory emits error, does not crash."""
        collector = _SignalCollector(watcher, qt_app)
        nonexistent = "/tmp/nonexistent_dir_xyz_12345"
        watcher.watch(nonexistent)

        assert any("does not exist" in e for e in collector.errors)

    def test_watched_dirs_tracking(self, watcher, watched_dir):
        """_watched_dirs dict tracks active observers."""
        assert len(watcher._watched_dirs) == 1
        path_str = str(watched_dir.resolve())
        assert path_str in watcher._watched_dirs
        watcher.unwatch(path_str)
        assert len(watcher._watched_dirs) == 0

    def test_unwatch_nonexistent_no_crash(self, watcher):
        """Unwatching a path that was never added should not crash."""
        watcher.unwatch("/nonexistent/path")
        assert True

    def test_watch_nonexistent_emits_error(self, watcher, qt_app):
        collector = _SignalCollector(watcher, qt_app)
        watcher.watch("/tmp/definitely_does_not_exist_12345")
        assert any("does not exist" in e for e in collector.errors)

    def test_is_available_false(self, watcher, monkeypatch):
        monkeypatch.setattr("importlib.util.find_spec", lambda _: None)
        assert watcher.is_available is False


class TestFileWatcherQtHandler:
    """Unit tests for the watch error paths."""

    def test_watch_emits_error_without_watchdog(self, monkeypatch):
        monkeypatch.setattr("importlib.util.find_spec", lambda _: None)
        w = FileWatcher()
        errors = []
        w.error_occurred.connect(errors.append)
        w.watch("/tmp/some_dir")
        assert any("watchdog not installed" in e for e in errors)

    def test_watch_emits_error_nonexistent_dir(self, monkeypatch):
        """watch emits error for non-existent directory when watchdog exists."""
        w = FileWatcher()
        errors = []
        w.error_occurred.connect(errors.append)
        w.watch("/tmp/definitely_does_not_exist_99999999")
        assert any("does not exist" in e for e in errors)
