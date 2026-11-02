"""Translate presentation output only, without touching game recognition or stored values.

The supplementary catalog contains the original output templates. Matching happens
only at the logging/CLI/notification boundary, after all game decisions are made.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from SRACore.localization import Resources

_FIELD = re.compile(r"\{(\d+)\}")


@lru_cache(maxsize=1)
def _catalog():
    entries = json.loads(Path(__file__).with_name("presentation.json").read_text(encoding="utf-8"))
    exact = {}
    patterns = {}
    for entry in entries:
        source, target = entry["source"], entry["ru"]
        fields = list(_FIELD.finditer(source))
        if not fields:
            exact.setdefault(source, target)
            continue
        parts, last = [], 0
        for field in fields:
            parts.extend((re.escape(source[last:field.start()]), "(.*?)"))
            last = field.end()
        parts.append(re.escape(source[last:]))
        literal_size = len(source) - sum(len(m[0]) for m in fields)
        if literal_size < 3:
            continue
        prefix = source[:fields[0].start()]
        patterns.setdefault(prefix[:1], []).append((literal_size, prefix, re.compile("".join(parts), re.DOTALL), target))
    for items in patterns.values():
        items.sort(key=lambda item: item[0], reverse=True)
    return exact, patterns


@lru_cache(maxsize=1024)
def _russian(text: str) -> str:
    exact, patterns = _catalog()
    if text in exact:
        return exact[text]
    for _, prefix, pattern, target in (*patterns.get(text[:1], ()), *patterns.get("", ())):
        if not text.startswith(prefix):
            continue
        match = pattern.fullmatch(text)
        if match:
            # Replace fields, not str.format: captured text may contain braces.
            def replacement(field):
                value = match[int(field[1]) + 1]
                return _russian(value) if len(value) < len(text) else exact.get(value, value)
            return _FIELD.sub(replacement, target)
    return text


def translate(text: str) -> str:
    return _russian(text) if Resources.lang == "ru-ru" else text


def to_russian(text: str) -> str:
    """无条件返回俄语译文；用于接口一次返回多语、不依赖全局语言的场景。"""
    return _russian(text)


