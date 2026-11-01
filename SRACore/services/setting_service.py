"""设置服务：settings.json 的读写与「section + 点号字段名」部分更新。"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger
from pydantic import ValidationError

from SRACore.models.app_settings import AppSettings
from SRACore.util.const import SettingsJson


class SettingsService:
    """应用设置的读写：按 mtime 热重载 + 字典化读写。"""

    def __init__(self) -> None:
        self.path = SettingsJson
        self.st_mtime = self.path.stat().st_mtime if self.path.exists() else 0
        self._settings: AppSettings = self.load_settings() if self.path.exists() else AppSettings()

    @property
    def settings(self) -> AppSettings:
        """获取应用设置（文件被外部修改时按 mtime 自动重载）"""
        if self.path.exists():
            mtime = self.path.stat().st_mtime
            if mtime != self.st_mtime:
                logger.debug("Settings file modified, reload settings")
                self._settings = self.load_settings()
                self.st_mtime = mtime
        return self._settings

    def load_settings(self) -> AppSettings:
        with open(self.path, 'r') as f:
            return AppSettings.from_dict(json.load(f))

    def save_settings(self) -> None:
        # 必须在打开文件（截断）前求值：否则 settings 属性会因 mtime 变化触发热重载，
        # 读到刚被清空的文件而抛出 JSONDecodeError，导致设置文件被清空
        payload = self.settings.to_dict()
        with open(self.path, 'w') as f:
            json.dump(payload, f, indent=2)
        self.st_mtime = self.path.stat().st_mtime

    def get_dict(self) -> dict[str, Any]:
        """返回 {section: {点号字段: 值}} 形式的应用设置。"""
        return self.settings.to_dict()

    def patch(self, partial: Any) -> list[str]:
        """按 section + 点号字段名部分更新设置。

        Args:
            partial: {section: {fieldKey: value}} 形式的部分设置。

        Returns:
            被更新的字段名列表（如 ``["advanced.backend.remote.enabled"]``）。
            无有效字段时返回空列表（由控制器转成 400）。

        类型不符等非法值会被跳过并告警（对齐 C# 端 SetFieldByJsonName 的行为），
        其余合法字段照常生效，因此「部分非法」只会得到 200（含已更新列表）或 400（全被跳过），
        不会因 Pydantic 校验异常抛 500。
        """
        current = self.get_dict()
        updated: list[str] = []
        if not isinstance(partial, dict):
            return updated
        for section, fields in partial.items():
            target = current.get(section)
            if not isinstance(target, dict) or not isinstance(fields, dict):
                continue
            for key, value in fields.items():
                if key not in target:
                    continue
                original = target[key]
                target[key] = value
                try:
                    candidate = AppSettings.from_dict(current)
                except ValidationError as e:
                    target[key] = original
                    logger.warning(f"忽略非法设置项 {section}.{key}={value!r}: {e.errors()[0].get('msg')}")
                    continue
                self._settings = candidate
                updated.append(f"{section}.{key}")

        if updated:
            self.save_settings()
        return updated