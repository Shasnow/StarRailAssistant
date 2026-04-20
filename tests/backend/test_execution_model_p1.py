"""
P1 最小执行模型测试：多进程 → 线程 + 优雅停止
"""

import importlib
import sys
import threading
import types
import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch


class DummyOperator:
    def __init__(self):
        self.settings = MagicMock()


def import_task_module(module_name: str):
    tasks_package = types.ModuleType("tasks")
    tasks_package.__path__ = [str(Path(__file__).resolve().parents[2] / "tasks")]
    mock_errors = types.ModuleType("SRACore.util.errors")
    mock_errors.ErrorCode = MagicMock()
    mock_errors.SRAError = Exception
    with patch.dict(sys.modules, {"tasks": tasks_package, "SRACore.util.errors": mock_errors}):
        return importlib.import_module(module_name)


def test_base_task_should_stop_reflects_event():
    """BaseTask.should_stop 应反映注入的 stop_event 状态"""
    from SRACore.task import BaseTask

    class DemoTask(BaseTask):
        def run(self) -> bool:
            return True

    stop_event = threading.Event()
    task = DemoTask(DummyOperator(), {}, stop_event)
    assert task.should_stop is False

    stop_event.set()
    assert task.should_stop is True


def test_task_manager_has_request_stop_method():
    """TaskManager 应提供 request_stop() 接口"""
    from SRACore.thread.task_process import TaskManager

    mgr = TaskManager.__new__(TaskManager)
    mgr._stop_event = threading.Event()
    mgr.request_stop()
    assert mgr._stop_event.is_set() is True


def test_run_clears_stop_event_before_execution():
    """run() 开始前应 clear stop_event，避免上次停止信号影响本次执行"""
    from SRACore.thread.task_process import TaskManager

    class DemoTask:
        executed = False

        def run(self):
            DemoTask.executed = True
            return True

        def __str__(self):
            return "DemoTask"

    mgr = TaskManager.__new__(TaskManager)
    mgr.log_level = "TRACE"
    mgr.log_queue = None
    mgr._stop_event = threading.Event()
    mgr._stop_event.set()

    with patch("SRACore.thread.task_process.setup_logger"):
        with patch("SRACore.thread.task_process.load_cache", return_value={"ConfigNames": ["cfg"]}):
            with patch.object(mgr, "get_tasks", return_value=[DemoTask()]):
                with patch("SRACore.thread.task_process.notify"):
                    mgr.run()

    assert DemoTask.executed is True
    assert mgr._stop_event.is_set() is False


def test_run_stops_loop_when_request_stop_is_set():
    """run() 在循环中检测到 stop_event 后应停止后续任务"""
    from SRACore.thread.task_process import TaskManager

    class FirstTask:
        def __init__(self, stop_event):
            self.stop_event = stop_event

        def run(self):
            self.stop_event.set()
            return True

        def __str__(self):
            return "FirstTask"

    class SecondTask:
        executed = False

        def run(self):
            SecondTask.executed = True
            return True

        def __str__(self):
            return "SecondTask"

    mgr = TaskManager.__new__(TaskManager)
    mgr.log_level = "TRACE"
    mgr.log_queue = None
    mgr._stop_event = threading.Event()

    first = FirstTask(mgr._stop_event)
    second = SecondTask()

    with patch("SRACore.thread.task_process.setup_logger"):
        with patch("SRACore.thread.task_process.load_cache", return_value={"ConfigNames": ["cfg"]}):
            with patch.object(mgr, "get_tasks", return_value=[first, second]):
                with patch("SRACore.thread.task_process.notify"):
                    mgr.run()

    assert SecondTask.executed is False


