import importlib
import sys
import threading
import time
import types
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from SRACore.localization import Resource


def _import_task_process_module():
    util_package = types.ModuleType("SRACore.util")
    util_package.__path__ = [str(Path(__file__).resolve().parents[2] / "SRACore" / "util")]

    errors_module = types.ModuleType("SRACore.util.errors")
    errors_module.SRAError = Exception
    errors_module.ThreadStoppedError = Exception

    logger_module = types.ModuleType("SRACore.util.logger")
    logger_module.logger = MagicMock()
    logger_module.setup_logger = MagicMock()

    data_persister_module = types.ModuleType("SRACore.util.data_persister")
    data_persister_module.load_cache = MagicMock(return_value={})
    data_persister_module.load_config = MagicMock(return_value={})

    notify_module = MagicMock()

    sys.modules.pop("SRACore.thread.task_process", None)
    with patch.dict(
        sys.modules,
        {
            "SRACore.util": util_package,
            "SRACore.util.errors": errors_module,
            "SRACore.util.logger": logger_module,
            "SRACore.util.data_persister": data_persister_module,
            "SRACore.util.notify": notify_module,
        },
    ):
        module = importlib.import_module("SRACore.thread.task_process")
    return module


def _make_manager():
    task_process = _import_task_process_module()
    mgr = task_process.TaskManager.__new__(task_process.TaskManager)
    mgr.log_level = "TRACE"
    mgr.log_queue = None
    mgr._stop_event = threading.Event()
    return mgr, task_process


class _DemoTask:
    def __init__(self, operator, result=True):
        self.operator = operator
        self._result = result

    def run(self):
        return self._result

    def __str__(self):
        return "DemoTask"


def _import_mission_task_module():
    tasks_package = types.ModuleType("tasks")
    tasks_package.__path__ = [str(Path(__file__).resolve().parents[2] / "tasks")]
    tasks_package.__package__ = "tasks"

    util_parent = MagicMock()
    util_module = types.ModuleType("SRACore.util")
    util_module.notify = util_parent.notify
    util_module.sys_util = util_parent.sys_util
    util_parent.notify.should_capture_notification_screenshot.return_value = True

    img_module = types.ModuleType("tasks.img")
    img_module.IMG = MagicMock()
    img_module.MAIMG = MagicMock()

    errors_module = types.ModuleType("SRACore.util.errors")
    errors_module.ErrorCode = MagicMock()
    errors_module.SRAError = Exception

    sys.modules.pop("tasks.MissionAccomplishTask", None)
    with patch.dict(
        sys.modules,
        {
            "tasks": tasks_package,
            "tasks.img": img_module,
            "SRACore.util": util_module,
            "SRACore.util.errors": errors_module,
        },
    ):
        module = importlib.import_module("tasks.MissionAccomplishTask")
    return module, util_parent


def _import_notify_module():
    util_package = types.ModuleType("SRACore.util")
    util_package.__path__ = [str(Path(__file__).resolve().parents[2] / "SRACore" / "util")]

    encryption_module = types.ModuleType("SRACore.util.encryption")
    encryption_module.win_decryptor = MagicMock(return_value="")

    data_persister_module = types.ModuleType("SRACore.util.data_persister")
    data_persister_module.load_settings = MagicMock(return_value={})

    logger_module = types.ModuleType("SRACore.util.logger")
    logger_module.logger = MagicMock()

    plyer_module = types.ModuleType("plyer")
    plyer_module.notification = MagicMock()

    sys.modules.pop("SRACore.util.notify", None)
    with patch.dict(
        sys.modules,
        {
            "SRACore.util": util_package,
            "SRACore.util.encryption": encryption_module,
            "SRACore.util.data_persister": data_persister_module,
            "SRACore.util.logger": logger_module,
            "plyer": plyer_module,
        },
    ):
        module = importlib.import_module("SRACore.util.notify")
    return module, data_persister_module, logger_module


