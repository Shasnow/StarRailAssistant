"""
conftest.py — 公共测试基础设施

在任何测试模块被导入之前，统一 mock 掉所有重依赖（pyautogui、onnxruntime、
pyperclip、win32 等），确保测试可在无 GUI、无游戏、无硬件的 CI 环境中运行。
"""

import sys
from abc import ABC, abstractmethod
from typing import Any
from unittest.mock import MagicMock

# ============================================================
# 1. Mock 掉所有重依赖模块（模块级，先于被测代码导入）
# ============================================================

# Operator 相关依赖
_mock_operators = MagicMock()


class MockOperatorSettings:
    """Operator.settings 的替身"""
    pass


class MockOperator:
    """Operator 替身，避免初始化 OCR / PyAutoGUI / 窗口句柄"""
    def __init__(self):
        self.settings = MockOperatorSettings()


class MockIOperator:
    """IOperator 接口替身"""
    def __init__(self):
        self.settings = MockOperatorSettings()


_mock_operators.Operator = MockOperator
_mock_operators.IOperator = MockIOperator

sys.modules.setdefault("SRACore.operators", _mock_operators)
sys.modules.setdefault("SRACore.operators.ioperator", MagicMock())
sys.modules.setdefault("SRACore.operators.operator", MagicMock())
sys.modules.setdefault("SRACore.operators.model", MagicMock())

# util 子模块（encryption 依赖 win32 DPAPI，notify 依赖邮件等）
sys.modules.setdefault("SRACore.util", MagicMock())
sys.modules.setdefault("SRACore.util.encryption", MagicMock())
sys.modules.setdefault("SRACore.util.notify", MagicMock())
sys.modules.setdefault("SRACore.util.sys_util", MagicMock())

# localization
_mock_resource = MagicMock()
_mock_resource.task_instantiateFailed = lambda *args: f"实例化失败: {args}"
_mock_resource.task_currentConfig = lambda name: f"当前配置: {name}"
_mock_resource.task_noSelectedTasks = lambda name: f"无选中任务: {name}"
_mock_resource.task_taskFailed = lambda name: f"任务失败: {name}"
_mock_resource.task_taskCrashed = lambda *args: f"任务崩溃: {args}"
_mock_resource.task_configCompleted = lambda name: f"配置完成: {name}"
_mock_resource.task_managerCrashed = lambda msg: f"管理器崩溃: {msg}"
_mock_resource.task_notificationTitle = "通知标题"
_mock_resource.task_notificationMessage = "通知内容"
_mock_resource.task_noSuchTask = lambda name: f"任务不存在: {name}"
_mock_resource.task_taskCompleted = lambda name: f"任务完成: {name}"
_mock_resource.config_fileNotFound = lambda path: f"配置文件未找到: {path}"
_mock_resource.config_parseError = lambda path, err: f"配置解析错误: {path}, {err}"
_mock_resource.config_exception = lambda path, err: f"配置异常: {path}, {err}"

_mock_localization = MagicMock()
_mock_localization.Resource = _mock_resource
sys.modules["SRACore.localization"] = _mock_localization

# logger
_mock_logger_module = MagicMock()
_mock_logger_module.logger = MagicMock()
_mock_logger_module.setup_logger = MagicMock()
sys.modules["SRACore.util.logger"] = _mock_logger_module

# const
_mock_const = MagicMock()
_mock_const.AppDataSraDir = "/tmp/sra"
sys.modules["SRACore.util.const"] = _mock_const

# data_persister（提供真实签名的 mock，各测试可按需覆盖）
_mock_data_persister = MagicMock()
_mock_data_persister.load_config = MagicMock(return_value=None)
_mock_data_persister.load_cache = MagicMock(return_value={})
_mock_data_persister.load_settings = MagicMock(return_value={})
sys.modules["SRACore.util.data_persister"] = _mock_data_persister


# ============================================================
# 2. 测试用的 Fake 任务类（与真实 BaseTask 保持相同签名）
# ============================================================