def test_main_imports_sra_cli_from_new_path():
    """main.main 应从 SRACore.cli 导入 SRACli"""
    import main as main_module

    fake_cli_class = MagicMock()
    fake_cli_instance = MagicMock()
    fake_cli_instance.task_manager = MagicMock()
    fake_cli_instance.onecmd.return_value = False
    fake_cli_instance.cmdloop = MagicMock()
    fake_cli_class.return_value = fake_cli_instance

    mock_resource = MagicMock()
    mock_resource.argparse_description = "desc"
    mock_resource.argparse_epilog = "epilog"

    with patch.object(main_module, "load_settings", return_value={"Language": 0}):
        with patch.object(main_module, "Resource", mock_resource):
            with patch.dict(sys.modules, {"SRACore.cli": types.SimpleNamespace(SRACli=fake_cli_class)}):
                with patch.object(sys, "argv", ["main.py"]):
                    with patch("sys.exit"):
                        main_module.main()

    fake_cli_class.assert_called_once_with(settings={"Language": 0})
    fake_cli_instance.cmdloop.assert_called_once()


def test_sra_cli_uses_thread_instead_of_process_for_task_run():
    """SRACli.do_task('run') 应启动线程而非 multiprocessing.Process"""
    with patch("SRACore.cli.TaskManager") as MockTaskManager:
        with patch("SRACore.cli.TriggerManager") as MockTriggerManager:
            with patch("SRACore.cli.KeyboardListener") as MockKeyboardListener:
                trigger_manager = MockTriggerManager.return_value
                trigger_manager.run = MagicMock()
                trigger_manager.stop = MagicMock()

                keyboard_listener = MockKeyboardListener.return_value
                keyboard_listener.register_key_event = MagicMock()
                keyboard_listener.start = MagicMock()
                keyboard_listener.stop = MagicMock()

                fake_trigger_thread = MagicMock()
                fake_trigger_thread.is_alive.return_value = True
                fake_task_thread = MagicMock()
                fake_task_thread.is_alive.return_value = False

                with patch("SRACore.cli.threading.Thread", side_effect=[fake_trigger_thread, fake_task_thread]) as MockThread:
                    from SRACore.cli import SRACli
                    cli = SRACli(settings={"StartStopHotkey": "f9"})
                    cli.do_task("run demo")

                    assert MockThread.call_count >= 2


def test_sra_cli_stop_calls_request_stop_not_terminate():
    """SRACli.do_task('stop') 应调用 request_stop，而不是 terminate"""
    with patch("SRACore.cli.TaskManager") as MockTaskManager:
        with patch("SRACore.cli.TriggerManager") as MockTriggerManager:
            with patch("SRACore.cli.KeyboardListener") as MockKeyboardListener:
                trigger_manager = MockTriggerManager.return_value
                trigger_manager.run = MagicMock()
                trigger_manager.stop = MagicMock()

                keyboard_listener = MockKeyboardListener.return_value
                keyboard_listener.register_key_event = MagicMock()
                keyboard_listener.start = MagicMock()
                keyboard_listener.stop = MagicMock()

                fake_trigger_thread = MagicMock()
                fake_trigger_thread.is_alive.return_value = True
                fake_task_thread = MagicMock()
                fake_task_thread.is_alive.return_value = True

                with patch("SRACore.cli.threading.Thread", side_effect=[fake_trigger_thread, fake_task_thread]):
                    from SRACore.cli import SRACli
                    cli = SRACli(settings={"StartStopHotkey": "f9"})
                    cli.task_thread = fake_task_thread
                    cli.do_task("stop")

                    MockTaskManager.return_value.request_stop.assert_called_once()
                    fake_task_thread.join.assert_called()


def test_sra_cli_do_run_uses_shared_execution_path():
    """SRACli.do_run 应复用统一任务执行路径调用 task_manager.run"""
    with patch("SRACore.cli.TaskManager") as MockTaskManager:
        with patch("SRACore.cli.TriggerManager") as MockTriggerManager:
            with patch("SRACore.cli.KeyboardListener") as MockKeyboardListener:
                trigger_manager = MockTriggerManager.return_value
                trigger_manager.run = MagicMock()
                trigger_manager.stop = MagicMock()

                keyboard_listener = MockKeyboardListener.return_value
                keyboard_listener.register_key_event = MagicMock()
                keyboard_listener.start = MagicMock()
                keyboard_listener.stop = MagicMock()

                fake_trigger_thread = MagicMock()
                fake_trigger_thread.is_alive.return_value = True

                with patch("SRACore.cli.threading.Thread", side_effect=[fake_trigger_thread]):
                    from SRACore.cli import SRACli
                    cli = SRACli(settings={"StartStopHotkey": "f9"})
                    cli.do_run("demo another")

                    MockTaskManager.return_value.run.assert_called_once_with("demo", "another")



