"""Strict text observations for configurable preparation policies.

These parsers do not authenticate a page or make input decisions. Their caller
must crop the intended UI and require matching observations on separate frames.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class OpeningPolicyConfig:
    sell_from_round: tuple[int, int] | None = None
    refresh_from_round: tuple[int, int] | None = None


def parse_opening_policy_config(data) -> OpeningPolicyConfig | None:
    """Optional inclusive round boundaries, independent of the economy stage."""
    if data is None:
        return None
    keys = {"sell_from_round", "refresh_from_round"}
    if not isinstance(data, dict) or not data.keys() <= keys:
        raise ValueError("opening_policy 仅支持 sell_from_round 和 refresh_from_round")
    rounds = {}
    for key, value in data.items():
        if not isinstance(value, str) or re.fullmatch(r"[1-9]-[1-9]", value) is None:
            raise ValueError(f"opening_policy.{key} 必须为 x-y 格式的回合，如 1-4")
        rounds[key] = tuple(int(part) for part in value.split("-"))
    return OpeningPolicyConfig(**rounds)


def parse_preparation_round(text: str) -> tuple[int, int] | None:
    """Read only a complete x-y label, optionally with the preparation heading."""
    if not isinstance(text, str):
        return None
    normalized = unicodedata.normalize("NFKC", text)
    normalized = re.sub(r"[\s|]+", "", normalized)
    normalized = re.sub(r"[‐‑‒–—−]", "-", normalized)
    match = re.fullmatch(r"(?:备战阶段)?([1-9])-([1-9])", normalized)
    return (int(match[1]), int(match[2])) if match is not None else None


def parse_experience_progress(text: str, *, level: int) -> tuple[int, int] | None:
    """Bind a unique progress fraction to its adjacent explicit shop level.

    Population fractions, unrelated numbers, mixed frames and conflicting
    labels cannot supply a quote for spending the reserve.
    """
    if not isinstance(text, str) or type(level) is not int or not 1 <= level <= 20:
        return None
    normalized = unicodedata.normalize("NFKC", text)
    labels = list(re.finditer(r"(?<![\w])LV\s*[.:]?\s*([0-9]+)(?![0-9./])",
                             normalized, re.IGNORECASE))
    fractions = list(re.finditer(r"(?<![\d.])([0-9]{1,4})\s*/\s*([0-9]{1,4})(?![\d.])",
                                normalized))
    if len(labels) != 1 or int(labels[0][1]) != level or len(fractions) != 1:
        return None
    label, fraction = labels[0], fractions[0]
    if fraction.start() < label.end():
        return None
    if re.fullmatch(r"[\s|]*", normalized[label.end():fraction.start()]) is None:
        return None
    current, required = int(fraction[1]), int(fraction[2])
    return (current, required) if 0 <= current < required else None


def parse_experience_cap(text: str, *, level: int) -> bool | None:
    """Bind an explicit cap marker to the sole matching shop-level label.

    True confirms a cap; False leaves ordinary progress parsing available.
    None means cap evidence conflicts with a label, fraction or its location.
    Surrounding OCR text is allowed, but it cannot supply another cap or level.
    The caller must still require agreeing observations on separate frames.
    """
    if not isinstance(text, str) or type(level) is not int or not 1 <= level <= 20:
        return None
    normalized = unicodedata.normalize("NFKC", text)
    markers = list(re.finditer(r"(?:MAX|等级已满|已满级|满级)(?![\w])",
                              normalized, re.IGNORECASE))
    if not markers:
        return False
    labels = list(re.finditer(r"(?<![\w])LV\s*[.:]?\s*([0-9]+)(?![0-9./])",
                             normalized, re.IGNORECASE))
    if (len(markers) != 1 or len(labels) != 1 or int(labels[0][1]) != level
            or re.search(r"\d\s*/\s*\d", normalized) is not None):
        return None
    label, marker = labels[0], markers[0]
    if (marker.start() < label.end()
            or re.fullmatch(r"[\s|]*", normalized[label.end():marker.start()]) is None):
        return None
    return True
