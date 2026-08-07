import json

from loguru import logger

from SRACore.models.app_settings import AppSettings
from SRACore.util.const import AppDataDir


class SettingsService:
    def __init__(self):
        self.path = AppDataDir / 'settings.json'
        self.st_mtime = self.path.stat().st_mtime if self.path.exists() else 0
        self._settings: AppSettings = self.load_settings() if self.path.exists() else AppSettings()

    @property
    def settings(self) -> AppSettings:
        """获取应用设置"""
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
