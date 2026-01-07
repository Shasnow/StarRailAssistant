from SRACore.localization.resource import Resource
from SRACore.util.config import load_settings

lang_support = [
    'zh-cn',  # 中文
    'en-us',  # 英文
]
current_lang = lang_support[load_settings().get('Language', 0)]
Resource.set_language(current_lang)

__all__ = ['Resource']