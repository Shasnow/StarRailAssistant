#   This file is part of StarRailAssistant.

#   StarRailAssistant is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by the Free Software Foundation,
#   either version 3 of the License, or (at your option) any later version.

#   StarRailAssistant is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
#   without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#   See the GNU General Public License for more details.

#   You should have received a copy of the GNU General Public License along with StarRailAssistant.
#   If not, see <https://www.gnu.org/licenses/>.

#   yukikage@qq.com

"""
国际化(i18n)工具模块
提供多语言支持功能
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

from SRACore.util.const import AppDataSraDir


class I18n:
    """国际化管理类"""
    
    _instance: Optional['I18n'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._translations = {}
            cls._instance._current_language = "zh_CN"
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialized = True
            self._load_language()
    
    def _load_language(self):
        """从settings.json加载语言设置并加载对应的翻译文件"""
        try:
            with open(AppDataSraDir / 'settings.json', 'r') as f:
                settings = json.load(f)
            language_code = settings.get('language', settings.get('Language', 1))
            # language: 0 = 中文, 1 = 英文
            self._current_language = "zh_CN" if language_code == 0 else "en_US"
        except Exception:
            self._current_language = "zh_CN"
        # 加载翻译文件
        self._load_translations()
    
    def _load_translations(self):
        """加载翻译文件"""
        try:
            translation_file = Path(f"SRACore/i18n/{self._current_language}.json")
            if translation_file.exists():
                with open(translation_file, 'r', encoding='utf-8') as f:
                    self._translations = json.load(f)
            else:
                self._translations = {}
        except Exception:
            self._translations = {}
    
    def get(self, key: str, **kwargs) -> str:
        """
        获取翻译文本
        
        Args:
            key: 翻译键，使用点号分隔的路径，如 "cli.description"
            **kwargs: 格式化参数
        
        Returns:
            翻译后的文本，如果找不到则返回键本身
        """
        keys = key.split('.')
        value = self._translations
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return key
        
        if value is None:
            return key
        
        # 如果有格式化参数，进行格式化
        if kwargs and isinstance(value, str):
            try:
                return value.format(**kwargs)
            except (KeyError, ValueError):
                return value
        
        return str(value)
    
    def reload(self):
        """重新加载语言设置"""
        # 强制重新加载
        self._load_language()


# 全局实例
_i18n = I18n()


def t(key: str, **kwargs) -> str:
    """
    获取翻译文本的快捷函数
    
    Args:
        key: 翻译键
        **kwargs: 格式化参数
    
    Returns:
        翻译后的文本
    """
    return _i18n.get(key, **kwargs)


def reload_i18n():
    """重新加载i18n配置"""
    _i18n.reload()


__all__ = ['I18n', 't', 'reload_i18n']
