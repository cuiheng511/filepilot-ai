"""Tests for filepilot.core.task_queue — priority-based background task queue"""

from filepilot.core.task_queue import Task, TaskPriority, TaskQueueWorker


def test_enqueue_sorts_by_priority(qtbot):
    worker = TaskQueueWorker()
    worker.enqueue(Task(fn=lambda: "low", priority=TaskPriority.LOW, name="low"))
    worker.enqueue(Task(fn=lambda: "high", priority=TaskPriority.HIGH, name="high"))
    worker.enqueue(Task(fn=lambda: "normal", priority=TaskPriority.NORMAL, name="normal"))
    names = [t.name for t in worker._queue]
    assert names == ["high", "normal"]
    with qtbot.waitSignal(worker.all_completed, timeout=2000):
        pass


def test_cancel_all():
    worker = TaskQueueWorker()
    worker._queue = [Task(fn=lambda: "a", name="a"), Task(fn=lambda: "b", name="b")]
    worker.cancel_all()
    assert len(worker._queue) == 0


def test_task_attributes():
    t = Task(fn=lambda: 42, name="test", priority=TaskPriority.HIGH)
    assert t.name == "test"
    assert t.priority == TaskPriority.HIGH
    assert t.state.name == "PENDING"
    assert t.result is None
    assert t.error is None


def test_task_defaults():
    t = Task(fn=lambda: None)
    assert t.priority == TaskPriority.NORMAL
    assert t.args == ()
    assert t.kwargs == {}


def test_worker_initial_state():
    worker = TaskQueueWorker()
    assert worker._queue == []
    assert worker._running is False
    assert worker._cancelled is False


def test_task_has_id():
    t = Task(fn=lambda: None)
    assert hasattr(t, "id")
    assert len(t.id) == 12


def test_task_priority_comparison():
    assert TaskPriority.LOW.value == 1
    assert TaskPriority.NORMAL.value == 2
    assert TaskPriority.HIGH.value == 3
