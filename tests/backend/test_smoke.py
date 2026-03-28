"""
冒烟测试：验证真实的初始化链路能走通。
不 mock 核心模块，不需要游戏窗口。

注意：冒烟测试通过 subprocess 在独立进程中执行验证，
避免单元测试的 conftest.py 中的 sys.modules mock 污染。
"""

import os
import subprocess
import sys

import pytest

# CI 环境（Windows runner）默认编码为 cp1252，无法输出中文字符。
# 强制所有子进程使用 UTF-8 编码，避免 UnicodeEncodeError。
_UTF8_ENV = {**os.environ, "PYTHONUTF8": "1"}


class TestCLISmoke:
    """验证 CLI 入口能正常启动"""

    def test_main_help(self):
        """main.py --help 能正常输出"""
        result = subprocess.run(
            [sys.executable, "main.py", "--help"],
            capture_output=True, encoding="utf-8", errors="replace",
            timeout=10, env=_UTF8_ENV
        )
        assert result.returncode == 0, f"--help 失败:\n{result.stderr}"
        assert "SRA-cli" in result.stdout or "usage" in result.stdout.lower()

    def test_main_version(self):
        """main.py --version 能正常输出版本号"""
        result = subprocess.run(
            [sys.executable, "main.py", "--version"],
            capture_output=True, encoding="utf-8", errors="replace",
            timeout=10, env=_UTF8_ENV
        )
        assert result.returncode == 0, f"--version 失败:\n{result.stderr}"


class TestTaskRegistrySmoke:
    """验证 config.toml → 任务类的完整加载链路（在独立进程中执行）"""

    @staticmethod
    def _run_check(code: str) -> subprocess.CompletedProcess:
        """在独立子进程中执行验证代码，避免 conftest mock 污染"""
        return subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, encoding="utf-8", errors="replace",
            timeout=10, env=_UTF8_ENV
        )

    def test_config_toml_loads(self):
        """config.toml 能正常解析"""
        result = self._run_check("""
import tomllib
with open("SRACore/config.toml", "rb") as f:
    config = tomllib.load(f)
assert "tasks" in config
assert len(config["tasks"]) > 0
print(f"OK: {len(config['tasks'])} tasks registered")
""")
        assert result.returncode == 0, result.stderr

    def test_all_task_modules_importable(self):
        """config.toml 中声明的所有任务模块都能导入"""
        result = self._run_check("""
import tomllib, importlib
with open("SRACore/config.toml", "rb") as f:
    tasks = tomllib.load(f).get("tasks", [])
for task in tasks:
    module = importlib.import_module(task["module"])
    cls = getattr(module, task["main"])
    assert cls is not None, f"Class {task['main']} not found in {task['module']}"
    print(f"OK: {task['main']}")
""")
        assert result.returncode == 0, f"导入失败:\n{result.stderr}"

    def test_task_classes_are_base_task(self):
        """所有注册的任务类都继承自 BaseTask"""
        result = self._run_check("""
import tomllib, importlib
from SRACore.task import BaseTask
with open("SRACore/config.toml", "rb") as f:
    tasks = tomllib.load(f).get("tasks", [])
for task in tasks:
    module = importlib.import_module(task["module"])
    cls = getattr(module, task["main"])
    assert issubclass(cls, BaseTask), f"{task['main']} not subclass of BaseTask"
    print(f"OK: {task['main']} is BaseTask")
""")
        assert result.returncode == 0, f"继承检查失败:\n{result.stderr}"

    def test_task_classes_have_run_method(self):
        """所有注册的任务类都实现了 run() 方法"""
        result = self._run_check("""
import tomllib, importlib
with open("SRACore/config.toml", "rb") as f:
    tasks = tomllib.load(f).get("tasks", [])
for task in tasks:
    module = importlib.import_module(task["module"])
    cls = getattr(module, task["main"])
    assert callable(getattr(cls, "run", None)), f"{task['main']} missing run()"
    print(f"OK: {task['main']} has run()")
""")
        assert result.returncode == 0, f"方法检查失败:\n{result.stderr}"
