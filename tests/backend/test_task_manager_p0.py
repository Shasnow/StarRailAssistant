"""
P0 测试：TaskManager 重构 —— EnabledTasks → TaskOrder

测试新的 task_registry + TaskOrder 机制。
"""

from dataclasses import dataclass
from unittest.mock import patch, MagicMock

import pytest

from tests.backend.conftest import (
    MockOperator, FakeBaseTask,
    FakeStartGameTask, FakeTrailblazePowerTask, FakeReceiveRewardsTask,
    FakeCosmicStrifeTask, FakeMissionAccomplishTask,
    FakeFailingTask, TASK_MAP, build_import_side_effect,
)


# ============================================================
# Fixtures：构建使用 fixed 字段的 config.toml + 新版 TaskManager
# ============================================================

TASK_MAP_WITH_FIXED = {
    "StartGameTask": ("first", FakeStartGameTask),
    "TrailblazePowerTask": (None, FakeTrailblazePowerTask),
    "ReceiveRewardsTask": (None, FakeReceiveRewardsTask),
    "CosmicStrifeTask": (None, FakeCosmicStrifeTask),
    "MissionAccomplishTask": ("last", FakeMissionAccomplishTask),
}


@pytest.fixture
def config_toml_with_fixed(tmp_path):
    """创建带 fixed 字段的 config.toml"""
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
def p0_task_manager(config_toml_with_fixed):
    """创建使用新架构（task_registry + TaskMeta）的 TaskManager"""
    from SRACore.thread.task_process import TaskManager, TaskMeta
    with patch("importlib.import_module", side_effect=build_import_side_effect(TASK_MAP)):
        with patch("SRACore.thread.task_process.BaseTask", FakeBaseTask):
            mgr = TaskManager.__new__(TaskManager)
            mgr.log_level = "TRACE"
            mgr.log_queue = None
            mgr.task_registry = {}
            import tomllib
            with open(config_toml_with_fixed, "rb") as f:
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


# ============================================================
# task_registry 基础测试
# ============================================================

class TestTaskRegistry:
    """验证 TaskManager 使用 task_registry 替代 task_list"""

    def test_registry_has_all_tasks(self, p0_task_manager):
        """注册表应包含 config.toml 中所有任务"""
        assert len(p0_task_manager.task_registry) == 5
        assert "StartGameTask" in p0_task_manager.task_registry
        assert "MissionAccomplishTask" in p0_task_manager.task_registry

    def test_registry_stores_fixed_field(self, p0_task_manager):
        """注册表应正确存储 fixed 字段"""
        assert p0_task_manager.task_registry["StartGameTask"].fixed == "first"
        assert p0_task_manager.task_registry["TrailblazePowerTask"].fixed is None
        assert p0_task_manager.task_registry["MissionAccomplishTask"].fixed == "last"

    def test_registry_stores_task_class(self, p0_task_manager):
        """注册表应存储正确的任务类"""
        assert p0_task_manager.task_registry["StartGameTask"].task_class is FakeStartGameTask
        assert p0_task_manager.task_registry["CosmicStrifeTask"].task_class is FakeCosmicStrifeTask


# ============================================================
# get_tasks() 使用 TaskOrder 测试
# ============================================================

class TestGetTasksWithTaskOrder:
    """验证 get_tasks() 使用 TaskOrder 替代 EnabledTasks"""

    def test_task_order_determines_enabled_tasks(self, p0_task_manager):
        """TaskOrder 中出现的任务 = 启用，顺序 = 执行顺序"""
        config = {
            "TaskOrder": [
                "StartGameTask",
                "ReceiveRewardsTask",
                "MissionAccomplishTask",
            ]
        }
        with patch("SRACore.thread.task_process.load_config", return_value=config):
            with patch("SRACore.thread.task_process.Operator", MockOperator):
                tasks = p0_task_manager.get_tasks("test")
        assert len(tasks) == 3
        assert isinstance(tasks[0], FakeStartGameTask)
        assert isinstance(tasks[1], FakeReceiveRewardsTask)
        assert isinstance(tasks[2], FakeMissionAccomplishTask)

    def test_empty_task_order_returns_empty(self, p0_task_manager):
        """空 TaskOrder 返回空列表"""
        config = {"TaskOrder": []}
        with patch("SRACore.thread.task_process.load_config", return_value=config):
            tasks = p0_task_manager.get_tasks("test")
        assert tasks == []

    def test_unknown_task_in_order_is_skipped(self, p0_task_manager):
        """TaskOrder 中包含未知任务名时跳过"""
        config = {
            "TaskOrder": [
                "StartGameTask",
                "NonExistentTask",
                "MissionAccomplishTask",
            ]
        }
        with patch("SRACore.thread.task_process.load_config", return_value=config):
            with patch("SRACore.thread.task_process.Operator", MockOperator):
                tasks = p0_task_manager.get_tasks("test")
        assert len(tasks) == 2
        assert isinstance(tasks[0], FakeStartGameTask)
        assert isinstance(tasks[1], FakeMissionAccomplishTask)

    def test_fixed_first_always_at_head(self, p0_task_manager):
        """fixed=first 的任务无论 TaskOrder 中位置如何，始终排在最前"""
        config = {
            "TaskOrder": [
                "ReceiveRewardsTask",
                "StartGameTask",  # fixed=first，但放在中间
                "MissionAccomplishTask",
            ]
        }
        with patch("SRACore.thread.task_process.load_config", return_value=config):
            with patch("SRACore.thread.task_process.Operator", MockOperator):
                tasks = p0_task_manager.get_tasks("test")
        assert isinstance(tasks[0], FakeStartGameTask)  # 必须在最前
        assert isinstance(tasks[-1], FakeMissionAccomplishTask)  # 必须在最后

    def test_fixed_last_always_at_tail(self, p0_task_manager):
        """fixed=last 的任务无论 TaskOrder 中位置如何，始终排在最后"""
        config = {
            "TaskOrder": [
                "MissionAccomplishTask",  # fixed=last，但放在最前
                "TrailblazePowerTask",
                "StartGameTask",
            ]
        }
        with patch("SRACore.thread.task_process.load_config", return_value=config):
            with patch("SRACore.thread.task_process.Operator", MockOperator):
                tasks = p0_task_manager.get_tasks("test")
        assert isinstance(tasks[0], FakeStartGameTask)  # first
        assert isinstance(tasks[1], FakeTrailblazePowerTask)  # 中间
        assert isinstance(tasks[-1], FakeMissionAccomplishTask)  # last

    def test_user_order_preserved_for_non_fixed(self, p0_task_manager):
        """非 fixed 任务的用户自定义顺序应被保留"""
        config = {
            "TaskOrder": [
                "StartGameTask",
                "CosmicStrifeTask",       # 用户把旷宇纷争放在清体力前面
                "TrailblazePowerTask",
                "ReceiveRewardsTask",
                "MissionAccomplishTask",
            ]
        }
        with patch("SRACore.thread.task_process.load_config", return_value=config):
            with patch("SRACore.thread.task_process.Operator", MockOperator):
                tasks = p0_task_manager.get_tasks("test")
        # first 固定在头
        assert isinstance(tasks[0], FakeStartGameTask)
        # 用户自定义顺序
        assert isinstance(tasks[1], FakeCosmicStrifeTask)
        assert isinstance(tasks[2], FakeTrailblazePowerTask)
        assert isinstance(tasks[3], FakeReceiveRewardsTask)
        # last 固定在尾
        assert isinstance(tasks[4], FakeMissionAccomplishTask)