def test_sra_cli_do_single_uses_shared_execution_path():
    """SRACli.do_single 应复用统一任务执行路径调用 task_manager.run_task"""
    with patch("SRACore.cli.TaskManager") as MockTaskManager:
        with patch("SRACore.cli.TriggerManager") as MockTriggerManager:
            with patch("SRACore.cli.KeyboardListener") as MockKeyboardListener:
                trigger_manager = MockTriggerManager.return_value
                trigger_manager.run = MagicMock()
                trigger_manager.stop = MagicMock()

                keyboard_listener = MockKeyboardListener.return_value
                keyboard_listener.register_key_event = MagicMock()
                keyboard_listener.start = MagicMock()
                keyboard_listener.stop = MagicMock()

                fake_trigger_thread = MagicMock()
                fake_trigger_thread.is_alive.return_value = True

                with patch("SRACore.cli.threading.Thread", side_effect=[fake_trigger_thread]):
                    from SRACore.cli import SRACli
                    cli = SRACli(settings={"StartStopHotkey": "f9"})
                    cli.do_single("DemoTask demo")

                    MockTaskManager.return_value.run_task.assert_called_once_with("DemoTask", "demo")



def test_sra_cli_do_task_run_and_do_run_share_same_helper():
    """do_task('run') 与 do_run 应共同复用统一 helper"""
    with patch("SRACore.cli.TaskManager") as MockTaskManager:
        with patch("SRACore.cli.TriggerManager") as MockTriggerManager:
            with patch("SRACore.cli.KeyboardListener") as MockKeyboardListener:
                trigger_manager = MockTriggerManager.return_value
                trigger_manager.run = MagicMock()
                trigger_manager.stop = MagicMock()

                keyboard_listener = MockKeyboardListener.return_value
                keyboard_listener.register_key_event = MagicMock()
                keyboard_listener.start = MagicMock()
                keyboard_listener.stop = MagicMock()

                fake_trigger_thread = MagicMock()
                fake_trigger_thread.is_alive.return_value = True
                fake_task_thread = MagicMock()
                fake_task_thread.is_alive.return_value = False

                with patch("SRACore.cli.threading.Thread", side_effect=[fake_trigger_thread, fake_task_thread]):
                    from SRACore.cli import SRACli
                    cli = SRACli(settings={"StartStopHotkey": "f9"})

                    with patch.object(cli, "_execute_task_command", wraps=cli._execute_task_command) as helper:
                        cli.do_task("run demo")
                        cli.do_run("demo")

                        assert helper.call_count == 2
                        helper.assert_any_call("run", ("demo",), threaded=True)
                        helper.assert_any_call("run", ("demo",), threaded=False)


def test_receive_rewards_task_without_args_stops_on_should_stop():
    """ReceiveRewardsTask 无参任务循环应响应 stop_event"""
    ReceiveRewardsTask = import_task_module("tasks.ReceiveRewardsTask").ReceiveRewardsTask

    stop_event = threading.Event()
    operator = MagicMock()
    task = ReceiveRewardsTask(operator, {"Name": "test"}, stop_event)

    executed: list[str] = []

    def first_task():
        executed.append("first")
        stop_event.set()

    def second_task():
        executed.append("second")

    assert task._execute_tasks_without_args([first_task, second_task]) is False
    assert executed == ["first"]


