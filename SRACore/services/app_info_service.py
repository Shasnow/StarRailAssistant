"""App 信息/静态资源服务：系统信息、首页短语与背景图。"""

from __future__ import annotations

import asyncio
import locale
import os
import platform
import sys
import urllib.request
from pathlib import Path

from SRACore.localization.presentation import translate
from SRACore.services.setting_service import SettingsService
from SRACore.util.const import VERSION, AppDataDir

_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
_DEFAULT_BACKGROUND = _ASSETS_DIR / "background.default.jpg"
_BACKGROUND_CACHE_DIR = AppDataDir / "cache" / "backgrounds"

_SPECIAL_BACKGROUND_URLS = {
    "shasnow": "https://shasnow.top/gallery/starrailassistant/shasnow.png",
    "yumemizukimizuki": "https://shasnow.top/gallery/starrailassistant/yumemizukimizuki.png",
}

_PHRASES_ZH = [
    "欢迎使用 SRA",
    "坐和放宽",
    "并非\n'Sequence Read Archive'",
    "启动器启动启动器",
    "-1073741819",
    "飞荧扑火，向死而生",
    "跨越寰宇终抵黯淡星外",
    "立志成为崩铁糕手",
    "Bon voyage",
    "May your path be clear",
    "May you get to where\ndreams are all\ncrystalline and sweet",
    "我们将在过去篆刻未来",
    "铁花飞，飘逸不残灰",
    "一切正常就是异常",
]

_PHRASES_EN = [
    "Welcome to SRA",
    "Sit back and relax",
    "not\n'Sequence Read Archive'",
    "Launcher launching launcher",
    "-1073741819",
    "Bon voyage",
    "May your path be clear",
    "May you get to where\ndreams are all\ncrystalline and sweet",
    "We will mark the past with the future",
    "Neverness To Everness",
]


class AppInfoService:
    """应用元信息与静态资源。"""

    def __init__(self, settings: SettingsService) -> None:
        self._settings = settings
        self._image_cache: dict[str, bytes] = {}

    def system_info(self) -> dict[str, object]:
        """后端运行时信息（字段名与 WebUI 的 AppSystemInfo 一致）。"""
        return {
            "version": VERSION,
            "osVersion": f"{platform.system()} {platform.release()}",
            "architecture": "x64" if sys.maxsize > 2**32 else "x86",
            "dotnetVersion": f"Python {platform.python_version()}",
            "processorCount": os.cpu_count() or 1,
            "cultureInfo": (locale.getlocale()[0] or ""),
        }

    def phrases(self) -> list[str]:
        """按界面语言返回首页短语。"""
        language = self._settings.settings.Display.Language
        if language == 1:
            return list(_PHRASES_EN)
        if language == 2:
            return [translate(phrase) for phrase in _PHRASES_ZH]
        return list(_PHRASES_ZH)

    async def background(self) -> bytes:
        """返回背景图字节；配置为空/加载失败时回退内置默认图。"""
        raw_uri = self._settings.settings.Display.backgroundImageUri.replace('"', "").strip()
        default = self._read_default()

        if not raw_uri:
            return default

        if raw_uri in _SPECIAL_BACKGROUND_URLS:
            data = await self._load_special_background(raw_uri)
            return data if data is not None else default

        if raw_uri in self._image_cache:
            return self._image_cache[raw_uri]

        try:
            if raw_uri.lower().startswith("http"):
                data = await asyncio.to_thread(self._download, raw_uri)
            else:
                data = await asyncio.to_thread(Path(raw_uri).read_bytes)
            self._image_cache[raw_uri] = data
            return data
        except Exception:
            return default

    @staticmethod
    def _download(url: str) -> bytes:
        with urllib.request.urlopen(url, timeout=15) as response:  # noqa: S310
            return response.read()

    @staticmethod
    def _read_default() -> bytes:
        try:
            return _DEFAULT_BACKGROUND.read_bytes()
        except Exception:
            return b""

    async def _load_special_background(self, name: str) -> bytes | None:
        cache_path = _BACKGROUND_CACHE_DIR / f"{name}.png"
        if cache_path.exists():
            try:
                return await asyncio.to_thread(cache_path.read_bytes)
            except Exception:
                pass
        try:
            data = await asyncio.to_thread(self._download, _SPECIAL_BACKGROUND_URLS[name])
        except Exception:
            return None
        try:
            _BACKGROUND_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(data)
        except Exception:
            pass
        return data