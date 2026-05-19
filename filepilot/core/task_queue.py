"""Task Queue — Unified background task manager with thread-safe signals"""

import logging
from collections.abc import Callable
from enum import Enum, auto
from uuid import uuid4

from PySide6.QtCore import QObject, QThreadPool, Signal, Slot

from filepilot.core.worker import Worker

logger = logging.getLogger("filepilot.task_queue")


class TaskPriority(Enum):
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()


class TaskState(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class Task:
    def __init__(
        self,
        fn: Callable,
        args: tuple = (),
        kwargs: dict | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        name: str = "",
    ):
        self.id = uuid4().hex[:12]
        self.fn = fn
        self.args = args
        self.kwargs = kwargs or {}
        self.priority = priority
        self.name = name or fn.__name__
        self.state = TaskState.PENDING
        self.result = None
        self.error: str | None = None


class TaskQueueWorker(QObject):
    task_started = Signal(str)
    task_progress = Signal(str, int)
    task_completed = Signal(str, object)
    task_failed = Signal(str, str)
    all_completed = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._queue: list[Task] = []
        self._running = False
        self._cancelled = False

    def enqueue(self, task: Task):
        self._queue.append(task)
        self._queue.sort(key=lambda t: t.priority.value, reverse=True)
        if not self._running:
            self._process_next()

    def cancel_all(self):
        self._cancelled = True
        self._queue.clear()
        self._running = False

    @Slot()
    def _process_next(self):
        if self._cancelled or not self._queue:
            self._running = False
            self._cancelled = False
            self.all_completed.emit()
            return

        task = self._queue.pop(0)
        task.state = TaskState.RUNNING
        self._running = True
        self.task_started.emit(task.id)

        def run():
            try:
                result = task.fn(*task.args, **task.kwargs)
                task.result = result
                task.state = TaskState.COMPLETED
                self.task_completed.emit(task.id, result)
            except Exception as e:
                logger.exception("Task %s failed", task.name)
                task.state = TaskState.FAILED
                task.error = str(e)
                self.task_failed.emit(task.id, str(e))
            finally:
                # Use QTimer to avoid recursive stack growth
                from PySide6.QtCore import QMetaObject, Qt

                QMetaObject.invokeMethod(self, "_process_next", Qt.QueuedConnection)

        worker = Worker(run)
        worker.signals.finished.connect(lambda _: None)
        worker.signals.error.connect(lambda msg: logger.error("Task worker error: %s", msg))
        QThreadPool.globalInstance().start(worker)