def test_receive_rewards_redeem_code_stops_mid_loop_when_stop_requested():
    """ReceiveRewardsTask.redeem_code 应在批量兑换中响应 stop_event"""
    ReceiveRewardsTask = import_task_module("tasks.ReceiveRewardsTask").ReceiveRewardsTask

    stop_event = threading.Event()
    operator = MagicMock()
    operator.click_point.return_value = True
    operator.click_img.return_value = True

    task = ReceiveRewardsTask(operator, {"Name": "test"}, stop_event)

    copied_codes: list[str] = []

    def copy_side_effect(code: str):
        copied_codes.append(code)
        stop_event.set()

    operator.copy.side_effect = copy_side_effect

    task.redeem_code("CODE1 CODE2")

    assert copied_codes == ["CODE1"]


def test_trailblaze_power_task_run_stops_between_manual_tasks():
    """TrailblazePowerTask.run 应在手动任务之间响应 stop_event"""
    TrailblazePowerTask = import_task_module("tasks.TrailblazePowerTask").TrailblazePowerTask

    stop_event = threading.Event()
    operator = MagicMock()
    task = TrailblazePowerTask(operator, {"TrailblazePowerUseBuildTarget": False}, stop_event)
    task.manual_tasks = []
    task.auto_detect_tasks = []

    executed: list[str] = []

    def first_task(**_kwargs):
        executed.append("first")
        stop_event.set()
        return True

    def second_task(**_kwargs):
        executed.append("second")
        return True

    def build_manual_tasks():
        task.manual_tasks = [
            (first_task, {}),
            (second_task, {}),
        ]

    task.init_custom_tasklist = MagicMock(side_effect=build_manual_tasks)

    assert task.run() is False
    assert executed == ["first"]




def test_task_manager_get_tasks_injects_shared_stop_event():
    """get_tasks() 应将同一个 stop_event 注入每个任务实例"""
    from SRACore.thread.task_process import TaskManager

    class DemoTask:
        def __init__(self, _operator, _config, stop_event):
            self.stop_event = stop_event

        def run(self):
            return True

    mgr = TaskManager.__new__(TaskManager)
    mgr.log_level = "TRACE"
    mgr.log_queue = None
    mgr._stop_event = threading.Event()
    mgr.task_list = [DemoTask]

    with patch("SRACore.thread.task_process.load_config", return_value={"EnabledTasks": [True]}):
        with patch("SRACore.thread.task_process.Operator", DummyOperator):
            tasks = mgr.get_tasks("cfg")

    assert len(tasks) == 1
    assert tasks[0].stop_event is mgr._stop_event


def test_sra_cli_uses_thread_for_single_task_run():
    """SRACli.do_task('single') 应启动线程执行 run_task"""
    with patch("SRACore.cli.TaskManager") as MockTaskManager:
        with patch("SRACore.cli.TriggerManager") as MockTriggerManager:
            with patch("SRACore.cli.KeyboardListener") as MockKeyboardListener:
                trigger_manager = MockTriggerManager.return_value
                trigger_manager.run = MagicMock()
                trigger_manager.stop = MagicMock()

                keyboard_listener = MockKeyboardListener.return_value
                keyboard_listener.register_key_event = MagicMock()
                keyboard_listener.start = MagicMock()
                keyboard_listener.stop = MagicMock()

                fake_trigger_thread = MagicMock()
                fake_trigger_thread.is_alive.return_value = True
                fake_task_thread = MagicMock()
                fake_task_thread.is_alive.return_value = False

                with patch("SRACore.cli.threading.Thread", side_effect=[fake_trigger_thread, fake_task_thread]) as MockThread:
                    from SRACore.cli import SRACli
                    cli = SRACli(settings={"StartStopHotkey": "f9"})
                    cli.do_task("single DemoTask demo")

                    assert MockThread.call_count >= 2