class FakeBaseTask(ABC):
    """BaseTask 替身"""
    def __init__(self, operator, config: dict[str, Any]):
        self.operator = operator
        self.config = config
        self.stop_flag = False

    @abstractmethod
    def run(self) -> bool:
        pass

    def __str__(self):
        return f"{self.__class__.__name__}"

    def __repr__(self):
        return f"<{self.__class__.__name__}>"


class FakeStartGameTask(FakeBaseTask):
    def run(self) -> bool:
        return True


class FakeTrailblazePowerTask(FakeBaseTask):
    def run(self) -> bool:
        return True


class FakeReceiveRewardsTask(FakeBaseTask):
    def run(self) -> bool:
        return True


class FakeCosmicStrifeTask(FakeBaseTask):
    def run(self) -> bool:
        return True


class FakeMissionAccomplishTask(FakeBaseTask):
    def run(self) -> bool:
        return True


class FakeFailingTask(FakeBaseTask):
    def run(self) -> bool:
        return False


class FakeExplodingTask(FakeBaseTask):
    def run(self) -> bool:
        raise RuntimeError("boom")


# ============================================================
# 3. 注入 FakeBaseTask 替代真实 BaseTask
# ============================================================

import SRACore.task
SRACore.task.BaseTask = FakeBaseTask  # type: ignore


# ============================================================
# 4. 公共 fixtures
# ============================================================

import pytest
from unittest.mock import patch


TASK_MAP = {
    "StartGameTask": FakeStartGameTask,
    "TrailblazePowerTask": FakeTrailblazePowerTask,
    "ReceiveRewardsTask": FakeReceiveRewardsTask,
    "CosmicStrifeTask": FakeCosmicStrifeTask,
    "MissionAccomplishTask": FakeMissionAccomplishTask,
}


def build_import_side_effect(task_map: dict[str, type]):
    """构建 importlib.import_module 的 side_effect"""
    def side_effect(module_name: str):
        mock_module = MagicMock()
        for class_name, cls in task_map.items():
            setattr(mock_module, class_name, cls)
        return mock_module
    return side_effect


@pytest.fixture
def config_toml_path(tmp_path):
    """创建测试用 config.toml（5 个标准任务，含 fixed 字段）"""
    content = """
[[tasks]]
name = "启动游戏"
main = "StartGameTask"
module = "tasks.StartGameTask"
fixed = "first"

[[tasks]]
name = "清开拓力"
main = "TrailblazePowerTask"
module = "tasks.TrailblazePowerTask"

[[tasks]]
name = "领取奖励"
main = "ReceiveRewardsTask"
module = "tasks.ReceiveRewardsTask"

[[tasks]]
name = "旷宇纷争"
main = "CosmicStrifeTask"
module = "tasks.CosmicStrifeTask"

[[tasks]]
name = "任务完成"
main = "MissionAccomplishTask"
module = "tasks.MissionAccomplishTask"
fixed = "last"
"""
    config_file = tmp_path / "config.toml"
    config_file.write_text(content, encoding="utf-8")
    return str(config_file)


@pytest.fixture
def task_manager(config_toml_path):
    """创建使用测试配置的 TaskManager"""
    from SRACore.thread.task_process import TaskManager, TaskMeta
    with patch("importlib.import_module", side_effect=build_import_side_effect(TASK_MAP)):
        with patch("SRACore.thread.task_process.BaseTask", FakeBaseTask):
            mgr = TaskManager.__new__(TaskManager)
            mgr.log_level = "TRACE"
            mgr.log_queue = None
            mgr.task_registry = {}
            import tomllib
            with open(config_toml_path, "rb") as f:
                tasks = tomllib.load(f).get("tasks", [])
                for task in tasks:
                    main_class = task.get("main")
                    cls = TASK_MAP.get(main_class)
                    if cls:
                        mgr.task_registry[main_class] = TaskMeta(
                            task_class=cls,
                            fixed=task.get("fixed"),
                        )
    return mgr
