"""File Watcher — Watchdog-based directory monitoring with Qt signals"""

import logging
from pathlib import Path
from threading import Thread

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("filepilot.file_watcher")


class FileWatcher(QObject):
    file_created = Signal(str)
    file_deleted = Signal(str)
    file_modified = Signal(str)
    file_moved = Signal(str, str)
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._watched_dirs: dict[str, Thread] = {}
        self._observer = None

    @property
    def is_available(self) -> bool:
        import importlib
        return importlib.util.find_spec("watchdog") is not None

    def watch(self, directory: str | Path):
        dir_path = str(Path(directory).resolve())
        if dir_path in self._watched_dirs:
            return
        if not self.is_available:
            self.error_occurred.emit("watchdog not installed — run: pip install watchdog")
            return

        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        class QtHandler(FileSystemEventHandler):
            def __init__(self, watcher):
                self.watcher = watcher

            def on_created(self, event):
                if not event.is_directory:
                    self.watcher.file_created.emit(event.src_path)

            def on_deleted(self, event):
                if not event.is_directory:
                    self.watcher.file_deleted.emit(event.src_path)

            def on_modified(self, event):
                if not event.is_directory:
                    self.watcher.file_modified.emit(event.src_path)

            def on_moved(self, event):
                if not event.is_directory:
                    self.watcher.file_moved.emit(event.src_path, event.dest_path)

        observer = Observer()
        observer.schedule(QtHandler(self), dir_path, recursive=True)
        observer.start()
        self._observer = observer
        self._watched_dirs[dir_path] = observer
        logger.info("Started watching %s", dir_path)

    def unwatch(self, directory: str | Path):
        dir_path = str(Path(directory).resolve())
        observer = self._watched_dirs.pop(dir_path, None)
        if observer:
            observer.stop()
            observer.join(timeout=2)
            logger.info("Stopped watching %s", dir_path)

    def unwatch_all(self):
        for dir_path in list(self._watched_dirs.keys()):
            self.unwatch(dir_path)

    def stop(self):
        self.unwatch_all()
