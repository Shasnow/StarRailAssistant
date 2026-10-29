from __future__ import annotations

import threading
import importlib

import pytest

from SRACore import task as task_module
from SRACore.localization import Resource
from SRACore.models.app_settings import AppSettings
from SRACore.models.tasks_config import TasksConfig
from SRACore.notification import service as notification_service


class FakeOperator:
    """A minimal operator implementation for task notification tests."""

    def __init__(self) -> None:
        self.settings = AppSettings.from_dict({})
        self.stop_event = threading.Event()
        self.width = 1920
        self.height = 1080
        self.type = "Desktop"

    def wait_any_img(self, *_args, **_kwargs):
        return 2, None

    def screenshot(self):
        return None

    def press_key(self, *_args, **_kwargs):
        pass

    def do_while(self, *_args, **_kwargs):
        pass

    def wait_img(self, *_args, **_kwargs):
        return True

    def click_img(self, *_args, **_kwargs):
        return True

    def click_point(self, *_args, **_kwargs):
        return True

    def sleep(self, *_args, **_kwargs):
        pass


@pytest.fixture(params=[0, 1, 2])
def notification_language(request):
    original = Resource.lang
    Resource.set_language(request.param)
    yield request.param
    Resource.set_language(original)


def test_load_all_tasks_and_trigger_start_complete_notifications(monkeypatch, notification_language) -> None:
    """Load all registered tasks and verify `start()`/`complete()` emit notifications.

	The test patches the task module's notification function so no real network/
	UI side effects happen, then instantiates each task class with a fake operator
	and a default `TasksConfig`.
	"""

    sent_notifications: list[tuple[str, str, str]] = []

    # Exercise the real localization boundary, but never dispatch a notification.
    monkeypatch.setattr(notification_service._notification_executor, "submit",
                        lambda fn, context: sent_notifications.append(
                            (context.title, context.message, context.payload['result'])))

    for module in ('StartGameTask', 'TrailblazePowerTask', 'ReceiveRewardsTask',
                   'CosmicStrifeTask', 'MissionAccomplishTask'):
        importlib.import_module(f'tasks.{module}')
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
        fake_operator.settings.Notification.isEnabled = True

        config = TasksConfig.from_dict({})
        task = task_cls(fake_operator, config)

        sent_notifications.clear()

        task.on_start()
        task.on_completed()

        assert len(sent_notifications) == 2
        assert all(title == Resource.task_notificationTitle for title, _, _ in sent_notifications)
        if notification_language == 2:
            assert sent_notifications[0][1] == f"Задача {task_name} запущена."
            assert sent_notifications[1][1] == f"Задача {task_name} выполнена."
        else:
            assert sent_notifications[0][1] == f"任务 {task_name} 开始执行。"
            assert sent_notifications[1][1] == f"任务 {task_name} 执行完成。"
        assert all(result == "success" for _, _, result in sent_notifications)
