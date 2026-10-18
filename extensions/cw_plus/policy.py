"""可配置准备阶段策略的严格文本观测。
解析器不认证页面，也不决定输入动作；调用方必须裁剪目标界面，并要求不同帧上的观测一致。
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
    """可选回合边界，包含端点，独立于经济阶段。"""
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
    """仅读取完整的 x-y 标签，可同时包含准备阶段标题。"""
    if not isinstance(text, str):
        return None
    normalized = unicodedata.normalize("NFKC", text)
    normalized = re.sub(r"[\s|]+", "", normalized)
    normalized = re.sub(r"[‐‑‒–—−]", "-", normalized)
    match = re.fullmatch(r"(?:备战阶段)?([1-9])-([1-9])", normalized)
    return (int(match[1]), int(match[2])) if match is not None else None


def parse_experience_progress(text: str, *, level: int) -> tuple[int, int] | None:
    """将唯一的进度分数关联到相邻且明确的商店等级。
    人口分数、无关数字、混合帧和冲突标签都不能作为花费保留金币的报价依据。
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


# Yukki：满级标签须与对应等级相邻，不能靠孤立文字推断。
def parse_experience_cap(text: str, *, level: int) -> bool | None:
    """将明确的满级标记关联到唯一匹配的商店等级标签。
    True 确认满级；False 允许继续普通进度解析。
    None 表示满级证据与标签、分数或位置存在冲突。
    允许周围 OCR 文本，但不能再提供另一满级标记或等级。
    调用方仍须要求不同帧的观测一致。
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
    if marker.end() <= label.start() and marker[0] in ("等级已满", "已满级", "满级"):
        # 游戏满级面板把中文提示放在等级上方，OCR 按行先读提示。
        if marker.start() and re.match(r"\w", normalized[marker.start() - 1]):
            return None  # “未满级”等词中的子串不是独立的满级提示。
        between = normalized[marker.end():label.start()]
    elif label.end() <= marker.start():
        between = normalized[label.end():marker.start()]
    else:
        return None
    if re.fullmatch(r"[\s|]*", between) is None:
        return None
    return True
