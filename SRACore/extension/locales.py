"""扩展目录内 ``locales/*.json`` 的加载与单语合成。

约定（键为 schema 字段键名：有 ``alias`` 用 alias，否则字段名）：

- ``name`` / ``description``：扩展展示名与说明；
- ``<键>.description``：字段说明；
- ``<键>.labels``：枚举标签（与 ``enum`` 声明顺序对齐）。

后端按 ``settings.json`` 的界面语言返回单语文本：命中当前语言则用之，否则回退
中文。文件缺失或非法只记录告警，不影响扩展加载。
"""
from __future__ import annotations

import json
from pathlib import Path

from loguru import logger

SUPPORTED_LANGS = ("zh-CN", "en-US", "ru-RU")
_FALLBACK_LANG = "zh-CN"
# Resources.lang 使用小写风格，locales 文件名使用 BCP-47
_LANG_TAGS = {"zh-cn": "zh-CN", "en-us": "en-US", "ru-ru": "ru-RU"}


def load(package_dir: Path | None) -> dict[str, dict[str, object]]:
    """读取扩展目录下的三语表；无 ``locales`` 目录时返回空字典。"""
    if package_dir is None:
        return {}
    folder = Path(package_dir) / "locales"
    if not folder.is_dir():
        return {}
    tables: dict[str, dict[str, object]] = {}
    for lang in SUPPORTED_LANGS:
        path = folder / f"{lang}.json"
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(f"扩展本地化文件无效，已跳过 {path}: {exc}")
            continue
        if isinstance(data, dict):
            tables[lang] = data
    return tables


def current_lang() -> str:
    """当前界面语言（BCP-47），与 ``locales/*.json`` 文件名一致。"""
    from SRACore.localization import Resources

    raw = str(getattr(Resources, "lang", "zh-cn")).strip().lower()
    return _LANG_TAGS.get(raw, _FALLBACK_LANG)


def _pick(tables: dict[str, dict[str, object]], key: str, lang: str):
    """按当前语言取值，缺失时回退中文；没有可用值返回 ``None``。"""
    for candidate in (lang, _FALLBACK_LANG):
        value = tables.get(candidate, {}).get(key)
        if isinstance(value, (str, list)) and value:
            return value
    return None


def apply(schema: dict, tables: dict[str, dict[str, object]]) -> None:
    """就地把字段说明与枚举标签替换为当前语言的单语文本。

    仅处理根级 ``properties``；扩展代码动态注入的 ``x-enum-labels`` 不被覆盖。
    可重复调用（幂等）。
    """
    if not tables:
        return
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return
    lang = current_lang()

    for key, node in properties.items():
        if not isinstance(node, dict):
            continue

        title = _pick(tables, f"{key}.title", lang)
        if isinstance(title, str):
            node["title"] = title

        description = _pick(tables, f"{key}.description", lang)
        if isinstance(description, str):
            node["description"] = description

        labels = _pick(tables, f"{key}.labels", lang)
        if isinstance(labels, list) and "enum" in node and "x-enum-labels" not in node:
            node["x-enum-labels"] = labels


def meta(tables: dict[str, dict[str, object]]) -> dict[str, str]:
    """返回当前语言的扩展展示名与说明。"""
    lang = current_lang()
    result: dict[str, str] = {}
    for field in ("name", "description"):
        text = _pick(tables, field, lang)
        if isinstance(text, str):
            result[field] = text
    return result
