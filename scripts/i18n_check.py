#!/usr/bin/env python3
"""校验三语术语表：键集（类名 + JsonPropertyName）与占位符必须一致。

用法：``python scripts/i18n_check.py``
退出码：0 表示一致；1 表示存在缺失/多余键、占位符不一致或空译文。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANG_DIR = ROOT / "SRACore" / "localization"
LANGS = ["zh-cn", "en-us", "ru-ru"]
PLACEHOLDER = re.compile(r"\{[^{}]*\}")


def load(lang: str) -> dict[str, dict[str, str]]:
    """读取某一语言的术语表；文件缺失直接失败。"""
    path = LANG_DIR / f"terms.{lang}.json"
    if not path.exists():
        print(f"[ERROR] 缺少语言文件: {path.relative_to(ROOT)}")
        sys.exit(1)
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def flatten(data: dict[str, dict[str, str]]) -> dict[str, str]:
    """展开为 ``类名.别名`` 形式的扁平表，便于逐键比对。"""
    return {
        f"{cls}.{key}": value
        for cls, entries in data.items()
        for key, value in entries.items()
    }


def main() -> int:
    base = flatten(load("zh-cn"))
    failed = False
    for lang in LANGS[1:]:
        other = flatten(load(lang))
        missing = sorted(base.keys() - other.keys())
        extra = sorted(other.keys() - base.keys())
        if missing:
            failed = True
            print(f"[MISSING] {lang}: {len(missing)} 个键未翻译")
            for key in missing:
                print(f"  - {key}")
        if extra:
            failed = True
            print(f"[EXTRA] {lang}: {len(extra)} 个键在中文表不存在")
            for key in extra:
                print(f"  - {key}")
        for key in sorted(base.keys() & other.keys()):
            expected = PLACEHOLDER.findall(base[key])
            actual = PLACEHOLDER.findall(other[key])
            if expected != actual:
                failed = True
                print(f"[PLACEHOLDER] {lang}.{key}: 期望 {expected}，实际 {actual}")
            if not other[key].strip():
                failed = True
                print(f"[EMPTY] {lang}.{key}: 译文为空")
    if failed:
        print("[FAIL] 三语术语表不一致")
        return 1
    print(f"[OK] 三语术语表一致：{len(base)} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())