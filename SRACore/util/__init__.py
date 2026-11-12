import importlib
import sys
from pathlib import Path

from loguru import logger

import SRACore.util.strutil as strutil
import SRACore.util.sys_util as sys_util

def dynamic_import(package: str):
    """动态导入包"""
    try:
        # 扫描 package 包下的所有 .py 文件，导入每个模块
        for file in Path(package).glob("*.py"):
            importlib.import_module(f"{package}.{file.stem}")
    except ModuleNotFoundError:
        pass

def reload_package(package: str):
    """重新加载包，并递归重载其中的子包（目录包）。

    以 ``tasks`` 为例：它本身不是 Python 包，主模块（``tasks/CosmicStrifeTask.py`` 等）
    通过子目录导入子模块（``tasks/currency_wars``）。只重载主模块时，子模块仍留在
    ``sys.modules`` 中，代码改动不会生效。因此先按“由深到浅”重载子包及其已导入的
    子模块，再重载顶层模块，保证主模块重新绑定到的都是新对象。
    """
    root = Path(package)
    if not root.is_dir():
        return
    for entry in sorted(root.iterdir()):
        if entry.is_dir() and not entry.name.startswith("__") and (entry / "__init__.py").is_file():
            _reload_module_tree(f"{package}.{entry.name}", entry)
    for file in root.glob("*.py"):
        module_name = f"{package}.{file.stem}"
        try:
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
            else:
                importlib.import_module(module_name)
        except ModuleNotFoundError:
            pass


def _reload_module_tree(module_name: str, package_dir: Path) -> None:
    """重载已导入的包及其子模块：子模块先于包本身重载（由深到浅）。"""
    prefix = f"{module_name}."
    root = package_dir.resolve()
    modules: list[str] = []
    for name, module in list(sys.modules.items()):
        if name != module_name and not name.startswith(prefix):
            continue
        module_file = getattr(module, "__file__", None)
        if module_file is None:
            continue
        try:
            Path(module_file).resolve().relative_to(root)
        except (OSError, ValueError):
            continue
        modules.append(name)
    modules.sort(key=lambda name: (name == module_name, -name.count(".")))
    for name in modules:
        try:
            importlib.reload(sys.modules[name])
        except Exception as e:
            logger.exception(f"Failed to reload module '{name}': {e}")

__all__ = [
    "strutil",
    "sys_util",
    "dynamic_import",
    "reload_package",
]
