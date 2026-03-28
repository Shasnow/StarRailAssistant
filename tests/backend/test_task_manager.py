"""
测试 TaskManager 核心逻辑：任务加载、筛选、执行流程。
"""

from unittest.mock import patch, MagicMock

from tests.backend.conftest import (
    MockOperator, FakeBaseTask,
    FakeStartGameTask, FakeTrailblazePowerTask, FakeReceiveRewardsTask,
    FakeCosmicStrifeTask, FakeMissionAccomplishTask,
    FakeFailingTask, FakeExplodingTask, TASK_MAP, build_import_side_effect,
)

from SRACore.thread.task_process import TaskManager


# ============================================================
# get_tasks() 测试
# ============================================================

class TestGetTasks:
    """任务筛选逻辑测试"""

    def test_all_enabled(self, task_manager):
        """所有任务启用时返回完整列表"""
        config = {"TaskOrder": ["StartGameTask", "TrailblazePowerTask", "ReceiveRewardsTask", "CosmicStrifeTask", "MissionAccomplishTask"]}
        with patch("SRACore.thread.task_process.load_config", return_value=config):
            with patch("SRACore.thread.task_process.Operator", MockOperator):
                tasks = task_manager.get_tasks("test")
        assert len(tasks) == 5

    def test_partial_enabled(self, task_manager):
        """部分启用时只返回选中的任务"""
        config = {"TaskOrder": ["StartGameTask", "ReceiveRewardsTask", "MissionAccomplishTask"]}
        with patch("SRACore.thread.task_process.load_config", return_value=config):
            with patch("SRACore.thread.task_process.Operator", MockOperator):
                tasks = task_manager.get_tasks("test")
        assert len(tasks) == 3
        assert isinstance(tasks[0], FakeStartGameTask)
        assert isinstance(tasks[1], FakeReceiveRewardsTask)
        assert isinstance(tasks[2], FakeMissionAccomplishTask)

    def test_none_enabled(self, task_manager):
        """空 TaskOrder 时返回空列表"""
        config = {"TaskOrder": []}
        with patch("SRACore.thread.task_process.load_config", return_value=config):
            tasks = task_manager.get_tasks("test")
        assert tasks == []

    def test_config_not_found(self, task_manager):
        """配置不存在时返回空列表"""
        with patch("SRACore.thread.task_process.load_config", return_value=None):
            tasks = task_manager.get_tasks("nonexistent")
        assert tasks == []

    def test_no_task_order_field(self, task_manager):
        """配置中缺少 TaskOrder 字段时返回空列表"""
        config = {"SomeOtherField": "value"}
        with patch("SRACore.thread.task_process.load_config", return_value=config):
            tasks = task_manager.get_tasks("test")
        assert tasks == []

    def test_password_hidden_in_log(self, task_manager):
        """验证密码在日志中被脱敏"""
        config = {
            "TaskOrder": ["StartGameTask"],
            "StartGamePassword": "my_secret_123"
        }
        with patch("SRACore.thread.task_process.load_config", return_value=config):
            with patch("SRACore.thread.task_process.Operator", MockOperator):
                tasks = task_manager.get_tasks("test")
        # 原始 config 不应被修改（脱敏用的是 copy）
        assert config["StartGamePassword"] == "my_secret_123"

    def test_execution_order_matches_task_order(self, task_manager):
        """执行顺序与 TaskOrder 声明顺序一致"""
        config = {"TaskOrder": ["StartGameTask", "CosmicStrifeTask", "TrailblazePowerTask", "MissionAccomplishTask"]}
        with patch("SRACore.thread.task_process.load_config", return_value=config):
            with patch("SRACore.thread.task_process.Operator", MockOperator):
                tasks = task_manager.get_tasks("test")
        assert len(tasks) == 4
        assert isinstance(tasks[0], FakeStartGameTask)       # fixed=first
        assert isinstance(tasks[1], FakeCosmicStrifeTask)    # 用户排序
        assert isinstance(tasks[2], FakeTrailblazePowerTask) # 用户排序
        assert isinstance(tasks[3], FakeMissionAccomplishTask) # fixed=last


# ============================================================
# get_task() 测试
# ============================================================

class TestGetTask:
    """单任务查找测试"""

    def test_find_by_class_name(self, task_manager):
        """按类名查找（命中 task_registry 中的类）"""
        config = {}
        with patch("SRACore.thread.task_process.load_config", return_value=config):
            with patch("SRACore.thread.task_process.Operator", MockOperator):
                task = task_manager.get_task("test_config", "StartGameTask")
        assert task is not None
        assert isinstance(task, FakeStartGameTask)

    def test_find_case_insensitive(self, task_manager):
        """类名查找不区分大小写"""
        config = {}
        with patch("SRACore.thread.task_process.load_config", return_value=config):
            with patch("SRACore.thread.task_process.Operator", MockOperator):
                task = task_manager.get_task("test_config", "startgametask")
        assert task is not None

    def test_nonexistent_task(self, task_manager):
        """任务不存在返回 None（动态导入也找不到）"""
        with patch("SRACore.thread.task_process.load_config", return_value={}):
            with patch("SRACore.thread.task_process.importlib.import_module", side_effect=ModuleNotFoundError):
                task = task_manager.get_task("test", "NoSuchTask")
        assert task is None

    def test_config_not_found(self, task_manager):
        """配置文件不存在返回 None"""
        with patch("SRACore.thread.task_process.load_config", return_value=None):
            task = task_manager.get_task("nonexistent", "StartGameTask")
        assert task is None