def test_sra_cli_exit_requests_stop_and_stops_services():
    """SRACli.do_exit() 应停止任务线程、触发器线程和键盘监听"""
    with patch("SRACore.cli.TaskManager") as MockTaskManager:
        with patch("SRACore.cli.TriggerManager") as MockTriggerManager:
            with patch("SRACore.cli.KeyboardListener") as MockKeyboardListener:
                trigger_manager = MockTriggerManager.return_value
                trigger_manager.run = MagicMock()
                trigger_manager.stop = MagicMock()

                keyboard_listener = MockKeyboardListener.return_value
                keyboard_listener.register_key_event = MagicMock()
                keyboard_listener.start = MagicMock()
                keyboard_listener.stop = MagicMock()

                fake_trigger_thread = MagicMock()
                fake_trigger_thread.is_alive.return_value = True
                fake_task_thread = MagicMock()
                fake_task_thread.is_alive.return_value = True

                with patch("SRACore.cli.threading.Thread", side_effect=[fake_trigger_thread]):
                    from SRACore.cli import SRACli
                    cli = SRACli(settings={"StartStopHotkey": "f9"})
                    cli.task_thread = fake_task_thread

                    assert cli.do_exit(None) is True

                    MockTaskManager.return_value.request_stop.assert_called_once()
                    fake_task_thread.join.assert_called()
                    trigger_manager.stop.assert_called_once()
                    fake_trigger_thread.join.assert_called()
                    keyboard_listener.stop.assert_called_once()


def test_currency_wars_run_stops_before_iteration_when_stop_requested():
    """CurrencyWars.run 应在外层循环开始前响应 stop_event"""
    CurrencyWars = import_task_module("tasks.currency_wars.CurrencyWars").CurrencyWars

    stop_event = threading.Event()
    stop_event.set()
    operator = MagicMock()
    task = CurrencyWars(operator, 1, stop_event)
    task.start_game = MagicMock()
    task.game_loop = MagicMock()

    assert task.run() is False
    task.start_game.assert_not_called()
    task.game_loop.assert_not_called()



def test_currency_wars_battle_stops_after_wait_when_stop_requested():
    """CurrencyWars.battle 在长等待被 stop_event 中断后应返回 False"""
    CurrencyWars = import_task_module("tasks.currency_wars.CurrencyWars").CurrencyWars

    stop_event = threading.Event()
    operator = MagicMock()
    operator.wait_img.return_value = object()
    operator.click_box.return_value = True
    # operator 层感知 stop_event 后返回 -1（等待被中断）
    operator.wait_any_img.side_effect = lambda *args, **kwargs: (stop_event.set(), (-1, None))[1]

    task = CurrencyWars(operator, 1, stop_event)

    assert task.battle() is False
    operator.click_point.assert_not_called()



def test_differential_universe_select_stops_before_waiting_when_stop_requested():
    """DifferentialUniverse._select 应在等待前响应 stop_event"""
    DifferentialUniverse = import_task_module("tasks.differential_universe.DifferentialUniverse").DifferentialUniverse

    stop_event = threading.Event()
    stop_event.set()
    operator = MagicMock()
    task = DifferentialUniverse(operator, 1, False, stop_event)

    assert task.select() is False
    operator.wait_any_img.assert_not_called()



def test_differential_universe_run_stops_before_iteration_when_stop_requested():
    """DifferentialUniverse.run 应在外层循环开始前响应 stop_event"""
    DifferentialUniverse = import_task_module("tasks.differential_universe.DifferentialUniverse").DifferentialUniverse

    stop_event = threading.Event()
    stop_event.set()
    operator = MagicMock()
    task = DifferentialUniverse(operator, 1, False, stop_event)
    task.page_locate = MagicMock()

    assert task.run() is False
    task.page_locate.assert_not_called()


# ============================================================
# Executable / BaseTask 新增覆盖
# ============================================================

def test_executable_should_stop_returns_false_when_no_event():
    """Executable.should_stop 在 stop_event 为 None 时应返回 False"""
    from SRACore.task import BaseTask

    class DemoTask(BaseTask):
        def run(self) -> bool:
            return True

    task = DemoTask(DummyOperator(), {})
    assert task.should_stop is False


