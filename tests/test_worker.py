"""Tests for filepilot.core.worker — QRunnable Worker helper"""

import time

from PySide6.QtCore import QObject, QThreadPool

from filepilot.core.worker import Worker, WorkerSignals


def test_worker_signals_have_correct_types():
    sigs = WorkerSignals()
    assert hasattr(sigs, "finished")
    assert hasattr(sigs, "error")
    assert isinstance(sigs, QObject)


def test_worker_runs_function():
    results = []

    def fn():
        results.append(42)

    worker = Worker(fn)
    worker.run()
    assert results == [42]


def test_worker_passes_args():
    results = []

    def fn(a, b):
        results.append(a + b)

    worker = Worker(fn, 3, 4)
    worker.run()
    assert results == [7]


def test_worker_passes_kwargs():
    results = []

    def fn(**kw):
        results.append(kw["x"])

    worker = Worker(fn, x=99)
    worker.run()
    assert results == [99]


def test_worker_error_signal(qtbot):
    sigs = WorkerSignals()
    errors = []
    sigs.error.connect(lambda e: errors.append(str(e)))

    def fn():
        raise ValueError("boom")

    worker = Worker(fn)
    worker.signals.error.connect(lambda e: errors.append(str(e)))
    worker.run()
    assert any("boom" in e for e in errors)


def test_worker_in_pool(qtbot):
    pool = QThreadPool.globalInstance()
    results = []

    def fn():
        time.sleep(0.05)
        results.append("done")

    worker = Worker(fn)
    worker.signals.finished.connect(lambda _: results.append("finished"))
    pool.start(worker)
    pool.waitForDone(5000)
    assert "done" in results