# ============================================================
# run() 测试
# ============================================================

class TestRun:
    """主执行循环测试"""

    def test_run_with_config_names(self, task_manager):
        """指定配置名执行"""
        config = {"TaskOrder": ["StartGameTask"]}
        with patch("SRACore.thread.task_process.load_config", return_value=config):
            with patch("SRACore.thread.task_process.Operator", MockOperator):
                with patch("SRACore.thread.task_process.notify"):
                    task_manager.run("config1")

    def test_run_without_args_uses_cache(self, task_manager):
        """不指定配置时从缓存读取"""
        config = {"TaskOrder": ["StartGameTask"]}
        with patch("SRACore.thread.task_process.load_cache", return_value={"ConfigNames": ["c1"]}):
            with patch("SRACore.thread.task_process.load_config", return_value=config):
                with patch("SRACore.thread.task_process.Operator", MockOperator):
                    with patch("SRACore.thread.task_process.notify"):
                        task_manager.run()

    def test_run_skips_empty_tasks(self, task_manager):
        """空 TaskOrder 跳过该配置"""
        config = {"TaskOrder": []}
        with patch("SRACore.thread.task_process.load_config", return_value=config):
            with patch("SRACore.thread.task_process.notify"):
                task_manager.run("config1")

    def test_run_stops_on_failure(self, task_manager):
        """任务失败时停止后续任务"""
        task_manager.task_registry["StartGameTask"].task_class = FakeFailingTask
        config = {"TaskOrder": ["StartGameTask"]}
        with patch("SRACore.thread.task_process.load_config", return_value=config):
            with patch("SRACore.thread.task_process.Operator", MockOperator):
                with patch("SRACore.thread.task_process.notify"):
                    task_manager.run("config1")

    def test_run_handles_exception(self, task_manager):
        """任务抛异常时 break 不崩溃"""
        task_manager.task_registry["StartGameTask"].task_class = FakeExplodingTask
        config = {"TaskOrder": ["StartGameTask"]}
        with patch("SRACore.thread.task_process.load_config", return_value=config):
            with patch("SRACore.thread.task_process.Operator", MockOperator):
                with patch("SRACore.thread.task_process.notify"):
                    task_manager.run("config1")

    def test_run_multiple_configs(self, task_manager):
        """多配置依次执行"""
        config = {"TaskOrder": ["StartGameTask"]}
        with patch("SRACore.thread.task_process.load_config", return_value=config):
            with patch("SRACore.thread.task_process.Operator", MockOperator):
                with patch("SRACore.thread.task_process.notify"):
                    task_manager.run("c1", "c2")

    def test_run_handles_top_level_crash(self, task_manager):
        """主循环异常被捕获"""
        with patch("SRACore.thread.task_process.load_cache", side_effect=RuntimeError("crash")):
            task_manager.run()  # 不应抛异常


# ============================================================
# run_task() 测试
# ============================================================

class TestRunTask:
    """单任务执行测试"""

    def test_run_task_success(self, task_manager):
        """成功执行单任务"""
        config = {}
        with patch("SRACore.thread.task_process.load_config", return_value=config):
            with patch("SRACore.thread.task_process.Operator", MockOperator):
                result = task_manager.run_task("StartGameTask", "test")
        assert result is True

    def test_run_task_failure(self, task_manager):
        """任务返回 False"""
        task_manager.task_registry["StartGameTask"].task_class = FakeFailingTask
        config = {}
        with patch("SRACore.thread.task_process.load_config", return_value=config):
            with patch("SRACore.thread.task_process.Operator", MockOperator):
                result = task_manager.run_task("StartGameTask", "test")
        assert result is False

    def test_run_task_no_config(self, task_manager):
        """缓存中无配置时返回 False"""
        with patch("SRACore.thread.task_process.load_cache", return_value={}):
            result = task_manager.run_task("StartGameTask")
        assert result is False

    def test_run_task_uses_cache(self, task_manager):
        """不指定配置名时从缓存获取"""
        config = {}
        with patch("SRACore.thread.task_process.load_cache", return_value={"CurrentConfigName": "cached"}):
            with patch("SRACore.thread.task_process.load_config", return_value=config):
                with patch("SRACore.thread.task_process.Operator", MockOperator):
                    result = task_manager.run_task("StartGameTask")
        assert result is True

    def test_run_task_not_found(self, task_manager):
        """任务不存在返回 False"""
        with patch("SRACore.thread.task_process.load_config", return_value={}):
            with patch("importlib.import_module", side_effect=ModuleNotFoundError):
                result = task_manager.run_task("NoSuch", "test")
        assert result is False