def test_executable_stop_sets_event():
    """Executable.stop() 应将 stop_event 置位"""
    from SRACore.task import Executable

    op = DummyOperator()
    stop_event = threading.Event()
    exe = Executable(op, stop_event)
    assert not stop_event.is_set()
    exe.stop()
    assert stop_event.is_set()


def test_executable_stop_noop_when_no_event():
    """Executable.stop() 在无 stop_event 时不应抛出异常"""
    from SRACore.task import Executable

    op = DummyOperator()
    exe = Executable(op)
    exe.stop()  # 不应抛出


def test_base_task_str_and_repr():
    """BaseTask.__str__ 和 __repr__ 应返回类名"""
    from SRACore.task import BaseTask

    class MyTask(BaseTask):
        def run(self) -> bool:
            return True

    task = MyTask(DummyOperator(), {})
    assert str(task) == "MyTask"
    assert repr(task) == "<MyTask>"


def test_executable_should_stop_true_when_event_set():
    """Executable.should_stop 在 stop_event 已置位时应返回 True"""
    from SRACore.task import Executable

    stop_event = threading.Event()
    exe = Executable(DummyOperator(), stop_event)
    assert exe.should_stop is False
    stop_event.set()
    assert exe.should_stop is True


# ============================================================
# StartGameTask should_stop 检查点覆盖
# ============================================================

def _make_start_game_task(stop_event=None):
    """构造 StartGameTask，mock 掉所有重依赖"""
    import sys, types, importlib
    # mock tasks.img
    mock_img_mod = types.ModuleType("tasks.img")
    mock_img_mod.IMG = MagicMock()
    mock_img_mod.SGIMG = MagicMock()
    # mock SRACore.util.errors
    mock_errors = types.ModuleType("SRACore.util.errors")
    mock_errors.ErrorCode = MagicMock()
    mock_errors.SRAError = Exception
    # mock tasks 包（防止 tasks/__init__.py 触发整个导入链）
    mock_tasks_pkg = types.ModuleType("tasks")
    mock_tasks_pkg.__path__ = [str(Path(__file__).resolve().parents[2] / "tasks")]
    mock_tasks_pkg.__package__ = "tasks"
    extra_mocks = {
        "tasks": mock_tasks_pkg,
        "tasks.img": mock_img_mod,
        "SRACore.util.errors": mock_errors,
        "SRACore.util.sys_util": MagicMock(),
        "SRACore.util.encryption": MagicMock(),
    }
    # 清除可能缓存的旧模块
    for key in list(sys.modules.keys()):
        if key == "tasks.StartGameTask":
            del sys.modules[key]
    with patch.dict(sys.modules, extra_mocks):
        mod = importlib.import_module("tasks.StartGameTask")
        StartGameTask = mod.StartGameTask
    operator = MagicMock()
    config = {"StartGameAlwaysLogin": False, "StartGameAutoLogin": False, "StartGameChannel": 0}
    return StartGameTask(operator, config, stop_event), operator


def test_start_game_task_run_stops_after_launch():
    """run() 在 launch_game 后检查 should_stop，stop 后不应调用 login_and_enter_game"""
    stop_event = threading.Event()
    task, operator = _make_start_game_task(stop_event)
    task.launch_game = MagicMock(side_effect=lambda: stop_event.set())
    task.login_and_enter_game = MagicMock()

    result = task.run()

    assert result is False
    task.login_and_enter_game.assert_not_called()


# ============================================================
# SRACli._stop_task_thread 超时降级为 warning
# ============================================================

def test_stop_task_thread_warns_on_timeout():
    """_stop_task_thread：join 超时后应记 warning 而非 error"""
    import SRACore.cli as cli_module

    cli_mock_logger = MagicMock()
    with patch.object(cli_module, "logger", cli_mock_logger):
        from SRACore.cli import SRACli
        cli = SRACli.__new__(SRACli)
        cli.task_manager = MagicMock()
        # 模拟一个永不退出的线程
        never_done = threading.Thread(target=lambda: threading.Event().wait(), daemon=True)
        never_done.start()
        cli.task_thread = never_done

        # join timeout=30 太长，直接 mock join
        with patch.object(never_done, "join"):
            with patch.object(never_done, "is_alive", return_value=True):
                cli._stop_task_thread()

        cli_mock_logger.warning.assert_called()
        # 确保没有调用 error
        cli_mock_logger.error.assert_not_called()


