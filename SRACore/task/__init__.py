from abc import ABC, abstractmethod
from typing import Any
import json
import os

from SRACore.operators import IOperator


class Executable:
    def __init__(self, operator: IOperator):
        self.operator = operator
        self.settings = operator.settings
        self.stop_event = self.operator.stop_event

    def stop(self):
        if self.stop_event is not None:
            self.stop_event.set()


class BaseTask(Executable, ABC):
    def __init__(self, operator: IOperator, config: dict[str, Any]):
        """
        基础任务类，所有任务类都应继承自此类。

        参数读取优先级（通过 self.get_param）：
          1. 脚本目录下的 config.json（用户手动编辑，最高优先级）
          2. SRA 任务页面配置的 Params（通过前端 UI 设置）
          3. 调用方传入的 default 值
        """
        super().__init__(operator)
        self.config = config
        self.script_config: dict[str, Any] = self._load_script_config()
        self._post_init()

    # ------------------------------------------------------------------
    # 脚本自带配置文件加载
    # ------------------------------------------------------------------

    def _load_script_config(self) -> dict[str, Any]:
        """
        加载脚本目录下的 config.json。
        路径：%APPDATA%/SRA/scripts/{script_id}/config.json

        脚本可在此文件中放置任意复杂的配置结构，
        格式和字段完全由脚本自己定义，SRA 不做任何约束。
        """
        from SRACore.util.script_manager import ScriptsDir

        script_id = self._resolve_script_id()
        if not script_id:
            return {}

        config_path = ScriptsDir / script_id / "config.json"
        if not config_path.exists():
            return {}

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return {}
            return data
        except Exception as e:
            from SRACore.util.logger import logger
            logger.warning(f"[BaseTask] 加载脚本配置失败 ({config_path}): {e}")
            return {}

    def _resolve_script_id(self) -> str | None:
        """从 SRA config 的 CustomTasks 里找到本任务对应的 ScriptId"""
        custom_tasks = self.config.get("CustomTasks", [])
        cls_name = self.__class__.__name__
        for entry in custom_tasks:
            if entry.get("TaskClassName") == cls_name:
                return entry.get("ScriptId") or None
        return None

    def _get_script_dir(self) -> str | None:
        """返回脚本安装目录的绝对路径，脚本内部可用此方法定位资产文件"""
        from SRACore.util.script_manager import ScriptsDir
        script_id = self._resolve_script_id()
        if not script_id:
            return None
        path = ScriptsDir / script_id
        return str(path) if path.exists() else None

    # ------------------------------------------------------------------
    # 统一参数读取接口
    # ------------------------------------------------------------------

    def get_param(self, key: str, default: Any = None) -> Any:
        """
        按优先级读取参数：
          1. 脚本目录的 config.json（script_config）
          2. SRA 前端任务配置的 Params 字典
          3. default

        用法：
            path = self.get_param("March7thAssistantPath", "")
            level = int(self.get_param("Level", "4"))
        """
        # 1. 脚本自带配置（支持嵌套 key，如 "divergent.level"）
        val = self._get_nested(self.script_config, key)
        if val is not None:
            return val

        # 2. SRA 前端 Params
        cls_name = self.__class__.__name__
        for entry in self.config.get("CustomTasks", []):
            if entry.get("TaskClassName") == cls_name:
                params = entry.get("Params", {})
                if key in params:
                    return params[key]
                break

        return default

    @staticmethod
    def _get_nested(d: dict, key: str) -> Any:
        """
        支持用 '.' 分隔的嵌套键读取。
        例如 key="divergent.level" 等价于 d["divergent"]["level"]
        """
        if not isinstance(d, dict):
            return None
        parts = key.split(".", 1)
        val = d.get(parts[0])
        if len(parts) == 1:
            return val
        if isinstance(val, dict):
            return BaseTask._get_nested(val, parts[1])
        return None

    # ------------------------------------------------------------------
    # 脚本配置持久化（脚本可主动保存配置）
    # ------------------------------------------------------------------

    def save_script_config(self, data: dict | None = None) -> bool:
        """
        将配置写回脚本目录的 config.json。
        如果传入 data，则合并到 script_config 后保存；
        如果不传，则直接保存当前 script_config。

        用法（脚本内首次运行时引导用户配置）：
            if not self.get_param("March7thAssistantPath"):
                # 引导用户填写...
                self.script_config["March7thAssistantPath"] = user_input
                self.save_script_config()
        """
        from SRACore.util.script_manager import ScriptsDir
        from SRACore.util.logger import logger

        script_id = self._resolve_script_id()
        if not script_id:
            logger.warning("[BaseTask] save_script_config: 无法确定脚本ID，保存失败")
            return False

        if data is not None:
            self.script_config.update(data)

        config_path = ScriptsDir / script_id / "config.json"
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.script_config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.warning(f"[BaseTask] 保存脚本配置失败 ({config_path}): {e}")
            return False

    # ------------------------------------------------------------------
    # 抽象接口
    # ------------------------------------------------------------------

    def _post_init(self):
        """子类可重写此方法以进行额外初始化"""
        pass

    @abstractmethod
    def run(self) -> bool:
        pass

    def __str__(self):
        return f"{self.__class__.__name__}"

    def __repr__(self):
        return f"<{self.__class__.__name__}>"
