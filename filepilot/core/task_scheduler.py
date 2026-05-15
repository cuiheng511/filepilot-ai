"""Task Scheduler — scheduled tasks for auto scan/index/dedup."""

import json
import logging
from datetime import datetime
from pathlib import Path
from threading import Thread

logger = logging.getLogger("filepilot.task_scheduler")

TASKS_FILE = Path.home() / ".filepilot" / "scheduled_tasks.json"


class ScheduledTask:
    """Represents a single scheduled task."""

    def __init__(
        self,
        task_id: str,
        task_type: str,  # scan, index, dedup, organize
        directory: str,
        schedule_type: str,  # daily, weekly, monthly
        schedule_time: str,  # HH:MM format
        enabled: bool = True,
        last_run: str | None = None,
    ):
        self.task_id = task_id
        self.task_type = task_type
        self.directory = directory
        self.schedule_type = schedule_type
        self.schedule_time = schedule_time
        self.enabled = enabled
        self.last_run = last_run

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "directory": self.directory,
            "schedule_type": self.schedule_type,
            "schedule_time": self.schedule_time,
            "enabled": self.enabled,
            "last_run": self.last_run,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScheduledTask":
        return cls(
            task_id=data["task_id"],
            task_type=data["task_type"],
            directory=data["directory"],
            schedule_type=data["schedule_type"],
            schedule_time=data["schedule_time"],
            enabled=data.get("enabled", True),
            last_run=data.get("last_run"),
        )


class TaskScheduler:
    """Manages scheduled tasks for FilePilot operations."""

    def __init__(self):
        self.tasks: list[ScheduledTask] = []
        self._load()

    def _load(self):
        """Load tasks from disk."""
        if TASKS_FILE.exists():
            try:
                data = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
                self.tasks = [ScheduledTask.from_dict(t) for t in data]
            except Exception as e:
                logger.warning("Failed to load scheduled tasks: %s", e)
                self.tasks = []

    def _save(self):
        """Save tasks to disk."""
        TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = [t.to_dict() for t in self.tasks]
            TASKS_FILE.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning("Failed to save scheduled tasks: %s", e)

    def add_task(
        self,
        task_type: str,
        directory: str,
        schedule_type: str,
        schedule_time: str,
        enabled: bool = True,
    ) -> ScheduledTask:
        """Add a new scheduled task."""
        import uuid

        task = ScheduledTask(
            task_id=str(uuid.uuid4())[:8],
            task_type=task_type,
            directory=directory,
            schedule_type=schedule_type,
            schedule_time=schedule_time,
            enabled=enabled,
        )
        self.tasks.append(task)
        self._save()
        return task

    def remove_task(self, task_id: str) -> bool:
        """Remove a task by ID."""
        before = len(self.tasks)
        self.tasks = [t for t in self.tasks if t.task_id != task_id]
        if len(self.tasks) < before:
            self._save()
            return True
        return False

    def toggle_task(self, task_id: str) -> bool:
        """Toggle task enabled/disabled state."""
        for task in self.tasks:
            if task.task_id == task_id:
                task.enabled = not task.enabled
                self._save()
                return True
        return False

    def get_due_tasks(self) -> list[ScheduledTask]:
        """Get tasks that are due to run now."""
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_date = now.day

        due = []
        for task in self.tasks:
            if not task.enabled:
                continue

            # Check time match
            if task.schedule_time != current_time:
                continue

            # Check schedule type
            if task.schedule_type == "daily":
                due.append(task)
            elif task.schedule_type == "weekly":
                # For weekly, we'd need to store the day; simplified here
                due.append(task)
            elif task.schedule_type == "monthly" and current_date == 1:
                due.append(task)

        return due

    def mark_task_run(self, task_id: str):
        """Mark a task as having run."""
        for task in self.tasks:
            if task.task_id == task_id:
                task.last_run = datetime.now().isoformat()
                self._save()
                break

    def get_all_tasks(self) -> list[ScheduledTask]:
        """Get all tasks."""
        return list(self.tasks)

    def execute_task(self, task: ScheduledTask, callback=None):
        """Execute a scheduled task in background thread."""

        def worker():
            try:
                logger.info(
                    "Executing task %s: %s on %s",
                    task.task_id,
                    task.task_type,
                    task.directory,
                )

                # This would integrate with actual services
                # For now, just log and mark as run
                self.mark_task_run(task.task_id)

                if callback:
                    callback(task.task_id, True, "Task completed")

            except Exception as e:
                logger.error("Task %s failed: %s", task.task_id, e)
                if callback:
                    callback(task.task_id, False, str(e))

        Thread(target=worker, daemon=True).start()
