"""缓存服务：读写 AppDataDir/cache.json 的配置名列表与当前配置名。"""

from __future__ import annotations

import json
from typing import Any, Callable

from SRACore.util.const import AppDataDir

CACHE_JSON = AppDataDir / "cache.json"


class CacheService:
    """cache.json 的轻量读写封装（保留其它字段）。"""

    def get(self) -> dict[str, Any]:
        try:
            with open(CACHE_JSON, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except FileNotFoundError:
            return {}
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}

    def config_names(self) -> list[str]:
        names = self.get().get("ConfigNames", [])
        return list(names) if isinstance(names, list) else []

    def current_config_name(self) -> str:
        value = self.get().get("CurrentConfigName", "")
        return value if isinstance(value, str) else ""

    def update(self, mutator: Callable[[dict[str, Any]], None]) -> None:
        """读-改-写 cache.json。"""
        data = self.get()
        mutator(data)
        CACHE_JSON.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_config_name(self, name: str) -> None:
        def _mutate(data: dict[str, Any]) -> None:
            names = data.setdefault("ConfigNames", [])
            if name not in names:
                names.append(name)

        self.update(_mutate)

    def remove_config_name(self, name: str) -> bool:
        removed = False

        def _mutate(data: dict[str, Any]) -> None:
            nonlocal removed
            names = data.get("ConfigNames", [])
            if name in names:
                names.remove(name)
                removed = True

        self.update(_mutate)
        return removed