"""三语术语表的加载，以及向 JSON Schema 注入 ``x-i18n``。

术语表由 ``scripts/model_gen.py`` 以中文为基准生成（``terms.zh-cn.json``），
``terms.en-us.json`` / ``terms.ru-ru.json`` 由人工维护。本模块只读，无副作用。

约定：节点上的 ``x-i18n`` 是该节点 ``description`` 的多语言译文，
键为 BCP-47 语言标识；``description`` 原字符串保留作中文兜底。
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_BASE = Path(__file__).resolve().parent
# 文件名后缀 → 对外语言标识
_LANG_FILES = {"zh-cn": "zh-CN", "en-us": "en-US", "ru-ru": "ru-RU"}


@lru_cache(maxsize=1)
def terms() -> dict[str, dict[str, dict[str, str]]]:
    """返回 ``{类名: {JsonPropertyName: {语言: 文案}}}``。

    缺失的语言文件会被跳过，因此只有中文表时也能工作。
    """
    result: dict[str, dict[str, dict[str, str]]] = {}
    for suffix, tag in _LANG_FILES.items():
        path = _BASE / f"terms.{suffix}.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for cls, entries in data.items():
            for key, text in entries.items():
                result.setdefault(cls, {}).setdefault(key, {})[tag] = text
    return result


def _ref_target(node: dict) -> str | None:
    """取 ``{"$ref": "#/components/schemas/Foo"}`` 的目标类名。"""
    ref = node.get("$ref")
    return ref.rsplit("/", 1)[-1] if isinstance(ref, str) else None


def attach_i18n(schemas: dict[str, dict]) -> None:
    """就地为模型 schema 注入 ``x-i18n``。

    - **属性节点**：按「所属类名 + 属性别名」命中术语表；
    - **模型节点**：类说明存放在引用它的属性术语里（如 ``AppSettings.advanced`` →
      ``AdvancedSettings``），据此补到模型级 ``description`` 上。

    未命中的节点保持原样，``description`` 继续作为中文兜底。可重复调用（幂等）。
    """
    catalog = terms()

    # 先由「引用该类的属性」推导出每个类的说明译文
    class_i18n: dict[str, dict[str, str]] = {}
    for model_name, schema in schemas.items():
        for key, node in (schema.get("properties") or {}).items():
            target = _ref_target(node) if isinstance(node, dict) else None
            if target:
                texts = catalog.get(model_name, {}).get(key)
                if texts:
                    class_i18n.setdefault(target, texts)

    for model_name, schema in schemas.items():
        for key, node in (schema.get("properties") or {}).items():
            if not isinstance(node, dict):
                continue
            texts = catalog.get(model_name, {}).get(key)
            if texts:
                node["x-i18n"] = dict(texts)
        if model_name in class_i18n:
            schema["x-i18n"] = dict(class_i18n[model_name])