# ============================================================
# SRACore/task/__init__.py — 缺失行补充
# ============================================================

def test_executable_should_stop_false_when_event_none():
    """should_stop 在 stop_event 为 None 时返回 False（覆盖 line 17）"""
    from SRACore.task import Executable
    exe = Executable(DummyOperator(), None)
    assert exe.should_stop is False


def test_base_task_config_stored():
    """BaseTask.__init__ 应正确存储 config（覆盖 line 31）"""
    from SRACore.task import BaseTask

    class DemoTask(BaseTask):
        def run(self) -> bool:
            return True

    cfg = {"key": "val"}
    task = DemoTask(DummyOperator(), cfg)
    assert task.config is cfg


# ============================================================
# SRACore/thread/task_process.py — 缺失行补充
# ============================================================

def test_run_task_returns_false_when_stop_set_before_run():
    """run_task() stop_event 在 get_task 后置位时不执行任务（覆盖 line 175）"""
    from SRACore.thread.task_process import TaskManager

    mgr = TaskManager.__new__(TaskManager)
    mgr.log_level = "TRACE"
    mgr.log_queue = None
    mgr._stop_event = threading.Event()

    fake_task = MagicMock()
    # get_task 调用时设置 stop_event，模拟任务获取完成后用户触发 stop
    def get_task_and_stop(*args, **kwargs):
        mgr._stop_event.set()
        return fake_task

    with patch("SRACore.thread.task_process.setup_logger"):
        with patch.object(mgr, "get_task", side_effect=get_task_and_stop):
            result = mgr.run_task("DemoTask", "cfg")

    assert result is False
    fake_task.run.assert_not_called()


# ============================================================
# SRACore/cli.py — 缺失行补充
# ============================================================

def test_stop_task_thread_logs_done_when_thread_exits():
    """线程正常退出后应 debug('[Done]')（覆盖 line 77-78）"""
    import SRACore.cli as cli_module
    cli_mock_logger = MagicMock()
    with patch.object(cli_module, "logger", cli_mock_logger):
        from SRACore.cli import SRACli
        cli = SRACli.__new__(SRACli)
        cli.task_manager = MagicMock()
        mock_thread = MagicMock()
        # is_alive 第一次返回 True（进入 if 分支），join 后返回 False（走 else 分支）
        mock_thread.is_alive.side_effect = [True, False]
        cli.task_thread = mock_thread
        cli._stop_task_thread()
    cli_mock_logger.debug.assert_called_with('[Done]')


def test_stop_task_thread_prints_not_running_when_no_thread():
    """无活跃线程时应 print notRunning（覆盖 line 80）"""
    from SRACore.cli import SRACli
    cli = SRACli.__new__(SRACli)
    cli.task_manager = MagicMock()
    cli.task_thread = None
    with patch("builtins.print") as mock_print:
        cli._stop_task_thread()
    mock_print.assert_called_once()


def test_execute_task_command_invalid_prints_help():
    """未知命令应 print invalidArguments（覆盖 line 124）"""
    from SRACore.cli import SRACli
    cli = SRACli.__new__(SRACli)
    cli.task_manager = MagicMock()
    cli.task_thread = None
    with patch("builtins.print") as mock_print:
        cli._execute_task_command("unknown", (), threaded=True)
    mock_print.assert_called_once()


# ============================================================
# tasks/ReceiveRewardsTask.py — should_stop 检查点
# ============================================================

