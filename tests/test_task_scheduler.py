"""Tests for task scheduler."""

import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from filepilot.core.task_scheduler import ScheduledTask, TaskScheduler


class TestTaskScheduler(TestCase):
    def setUp(self):
        self.temp_file = Path(tempfile.gettempdir()) / f"test_tasks_{id(self)}.json"
        self.patcher = None

    def _make_scheduler(self):
        import filepilot.core.task_scheduler as ts
        self.patcher = patch.object(ts, "TASKS_FILE", self.temp_file)
        self.patcher.start()
        return TaskScheduler()

    def tearDown(self):
        if self.patcher:
            self.patcher.stop()
        if self.temp_file.exists():
            self.temp_file.unlink()

    def test_add_task(self):
        scheduler = self._make_scheduler()
        task = scheduler.add_task(
            task_type="scan",
            directory="/tmp/test",
            schedule_type="daily",
            schedule_time="09:00",
        )
        self.assertEqual("scan", task.task_type)
        self.assertEqual("/tmp/test", task.directory)
        self.assertEqual("daily", task.schedule_type)
        self.assertEqual("09:00", task.schedule_time)
        self.assertTrue(task.enabled)

    def test_remove_task(self):
        scheduler = self._make_scheduler()
        task = scheduler.add_task("index", "/tmp", "daily", "10:00")
        self.assertTrue(scheduler.remove_task(task.task_id))
        self.assertEqual(0, len(scheduler.get_all_tasks()))

    def test_toggle_task(self):
        scheduler = self._make_scheduler()
        task = scheduler.add_task("dedup", "/tmp", "weekly", "12:00")
        self.assertTrue(task.enabled)
        scheduler.toggle_task(task.task_id)
        tasks = scheduler.get_all_tasks()
        self.assertEqual(1, len(tasks))
        self.assertFalse(tasks[0].enabled)

    def test_get_all_tasks(self):
        scheduler = self._make_scheduler()
        scheduler.add_task("scan", "/tmp1", "daily", "08:00")
        scheduler.add_task("index", "/tmp2", "monthly", "09:00")
        tasks = scheduler.get_all_tasks()
        self.assertEqual(2, len(tasks))

    def test_mark_task_run(self):
        scheduler = self._make_scheduler()
        task = scheduler.add_task("organize", "/tmp", "daily", "11:00")
        self.assertIsNone(task.last_run)
        scheduler.mark_task_run(task.task_id)
        tasks = scheduler.get_all_tasks()
        self.assertIsNotNone(tasks[0].last_run)

    def test_scheduled_task_to_dict(self):
        task = ScheduledTask("t1", "scan", "/tmp", "daily", "09:00")
        d = task.to_dict()
        self.assertEqual("t1", d["task_id"])
        self.assertEqual("scan", d["task_type"])
        self.assertEqual("/tmp", d["directory"])
        self.assertEqual("daily", d["schedule_type"])
        self.assertEqual("09:00", d["schedule_time"])
        self.assertTrue(d["enabled"])

    def test_scheduled_task_from_dict(self):
        data = {
            "task_id": "t2",
            "task_type": "index",
            "directory": "/data",
            "schedule_type": "weekly",
            "schedule_time": "14:30",
            "enabled": False,
            "last_run": "2024-01-01T10:00:00",
        }
        task = ScheduledTask.from_dict(data)
        self.assertEqual("t2", task.task_id)
        self.assertEqual("index", task.task_type)
        self.assertFalse(task.enabled)
        self.assertEqual("2024-01-01T10:00:00", task.last_run)
