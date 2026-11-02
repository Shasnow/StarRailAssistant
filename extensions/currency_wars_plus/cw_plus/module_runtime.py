"""在宿主重载后统一本包的类型身份，不改动宿主或其他扩展。"""
from __future__ import annotations

import importlib
from pathlib import Path
import sys
from types import FunctionType, ModuleType


# ssyb：基础模块排在使用者之前，重新执行模块时一并刷新默认参数与缓存。
_MODULE_ORDER = (
    "characters", "economy", "equipment_choice", "equipment_policy", "formation",
    "layout", "logic", "ocr_geometry", "paths", "policy", "preparation",
    "reward_fast", "session", "runtime_rebuild", "shop_overlay", "shop_stall_recovery",
    "shopping_batch", "stop_compat", "bench_full", "coins", "images",
    "population_vision", "scoped_logging", "silver_wolf_fee_recovery",
    "strategy_catalog", "unicode_templates", "game_input", "vision", "CurrencyWars",
)


def _loaded_package_modules() -> dict[str, ModuleType]:
    """只收录此包目录内、名单中已经加载的运行模块。"""
    if not __package__:
        return {}
    root = Path(__file__).resolve().parent
    modules = {}
    for stem in _MODULE_ORDER:
        name = f"{__package__}.{stem}"
        module = sys.modules.get(name)
        if not isinstance(module, ModuleType):
            continue
        filename = vars(module).get("__file__")
        if filename is None:
            continue
        try:
            if Path(filename).resolve().parent != root:
                continue
        except (OSError, TypeError, ValueError):
            continue
        modules[name] = module
    return modules


def _has_mixed_identities(modules: dict[str, ModuleType]) -> bool:
    """检查跨模块导入的顶层类与函数是否仍指向定义模块的当前对象。"""
    missing = object()
    for consumer_name, consumer in modules.items():
        for value in tuple(vars(consumer).values()):
            if not isinstance(value, (type, FunctionType)):
                continue
            owner_name = value.__module__
            if owner_name == consumer_name or owner_name not in modules:
                continue
            # 局部闭包与嵌套类型不对应模块顶层名称，不用它们推断重载状态。
            if value.__qualname__ != value.__name__:
                continue
            current = vars(modules[owner_name]).get(value.__name__, missing)
            if current is not value:
                return True
    return False


def align_runtime_modules() -> tuple[str, ...]:
    """仅在自身依赖身份混杂时，按依赖顺序重载已经加载的模块。

    初次导入及一致的重复导入不会额外重载。入口在读取引擎类型之前
    调用本函数，宿主仍负责禁止运行期间重新加载扩展。
    """
    modules = _loaded_package_modules()
    if not _has_mixed_identities(modules):
        return ()

    reloaded = []
    for name, module in modules.items():
        # 不重载本辅助模块或包入口，避免在修复过程中替换当前执行函数。
        importlib.reload(module)
        reloaded.append(name)
    if _has_mixed_identities(_loaded_package_modules()):
        raise ImportError("货币战争扩展依赖重载后仍存在不一致的类型引用。")
    return tuple(reloaded)