def _make_receive_rewards_task(stop_event=None):
    import sys, types, importlib
    mock_img = types.ModuleType("tasks.img")
    mock_img.RRIMG = MagicMock()
    mock_img.DUIMG = MagicMock()
    mock_img.IMG = MagicMock()
    mock_errors = types.ModuleType("SRACore.util.errors")
    mock_errors.ErrorCode = MagicMock()
    mock_errors.SRAError = Exception
    mock_tasks_pkg = types.ModuleType("tasks")
    mock_tasks_pkg.__path__ = [str(Path(__file__).resolve().parents[2] / "tasks")]
    mock_tasks_pkg.__package__ = "tasks"
    for key in [k for k in sys.modules if k == "tasks.ReceiveRewardsTask"]:
        del sys.modules[key]
    with patch.dict(sys.modules, {
        "tasks": mock_tasks_pkg,
        "tasks.img": mock_img,
        "SRACore.util.errors": mock_errors,
    }):
        mod = importlib.import_module("tasks.ReceiveRewardsTask")
    operator = MagicMock()
    config = {"ReceiveRewards": [False]*10, "ReceiveRewardRedeemCodes": []}
    task = mod.ReceiveRewardsTask(operator, config, stop_event)
    return task, operator


def test_receive_rewards_execute_with_args_stops_mid_loop():
    """_execute_tasks_with_args 循环中 should_stop（覆盖 line 76）"""
    stop_event = threading.Event()
    task, _ = _make_receive_rewards_task(stop_event)
    called = []
    def fake_task():
        stop_event.set()
        called.append(1)
    task._execute_tasks_with_args([(fake_task, ()), (fake_task, ())])
    assert len(called) == 1


# ============================================================
# tasks/TrailblazePowerTask.py — line 49
# ============================================================

def _make_trailblaze_power_task(stop_event=None):
    import sys, types, importlib
    mock_img = types.ModuleType("tasks.img")
    mock_img.IMG = MagicMock()
    mock_img.TPIMG = MagicMock()
    mock_errors = types.ModuleType("SRACore.util.errors")
    mock_errors.ErrorCode = MagicMock()
    mock_errors.SRAError = Exception
    mock_tasks_pkg = types.ModuleType("tasks")
    mock_tasks_pkg.__path__ = [str(Path(__file__).resolve().parents[2] / "tasks")]
    mock_tasks_pkg.__package__ = "tasks"
    for key in [k for k in sys.modules if k == "tasks.TrailblazePowerTask"]:
        del sys.modules[key]
    with patch.dict(sys.modules, {
        "tasks": mock_tasks_pkg,
        "tasks.img": mock_img,
        "SRACore.util.errors": mock_errors,
    }):
        mod = importlib.import_module("tasks.TrailblazePowerTask")
    operator = MagicMock()
    config = {"TrailblazePower": [], "AutoDetect": False}
    task = mod.TrailblazePowerTask(operator, config, stop_event)
    # _post_init 依赖真实 BaseTask，手动补全实例属性
    if not hasattr(task, "manual_tasks"):
        task.manual_tasks = []
    if not hasattr(task, "auto_detect_tasks"):
        task.auto_detect_tasks = []
    return task, operator
    """run() detected_tasks 循环中 should_stop（覆盖 line 49）"""
    stop_event = threading.Event()
    task, operator = _make_trailblaze_power_task(stop_event)
    called = []

    def fake_task(**kwargs):
        stop_event.set()
        called.append(1)

    # 绕开 run() 内部的 clear()，直接 mock run() 中调用的关键方法
    with patch.object(task, "init_custom_tasklist"):
        with patch.object(task, "detect_tasks", return_value=[(fake_task, {}), (fake_task, {})]):
            # 在 init_custom_tasklist mock 后，手动设置 auto_detect_tasks
            # 通过 side_effect 在 init_custom_tasklist 调用时填入
            def fill_auto(*a, **kw):
                task.auto_detect_tasks.append("something")
            task.init_custom_tasklist.side_effect = fill_auto
            task.config["TrailblazePowerUseBuildTarget"] = False
            result = task.run()

    assert result is False
    assert len(called) == 1


# ============================================================
# tasks/StartGameTask.py — line 192-193
# ============================================================


