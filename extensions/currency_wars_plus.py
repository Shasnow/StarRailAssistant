"""将最新修复的货币战争流程注册为独立扩展。"""
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field

from SRACore.extension import BaseExtension, extension
from .cw_plus.module_runtime import align_runtime_modules

# ssyb：先统一依赖身份，再绑定本次使用的引擎与恢复类型。
align_runtime_modules()

from .cw_plus.CurrencyWars import CurrencyWars
from .cw_plus.characters import Characters
from .cw_plus.paths import DEFAULT_STRATEGY, resolve_strategy_path
from .cw_plus.scoped_logging import isolated_run_log
from .cw_plus.runtime_rebuild import run_with_runtime_rebuild
from .cw_plus.strategy_catalog import scan_strategy_options
from .cw_plus.stop_compat import install_stop_compat
from .cw_plus.unicode_templates import adapt_template_operator


class CurrencyWarsPlusConfig(BaseModel):
    """通过配置结构提供攻略扫描与难度选项，高级策略保留在攻略文件中。"""
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True, extra="forbid")

    username: str = Field(default="", alias="开拓者名称", description="填写游戏内开拓者名称。")
    strategy: str = Field(default=DEFAULT_STRATEGY, alias="攻略", description="选择攻略；新增 JSON 后点击扫描攻略文件夹。也可填写攻略 JSON 的完整路径。")
    runtimes: int = Field(default=1, ge=1, le=99999, alias="运行次数", description="本次运行的局数。")
    difficulty: int = Field(default=0, ge=0, le=2, alias="难度", description="选择最低难度、最高难度或保持当前难度。",
        json_schema_extra={"enum": [0, 1, 2], "x-enum-labels": ["最低难度", "最高难度", "当前难度"]})
    overclock: bool = Field(default=False, alias="超频博弈", description="开启后运行超频博弈，关闭后运行常规博弈。")

    # Yukki：选项扫描只重建显示列表，保存值继续使用攻略文件名。
    @classmethod
    def model_json_schema(cls, *args, **kwargs):
        """扫描发生在每次配置结构请求中，新增攻略无需重新加载游戏流程。"""
        schema = super().model_json_schema(*args, **kwargs)
        options = scan_strategy_options()
        for key in ("攻略", "strategy"):
            prop = schema.get("properties", {}).get(key)
            if prop is not None:
                prop.update({"enum": [value for value, _ in options],
                    "x-enum-labels": [label for _, label in options],
                    "x-refreshable": True, "x-refresh-label": "扫描攻略文件夹",
                    "x-allow-custom": True})
        return schema


@extension(extension_id="CurrencyWarsPlus", name="货币战争优化版", description="常规与超频博弈，包含最新金币、支援识别和失败汇总修复。", background=False)
class CurrencyWarsPlusExtension(BaseExtension[CurrencyWarsPlusConfig]):
    """复用宿主操作器执行优化流程，保持独立角色表、资源和存档。"""

    def run(self) -> bool:
        if not self.config.username.strip():
            logger.error("请先在货币战争优化版的配置中填写开拓者名称。")
            return False
        try:
            strategy = resolve_strategy_path(self.config.strategy)
            if not strategy.is_file():
                logger.error(f"货币战争优化版攻略不存在：{strategy}")
                return False
        except (OSError, ValueError, TypeError) as error:
            logger.error(f"货币战争优化版配置未通过检查：{error}")
            return False
        with isolated_run_log():
            try:
                Characters.set_username(self.config.username)
                operator = adapt_template_operator(self.operator)

                # Yukki：重建只换任务对象，原操作器和停止信号保持同一归属。
                def make_engine(*, initialize_strategy=True):
                    task = CurrencyWars(operator=operator, runtimes=self.config.runtimes)
                    task._check_stop()
                    if initialize_strategy:
                        task.load_strategy(str(strategy))
                        task.set_difficulty(self.config.difficulty)
                        task.set_overclock(self.config.overclock)
                    return task

                engine = make_engine()
            except (OSError, ValueError, TypeError) as error:
                logger.error(f"货币战争优化版配置未通过检查：{error}")
                return False
            # 加载攻略会先卸载原攻略，并重置角色单例 Character。
            # 替换对象从上下文接收原先已验证的攻略，不能再次加载并清空角色事实。
            result = run_with_runtime_rebuild(engine,
                lambda: make_engine(initialize_strategy=False))
            logger.info(f"货币战争优化版本次运行结果：{'完成' if result else '失败'}（{result}）")
            return result


# 仅修正本扩展运行期间的卡片停止命令，其他任务和扩展继续由宿主处理。
install_stop_compat()