def test_run_failure_notification_passes_task_operator():
    mgr, task_process = _make_manager()
    operator = object()
    task = _DemoTask(operator, result=False)

    with patch.object(mgr, "get_tasks", return_value=[task]):
        with patch.object(task_process, "notify") as mock_notify:
            mgr.run("cfg")

    mock_notify.try_send_notification.assert_called_once_with(
        Resource.task_notificationTitle,
        Resource.task_taskFailed("DemoTask"),
        result="fail",
        operator=operator,
    )


def test_run_success_notification_uses_shared_operator():
    mgr, task_process = _make_manager()
    operator = object()
    task = _DemoTask(operator, result=True)

    with patch.object(mgr, "get_tasks", return_value=[task]):
        with patch.object(task_process, "notify") as mock_notify:
            mgr.run("cfg")

    mock_notify.try_send_notification.assert_called_once_with(
        Resource.task_notificationTitle,
        Resource.task_notificationMessage,
        operator=operator,
    )


def test_run_task_failure_notification_passes_task_operator():
    mgr, task_process = _make_manager()
    operator = object()
    task = _DemoTask(operator, result=False)

    with patch.object(task_process, "setup_logger"):
        with patch.object(mgr, "get_task", return_value=task):
            with patch.object(task_process, "notify") as mock_notify:
                result = mgr.run_task("DemoTask", "cfg")

    assert result is False
    mock_notify.try_send_notification.assert_called_once_with(
        Resource.task_notificationTitle,
        Resource.task_taskFailed("DemoTask"),
        result="fail",
        operator=operator,
    )


def test_mission_logout_caches_game_frame_before_logout():
    module, util_parent = _import_mission_task_module()
    operator = MagicMock()
    operator.settings = {}
    operator.wait_img.return_value = True

    task = module.MissionAccomplishTask(operator, {"AfterLogout": True, "AfterExitGame": False})
    task.logout()

    util_parent.notify.should_capture_notification_screenshot.assert_called_once_with(task.settings)
    util_parent.notify.capture_game_screenshot.assert_called_once_with(operator)


def test_mission_quit_game_caches_game_frame_before_process_kill():
    module, util_parent = _import_mission_task_module()
    operator = MagicMock()
    operator.settings = {}

    task = module.MissionAccomplishTask(operator, {"AfterLogout": False, "AfterExitGame": True})
    task.quit_game()

    assert util_parent.mock_calls[:3] == [
        call.notify.should_capture_notification_screenshot(task.settings),
        call.notify.capture_game_screenshot(operator),
        call.sys_util.task_kill("StarRail.exe"),
    ]


def test_try_send_notification_dispatches_channels_in_parallel():
    notify_module, data_persister_module, _ = _import_notify_module()
    data_persister_module.load_settings.return_value = {
        "AllowNotifications": True,
        "AllowEmailNotifications": True,
        "AllowWeComNotifications": True,
        "WeComSendImage": False,
    }

    called = []

    def slow_mail(*_):
        time.sleep(0.2)
        called.append("mail")

    def slow_wecom(*_):
        time.sleep(0.2)
        called.append("wecom")

    start = time.perf_counter()
    with patch.object(notify_module, "send_mail_notification", side_effect=slow_mail):
        with patch.object(notify_module, "send_wecom_notification", side_effect=slow_wecom):
            notify_module.try_send_notification("title", "message")
    elapsed = time.perf_counter() - start

    assert set(called) == {"mail", "wecom"}
    assert elapsed < 0.35


def test_try_send_notification_continues_when_one_channel_raises():
    notify_module, data_persister_module, _ = _import_notify_module()
    data_persister_module.load_settings.return_value = {
        "AllowNotifications": True,
        "AllowEmailNotifications": True,
        "AllowWebhookNotifications": True,
    }

    called = []

    with patch.object(notify_module, "send_mail_notification", side_effect=RuntimeError("boom")):
        with patch.object(notify_module, "send_webhook_notification", side_effect=lambda *_: called.append("webhook")):
            notify_module.try_send_notification("title", "message")

    assert called == ["webhook"]
