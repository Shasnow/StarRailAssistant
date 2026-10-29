"""Translate presentation output only, without touching game recognition or stored values.

The supplementary catalog contains the original output templates. Matching happens
only at the logging/CLI/notification boundary, after all game decisions are made.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from SRACore.localization.resource import Resource

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
    return _russian(text) if Resource.lang == "ru-ru" else text


def localize_record(record) -> None:
    record["message"] = translate(record["message"])


def localize_schema(schema):
    """Copy schema labels; never rename properties, aliases, enum values, or defaults."""
    if Resource.lang != "ru-ru":
        return schema
    if isinstance(schema, list):
        return [localize_schema(item) for item in schema]
    if not isinstance(schema, dict):
        return schema
    result = {}
    for key, value in schema.items():
        if key in ("title", "description", "x-refresh-label") and isinstance(value, str):
            result[key] = translate(value)
        elif key == "x-enum-labels" and isinstance(value, list):
            result[key] = [translate(item) if isinstance(item, str) else item for item in value]
        elif key in ("properties", "$defs", "definitions"):
            result[key] = {name: localize_schema(prop) for name, prop in value.items()}
            if key == "properties":
                for name, prop in result[key].items():
                    if isinstance(prop, dict):
                        prop["title"] = translate(value[name].get("title", name))
        elif key not in ("enum", "default", "const", "required", "examples"):
            result[key] = localize_schema(value)
        else:
            result[key] = value
    return result
