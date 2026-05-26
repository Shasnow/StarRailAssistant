from __future__ import annotations

import threading

from SRACore import task as task_module
from SRACore.localization import Resource
from SRACore.models.app_settings import AppSettings
from SRACore.models.tasks_config import TasksConfig


class FakeOperator:
    """A minimal operator implementation for task notification tests."""

    def __init__(self) -> None:
        self.settings = AppSettings.from_dict({})
        self.stop_event = threading.Event()
        self.width = 1920
        self.height = 1080
        self.type = "Desktop"


def test_load_all_tasks_and_trigger_start_complete_notifications(monkeypatch) -> None:
    """Load all registered tasks and verify `start()`/`complete()` emit notifications.

	The test patches the task module's notification function so no real network/
	UI side effects happen, then instantiates each task class with a fake operator
	and a default `TasksConfig`.
	"""

    sent_notifications: list[tuple[str, str, str]] = []

    def fake_try_send_notification(title, message, result="success", operator=None):
        sent_notifications.append((title, message, result))
        return True

    monkeypatch.setattr(task_module, "try_send_notification", fake_try_send_notification)

    task_classes = task_module.get_task_classes()
    loaded_names = [cls.__name__ for cls in task_classes]

    assert loaded_names == [
        "StartGameTask",
        "TrailblazePowerTask",
        "ReceiveRewardsTask",
        "CosmicStrifeTask",
        "MissionAccomplishTask",
    ]

    for task_cls in task_classes:
        fake_operator = FakeOperator()
        task_name = task_cls.__name__

        # Trigger both start/completed notification paths for the current task.
        fake_operator.settings.Notification.onStart = [task_name]
        fake_operator.settings.Notification.onCompleted = [task_name]

        config = TasksConfig.from_dict({})
        task = task_cls(fake_operator, config)

        sent_notifications.clear()

        task.start()
        task.complete()

        assert len(sent_notifications) == 2
        assert all(title == Resource.task_notificationTitle for title, _, _ in sent_notifications)
        assert sent_notifications[0][1] == f"任务 {task_name} 开始执行。"
        assert sent_notifications[1][1] == f"任务 {task_name} 执行完成。"
        assert all(result == "success" for _, _, result in sent_notifications)
