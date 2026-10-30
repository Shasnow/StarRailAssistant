"""任务专用视觉证据，校准须主动启用且明确标注。
配套配置含已审核的真实样本，覆盖九个备战区槽位与五个商店槽位。
独立 field_profile.json 含固定四前台、六后台布局的已审核场上图标；动态后台仅在完整双帧认证后重定位这些图标。
配置缺失或无效时始终返回 UNKNOWN。
校准流程：截取真实窗口图像，用 crop_slot_template 裁剪，保存明确标注为空或占用的 PNG，再以 make_template_entry 构建条目并验证生成的 JSON 配置。
辅助函数不能判断人工标注是否正确，仍须在真实游戏中审核。
本模块不导入 SRACore，也不启动 GUI。
配置模式中的所有模板路径均相对于配置目录。
模式示例：{"version": 2, "window_size": [1920, 1080], "aspect_tolerance": 0.005, "scale_tolerance": 0.01, "slots": [{"area": "in_hand", "index": 0, "position": [0.229, 0.844], "relative_box": [-0.02, -0.03, 0.02, 0.03], "max_mae": 0.035, "min_margin": 0.025, "require_empty_structure": true, "empty": [{"path": "empty.png", "label": "empty", "sha256": "..."}], "occupied": [{"path": "occupied.png", "label": "occupied", "sha256": "..."}]}]}。
版本 1 保留原行为，除非槽位明确启用 require_empty_structure。
版本 2 要求所有槽位启用该标志，使旧读取器拒绝配置，而非默默省略结构检查。
"""

from __future__ import annotations

from .paths import RESOURCE_ROOT
from .layout import current_backend_extent_matches

import hashlib
from collections import OrderedDict
from copy import deepcopy
import json
import math
import re
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

ORIGINAL_LEVEL_ROI = (0.05, 0.815, 0.30, 0.87)
EXPANDED_LEVEL_ROI = (0.015, 0.74, 0.335, 0.965)
# 左下经验按钮的 Lv 标签与进度，避开底部性能叠层和大块空白。
FOCUSED_LEVEL_ROI = (0.115, 0.780, 0.195, 0.905)
# 准备界面中央计数区域，排除人物图标和前台标签。
# 此 ROI 独立于商店等级与经验文本。
POPULATION_ROI = (0.46, 0.185, 0.54, 0.26)
POPULATION_MIN_CONFIDENCE = 0.9
# 成功或失败标题先出现在屏幕中央，再移动到顶部。
BATTLE_RESULT_HEADER_ROI = (0.4, 0.17, 0.6, 0.55)
BATTLE_RESULT_ACTION_ROI = (0.35, 0.77, 0.65, 0.90)
# 已审核的结果页标签；调用方使用前须认证该页面。
# 准备页生命值没有已校准的默认 ROI。
RESULT_HEALTH_ROI = (0.30, 0.43, 0.47, 0.50)
FINAL_HEALTH_ROI = (0.43, 0.25, 0.57, 0.30)
FINAL_IDENTITY_ROI = (0.30, 0.31, 0.69, 0.39)
# 所有入口使用相同的终局操作链，包括首个按钮。
TERMINAL_STATE_ORDER = {
    "final_settle": 0, "final_summary": 1, "final_next_page": 2, "final_return": 3,
}
TERMINAL_STATES = frozenset(TERMINAL_STATE_ORDER)
CRITICAL_SAMPLE_REASONS = frozenset({"battle_entry_timeout", "result_timeout", "startup_page_not_found",
                                    "preparation_not_ready", "placement_failed", "placement_unknown",
                                    "invalid_backend_layout"})
AREAS = {"on_field", "off_field", "in_hand", "store"}


class VisionStoppedError(InterruptedError):
    """未提供宿主 stop_check 回调时，使用后备取消检查。"""


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


@dataclass(frozen=True)
class PopulationObservation:
    current: int | None
    capacity: int | None
    evidence: str
    reason: str
    raw_text: str


@dataclass(frozen=True)
class BattleScreenObservation:
    state: str
    continue_point: tuple[float, float] | None
    accelerate_point: tuple[float, float] | None
    evidence: str
    raw_text: str
    outcome: str = "unknown"
    terminal_point: tuple[float, float] | None = None


@dataclass(frozen=True)
class HealthObservation:
    current: int | None
    maximum: int | None
    evidence: str
    reason: str
    raw_text: str


def _health_value(text):
    match = re.fullmatch(r"([0-9]{1,3})(?:/([0-9]{1,3}))?", text)
    if match is None:
        return None
    current = int(match[1])
    maximum = int(match[2]) if match[2] is not None else None
    if not 0 <= current <= 100 or maximum is not None and not current <= maximum <= 100:
        return False
    if maximum == 0:
        return False
    return current, maximum


def parse_squad_health(results, *, image_size=None, evidence="squad_health_ocr") -> HealthObservation:
    """要求精确的小队生命值上下文、置信度与附近受界限约束的数字。
    裸数值、角色生命值、等级或经验均不能认证小队生命值。
    单个显示值不能推断最大值或终局结果。
    """
    rows, raw_parts = [], []
    if image_size is not None and (not isinstance(image_size, (list, tuple)) or len(image_size) != 2
                                  or not all(_number(v) and v > 0 for v in image_size)):
        return HealthObservation(None, None, evidence, "invalid_health_image_size", "")
    for entry in results[:32] if isinstance(results, (list, tuple)) else ():
        if not isinstance(entry, (list, tuple)) or len(entry) != 3 or not isinstance(entry[1], str):
            continue
        raw_parts.append(entry[1])
        try:
            if isinstance(entry[2], bool):
                continue
            score = float(entry[2])
            if not math.isfinite(score) or not 0 <= score <= 1:
                continue
            box = entry[0].tolist() if hasattr(entry[0], "tolist") else entry[0]
            if (not isinstance(box, (list, tuple)) or len(box) != 4
                    or any(not isinstance(p, (list, tuple)) or len(p) != 2
                           or any(isinstance(v, bool) for v in p) for p in box)):
                continue
            points = tuple(tuple(float(v) for v in p) for p in box)
            if any(not math.isfinite(x) or not math.isfinite(y) or x < 0 or y < 0
                   or image_size is not None and (x > image_size[0] or y > image_size[1]) for x, y in points):
                continue
            bounds = (min(x for x, _ in points), min(y for _, y in points),
                      max(x for x, _ in points), max(y for _, y in points))
            if bounds[0] >= bounds[2] or bounds[1] >= bounds[3]:
                continue
            text = re.sub(r"\s+", "", entry[1]).translate(str.maketrans("０１２３４５６７８９／", "0123456789/"))
            rows.append((text, bounds, score))
        except (TypeError, ValueError, OverflowError):
            continue
    readings, confident = set(), set()
    invalid_range, label_seen = False, False

    def add(value, score):
        nonlocal invalid_range
        if value is False:
            invalid_range = True
        elif value is not None:
            readings.add(value)
            if score >= 0.9:
                confident.add(value)

    for label, label_box, label_score in rows:
        # 心形属于生命值标签；仅去除此标签后的字形，不改数值、置信度或框校验。
        label = re.sub(r"^(小队生命值[:：]?)[❤♥♡]", r"\1", label)
        combined = re.fullmatch(r"小队生命值[:：]?([0-9]{1,3}(?:/[0-9]{1,3})?)", label)
        if combined:
            label_seen = True
            add(_health_value(combined[1]), label_score)
        elif label.rstrip(":：") == "小队生命值":
            label_seen = True
            for value_text, value_box, value_score in rows:
                value = _health_value(value_text)
                if value is None:
                    continue
                lh, vh = label_box[3] - label_box[1], value_box[3] - value_box[1]
                overlap = min(label_box[3], value_box[3]) - max(label_box[1], value_box[1])
                gap = value_box[0] - label_box[2]
                # 相邻字形边界常出现小幅框重叠。
                if overlap >= 0.5 * min(lh, vh) and -0.25 * min(lh, vh) <= gap <= 1.5 * max(lh, vh):
                    add(value, min(label_score, value_score))
    raw_text = " | ".join(raw_parts)[:240]
    if invalid_range:
        reason = "invalid_health_range"
    elif len(readings) > 1:
        reason = "ambiguous_health"
    elif len(confident) == 1:
        current, maximum = next(iter(confident))
        return HealthObservation(current, maximum, evidence, "labelled_health", raw_text)
    else:
        reason = "low_health_confidence" if readings else ("health_value_missing" if label_seen else "health_label_missing")
    return HealthObservation(None, None, evidence, reason, raw_text)


def _battle_result_lines(results, image_size):
    """仅保留精确且高置信度的词，其完整框须在 OCR 裁剪区域内。"""
    valid, texts = [], []
    if not isinstance(results, (list, tuple)):
        return valid, ""
    width, height = image_size
    for entry in results:
        if not isinstance(entry, (list, tuple)) or len(entry) != 3 or not isinstance(entry[1], str):
            continue
        texts.append(entry[1])
        try:
            if isinstance(entry[2], bool):
                continue
            score = float(entry[2])
            if not math.isfinite(score) or not 0.9 <= score <= 1:
                continue
            box = entry[0].tolist() if hasattr(entry[0], "tolist") else entry[0]
            if not isinstance(box, (list, tuple)) or len(box) != 4:
                continue
            if any(not isinstance(point, (list, tuple)) or len(point) != 2
                   or any(isinstance(value, bool) for value in point) for point in box):
                continue
            points = tuple(tuple(float(value) for value in point) for point in box)
            if any(not math.isfinite(x) or not math.isfinite(y)
                   or not 0 <= x <= width or not 0 <= y <= height for x, y in points):
                continue
            left, right = min(point[0] for point in points), max(point[0] for point in points)
            top, bottom = min(point[1] for point in points), max(point[1] for point in points)
            if left >= right or top >= bottom:
                continue
            valid.append((re.sub(r"\s+", "", entry[1]), ((left + right) / 2, (top + bottom) / 2)))
        except (TypeError, ValueError, OverflowError):
            continue
    return valid, " | ".join(texts)[:240]


def parse_population(results, *, evidence: str = "population_ocr") -> PopulationObservation:
    """仅接受完整且高置信度的 n/m 计数，绝不推断缺失的零。"""
    readings, confident, text_parts = set(), set(), []
    invalid_range = False
    if isinstance(results, (list, tuple)):
        for entry in results:
            if not isinstance(entry, (list, tuple)) or len(entry) != 3 or not isinstance(entry[1], str):
                continue
            raw = entry[1]
            text_parts.append(raw)
            # 全半角变体与空白处理仍保留原数字和斜线；
            # 字母 O、裸数字或不完整计数必须保持 UNKNOWN。
            normalized = re.sub(r"\s+", "", raw).translate(str.maketrans("０１２３４５６７８９／", "0123456789/"))
            match = re.fullmatch(r"([0-9]{1,2})/([0-9]{1,2})", normalized)
            if match is None:
                continue
            current, capacity = (int(value) for value in match.groups())
            if not (0 <= current <= capacity and 1 <= capacity <= 10):
                invalid_range = True
                continue
            reading = current, capacity
            readings.add(reading)
            try:
                score = float(entry[2]) if not isinstance(entry[2], bool) else float("nan")
            except (TypeError, ValueError, OverflowError):
                continue
            if math.isfinite(score) and POPULATION_MIN_CONFIDENCE <= score <= 1:
                confident.add(reading)
    raw_text = " | ".join(text_parts)[:240]
    if invalid_range:
        reason = "invalid_population_range"
    elif len(readings) > 1:
        reason = "ambiguous_population"
    elif len(confident) == 1:
        current, capacity = next(iter(confident))
        return PopulationObservation(current, capacity, evidence, "complete_population", raw_text)
    else:
        reason = "low_population_confidence" if readings else "population_missing"
    return PopulationObservation(None, None, evidence, reason, raw_text)


def _point(position):
    if (not isinstance(position, (list, tuple)) or len(position) != 2
            or not all(_number(v) and 0 <= v <= 1 for v in position)):
        raise ValueError("position must contain two normalized coordinates")
    return tuple(float(v) for v in position)


def _box(position, relative_box):
    x, y = _point(position)
    if (not isinstance(relative_box, (list, tuple)) or len(relative_box) != 4
            or not all(_number(v) for v in relative_box)):
        raise ValueError("relative_box must contain four finite offsets")
    left, top, right, bottom = (x + relative_box[0], y + relative_box[1],
                                x + relative_box[2], y + relative_box[3])
    if not (0 <= left < right <= 1 and 0 <= top < bottom <= 1):
        raise ValueError("slot crop must fit inside the game window")
    return left, top, right, bottom


def crop_slot_template(window_image, position, relative_box):
    """仅裁剪明确提供的真实窗口图像，不进行分类。"""
    left, top, right, bottom = _box(position, relative_box)
    width, height = window_image.size
    pixels = (round(left * width), round(top * height), round(right * width), round(bottom * height))
    if pixels[2] - pixels[0] < 8 or pixels[3] - pixels[1] < 8:
        raise ValueError("slot crop must be at least 8 by 8 pixels")
    return window_image.crop(pixels).convert("RGB")


def image_distance(image_a, image_b):
    """在固定且有界的比较网格上计算归一化 RGB 平均绝对误差。"""
    from PIL import Image, ImageChops
    size = (64, 64)
    a = image_a.convert("RGB").resize(size, Image.Resampling.BILINEAR)
    b = image_b.convert("RGB").resize(size, Image.Resampling.BILINEAR)
    histogram = ImageChops.difference(a, b).histogram()
    return sum((value % 256) * count for value, count in enumerate(histogram)) / (64 * 64 * 3 * 255)


def _rgb_grid(image):
    from PIL import Image
    data = image.convert("RGB").resize((64, 64), Image.Resampling.BILINEAR).tobytes()
    return tuple(tuple(data[offset:offset + 3]) for offset in range(0, len(data), 3))


@dataclass(frozen=True)
class EmptyStructure:
    foreground: tuple[tuple[int, tuple[int, int, int]], ...]
    background: tuple[int, ...]


def _empty_structure(image):
    """要求模板包含实际细节；标注过的纯色图块不能作为证据。"""
    pixels = _rgb_grid(image)
    counts = {}
    for pixel in pixels:
        counts[pixel] = counts.get(pixel, 0) + 1
    base = max(counts, key=counts.get)
    foreground, background = [], []
    for index, pixel in enumerate(pixels):
        delta = tuple(value - reference for value, reference in zip(pixel, base))
        contrast = max(abs(value) for value in delta)
        if contrast >= 8:
            foreground.append((index, delta))
        elif contrast <= 2:
            background.append(index)
    if len(foreground) < 24 or len(background) < 1024:
        raise ValueError("empty template lacks reliable foreground/background structure")
    return EmptyStructure(tuple(foreground), tuple(background))


def _matches_empty_structure(crop, structure):
    """在标注位置匹配相对 RGB 细节，允许小范围遮挡。"""
    pixels = _rgb_grid(crop)
    # 各通道独立中位数可防止小范围光标或动画遮挡
    # 偏移背景色估计。均匀颜色的相对对比度始终为零，
    # 因此不能通过前景检查。
    middle = len(structure.background) // 2
    base = tuple(sorted(pixels[index][channel] for index in structure.background)[middle]
                 for channel in range(3))
    background_matches = sum(
        max(abs(value - reference) for value, reference in zip(pixels[index], base)) <= 6
        for index in structure.background)
    if background_matches < 0.85 * len(structure.background):
        return False
    foreground_matches = 0
    for index, expected in structure.foreground:
        actual = tuple(value - reference for value, reference in zip(pixels[index], base))
        tolerance = max(3.0, 0.4 * max(abs(value) for value in expected))
        if max(abs(a - b) for a, b in zip(actual, expected)) <= tolerance:
            foreground_matches += 1
    return foreground_matches >= 0.70 * len(structure.foreground)


def _field_highpass(image):
    """利用局部亮度消除场地缓慢动画的蓝色背景。"""
    from PIL import Image, ImageFilter
    gray = image.convert("L").resize((64, 96), Image.Resampling.BILINEAR)
    blurred = gray.filter(ImageFilter.GaussianBlur(3))
    return tuple(a - b for a, b in zip(gray.tobytes(), blurred.tobytes()))


def _field_structure(image):
    # 每条带状区域都必须包含已审核空位标志的明确细节。
    # 纯色或渐变蓝色图块不能作为已标注的空位模板。
    detail = _field_highpass(image)
    bands = tuple(tuple((index, detail[index]) for index in range(band * 1024, (band + 1) * 1024)
                        if detail[index] >= 3) for band in range(6))
    if any(len(band) < 24 for band in bands):
        raise ValueError("field template lacks complete empty-glyph structure")
    return bands


def _matches_field_structure(crop, structure, *, allow_antialiasing=False):
    detail = _field_highpass(crop)
    if all(sum(max(1, expected * 0.4) <= detail[index] <= expected + 6
               for index, expected in band) >= 0.65 * len(band) for band in structure):
        return True
    if not allow_antialiasing:
        return False
    # 仅为完整轮廓高度相关的细线开放一个网格像素的抗锯齿容差。
    # 单靠邻域覆盖会误收密集噪点，先认证全局正轮廓相关性。
    positive = tuple(value if value >= 3 else 0 for value in detail)
    norm = sum(value * value for value in positive)
    reference_norm = sum(expected * expected for band in structure for _, expected in band)
    dot = sum(expected * positive[index] for band in structure for index, expected in band)
    if not norm or dot * dot < 0.9 ** 2 * reference_norm * norm:
        return False

    def matches(index, expected):
        low, high = max(1, expected * 0.4), expected + 6
        if low <= detail[index] <= high:
            return True
        y, x = divmod(index, 64)
        return any(low <= detail[row * 64 + column] <= high
                   for row in range(max(0, y - 1), min(96, y + 2))
                   for column in range(max(0, x - 1), min(64, x + 2)))
    # 逐段检查，避免孤立星星或被遮挡标志残留的一小部分
    # 认证整个部署槽位为空。
    return all(sum(matches(index, expected) for index, expected in band) >= 0.65 * len(band)
                for band in structure)


def _safe_template_path(base_dir, relative):
    if not isinstance(relative, str) or not relative:
        raise ValueError("template path must be relative")
    base = Path(base_dir).resolve()
    path = (base / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(base) or path.suffix.lower() != ".png":
        raise ValueError("template must be a PNG inside the profile directory")
    return path


# Yukki：校准条目保存局部模板哈希，读取时仍验证模板本身。
def make_template_entry(area: str, index: int, position, relative_box,
                        empty_path: str, occupied_path: str, profile_dir: Path,
                        *, max_mae: float = 0.035, min_margin: float = 0.025,
                        require_empty_structure: bool = False) -> dict:
    """描述两张已有且明确标注的 PNG 裁剪图，不写入文件。"""
    entry = {"area": area, "index": index, "position": list(position),
             "relative_box": list(relative_box), "max_mae": max_mae, "min_margin": min_margin,
             "require_empty_structure": require_empty_structure}
    for label, path in (("empty", empty_path), ("occupied", occupied_path)):
        resolved = _safe_template_path(profile_dir, path)
        entry[label] = [{"path": path, "label": label,
                         "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest()}]
    _validate_slot(entry, Path(profile_dir))
    return entry


@dataclass(frozen=True)
class SlotProfile:
    area: str
    index: int
    position: tuple[float, float]
    relative_box: tuple[float, float, float, float]
    max_mae: float
    min_margin: float
    empty_images: tuple[Any, ...]
    occupied_images: tuple[Any, ...]
    require_empty_structure: bool = False
    empty_structures: tuple[EmptyStructure, ...] = ()
    field_structures: tuple[Any, ...] = ()
    # 动态行只重定位已审核模板；保留源锚点以共同校正裁剪内的水平透视。
    reference_position: tuple[float, float] | None = None
    # 仅含已审核的相邻视角模板；动态槽位身份始终来自当前双帧布局。
    alternative_field_slots: tuple[SlotProfile, ...] = ()


@dataclass(frozen=True)
class VisionProfile:
    window_size: tuple[int, int]
    aspect_tolerance: float
    scale_tolerance: float
    slots: Mapping[tuple[str, int], SlotProfile]


def _validate_slot(entry, base_dir):
    from PIL import Image
    if not isinstance(entry, Mapping) or entry.get("area") not in AREAS:
        raise ValueError("invalid slot area")
    index = entry.get("index")
    if type(index) is not int or not 0 <= index < 20:
        raise ValueError("invalid slot index")
    position = _point(entry.get("position"))
    relative_box = entry.get("relative_box")
    _box(position, relative_box)
    max_mae, margin = entry.get("max_mae", 0.035), entry.get("min_margin", 0.025)
    require_structure = entry.get("require_empty_structure", False)
    if type(require_structure) is not bool:
        raise ValueError("require_empty_structure must be a boolean")
    if not (_number(max_mae) and 0 < max_mae <= 0.10
            and _number(margin) and 0.01 <= margin <= 0.25):
        raise ValueError("unsafe image-distance thresholds")
    groups = {}
    for label in ("empty", "occupied"):
        examples = entry.get(label)
        if not isinstance(examples, list) or not 1 <= len(examples) <= 12:
            raise ValueError("each slot needs 1 to 12 empty and occupied examples")
        images = []
        for example in examples:
            if not isinstance(example, Mapping) or example.get("label") != label:
                raise ValueError("template needs an explicit matching label")
            path = _safe_template_path(base_dir, example.get("path"))
            if path.stat().st_size > 5 * 1024 * 1024:
                raise ValueError("template file is too large")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if example.get("sha256") != digest:
                raise ValueError("template checksum mismatch")
            with Image.open(path) as image:
                if not (8 <= image.width <= 2048 and 8 <= image.height <= 2048):
                    raise ValueError("invalid template size")
                images.append(image.convert("RGB").copy())
        groups[label] = tuple(images)
    # 正负样本的接受区域即使在边缘也必须分离。
    if min(image_distance(a, b) for a in groups["empty"] for b in groups["occupied"]) <= 2 * max_mae + margin:
        raise ValueError("empty and occupied examples are not sufficiently separated")
    structures = tuple(_empty_structure(image) for image in groups["empty"]) if require_structure else ()
    return SlotProfile(entry["area"], index, position, tuple(relative_box),
                       float(max_mae), float(margin), groups["empty"], groups["occupied"],
                       require_structure, structures)


def validate_profile(profile: Mapping[str, Any], base_dir: Path) -> VisionProfile:
    """加载已校验校验和的样本，拒绝缺失标签或类别歧义。"""
    if (not isinstance(profile, Mapping) or type(profile.get("version")) is not int
            or profile.get("version") not in (1, 2)):
        raise ValueError("unsupported vision profile version")
    size = profile.get("window_size")
    if (not isinstance(size, (list, tuple)) or len(size) != 2
            or not all(type(v) is int and 100 <= v <= 16384 for v in size)):
        raise ValueError("profile needs the real reference window dimensions")
    aspect, scale = profile.get("aspect_tolerance", 0.005), profile.get("scale_tolerance", 0.01)
    if not (_number(aspect) and 0 <= aspect <= 0.03 and _number(scale) and 0 <= scale <= 0.25):
        raise ValueError("invalid window tolerances")
    raw_slots = profile.get("slots")
    if not isinstance(raw_slots, list) or not 1 <= len(raw_slots) <= 40:
        raise ValueError("profile must contain explicitly calibrated slots")
    slots = {}
    for raw in raw_slots:
        if (profile["version"] == 2 and
                (not isinstance(raw, Mapping) or raw.get("require_empty_structure") is not True)):
            raise ValueError("version 2 requires empty structure checks on every slot")
        slot = _validate_slot(raw, base_dir)
        left, top, right, bottom = _box(slot.position, slot.relative_box)
        expected_size = (round(right * size[0]) - round(left * size[0]),
                         round(bottom * size[1]) - round(top * size[1]))
        if any(image.size != expected_size for image in slot.empty_images + slot.occupied_images):
            raise ValueError("template dimensions do not match the labelled window crop")
        key = slot.area, slot.index
        if key in slots:
            raise ValueError("duplicate calibrated slot")
        slots[key] = slot
    return VisionProfile(tuple(size), float(aspect), float(scale), slots)


def validate_field_profile(profile: Mapping[str, Any], base_dir: Path) -> VisionProfile:
    """场上图标配置独立于旧版备战区与商店校准。"""
    if (not isinstance(profile, Mapping) or profile.get("kind") != "field_glyph_templates"
            or profile.get("window_size") != [1920, 1080]
            or profile.get("aspect_tolerance") != 0 or profile.get("scale_tolerance") != 0
            or profile.get("layout") != {"on_field": 4, "off_field": 6}):
        raise ValueError("unsupported field calibration layout")
    validated = validate_profile(profile, base_dir)
    expected = {("on_field", i) for i in range(4)} | {("off_field", i) for i in range(6)}
    if set(validated.slots) != expected:
        raise ValueError("field calibration must cover the complete reviewed layout")
    slots = {}
    for key, slot in validated.slots.items():
        # 拒绝过大的裁剪区域，避免仅通过周围场景完成认证。
        left, top, right, bottom = _box(slot.position, slot.relative_box)
        if not (40 <= (right-left)*1920 <= 70 and 85 <= (bottom-top)*1080 <= 120):
            raise ValueError("field crop must isolate the empty emblem")
        slots[key] = replace(slot, field_structures=tuple(_field_structure(image)
                                                        for image in slot.empty_images))
    return replace(validated, slots=slots)


def validate_dynamic_backend_profile(profile: Mapping[str, Any], base_dir: Path) -> VisionProfile:
    """动态行外侧空标的真实标注；不依赖五/六个普通槽或固定 NPC 数量。"""
    if (not isinstance(profile, Mapping) or profile.get("kind") != "backend_field_glyph_templates"
            or profile.get("window_size") != [1920, 1080]
            or profile.get("aspect_tolerance") != 0 or profile.get("scale_tolerance") != 0):
        raise ValueError("unsupported dynamic backend calibration")
    validated = validate_profile(profile, base_dir)
    slots = {}
    for (area, index), slot in validated.slots.items():
        left, top, right, bottom = _box(slot.position, slot.relative_box)
        if (area != "off_field" or not 0 <= index < 12
                or not (40 <= (right-left)*1920 <= 70 and 85 <= (bottom-top)*1080 <= 120)):
            raise ValueError("dynamic backend crop must isolate the empty emblem")
        slots[(area, index)] = replace(slot, field_structures=tuple(
            _field_structure(image) for image in slot.empty_images))
    return replace(validated, slots=slots)


class CurrencyWarsVision:
    def __init__(self, operator, profile_path: Path, sample_dir: Path, *,
                 stop_check: Callable[[], None] | None = None, max_samples: int = 12,
                 health_roi=None):
        self.operator = operator
        self.profile_path, self.sample_dir = Path(profile_path), Path(sample_dir)
        self.stop_check = stop_check
        self.max_samples = min(max_samples, 32) if type(max_samples) is int and max_samples >= 0 else 12
        self._sampled = set()
        self._sample_base_dir = self.sample_dir
        self._sample_scope = None
        self._sample_counts = {}
        self._sample_attempts = 0
        self._normal_sample_attempts = 0
        self._critical_reserve = 0  # 旧版平面采样保留原有总量上限。
        self._reason_quota = 1
        self._reason_quotas = {}
        self.last_sample_reason = "not_attempted"
        self.health_roi = health_roi
        self._profile = None
        self._profile_stamp = None
        self.profile_status = "not_loaded"
        self._field_profile = None
        self._field_profile_stamp = None
        self.last_slot_reason = "not_attempted"
        self.last_level_attempts = []
        self.last_population_attempts = []
        self.last_population_sample = None
        self.last_battle_attempts = []
        self.last_health_attempts = []
        self.last_layout_diagnostics = {}
        self._backend_layout_frames = []
        self._backend_layout_failures = 0
        self._backend_deep_confirmed = False

    def reset_backend_layout(self):
        """新局或页面失效时清除坐标认证，模板缓存仍可复用。"""
        self._backend_layout_failures = 0
        self._backend_deep_confirmed = False
        self._confirmed_backend_positions = ()
        self._confirmed_backend_protected_slots = ()
        self._confirmed_backend_unknown_slots = ()
        self._confirmed_backend_ordinary_slots = ()
        self._confirmed_backend_ordinary_count = None

    def _remember_backend_layout(self, observation):
        frames = getattr(self, "_backend_layout_frames", ())
        self._backend_deep_confirmed = bool(frames and
            any(details.get("layout_deep_recheck") for _, details in frames[-2:]))
        self._backend_layout_failures = 0
        observation = replace(observation, geometry_valid=True)
        self._confirmed_backend_positions = observation.positions
        self._confirmed_backend_protected_slots = observation.protected_slots
        self._confirmed_backend_unknown_slots = observation.unknown_protected_slots
        self._confirmed_backend_ordinary_slots = observation.ordinary_slots
        # 通用站位角标不能认证支援；身份疑点只撤销对应槽的动作权限。
        if observation.ordinary_count_confirmed:
            self._confirmed_backend_ordinary_count = observation.ordinary_count
        return observation

    def read_backend_layout(self, previous_positions, *, recover=False):
        """完整双帧几何与逐槽身份分开认证；角标单独命中仅触发有限身份复核。"""
        self._backend_layout_frames = []
        api = getattr(self, "layout_api", None)
        if api is None:
            from .layout import (LayoutObservation, backend_rectangle_candidates,
                                                   layout_diagnostics, revalidate_backend_layout,
                                                   validate_backend_layout)
        else:
            (LayoutObservation, backend_rectangle_candidates, layout_diagnostics,
             revalidate_backend_layout, validate_backend_layout) = api
        self._check_stop()
        self.last_layout_diagnostics = {}
        # 未完成这一轮双帧认证前，旧动态坐标不能继续授予空槽裁剪权限。
        # 历史普通槽数只用于诊断，不能否决当前画面中的新数量。
        self._confirmed_backend_positions = ()
        self._confirmed_backend_protected_slots = ()
        self._confirmed_backend_unknown_slots = ()
        self._confirmed_backend_ordinary_slots = ()
        known_ordinary_count = getattr(self, "_confirmed_backend_ordinary_count", None)
        window = (self.operator.window_context.width, self.operator.window_context.height)

        def read_once(previous):
            self._check_stop()
            self._backend_support_diagnostics = None
            frame = self.operator.screenshot()
            self._check_stop()
            if (frame is None or tuple(frame.size) != tuple(window)
                    or tuple(window) != (1920, 1080)):
                return LayoutObservation(False, reason="layout_window_mismatch"), {}
            # 始终检查整张新鲜帧，不能因宿主碰巧找到六个框就跳过行外的支援。
            # 旧坐标只帮助搜索真实边框；完整的新行优先于旧布局。
            deep = False
            boxes = backend_rectangle_candidates(frame, previous_positions=previous)
            observation = validate_backend_layout(boxes, window, previous_positions=previous)
            if not observation.valid and recover and previous:
                observation = revalidate_backend_layout(boxes, window, previous_positions=previous)
            if not observation.valid and (self._backend_layout_failures >= 3 or self._backend_deep_confirmed):
                from .layout import supplement_backend_dark_borders
                deep = True
                boxes = supplement_backend_dark_borders(frame, boxes)
                observation = validate_backend_layout(boxes, window, previous_positions=previous)
                if not observation.valid and recover and previous:
                    observation = revalidate_backend_layout(boxes, window, previous_positions=previous)
            if observation.valid:
                protected = self._authenticated_backend_support(frame, observation.positions)
                support_details = self._backend_support_diagnostics or {}
                # 居中的五框子集也能通过纯几何校验。行外探针只用于
                # 发现遗漏的真实支援；没有边框的探针绝不增加槽位或人口。
                from .layout import backend_probe_positions
                probes = backend_probe_positions(boxes, window)
                exterior = tuple(point for point in probes if not any(
                    max(abs(point[i] - anchor[i]) for i in (0, 1)) <= 0.006
                    for anchor in observation.positions))
                omitted_support = ()
                exterior_unknown = ()
                if exterior:
                    omitted_support = self._authenticated_backend_support(frame, exterior)
                    exterior_details = self._backend_support_diagnostics or {}
                    exterior_unknown = tuple(exterior_details.get("unresolved_slots", ()))
                    support_details["exterior_positions"] = list(exterior)
                    support_details["exterior_authentication"] = exterior_details
                    self._backend_support_diagnostics = support_details
                # 普通角色也有站位角标。没有支援头像时既不认证 NPC，也不推断普通身份；
                # 对应槽只允许上层有限的普通姓名/星级或双帧空位复核。
                unknown = tuple(sorted(set(support_details.get("unresolved_slots", ())) - set(protected)))
                ordinary = tuple(index for index in range(len(observation.positions))
                                 if index not in protected and index not in unknown)
                profile_valid = support_details.get("profile_valid") is True
                if not profile_valid:
                    # 支援模板不可用时，仅保存几何供恢复，不能授予身份权限。
                    unknown = tuple(index for index in range(len(observation.positions))
                                    if index not in protected)
                    ordinary = ()
                # 支援退场后仍可能保留原有边框，普通槽数会从六变成七、八等。
                # 数量不授予身份：每个普通候选仍须由角色 OCR 或双帧空标确认占用。
                # 仅角标命中的身份疑点只隔离对应槽，不将整行标成支援。
                count_confirmed = profile_valid and not unknown
                ordinary_count = len(ordinary) if count_confirmed else None
                support_details.update(ordinary_count=ordinary_count,
                    ordinary_count_confirmed=count_confirmed, ordinary_slots=list(ordinary),
                    unknown_protected_slots=list(unknown), previous_ordinary_count=known_ordinary_count)
                observation = replace(observation, protected_slots=protected,
                    unknown_protected_slots=unknown, ordinary_slots=ordinary,
                    ordinary_count_confirmed=count_confirmed, ordinary_count=ordinary_count)
                if omitted_support or exterior_unknown:
                    # 行外角标疑点只能否决完整性，不授予坐标或支援身份。
                    observation = replace(observation, valid=False, reason="backend_support_row_incomplete")
                elif len(previous_positions) > len(observation.positions):
                    extent = current_backend_extent_matches(frame, observation.positions,
                                                            previous_positions=previous_positions)
                    support_details["current_extent_confirmed"] = extent
                    if not extent:
                        observation = replace(observation, valid=False, reason="backend_support_row_incomplete")
                elif unknown:
                    observation = replace(observation, reason=("backend_identity_partial"
                        if profile_valid else "backend_support_profile_unavailable"))
            details = layout_diagnostics(boxes, window, previous_positions=previous_positions)
            if not observation.valid:
                self._backend_layout_failures = min(3, self._backend_layout_failures + 1)
            details.update(layout_deep_recheck=deep,
                           layout_detection_failures=self._backend_layout_failures)
            details.update(evidence=observation.reason, layout_recovery=recover,
                           layout_alternative=True,
                           layout_protected_slots=list(observation.protected_slots),
                           layout_unknown_protected_slots=list(observation.unknown_protected_slots),
                           layout_ordinary_slots=list(observation.ordinary_slots),
                           layout_ordinary_count_confirmed=observation.ordinary_count_confirmed,
                           layout_ordinary_count=observation.ordinary_count)
            if self._backend_support_diagnostics is not None:
                details["layout_support_authentication"] = dict(self._backend_support_diagnostics)
            # 保存实际参加认证的帧，诊断时不能换成稍后的动画画面。
            self._backend_layout_frames.append((frame, dict(details)))
            return observation, details

        try:
            if recover:
                # 缺失锚点会打断连续证据，但不能仅因一张坏帧
                # 就耗尽整个恢复机会。
                # 每个接受的槽位在两帧上仍须有真实边框。
                previous = None
                saw_valid = False
                last = LayoutObservation(False, reason="layout_unknown")
                for attempt in range(5):
                    # 原恢复最多四帧；仅第四帧深度复测成功时允许第五帧确认。
                    if attempt == 4 and not (previous is not None and
                            self.last_layout_diagnostics.get("layout_deep_recheck")):
                        break
                    if attempt:
                        self.operator.sleep(0.2)
                        self._check_stop()
                    # 各次尝试之间固定原始锚点，
                    # 避免多个不稳定候选使整行逐步漂移。
                    current, details = read_once(previous_positions)
                    details["layout_recovery_frames"] = attempt + 1
                    last = current
                    if previous is not None:
                        self.last_layout_diagnostics.update(
                            layout_second_evidence=current.reason,
                            layout_second_boxes=details.get("layout_boxes", []),
                            layout_second_positions=list(current.positions),
                            layout_second_support_authentication=details.get("layout_support_authentication"),
                            layout_recovery_frames=attempt + 1)
                        stable = (current.valid and len(current.positions) == len(previous.positions)
                            and current.protected_slots == previous.protected_slots
                            and current.unknown_protected_slots == previous.unknown_protected_slots
                            and current.ordinary_slots == previous.ordinary_slots
                            and current.ordinary_count_confirmed == previous.ordinary_count_confirmed
                            and all(abs(a - b) <= 0.002
                                for old, new in zip(previous.positions, current.positions)
                                for a, b in zip(old, new)))
                        if stable:
                            return self._remember_backend_layout(current)
                        if current.valid:
                            self._backend_layout_failures = min(3, self._backend_layout_failures + 1)
                    else:
                        self.last_layout_diagnostics = details
                    if current.valid:
                        previous = current
                        saw_valid = True
                        self.last_layout_diagnostics = details
                    else:
                        previous = None
                return replace(last, valid=False,
                    reason="layout_not_stable" if saw_valid else last.reason)
            first, details = read_once(previous_positions)
            self.last_layout_diagnostics = details
            if not first.valid:
                return first
            self.operator.sleep(0.2)
            self._check_stop()
            second, second_details = read_once(first.positions)
            self.last_layout_diagnostics.update(layout_second_evidence=second.reason,
                layout_second_boxes=second_details.get("layout_boxes", []),
                layout_second_positions=list(second.positions),
                layout_second_support_authentication=second_details.get("layout_support_authentication"))
            if (not second.valid or second.changed
                    or second.protected_slots != first.protected_slots
                    or second.unknown_protected_slots != first.unknown_protected_slots
                    or second.ordinary_slots != first.ordinary_slots
                    or second.ordinary_count_confirmed != first.ordinary_count_confirmed):
                if second.valid:
                    self._backend_layout_failures = min(3, self._backend_layout_failures + 1)
                return replace(first, valid=False, reason="layout_not_stable")
            # 提交最新帧位置，变化标记仍相对于调用方提供的旧布局。
            return self._remember_backend_layout(replace(second, changed=first.changed,
                                                          reason=first.reason))
        except Exception as error:
            self._failure(error)
            self.last_layout_diagnostics.update(evidence="layout_observation_failed",
                                                error_type=type(error).__name__)
            return LayoutObservation(False, reason="layout_observation_failed")

    # ssyb：锁定支援身份须同时满足头像、锁标与布局证据。
    def _authenticated_backend_support(self, frame, positions):
        """真实槽位的已审核支援头像与通用站位角标共同认证支援索引。
        两个裁剪必须共享平移和透视；角标本身不是支援锁，也不授予普通身份。
        """
        diagnostics = {"reason": "invalid_support_geometry", "search_radius_px": 10,
                       "profile_valid": False, "slots": [], "unresolved_slots": [],
                       "positioning_badge_slots": []}
        self._backend_support_diagnostics = diagnostics
        if not positions or len(positions) > 12 or tuple(frame.size) != (1920, 1080):
            return ()
        try:
            from PIL import Image, ImageChops
            diagnostics["reason"] = "invalid_support_profile"
            reference_position, portraits, badge = self._load_backend_support_profile()
            diagnostics["profile_valid"] = True
            radius = diagnostics["search_radius_px"]
            # 卡片的透视剪切将站位角标映到半像素位置。头像与角标仍共享
            # 同一平移和剪切，不改变素材、大小或认证阈值。
            offsets = sorted(((dx / 2, dy) for dx in range(-2 * radius, 2 * radius + 1)
                              for dy in range(-radius, radius + 1)),
                             key=lambda offset: (abs(offset[0]) + abs(offset[1]), offset))
            matched = []
            frame = frame.convert("RGB")
            for index, position in enumerate(positions):
                self._check_stop()
                position = _point(position)
                slot_details = {"index": index, "reason": "positioning_badge_not_matched"}
                diagnostics["slots"].append(slot_details)
                best_score, badge_seen, authenticated = float("inf"), False, False

                def distance_at(calibrated, shear, offset):
                    pixels, _, grid, _, _ = calibrated
                    crop = self._projected_field_crop(frame, pixels, reference_position,
                                                      position, shear, offset=offset)
                    if crop is None:
                        return float("inf")
                    resized = crop.resize((64, 64), Image.Resampling.BILINEAR)
                    # 与 image_distance 相同的 RGB 网格及 MAE，比较由 Pillow 在 C 层执行。
                    difference = ImageChops.difference(resized, grid)
                    histogram = difference.histogram()
                    return sum((value % 256) * count for value, count in enumerate(histogram)) / (
                        difference.width * difference.height * 3 * 255)

                for shear in self._backend_projection_shears(reference_position, position):
                    for offset in offsets:
                        self._check_stop()
                        badge_distance = distance_at(badge, shear, offset)
                        # 角标可见时才比较支援头像，但角标可见不等于支援。
                        if badge_distance > badge[3]:
                            continue
                        badge_seen = True
                        portrait_distance, portrait = min(
                            ((distance_at(candidate, shear, offset), candidate) for candidate in portraits),
                            key=lambda value: value[0] / value[1][3])
                        score = portrait_distance / portrait[3]
                        if score < best_score:
                            best_score = score
                            slot_details.update(reason="positioning_badge_only",
                                offset_px=list(offset), shear=round(shear, 6),
                                portrait=Path(portrait[4]).stem.removeprefix("backend-locked-support-"),
                                distances=[round(portrait_distance, 6), round(badge_distance, 6)])
                        if score <= 1:
                            authenticated = True
                            matched.append(index)
                            slot_details["reason"] = "support_portrait_and_positioning_badge_matched"
                            break
                    if authenticated:
                        break
                if badge_seen:
                    diagnostics["positioning_badge_slots"].append(index)
                if badge_seen and not authenticated:
                    diagnostics["unresolved_slots"].append(index)
            diagnostics["reason"] = "support_slots_authenticated" if matched else "no_support_authenticated"
            return tuple(matched)
        except Exception as error:
            diagnostics.update(reason="support_authentication_error", profile_valid=False,
                               error_type=type(error).__name__, error_message=str(error)[:240])
            self._failure(error)
            return ()

    def _load_backend_support_profile(self):
        """校验和只在配置或素材变动时重算，复用解码图和比较网格。"""
        from PIL import Image
        path = self.profile_path.with_name("backend_locked_support.json")
        stat = path.stat()
        if stat.st_size > 64 * 1024:
            raise ValueError("backend support profile too large")
        stamp = stat.st_mtime_ns, stat.st_size
        cached = getattr(self, "_backend_support_profile", None)
        if cached is not None and getattr(self, "_backend_support_profile_stamp", None) == stamp:
            unchanged = True
            for asset, old_stamp in self._backend_support_asset_stamps:
                current = asset.stat()
                if (current.st_mtime_ns, current.st_size) != old_stamp:
                    unchanged = False
                    break
            if unchanged:
                return cached
        raw = json.loads(path.read_text(encoding="utf-8"))
        base_templates, variants = raw.get("templates", []), raw.get("portrait_variants", [])
        if (raw.get("kind") != "reviewed_locked_backend_support"
                or raw.get("window_size") != [1920, 1080]
                or not isinstance(base_templates, list) or len(base_templates) != 2
                or any(not isinstance(entry, dict) for entry in base_templates)
                or {entry.get("kind") for entry in base_templates} not in
                   ({"portrait", "positioning_badge"}, {"portrait", "lock"})
                or not isinstance(variants, list) or len(variants) > 16
                or any(not isinstance(entry, dict) or entry.get("kind") != "portrait" for entry in variants)):
            raise ValueError("invalid backend support profile")
        reference_position = _point(raw["position"])
        portraits, badge, asset_stamps = [], None, []
        for entry in base_templates + variants:
            self._check_stop()
            asset = _safe_template_path(path.parent, entry["path"])
            asset_stat = asset.stat()
            if (asset_stat.st_size > 1024 * 1024
                    or hashlib.sha256(asset.read_bytes()).hexdigest() != entry["sha256"]):
                raise ValueError("invalid backend support template")
            threshold = entry["max_mae"]
            limit = 0.025 if entry["kind"] in {"lock", "positioning_badge"} else 0.035
            if not _number(threshold) or not 0 < threshold <= limit:
                raise ValueError("unsafe backend support threshold")
            with Image.open(asset) as source:
                template = source.convert("RGB").copy()
            bounds = _box(reference_position, entry["relative_box"])
            pixels = tuple(round(value * (1920 if i % 2 == 0 else 1080)) for i, value in enumerate(bounds))
            if ((pixels[2] - pixels[0], pixels[3] - pixels[1]) != template.size
                    or not 8 <= template.width <= 256 or not 8 <= template.height <= 256):
                raise ValueError("invalid backend support crop size")
            calibrated = (pixels, template, template.resize((64, 64), Image.Resampling.BILINEAR),
                          threshold, entry["path"])
            if entry["kind"] == "portrait":
                portraits.append(calibrated)
            else:
                badge = calibrated
            asset_stamps.append((asset, (asset_stat.st_mtime_ns, asset_stat.st_size)))
        self._backend_support_profile = reference_position, tuple(portraits), badge
        self._backend_support_profile_stamp = stamp
        self._backend_support_asset_stamps = tuple(asset_stamps)
        return self._backend_support_profile

    @staticmethod
    def _backend_projection_shears(reference_position, position):
        """固定相机下，横移引起的水平剪切与离参考槽的距离同向、成比例。
        保留无变换分支，随后只尝试有界的共同投影；不缩放头像、不放宽阈值。
        """
        delta = (position[0] - reference_position[0]) * 1920
        estimates = tuple(max(-0.35, min(0.35, delta / depth))
                          for depth in (3600.0, 2400.0, 4800.0))
        # 边框中心带有轮廓取整误差；首选投影的千分之一邻域
        # 对应不足 0.12 像素的站位角标偏差，仍是同一个共同变换。
        local = tuple(max(-0.35, min(0.35, round(estimates[0], 3) + step / 1000))
                      for step in (0, -1, 1))
        return tuple(dict.fromkeys((0.0, *estimates, *local)))

    @staticmethod
    def _projected_field_crop(frame, pixels, reference_position, position, shear, *, offset=(0, 0)):
        """把源裁剪对应的同一四边形反采样，头像与站位角标共用完整的坐标变换。"""
        from PIL import Image
        shift_x = round((position[0] - reference_position[0]) * frame.width) + offset[0]
        shift_y = round((position[1] - reference_position[1]) * frame.height) + offset[1]
        reference_y = reference_position[1] * frame.height
        left, top, right, bottom = pixels
        xs = [x + shift_x + shear * (y - reference_y)
              for x in (left, right) for y in (top, bottom)]
        if not (min(xs) >= 0 and max(xs) <= frame.width
                and 0 <= top + shift_y < bottom + shift_y <= frame.height):
            return None
        if shear == 0:
            return frame.crop((left + shift_x, top + shift_y, right + shift_x, bottom + shift_y)).convert("RGB")
        return frame.transform((right - left, bottom - top), Image.Transform.AFFINE,
            (1, shear, left + shift_x + shear * (top - reference_y), 0, 1, top + shift_y),
            resample=Image.Resampling.BILINEAR).convert("RGB")

    def capture_layout_failure(self, reason, metadata=None, *, terminal=False):
        """每个子类型保留一个有界历史样本，同时保留最新失败。
        固定的最新样本对独立于历史配额，即使重新打开同一局也如此。
        终止证据拥有自己的固定样本对，因此常规失败不会替换上次实际导致执行停止的失败。
        """
        self._check_stop()
        if not isinstance(reason, str) or not reason or len(reason) > 160 or type(terminal) is not bool:
            self.last_sample_reason = "invalid_sample_request"
            return None
        details = dict(self.last_layout_diagnostics)
        if isinstance(metadata, Mapping):
            details.update(metadata)
        details["evidence"] = reason
        frames = getattr(self, "_backend_layout_frames", ())
        if not terminal:
            self.capture_sample("invalid_backend_layout_" + reason[:100], details, critical=True,
                                frame=frames[-1][0] if frames else None)
        if not self.max_samples:
            self.last_sample_reason = "sampling_disabled"
            return None
        try:
            frames = getattr(self, "_backend_layout_frames", ())
            image = frames[-1][0] if frames else self.operator.screenshot()
            self._check_stop()
            if image is None:
                self.last_sample_reason = "screenshot_unavailable"
                return None
            payload = self._sample_metadata(details)
            filename = "last_backend_layout_stop.png" if terminal else "last_backend_layout.png"
            path = self.sample_dir / filename
            payload.update(reason=reason, window_size=list(image.size), image_file=filename,
                           profile_status=self.profile_status, calibration_status="unlabelled_requires_review",
                           critical=True, terminal=terminal, captured_at_ns=time.time_ns())
            if self._sample_scope is not None:
                payload.update(session_id=self._sample_scope[0], run_id=self._sample_scope[1])
            encoded = json.dumps(payload, ensure_ascii=False, indent=2)
            if len(encoded.encode("utf-8")) > 8192:
                encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            if len(encoded.encode("utf-8")) > 8192:
                raise ValueError("sample metadata is too large")
            self.sample_dir.mkdir(parents=True, exist_ok=True)
            frame_records = []
            for index, (observed, observed_details) in enumerate(frames):
                frame_name = Path(filename).stem + f"_frame_{index + 1}.png"
                frame_path = self.sample_dir / frame_name
                observed.save(frame_path, format="PNG")
                record = dict(image_file=frame_name,
                    sha256=hashlib.sha256(frame_path.read_bytes()).hexdigest(),
                    evidence=observed_details.get("evidence"),
                    deep_recheck=observed_details.get("layout_deep_recheck", False),
                    detection_failures=observed_details.get("layout_detection_failures", 0),
                    layout_boxes=observed_details.get("layout_boxes", []))
                frame_path.with_suffix(".json").write_text(
                    json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
                frame_records.append(dict(image_file=frame_name, sha256=record["sha256"]))
            payload["layout_observed_frames"] = frame_records
            payload["image_source"] = "layout_observation" if frames else "diagnostic_capture"
            encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            image.save(path, format="PNG")
            self._check_stop()
            path.with_suffix(".json").write_bytes(encoded.encode("utf-8"))
            self.last_sample_reason = "captured_latest"
            return path
        except Exception as error:
            self.last_sample_reason = "capture_error:" + type(error).__name__
            self._failure(error)
            return None

    @staticmethod
    def _sample_metadata(metadata):
        allowed = {"area", "index", "position", "roi", "evidence", "ocr_attempts", "profile_status", "error_type", "source",
                   "source_area", "source_index", "target_area", "target_index", "source_position", "target_position",
                   "source_name", "target_name", "observed_source_name", "observed_target_name", "layout_positions",
                   "layout_boxes", "layout_version", "snapshot_revision", "action_result", "outcome", "state",
                   "layout_centers", "layout_gaps", "layout_median_gap", "layout_candidate_count",
                   "previous_layout_positions", "layout_window_size", "layout_recovery", "layout_second_evidence",
                   "layout_alternative", "layout_recovery_frames", "layout_deep_recheck", "layout_detection_failures",
                   "layout_second_boxes", "layout_second_positions", "layout_protected_slots",
                   "layout_unknown_protected_slots", "layout_ordinary_slots",
                   "layout_ordinary_count_confirmed", "layout_ordinary_count",
                   "layout_support_authentication", "layout_second_support_authentication", "population_reason"}
        payload = {key: value for key, value in (metadata.items() if isinstance(metadata, Mapping) else ()) if key in allowed}
        if "ocr_attempts" in payload:
            attempts = payload["ocr_attempts"]
            payload["ocr_attempts"] = [
                {key: value for key, value in attempt.items()
                 if key in {"method", "roi", "level", "current", "maximum", "capacity", "text", "reason",
                            "frame_size", "scores", "variants", "crop_box", "numeric_x_min", "coins",
                            "reliable", "source", "frame_index", "rows", "geometry"}}
                for attempt in (attempts[:3] if isinstance(attempts, (list, tuple)) else ()) if isinstance(attempt, Mapping)]
            for attempt in payload["ocr_attempts"]:
                variants = attempt.get("variants")
                if variants is not None:
                    # 每帧保留有界的恢复路径及真实裁剪边界，避免诊断超过样本大小上限。
                    attempt["variants"] = [
                        {key: value for key, value in variant.items()
                         if key in {"method", "roi", "crop_box", "image_size", "text", "invalid_range",
                                    "rows", "candidates", "geometry", "duplicate_boxes"}}
                        for variant in (variants[:3] if isinstance(variants, (list, tuple)) else ())
                        if isinstance(variant, Mapping)]
                for entry in [attempt] + list(attempt.get("variants") or ()):
                    if "rows" in entry:
                        entry["rows"] = [{key: value for key, value in row.items()
                                          if key in {"text", "score", "box", "touches_crop_boundary", "issues"}}
                                         for row in entry["rows"][:8] if isinstance(row, Mapping)]
                        for row in entry["rows"]:
                            if isinstance(row.get("text"), str):
                                row["text"] = row["text"][:120]
                    if "candidates" in entry:
                        entry["candidates"] = [{key: value for key, value in row.items()
                                                if key in {"current", "capacity", "score", "box", "parts"}}
                                               for row in entry["candidates"][:5] if isinstance(row, Mapping)]
                    if isinstance(entry.get("geometry"), Mapping):
                        entry["geometry"] = {key: value for key, value in entry["geometry"].items()
                                             if key in {"bounds_source", "reason", "ocr_box", "grounded_box", "glyph_boxes"}}
        return payload

    def _check_stop(self):
        if self.stop_check is not None:
            self.stop_check()
        event = getattr(self.operator, "stop_event", None)
        if event is not None and event.is_set():
            raise VisionStoppedError("Currency Wars vision stopped")

    def _failure(self, error):
        if isinstance(error, InterruptedError) or any(cls.__name__ == "ThreadStoppedError" for cls in type(error).__mro__):
            raise error
        self._check_stop()

    @staticmethod
    def _roi_args(roi):
        return dict(zip(("from_x", "from_y", "to_x", "to_y"), roi))

    def operator_ocr(self, from_x=None, from_y=None, to_x=None, to_y=None,
                     grayscale=True, confidence=None, trace=True):
        """保留宿主 OCR 全部入口语义，仅复用新截图中完全相同的像素。"""
        from .unicode_templates import CachedOperatorOCR

        if not hasattr(self, "_operator_ocr_proxy") or self._operator_ocr_proxy._operator is not self.operator:
            self._operator_ocr_proxy = CachedOperatorOCR(self.operator)
        return self._operator_ocr_proxy.ocr(from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y,
            grayscale=grayscale, confidence=confidence, trace=trace)

    def _engine_ocr(self, image, *, minimum_confidence=None):
        """仅复用完全相同的裁剪像素；调用方仍负责获取新鲜截图。"""
        self._check_stop()
        engine = getattr(self.operator, "ocr_engine", None)
        if not hasattr(self, "_text_pixel_cache") or getattr(self, "_text_cache_engine", None) is not engine:
            self._text_pixel_cache = OrderedDict()
            self._text_cache_engine = engine
        cache_key = None
        if (callable(getattr(image, "tobytes", None))
                and all(hasattr(image, name) for name in ("mode", "size", "width", "height"))
                and 0 < image.width * image.height <= 300000):
            threshold = (getattr(self.operator, "ocr_confidence", 0.7)
                         if minimum_confidence is None else minimum_confidence)
            cache_key = (image.mode, image.size, threshold, minimum_confidence is None,
                         image.tobytes())
            if cache_key in self._text_pixel_cache:
                self._text_pixel_cache.move_to_end(cache_key)
                self._check_stop()
                return deepcopy(self._text_pixel_cache[cache_key])
        result = self._engine_ocr_uncached(image, minimum_confidence=minimum_confidence)
        if cache_key is not None:
            self._text_pixel_cache[cache_key] = deepcopy(result)
            self._text_pixel_cache.move_to_end(cache_key)
            while len(self._text_pixel_cache) > 32:
                self._text_pixel_cache.popitem(last=False)
        return result

    def _engine_ocr_uncached(self, image, *, minimum_confidence=None):
        self._check_stop()
        output = self.operator.ocr_engine(image, use_det=True, use_cls=False, use_rec=True)
        self._check_stop()
        if hasattr(output, "txts"):
            from numpy import bool_

            if output.txts is None:
                return None
            threshold = (getattr(self.operator, "ocr_confidence", 0.7)
                         if minimum_confidence is None else minimum_confidence)
            return [(box.tolist() if hasattr(box, "tolist") else box, text, float(score))
                    for box, text, score in zip(output.boxes, output.txts, output.scores)
                    if not isinstance(score, (bool, bool_))
                    and (score > threshold if minimum_confidence is None else score >= threshold)]
        if isinstance(output, tuple) and len(output) == 2:
            return output[0]  # 较旧版本 RapidOCR 的元组输出。
        return output if isinstance(output, list) else None

    # Yukki：人口结果必须保留独立帧的一致性约束。
    def read_population(self, *, enhance=False) -> PopulationObservation:
        """要求两张独立且一致的帧；每帧最多三次有限裁剪恢复。
        这只读取计数；调用方须验证准备页面，才能把零作为部署槽位为空的证据。
        """
        answers, attempts = [], []
        self.last_population_sample = None
        frame_sizes = []
        sample_frame = None
        sample_images = []
        has_engine = callable(getattr(self.operator, "ocr_engine", None))
        for frame in range(2):
            self._check_stop()
            mode = "population_frame_structure" if has_engine else (
                "population_gray" if enhance else "population_color")
            frame_size = None
            try:
                if has_engine:
                    from .population_vision import read_population_frame
                    # 恢复必须从完整原帧补取左右像素；多个变体仍只是一帧证据。
                    image = self.operator.screenshot()
                    self._check_stop()
                    sample_frame = image
                    sample_images.append((f"frame_{frame + 1}", image))
                    frame_size = image.size
                    frame_sizes.append(frame_size)
                    found = read_population_frame(image,
                        lambda crop: self._engine_ocr(crop, minimum_confidence=0.0),
                        self._check_stop, enhance=enhance,
                        on_attempt=lambda name, crop: sample_images.append((f"frame_{frame + 1}_{name}", crop)))
                    answer = PopulationObservation(found.current, found.capacity, mode,
                                                   found.reason, found.raw_text)
                    detail = {"method": mode, "frame_size": list(frame_size), "frame_index": frame + 1,
                              "current": found.current, "capacity": found.capacity,
                              "text": found.raw_text, "reason": found.reason,
                              "variants": list(found.attempts)}
                else:
                    # 保留原始 OCR 证据；置信度和人口范围
                    # 由下方 parse_population 检查。
                    results = self.operator.ocr(**self._roi_args(POPULATION_ROI),
                                                grayscale=enhance, confidence=0.0, trace=False)
                    self._check_stop()
                    decision_results = []
                    raw_parts = []
                    for row in (results or ()):
                        if not isinstance(row, (list, tuple)) or len(row) != 3:
                            continue
                        if isinstance(row[1], str):
                            raw_parts.append(row[1])
                        try:
                            score = float(row[2]) if not isinstance(row[2], bool) else float("nan")
                        except (TypeError, ValueError, OverflowError):
                            continue
                        if math.isfinite(score) and POPULATION_MIN_CONFIDENCE <= score <= 1:
                            decision_results.append(row)
                    answer = replace(parse_population(decision_results, evidence=mode),
                                     raw_text=" | ".join(raw_parts)[:240])
                    if answer.current is None and not decision_results:
                        # 兼容没有独立 OCR 引擎的旧宿主，继续严格解析完整 n/m。
                        raw_answer = parse_population(results, evidence=mode)
                        answer = replace(answer, reason=raw_answer.reason)
                    detail = {"method": mode, "roi": list(POPULATION_ROI),
                              "current": answer.current, "capacity": answer.capacity,
                              "text": answer.raw_text, "reason": answer.reason,
                              "scores": [float(row[2]) for row in (results or ())
                                         if isinstance(row, (list, tuple)) and len(row) == 3
                                         and _number(row[2])][:16]}
                self._check_stop()
                answers.append(answer)
                attempts.append(detail)
            except Exception as error:
                self._failure(error)
                answers.append(PopulationObservation(None, None, mode, type(error).__name__, ""))
                attempts.append({"method": mode, "roi": list(POPULATION_ROI),
                                 "reason": type(error).__name__})
            if frame == 0:
                sleeper = getattr(self.operator, "sleep", time.sleep)
                sleeper(0.15)
                self._check_stop()
        self.last_population_attempts = attempts
        first, second = answers
        raw_text = " | ".join(answer.raw_text for answer in answers if answer.raw_text)[:240]
        window_changed = len(frame_sizes) == 2 and frame_sizes[0] != frame_sizes[1]
        if not window_changed and first.current is not None and (first.current, first.capacity) == (second.current, second.capacity):
            return PopulationObservation(first.current, first.capacity, "two_population_frames",
                                         "consistent_population", raw_text)
        reason = ("population_window_changed" if window_changed else
                  "conflicting_population_frames" if first.current is not None and second.current is not None
                  else "population_not_confirmed")
        try:
            self.last_population_sample = self.capture_sample("unknown_population", {
                "ocr_attempts": attempts, "roi": list(POPULATION_ROI), "population_reason": reason},
                frame=sample_frame, related_images=sample_images)
        except Exception as error:
            # 留证异常不能将一个可恢复的 UNKNOWN 变成整个任务异常。
            # 明确的用户停止仍由 _failure 原样传播。
            self._failure(error)
            self.last_sample_reason = "population_sample_error:" + type(error).__name__
        if (not window_changed and first.capacity is not None
                and first.capacity == second.capacity):
            # 上限与当前人数分别确认；同帧多次处理不能代替第二张新鲜帧。
            return PopulationObservation(None, first.capacity, "two_population_capacity_frames",
                                         "consistent_population_capacity", raw_text)
        return PopulationObservation(None, None, "two_population_frames", reason, raw_text)

    def _terminal_template_point(self, frame, name):
        """将已审核的动作模板与当前这一张结果帧匹配。"""
        try:
            import cv2
            import numpy as np
        except ImportError:
            # 缺少模板运行时，终局动作保持不可用。
            # 这不能禁用普通且已完整认证的 OCR 控件。
            return None
        from .unicode_templates import load_template, template_cache_key

        path = RESOURCE_ROOT / name
        if abs(frame.width / frame.height - 16 / 9) > 0.02 or not path.is_file():
            return None
        cache = getattr(self, "_terminal_template_cache", None)
        if cache is None:
            cache = self._terminal_template_cache = OrderedDict()
        key = (template_cache_key(path), frame.width)
        if (getattr(self, "_terminal_action_frame", None) is frame
                and key in getattr(self, "_terminal_action_results", {})):
            return self._terminal_action_results[key]
        if key not in cache:
            template = load_template(path, scale=frame.width / 1920)
            cache[key] = (cv2.cvtColor(np.asarray(template), cv2.COLOR_RGB2GRAY), template.size)
        cache.move_to_end(key)
        while len(cache) > 16:
            cache.popitem(last=False)
        pattern, (template_width, template_height) = cache[key]
        x, y, right, bottom = (round(v * (frame.width if i % 2 == 0 else frame.height))
                               for i, v in enumerate(BATTLE_RESULT_ACTION_ROI))
        if getattr(self, "_terminal_action_frame", None) is not frame:
            self._terminal_action_region = cv2.cvtColor(
                np.asarray(frame.crop((x, y, right, bottom))), cv2.COLOR_RGB2GRAY)
            self._terminal_action_frame = frame
            self._terminal_action_results = {}
        region = self._terminal_action_region
        if pattern.shape[0] > region.shape[0] or pattern.shape[1] > region.shape[1]:
            self._terminal_action_results[key] = None
            return None
        _, score, _, point = cv2.minMaxLoc(cv2.matchTemplate(region, pattern, cv2.TM_CCOEFF_NORMED))
        if not math.isfinite(score) or score < 0.90:
            self._terminal_action_results[key] = None
            return None
        result = ((x + point[0] + template_width / 2) / frame.width,
                  (y + point[1] + template_height / 2) / frame.height)
        self._terminal_action_results[key] = result
        return result

    def read_combat_screen(self, frame=None) -> BattleScreenObservation:
        """同帧同时匹配战斗暂停控件和前台角色序号；不把动画变化当作入战证据。"""
        self._check_stop()
        unknown = BattleScreenObservation("unknown", None, None, "combat_hud_not_confirmed", "")
        try:
            from PIL import Image
            import cv2
            import numpy as np
            from .unicode_templates import load_template, template_cache_key
            if frame is None:
                capture = getattr(self.operator, "screenshot", None)
                if not callable(capture):
                    return unknown
                frame = capture()
                self._check_stop()
            if not isinstance(frame, Image.Image) or frame.width < 640 or frame.height < 360:
                return unknown
            if abs(frame.width / frame.height - 16 / 9) > 0.02:
                return unknown
            scores = []
            cache = getattr(self, "_combat_template_cache", OrderedDict())
            self._combat_template_cache = cache
            for name, roi in (("combat_pause.png", (0.94, 0.015, 0.99, 0.08)),
                              ("combat_party_marker.png", (0.07, 0.69, 0.60, 0.88))):
                self._check_stop()
                key = (template_cache_key(RESOURCE_ROOT / name), frame.width)
                if key not in cache:
                    template = load_template(RESOURCE_ROOT / name, mode="L", scale=frame.width / 1920)
                    if name == "combat_party_marker.png":
                        # 序号圆圈外沿会混入战场背景；圆内序号才是稳定证据。
                        inset = max(1, round(2 * frame.width / 1920))
                        template = template.crop((inset, inset,
                            template.width - inset, template.height - inset))
                    cache[key] = np.asarray(template)
                cache.move_to_end(key)
                while len(cache) > 16:
                    cache.popitem(last=False)
                pattern = cache[key]
                bounds = tuple(round(v * (frame.width if i % 2 == 0 else frame.height))
                               for i, v in enumerate(roi))
                region = np.asarray(frame.crop(bounds).convert("L"))
                if pattern.shape[0] > region.shape[0] or pattern.shape[1] > region.shape[1]:
                    return unknown
                score = float(cv2.minMaxLoc(cv2.matchTemplate(region, pattern, cv2.TM_CCOEFF_NORMED))[1])
                scores.append(f"{name}={score:.3f}")
                if not math.isfinite(score) or score < 0.92:
                    return replace(unknown, raw_text=";".join(scores))
            self._check_stop()
            return BattleScreenObservation("combat", None, None,
                "same_frame_combat_controls_and_party", ";".join(scores))
        except (ImportError, OSError, ValueError, TypeError, AttributeError):
            self._check_stop()
            return unknown

    def read_battle_screen(self, frame=None) -> BattleScreenObservation:
        """从同一帧读取标题与动作；终局模板允许额外执行一次身份 OCR。
        结果标题即使在奖励动画期间，也可认证战斗已完成。
        控件只有在同一帧上具备自身精确标签和框时才获得点击点；孤立动作标签绝不能认证结果页面。
        """
        self._check_stop()
        attempts, raw_parts = [], []
        authenticated_outcome = "unknown"
        unknown = BattleScreenObservation("unknown", None, None, "battle_result_not_confirmed", "")
        try:
            if not callable(getattr(self.operator, "ocr_engine", None)):
                self.last_battle_attempts = [{"method": "same_frame_result", "reason": "ocr_engine_unavailable"}]
                return unknown
            if frame is None:
                frame = self.operator.screenshot()
                self._terminal_action_frame = None
            self._check_stop()
            # RGB 帧保留对象身份，快检与本次完整认证才能共用模板结果。
            # 其他模式仍使用原 RGB 转换；绝不缓存下一次截图的页面结论。
            if frame.mode != "RGB":
                frame = frame.convert("RGB")
            width, height = frame.size
            if width <= 0 or height <= 0:
                raise ValueError("invalid game frame size")
            regions = []
            for name, roi in (("result_header", BATTLE_RESULT_HEADER_ROI),
                              ("result_action", BATTLE_RESULT_ACTION_ROI)):
                self._check_stop()
                pixels = tuple(round(value * (width if index % 2 == 0 else height))
                               for index, value in enumerate(roi))
                crop = frame.crop(pixels)
                rows = self._engine_ocr(crop, minimum_confidence=0.9)
                self._check_stop()
                lines, raw = _battle_result_lines(rows, crop.size)
                raw_parts.append(raw)
                if name == "result_header":
                    header_words = {text for text, _ in lines if text in {"挑战成功", "挑战失败"}}
                    if len(header_words) == 1:
                        authenticated_outcome = "success" if header_words == {"挑战成功"} else "failure"
                attempts.append({"method": name, "roi": list(roi), "text": raw,
                                 "reason": "confident_bounded_text" if lines else "text_not_confirmed"})
                regions.append((lines, pixels))
            self.last_battle_attempts = attempts
            raw_text = " | ".join(part for part in raw_parts if part)[:480]
            titles = {text for text, _ in regions[0][0]
                      if text in {"挑战成功", "挑战失败", "挑战结束"}}
            headers = titles & {"挑战成功", "挑战失败"}
            # 后续终局页没有战斗标题；须认证其自身
            # 精确的动作标签和模板，绝不能使用存储的待点击动作。
            action_labels = {text for text, _ in regions[1][0]}
            # 此时整局已结束，正在等待明确的结算点击，
            # 并非最终会出现“继续”的奖励动画。
            # “挑战结束”本身不提供任何胜负证据。
            if len(titles) == 1 and "前往结算" in action_labels:
                point = self._terminal_template_point(frame, "settle.png")
                if point is not None:
                    return BattleScreenObservation("final_settle", None, None,
                        "same_frame_terminal_title_and_settle_template", raw_text,
                        authenticated_outcome, point)
            for label, template, state in (("下一页", "next_page.png", "final_next_page"),
                                           ("返回货币战争", "back_currency_wars.png", "final_return")):
                if label in action_labels:
                    point = self._terminal_template_point(frame, template)
                    if point is not None:
                        return BattleScreenObservation(state, None, None,
                            "same_frame_terminal_action_and_template", raw_text,
                            authenticated_outcome, point)
            if len(titles) != 1:
                self.capture_sample("unknown_battle_screen", {"ocr_attempts": attempts})
                return replace(unknown, raw_text=raw_text)
            outcome = authenticated_outcome
            # 真实最终截图中的动作 OCR 仅读到“下一”；
            # 强模板与汇总页标签共同认证该页面。
            # 孤立 NEXT_STEP 不足以认证，因为开局流程也使用它。
            point = self._terminal_template_point(frame, "next_step.png")
            if point is not None:
                pixels = tuple(round(v * (width if i % 2 == 0 else height))
                               for i, v in enumerate(FINAL_IDENTITY_ROI))
                crop = frame.crop(pixels)
                lines, raw = _battle_result_lines(self._engine_ocr(crop, minimum_confidence=0.9), crop.size)
                self._check_stop()
                attempts.append({"method": "final_identity", "roi": list(FINAL_IDENTITY_ROI),
                                 "text": raw, "reason": "summary_labels"})
                identity_labels = {text for text, _ in lines}
                # 失败整局可能完全不显示排名面板；其已审核布局
                # 在标题下方显示评价，在上方显示小队生命值。
                # 所有标签都必须在同一帧上具有高置信度且位于有效边界内。
                failure_summary = (headers == {"挑战失败"}
                    and "小队生命值" in {text for text, _ in regions[0][0]}
                    and "对局评价" in identity_labels)
                # 超频胜利汇总也可能没有当前职级；必须在同帧认证完整身份与精确动作。
                success_identity = (headers == {"挑战成功"}
                    and "对局评价" in identity_labels and any(text == "小队生命值" or
                        re.fullmatch(r"小队生命值[:：]?[❤♥♡]?(?:100|[1-9]?[0-9])", text)
                         for text, _ in regions[0][0]))
                conflicting_actions = action_labels & {"下一页", "返回货币战争", "前往结算", "继续挑战", "点击空白加速"}
                if success_identity and not conflicting_actions and "下一步" not in action_labels:
                    # 原尺寸可能只读到“下一”；仅放大同一帧的原动作ROI，仍须完整高置信度文字。
                    from PIL import Image
                    action_crop = frame.crop(regions[1][1])
                    action_crop = action_crop.resize((action_crop.width * 2, action_crop.height * 2),
                                                     Image.Resampling.LANCZOS)
                    action_lines, action_raw = _battle_result_lines(
                        self._engine_ocr(action_crop, minimum_confidence=0.9), action_crop.size)
                    self._check_stop()
                    attempts.append({"method": "final_action_2x", "roi": list(BATTLE_RESULT_ACTION_ROI),
                                     "text": action_raw, "reason": "exact_action_same_frame"})
                    if "下一步" in {text for text, _ in action_lines}:
                        action_labels.add("下一步")
                success_summary = success_identity and not conflicting_actions and "下一步" in action_labels
                if {"对局评价", "当前职级"} <= identity_labels or failure_summary or success_summary:
                    return BattleScreenObservation("final_summary", None, None,
                        ("same_frame_success_header_health_evaluation_and_next_step" if success_summary
                         else "same_frame_failure_header_health_evaluation_and_next_step" if failure_summary
                         else "same_frame_final_header_labels_and_next_step"), (raw_text + " | " + raw)[:480],
                        outcome, point)
            if not headers:
                self.capture_sample("unknown_battle_screen", {"ocr_attempts": attempts})
                return replace(unknown, raw_text=raw_text)
            actions = [(text, center) for text, center in regions[1][0]
                       if text in {"继续挑战", "点击空白加速"}]
            if len(actions) == 1:
                action, center = actions[0]
                action_pixels = regions[1][1]
                point = ((action_pixels[0] + center[0]) / width,
                         (action_pixels[1] + center[1]) / height)
                if action == "继续挑战":
                    return BattleScreenObservation("result_ready", point, None,
                                                   "same_frame_result_header_and_continue", raw_text, outcome)
                if headers == {"挑战成功"}:
                    return BattleScreenObservation("result_animation", None, point,
                                                   "same_frame_result_header_and_accelerate", raw_text, outcome)
            return BattleScreenObservation("result_animation", None, None,
                                           "same_frame_result_header", raw_text, outcome)
        except Exception as error:
            self._failure(error)
            attempts.append({"method": "same_frame_result", "reason": type(error).__name__})
            self.last_battle_attempts = attempts[:3]
            self.capture_sample("unknown_battle_screen", {"ocr_attempts": attempts})
            if authenticated_outcome != "unknown":
                return BattleScreenObservation("result_animation", None, None,
                                               "same_frame_result_header_action_unavailable",
                                               " | ".join(raw_parts)[:480], authenticated_outcome)
            return replace(unknown, raw_text=" | ".join(raw_parts)[:480])

    def read_squad_health(self, roi=None, *, page_validator=None) -> HealthObservation:
        """仅使用明确配置的标签 ROI，并要求两帧一致。
        不猜测默认准备页 ROI。
        RESULT_HEALTH_ROI 仅在调用方认证结果页后主动启用；它不是页面检测器。
        """
        self._check_stop()
        roi = self.health_roi if roi is None else roi
        self.last_health_attempts = []
        if roi is None:
            return HealthObservation(None, None, "health_roi_unconfigured", "health_roi_not_configured", "")
        if (not isinstance(roi, (list, tuple)) or len(roi) != 4
                or not all(_number(v) for v in roi)
                or not 0 <= roi[0] < roi[2] <= 1 or not 0 <= roi[1] < roi[3] <= 1):
            return HealthObservation(None, None, "health_roi_invalid", "invalid_health_roi", "")
        answers, attempts = [], []
        has_engine = callable(getattr(self.operator, "ocr_engine", None))
        for frame in range(2):
            self._check_stop()
            # 已审核的终局标签包含心形字形；放大会
            # 使其标签框覆盖数字，因此两张独立终局帧
            # 均保留原尺寸裁剪，而不是放宽框校验。
            upscale = has_engine and frame == 1 and tuple(roi) != FINAL_HEALTH_ROI
            method = "health_2x" if upscale else "health_color"
            try:
                size = None
                if has_engine:
                    from PIL import Image
                    if page_validator is None:
                        image = self.operator.screenshot(**self._roi_args(roi))
                    else:
                        full_frame = self.operator.screenshot()
                        self._check_stop()
                        if not page_validator(full_frame):
                            self.last_health_attempts = attempts + [{"method": method,
                                "reason": "page_departed_before_health", "current": None}]
                            return HealthObservation(None, None, "health_page_changed",
                                "page_departed_before_health", "")
                        width, height = full_frame.size
                        image = full_frame.crop(tuple(round(value * (width if i % 2 == 0 else height))
                            for i, value in enumerate(roi)))
                    self._check_stop()
                    image = image.convert("RGB")
                    if upscale:
                        image = image.resize((image.width * 2, image.height * 2), Image.Resampling.LANCZOS)
                    size = image.size
                    # 为纯解析器保留低置信度冲突。
                    rows = self._engine_ocr(image, minimum_confidence=0.0)
                else:
                    if page_validator is not None:
                        return HealthObservation(None, None, "health_page_unavailable",
                            "health_page_validation_unavailable", "")
                    rows = self.operator.ocr(**self._roi_args(roi), grayscale=False, confidence=0.0, trace=False)
                    context = getattr(self.operator, "window_context", None)
                    width, height = getattr(context, "width", None), getattr(context, "height", None)
                    if _number(width) and _number(height) and width > 0 and height > 0:
                        size = (round(roi[2] * width) - round(roi[0] * width),
                                round(roi[3] * height) - round(roi[1] * height))
                self._check_stop()
                answer = parse_squad_health(rows, image_size=size, evidence=method)
                if (has_engine and tuple(roi) == FINAL_HEALTH_ROI
                        and answer.reason in {"health_label_missing", "health_value_missing"}):
                    # 仅补同帧同ROI缺失的标签/数值；冲突、低置信度和越界RGB结果不能被覆盖。
                    gray_rows = self._engine_ocr(image.convert("L"), minimum_confidence=0.0)
                    self._check_stop()
                    gray_answer = parse_squad_health(gray_rows, image_size=size,
                                                     evidence="health_same_frame_gray")
                    if gray_answer.current is not None:
                        answer, method = gray_answer, "health_same_frame_gray"
            except Exception as error:
                self._failure(error)
                answer = HealthObservation(None, None, method, type(error).__name__, "")
            answers.append(answer)
            attempts.append({"method": method, "roi": list(roi), "current": answer.current,
                             "maximum": answer.maximum, "text": answer.raw_text, "reason": answer.reason})
            if frame == 0:
                self._check_stop()
                getattr(self.operator, "sleep", time.sleep)(0.15)
                self._check_stop()
        self.last_health_attempts = attempts
        raw_text = " | ".join(answer.raw_text for answer in answers if answer.raw_text)[:480]
        if (answers[0].current is not None and answers[1].current is not None
                and (answers[0].current, answers[0].maximum) == (answers[1].current, answers[1].maximum)):
            return replace(answers[0], evidence="two_health_frames", reason="consistent_health", raw_text=raw_text)
        reason = "conflicting_health_frames" if all(a.current is not None for a in answers) else "health_not_confirmed"
        self.capture_sample("unknown_squad_health", {"roi": list(roi), "ocr_attempts": attempts})
        return HealthObservation(None, None, "health_not_confirmed", reason, raw_text)

    def read_level(self, parse_shop_level):
        """同帧小区域优先；复用上次成功模式，失败时保留原有宽域恢复。"""
        attempts = []
        last = parse_shop_level(None)
        modes = [("focused_color", FOCUSED_LEVEL_ROI), ("original_gray", ORIGINAL_LEVEL_ROI),
                 ("expanded_color", EXPANDED_LEVEL_ROI), ("expanded_2x", EXPANDED_LEVEL_ROI)]
        preferred = getattr(self, "_preferred_level_mode", None)
        if preferred is not None:
            modes.sort(key=lambda item: item[0] != preferred)
        frame = None
        if callable(getattr(self.operator, "ocr_engine", None)):
            try:
                frame = self.operator.screenshot()
                self._check_stop()
            except Exception as error:
                self._failure(error)
                attempts.append({"method": "capture", "reason": type(error).__name__})
        for mode, roi in modes:
            self._check_stop()
            try:
                if frame is not None:
                    image = frame.crop(tuple(round(value * (frame.width if index % 2 == 0 else frame.height))
                                             for index, value in enumerate(roi)))
                    image = image.convert("L" if mode == "original_gray" else "RGB")
                    if mode == "expanded_2x":
                        from PIL import Image
                        image = image.resize((image.width * 2, image.height * 2), Image.Resampling.LANCZOS)
                    results = self._engine_ocr(image)
                elif mode == "expanded_2x":
                    if not callable(getattr(self.operator, "ocr_engine", None)):
                        attempts.append({"method": mode, "reason": "ocr_engine_unavailable"})
                        continue
                    from PIL import Image
                    image = self.operator.screenshot(**self._roi_args(roi))
                    self._check_stop()
                    image = image.convert("RGB")
                    image = image.resize((image.width * 2, image.height * 2), Image.Resampling.LANCZOS)
                    results = self._engine_ocr(image)
                else:
                    results = self.operator.ocr(**self._roi_args(roi),
                                                grayscale=mode == "original_gray", trace=False)
                self._check_stop()
                observation = parse_shop_level(results)
                attempts.append({"method": mode, "roi": list(roi), "level": observation.level,
                                 "text": observation.raw_text[:240], "reason": observation.reason})
                last = replace(observation, evidence=mode)
                if observation.level is not None:
                    self._preferred_level_mode = mode
                    self.last_level_attempts = attempts
                    return last
            except Exception as error:
                self._failure(error)
                attempts.append({"method": mode, "reason": type(error).__name__})
        self.last_level_attempts = attempts
        self._preferred_level_mode = None
        self.capture_sample("unknown_level", {"ocr_attempts": attempts, "roi": list(EXPANDED_LEVEL_ROI)},
                            frame=frame)
        return replace(last, level=None, evidence="bounded_level_fallback", reason="all_level_attempts_failed")

    def _load_profile(self):
        self._check_stop()
        try:
            stat = self.profile_path.stat()
            if stat.st_size > 256 * 1024:
                raise ValueError("profile is too large")
            stamp = stat.st_mtime_ns, stat.st_size
            if self._profile is None or stamp != self._profile_stamp:
                raw = json.loads(self.profile_path.read_text(encoding="utf-8"))
                self._profile = validate_profile(raw, self.profile_path.parent)
                self._profile_stamp = stamp
            self.profile_status = "validated_local_profile"
            return self._profile
        except Exception as error:
            self._failure(error)
            self._profile = None
            self._profile_stamp = None
            self.profile_status = "not_configured" if isinstance(error, FileNotFoundError) else "invalid_profile"
            return None

    def _load_field_profile(self):
        self._check_stop()
        path = self.profile_path.with_name("field_profile.json")
        try:
            stat = path.stat()
            if stat.st_size > 256 * 1024:
                raise ValueError("field profile is too large")
            stamp = stat.st_mtime_ns, stat.st_size
            if self._field_profile is None or stamp != self._field_profile_stamp:
                raw = json.loads(path.read_text(encoding="utf-8"))
                self._field_profile = validate_field_profile(raw, path.parent)
                self._field_profile_stamp = stamp
            return self._field_profile
        except Exception as error:
            self._failure(error)
            self._field_profile = None
            self._field_profile_stamp = None
            self.last_slot_reason = ("field_profile_missing" if isinstance(error, FileNotFoundError)
                                     else "field_profile_invalid")
            return None

    # ssyb：动态位置使用已认证布局，不凭单个空字形外推。
    def _matching_field_profile(self, area, index, position, selected, *, identity_review=False):
        """固定锚点优先；已通过双帧认证的普通后台槽可重定位已审核空标。"""
        confirmed = getattr(self, "_confirmed_backend_positions", ())
        if area == "off_field" and confirmed:
            protected = getattr(self, "_confirmed_backend_protected_slots", ())
            unknown = getattr(self, "_confirmed_backend_unknown_slots", ())
            ordinary = getattr(self, "_confirmed_backend_ordinary_slots", ())
            if (index not in range(len(confirmed)) or index in protected
                    or index in unknown and not identity_review
                    or index not in ordinary and not (identity_review and index in unknown)
                    or any(abs(a - b) > 0.002 for a, b in zip(position, confirmed[index]))):
                return replace(selected, slots={}) if selected is not None else None
        slot = selected.slots.get((area, index)) if selected is not None else None
        if (not confirmed and slot is not None
                and all(abs(a - b) <= 0.002 for a, b in zip(position, slot.position))):
            return selected
        if area != "off_field":
            return selected
        self._check_stop()
        path = self.profile_path.with_name("field_profile_locked_support.json")
        cached = None
        try:
            stat = path.stat()
            if stat.st_size > 256 * 1024:
                raise ValueError("support field profile too large")
            stamp = stat.st_mtime_ns, stat.st_size
            cached = getattr(self, "_support_field_profile", None)
            if cached is None or getattr(self, "_support_field_stamp", None) != stamp:
                cached = validate_field_profile(json.loads(path.read_text(encoding="utf-8")), path.parent)
                self._support_field_profile = cached
                self._support_field_stamp = stamp
            slot = cached.slots.get((area, index))
            if (not confirmed and slot is not None
                    and all(abs(a - b) <= 0.002 for a, b in zip(position, slot.position))):
                return cached
        except Exception as error:
            self._failure(error)
            cached = None
        dynamic = None
        if confirmed:
            try:
                path = self.profile_path.with_name("field_profile_backend_dynamic.json")
                stat = path.stat()
                if stat.st_size > 256 * 1024:
                    raise ValueError("dynamic backend profile too large")
                stamp = stat.st_mtime_ns, stat.st_size
                dynamic = getattr(self, "_dynamic_backend_profile", None)
                if dynamic is None or getattr(self, "_dynamic_backend_profile_stamp", None) != stamp:
                    dynamic = validate_dynamic_backend_profile(json.loads(path.read_text(encoding="utf8")), path.parent)
                    self._dynamic_backend_profile = dynamic
                    self._dynamic_backend_profile_stamp = stamp
            except Exception as error:
                self._failure(error)
                dynamic = None
        if confirmed and selected is not None:
            # 只从已审核的普通槽选取最接近的横向视角；索引不是模板身份。
            # 支援槽和没有完整新鲜布局的调用永远不能进入此分支。
            sources = [slot for profile in (selected, cached, dynamic) if profile is not None
                       for (source_area, _), slot in profile.slots.items()
                       if source_area == "off_field" and slot.field_structures]
            if sources:
                ordered = sorted(sources, key=lambda item: abs(item.position[0] - position[0]))
                source = ordered[0]
                alternatives = []
                for candidate in ordered[1:]:
                    if (abs(candidate.position[0] - position[0]) <= 0.2
                            and all(abs(candidate.position[0] - old.position[0]) > 0.02
                                    for old in (source, *alternatives))):
                        alternatives.append(candidate)
                        if len(alternatives) == 2:
                            break
                moved = replace(source, index=index, position=position,
                    reference_position=source.position, alternative_field_slots=tuple(
                        replace(candidate, index=index, position=position,
                                reference_position=candidate.position, alternative_field_slots=())
                        for candidate in alternatives))
                return replace(selected, slots={(area, index): moved})
        return selected

    def _dynamic_backend_frame_matches(self, image):
        """相对裁剪只能使用当前帧仍然完整、且未移位的已认证行。"""
        from .layout import backend_rectangle_candidates, validate_backend_layout, revalidate_backend_layout
        positions = getattr(self, "_confirmed_backend_positions", ())
        if not positions:
            return False
        boxes = backend_rectangle_candidates(image, previous_positions=positions)
        current = validate_backend_layout(boxes, image.size, previous_positions=positions)
        if not current.valid and getattr(self, "_backend_deep_confirmed", False):
            from .layout import supplement_backend_dark_borders
            boxes = supplement_backend_dark_borders(image, boxes)
            current = validate_backend_layout(boxes, image.size, previous_positions=positions)
        if not current.valid and getattr(self, "_backend_deep_confirmed", False):
            current = revalidate_backend_layout(boxes, image.size, previous_positions=positions)
        return current.valid and not current.changed

    def _classify_slot_image(self, image, slot, position):
        if slot.alternative_field_slots:
            primary = replace(slot, alternative_field_slots=())
            answers = {self._classify_slot_image(image, candidate, position)
                       for candidate in (primary, *slot.alternative_field_slots)} - {None}
            return next(iter(answers)) if len(answers) == 1 else None
        reference = slot.reference_position
        if reference is None:
            anchor = slot.position if slot.field_structures else position
            return self._classify(crop_slot_template(image, anchor, slot.relative_box), slot)
        bounds = _box(reference, slot.relative_box)
        pixels = tuple(round(value * (image.width if i % 2 == 0 else image.height))
                       for i, value in enumerate(bounds))
        answers = set()
        for shear in self._backend_projection_shears(reference, position):
            # 半像素边框中心取整可能产生一像素裁剪偏差；
            # 保持原有两像素搜索界限及完整空标、正负模板阈值。
            for offset in ((0, 0), (0, -1), (0, 1), (-1, 0), (1, 0),
                           (0, -2), (0, 2), (-2, 0), (2, 0)):
                self._check_stop()
                crop = self._projected_field_crop(image, pixels, reference, position, shear, offset=offset)
                if crop is not None:
                    answer = self._classify(crop, slot)
                    if answer is not None:
                        answers.add(answer)
        return next(iter(answers)) if len(answers) == 1 else None

    @staticmethod
    def _window_matches(image, profile):
        width, height = image.size
        ref_w, ref_h = profile.window_size
        return (width > 0 and height > 0
                and abs((width / height) / (ref_w / ref_h) - 1) <= profile.aspect_tolerance
                and abs(width / ref_w - 1) <= profile.scale_tolerance
                and abs(height / ref_h - 1) <= profile.scale_tolerance)

    @staticmethod
    def _classify(crop, slot):
        positive_distances = tuple(image_distance(crop, image) for image in slot.empty_images)
        positive = min(positive_distances)
        negative = min(image_distance(crop, image) for image in slot.occupied_images)
        if positive <= slot.max_mae and negative - positive >= slot.min_margin:
            if slot.field_structures:
                return True if any(distance <= slot.max_mae and negative - distance >= slot.min_margin
                    and _matches_field_structure(crop, structure, allow_antialiasing=slot.area == "on_field")
                    for distance, structure in zip(positive_distances, slot.field_structures)) else None
            if not slot.require_empty_structure or any(
                    distance <= slot.max_mae and negative - distance >= slot.min_margin
                    and _matches_empty_structure(crop, structure)
                    for distance, structure in zip(positive_distances, slot.empty_structures)):
                return True
            return None
        if negative <= slot.max_mae and positive - negative >= slot.min_margin:
            return False
        return None

    @staticmethod
    def _matches_bench_lock(crop, template, max_mae):
        """要求已审核的锁形轮廓，不能仅是深色矩形。"""
        if crop.size != template.size or image_distance(crop, template) > max_mae:
            return False
        expected = tuple(template.convert("L").tobytes())
        actual = tuple(crop.convert("L").tobytes())
        ordered = sorted(expected)
        low, high = ordered[len(ordered) // 5], ordered[len(ordered) * 4 // 5]
        if high - low < 12:
            return False
        bright = [i for i, value in enumerate(expected) if value >= high]
        dark = [i for i, value in enumerate(expected) if value <= low]
        middle = (low + high) / 2
        margin = (high - low) * 0.15
        return (sum(actual[i] >= middle + margin for i in bright) >= len(bright) * 0.8
                and sum(actual[i] <= middle - margin for i in dark) >= len(dark) * 0.8)

    def read_locked_bench_slots(self, positions) -> set[int]:
        """在两张新鲜且匹配的帧上认证不可用的备战区槽位。
        未匹配到意味着 UNKNOWN，绝不意味着槽位可用。
        后续解锁的槽位必须重新由普通空位读取器分类。
        """
        self._check_stop()
        requested = dict(positions) if isinstance(positions, Mapping) else dict(enumerate(positions))
        if not requested:
            return set()
        path = self.profile_path.with_name("locked_bench.json")
        try:
            stat = path.stat()
            if stat.st_size > 64 * 1024:
                raise ValueError("locked bench profile too large")
            stamp = stat.st_mtime_ns, stat.st_size
            if getattr(self, "_locked_bench_stamp", None) != stamp:
                from PIL import Image
                raw = json.loads(path.read_text(encoding="utf-8"))
                if (type(raw.get("version")) is not int or raw["version"] != 1
                        or raw.get("kind") != "reviewed_locked_bench_slots"
                        or raw.get("window_size") != [1920, 1080]
                        or not isinstance(raw.get("slots"), list) or not 1 <= len(raw["slots"]) <= 9):
                    raise ValueError("invalid locked bench profile")
                calibrated = {}
                for entry in raw["slots"]:
                    self._check_stop()
                    index = entry.get("index")
                    if type(index) is not int or not 0 <= index < 9 or index in calibrated:
                        raise ValueError("invalid locked bench slot index")
                    anchor = _point(entry.get("position"))
                    offsets = entry.get("relative_box")
                    bounds = _box(anchor, offsets)
                    threshold = entry.get("max_mae")
                    if not _number(threshold) or not 0 < threshold <= 0.025:
                        raise ValueError("unsafe locked bench threshold")
                    example = entry.get("template", {})
                    template_path = _safe_template_path(path.parent, example.get("path"))
                    if (example.get("label") != "locked" or template_path.stat().st_size > 1024 * 1024
                            or hashlib.sha256(template_path.read_bytes()).hexdigest() != example.get("sha256")):
                        raise ValueError("invalid locked bench template")
                    with Image.open(template_path) as template:
                        pixels = tuple(round(value * raw["window_size"][i % 2]) for i, value in enumerate(bounds))
                        if (template.size != (pixels[2] - pixels[0], pixels[3] - pixels[1])
                                or not 8 <= template.width <= 256 or not 8 <= template.height <= 256):
                            raise ValueError("invalid locked bench crop size")
                        calibrated[index] = (anchor, tuple(offsets), template.convert("RGB").copy(), threshold)
                self._locked_bench_calibration = calibrated
                self._locked_bench_stamp = stamp
            candidates = {index: entry for index, entry in self._locked_bench_calibration.items()
                          if index in requested and all(abs(a - b) <= 0.002
                              for a, b in zip(_point(requested[index]), entry[0]))}
            if not candidates:
                return set()
            matched = set(candidates)
            for frame_number in range(2):
                self._check_stop()
                frame = self.operator.screenshot()
                self._check_stop()
                if frame.size != (1920, 1080):
                    return set()
                for index, (anchor, offsets, template, threshold) in candidates.items():
                    self._check_stop()
                    crop = crop_slot_template(frame, anchor, offsets)
                    if not self._matches_bench_lock(crop, template, threshold):
                        matched.discard(index)
                if not matched:
                    return set()
                if frame_number == 0:
                    getattr(self.operator, "sleep", time.sleep)(0.15)
            self._check_stop()
            return matched
        except Exception as error:
            self._failure(error)
            return set()

    def read_empty_slots(self, area: str, positions) -> dict[int, bool | None]:
        """使用相同两张已校准窗口帧对多个槽位分类。
        positions 可为带索引的序列，或索引到位置的映射。
        每槽保留自己的未知结果；占用状态不能确定角色身份。
        调用方必须认证可见页面。
        """
        self._check_stop()
        requested = dict(positions) if isinstance(positions, Mapping) else dict(enumerate(positions))
        answers = dict.fromkeys(requested)
        reasons = self.last_empty_slot_reasons = dict.fromkeys(requested, "not_attempted")
        if not requested:
            return answers
        profile = self._load_profile()
        field_profile = None
        field_loaded = False
        candidates = {}
        for index, position in requested.items():
            self._check_stop()
            selected = profile
            if area in ("on_field", "off_field") and (selected is None or (area, index) not in selected.slots):
                if not field_loaded:
                    field_profile = self._load_field_profile()
                    field_loaded = True
                selected = field_profile
            if selected is None:
                reasons[index] = "empty_profile_missing"
                continue
            try:
                position = _point(position)
                selected = self._matching_field_profile(area, index, position, selected)
                slot = selected.slots.get((area, index))
                if slot is None or any(abs(a - b) > 0.002 for a, b in zip(position, slot.position)):
                    reasons[index] = "uncalibrated_slot"
                    continue
                candidates[index] = selected, slot, position
            except Exception as error:
                self._failure(error)
                reasons[index] = "uncalibrated_slot"
        screenshot = getattr(self.operator, "screenshot", None)
        if not callable(screenshot):
            for index in candidates:
                reasons[index] = "screenshot_unavailable"
            return answers
        if not candidates:
            return answers
        observed = {index: [] for index in candidates}
        for frame in range(2):
            self._check_stop()
            try:
                image = screenshot()
                self._check_stop()
                dynamic_frame_valid = (not any(slot.reference_position is not None
                    for _, slot, _ in candidates.values()) or self._dynamic_backend_frame_matches(image))
                for index, (selected, slot, position) in candidates.items():
                    self._check_stop()
                    try:
                        if not self._window_matches(image, selected):
                            observed[index].append(None)
                            reasons[index] = "window_profile_mismatch"
                            continue
                        if slot.reference_position is not None and not dynamic_frame_valid:
                            observed[index].append(None)
                            reasons[index] = "dynamic_layout_changed"
                            continue
                        observed[index].append(self._classify_slot_image(image, slot, position))
                    except Exception as error:
                        self._failure(error)
                        observed[index].append(None)
                        reasons[index] = "slot_evidence_failed"
                if frame == 0:
                    sleeper = getattr(self.operator, "sleep", time.sleep)
                    sleeper(0.15)
                    self._check_stop()
            except Exception as error:
                self._failure(error)
                for index in candidates:
                    reasons[index] = "slot_evidence_failed"
                return answers
        for index, values in observed.items():
            first, second = values
            if first is not None and first is second:
                answers[index] = first
                reasons[index] = "two_empty_frames" if first else "two_occupied_frames"
            elif reasons[index] == "not_attempted":
                reasons[index] = "ambiguous_slot" if None in values else "conflicting_slot_frames"
        return answers

    def slot_is_empty(self, area: str, index: int, position) -> bool | None:
        return self._slot_is_empty(area, index, position)

    def slot_is_empty_batch(self, area: str, positions) -> dict[int, bool | None]:
        """按原单格分支依次确认全部为空，首个非 True 结果立即结束。

        所有实际处理的槽位共享同一对新截图；第二帧按需截取，第一格
        已经未知时不额外截图。保留单格分类、阈值、原因及采样分支。
        返回字典只包含已处理的格，调用方须同时核对数量与全部 True。
        """
        self._check_stop()
        requested = dict(positions) if isinstance(positions, Mapping) else dict(enumerate(positions))
        frames, answers = [], {}
        reasons = self.last_empty_slot_reasons = {}

        def frame_source(number):
            if len(frames) <= number:
                if number == 1:
                    getattr(self.operator, "sleep", time.sleep)(0.15)
                    self._check_stop()
                frames.append(self.operator.screenshot())
            return frames[number]

        for index, position in requested.items():
            self._check_stop()
            answer = self._slot_is_empty(area, index, position, frame_source=frame_source)
            answers[index] = answer
            reasons[index] = self.last_slot_reason
            if answer is not True:
                break
        return answers

    # Yukki：槽位未知时保留未知，不能由采购需求推断为空。
    def _slot_is_empty(self, area: str, index: int, position, *, frame_source=None,
                       identity_review=False) -> bool | None:
        self.last_slot_reason = "not_attempted"
        self._check_stop()
        profile = self._load_profile()
        if area in ("on_field", "off_field") and (profile is None or (area, index) not in profile.slots):
            profile = self._load_field_profile()
        if profile is None:
            if self.last_slot_reason == "not_attempted":
                self.last_slot_reason = "empty_profile_missing"
            self.capture_sample("empty_profile_missing", {"area": area, "index": index,
                                                          "position": position, "profile_status": self.profile_status})
            return None
        try:
            position = _point(position)
            profile = self._matching_field_profile(area, index, position, profile,
                                                   identity_review=identity_review)
            slot = profile.slots.get((area, index))
            if slot is None or any(abs(a - b) > 0.002 for a, b in zip(position, slot.position)):
                self.last_slot_reason = "uncalibrated_slot"
                self.capture_sample("uncalibrated_slot", {"area": area, "index": index, "position": position})
                return None
            answers = []
            for frame in range(2):
                self._check_stop()
                image = self.operator.screenshot() if frame_source is None else frame_source(frame)
                self._check_stop()
                if not self._window_matches(image, profile):
                    self.last_slot_reason = "window_profile_mismatch"
                    self.capture_sample("window_profile_mismatch", {"area": area, "index": index})
                    return None
                if slot.reference_position is not None and not self._dynamic_backend_frame_matches(image):
                    self.last_slot_reason = "dynamic_layout_changed"
                    return None
                answer = self._classify_slot_image(image, slot, position)
                if answer is None:
                    self.last_slot_reason = "ambiguous_slot"
                    self.capture_sample("ambiguous_slot", {"area": area, "index": index, "position": position})
                    return None
                answers.append(answer)
                if frame == 0 and frame_source is None:
                    sleeper = getattr(self.operator, "sleep", time.sleep)
                    sleeper(0.15)
            if answers[0] != answers[1]:
                self.last_slot_reason = "conflicting_slot_frames"
                self.capture_sample("conflicting_slot_frames", {"area": area, "index": index, "position": position})
                return None
            self.last_slot_reason = "two_empty_frames" if answers[0] else "two_occupied_frames"
            return answers[0]
        except Exception as error:
            self._failure(error)
            self.last_slot_reason = "slot_evidence_failed"
            self.capture_sample("slot_evidence_failed", {"area": area, "index": index,
                                                         "error_type": type(error).__name__})
            return None

    @staticmethod
    def _sample_component(value):
        if not isinstance(value, str) or not value.strip() or len(value) > 160:
            raise ValueError("diagnostic identifiers must be nonempty strings of at most 160 characters")
        safe = re.sub(r"[^a-zA-Z0-9_-]", "_", value)[:64].strip("_-") or "sample"
        if safe != value:
            safe += "_" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]
        return safe

    def begin_sample_scope(self, session_id: str, run_id: str | None = None, *,
                           critical_reserve: int = 3, reason_quota: int = 1,
                           reason_quotas: Mapping[str, int] | None = None) -> Path:
        """选择有界的会话或局次目录，不删除此前样本。
        重新打开同一范围会保留内存及磁盘配额。
        省略此 API 时沿用旧版平面目录与 max_samples 行为。
        根任务负责真实会话和局次标识；本读取器不推断开局。
        """
        self._check_stop()
        if (type(critical_reserve) is not int or not 0 <= critical_reserve <= 32
                or type(reason_quota) is not int or not 0 <= reason_quota <= 32):
            raise ValueError("diagnostic quotas must be integers from 0 to 32")
        quotas = {} if reason_quotas is None else reason_quotas
        if not isinstance(quotas, Mapping) or len(quotas) > 64 or any(
                not isinstance(key, str) or not key or len(key) > 160
                or type(value) is not int or not 0 <= value <= 32 for key, value in quotas.items()):
            raise ValueError("invalid reason quotas")
        session = self._sample_component(session_id)
        run = self._sample_component(str(time.time_ns()) if run_id is None else run_id)
        path = self._sample_base_dir / ("session-" + session) / ("run-" + run)
        try:
            path.resolve().relative_to(self._sample_base_dir.resolve())
        except ValueError:
            raise ValueError("diagnostic scope must remain inside the sample directory") from None
        if path == self.sample_dir and self._sample_scope is not None:
            return path
        self.sample_dir = path
        self._sample_scope = (session_id, run_id if run_id is not None else run)
        self._sampled.clear()
        self._sample_counts.clear()
        self._sample_attempts = self._normal_sample_attempts = 0
        self._critical_reserve = min(critical_reserve, self.max_samples)
        self._reason_quota, self._reason_quotas = reason_quota, dict(quotas)
        self.last_sample_reason = "scope_ready"
        return path

    def capture_sample(self, reason: str, metadata: Mapping[str, Any] | None = None, *,
                       critical: bool = False, frame=None, related_images=()) -> Path | None:
        """在局次、原因配额及关键预留范围内截取游戏窗口。
        截图尝试失败也消耗配额。
        可传入产生判定的原始帧，避免采样时页面变化造成证据错配。
        每个样本组可在独立子目录保存最多八张实际参与判断的帧和处理图。
        last_sample_reason 解释每次返回 None 的原因，避免旧目录上限导致无提示失败。
        """
        self._check_stop()
        self.last_sample_reason = "checking_quota"
        if not self.max_samples:
            self.last_sample_reason = "sampling_disabled"
            return None
        if not isinstance(reason, str) or not reason or len(reason) > 160 or type(critical) is not bool:
            self.last_sample_reason = "invalid_sample_request"
            return None
        quota = self._reason_quotas.get(reason, self._reason_quota)
        if self._sample_counts.get(reason, 0) >= quota:
            self.last_sample_reason = "reason_quota_exhausted"
            return None
        if self._sample_attempts >= self.max_samples:
            self.last_sample_reason = "run_quota_exhausted"
            return None
        critical = critical or self._sample_scope is not None and reason in CRITICAL_SAMPLE_REASONS
        if not critical and self._normal_sample_attempts >= self.max_samples - self._critical_reserve:
            self.last_sample_reason = "critical_reserve_protected"
            return None
        self._sampled.add(reason)
        self._sample_counts[reason] = self._sample_counts.get(reason, 0) + 1
        self._sample_attempts += 1
        self._normal_sample_attempts += not critical
        try:
            safe_reason = self._sample_component(reason)
            if self.sample_dir.exists():
                from itertools import islice
                existing = list(islice((path for path in self.sample_dir.glob("*.png")
                    if path.name not in {"last_backend_layout.png", "last_backend_layout_stop.png"}), self.max_samples))
                if len(existing) >= self.max_samples:
                    self.last_sample_reason = "directory_quota_exhausted"
                    return None
                if self._sample_scope is not None:
                    if sum(path.name.endswith("_" + safe_reason + ".png") for path in existing) >= quota:
                        self.last_sample_reason = "saved_reason_quota_exhausted"
                        return None
                    if not critical:
                        normal_count = 0
                        for old_path in existing:
                            try:
                                sidecar = old_path.with_suffix(".json")
                                if sidecar.stat().st_size > 8192:
                                    raise ValueError("oversize diagnostic sidecar")
                                old = json.loads(sidecar.read_text(encoding="utf-8"))
                                is_critical = isinstance(old, dict) and old.get("critical") is True
                            except (OSError, ValueError, TypeError):
                                is_critical = False
                            normal_count += not is_critical
                        if normal_count >= self.max_samples - self._critical_reserve:
                            self.last_sample_reason = "saved_critical_reserve_protected"
                            return None
            payload = self._sample_metadata(metadata)
            image = frame if frame is not None else self.operator.screenshot()
            self._check_stop()
            if image is None:
                self.last_sample_reason = "screenshot_unavailable"
                return None
            self.sample_dir.mkdir(parents=True, exist_ok=True)
            path = self.sample_dir / f"{time.time_ns()}_{safe_reason}.png"
            attachments = []
            evidence_dir = path.with_name(path.stem + "_evidence")
            for index, (label, attached) in enumerate(related_images[:8] if isinstance(related_images, (list, tuple)) else ()):
                self._check_stop()
                size = getattr(attached, "size", ())
                if (not isinstance(size, (tuple, list)) or len(size) != 2
                        or any(type(value) is not int or value <= 0 for value in size)
                        or size[0] * size[1] > 1920 * 1080):
                    continue
                name = f"{index + 1}_{self._sample_component(str(label)[:60])}.png"
                attachments.append((evidence_dir / name, attached, str(label)[:60]))
            if attachments:
                payload["evidence_images"] = [{"role": label, "file": str(saved.relative_to(self.sample_dir)),
                                               "size": list(attached.size)}
                                              for saved, attached, label in attachments]
            payload.update(reason=str(reason)[:80], window_size=list(image.size),
                           profile_status=self.profile_status, image_file=path.name,
                            calibration_status="unlabelled_requires_review")
            if self._sample_scope is not None:
                payload.update(session_id=self._sample_scope[0], run_id=self._sample_scope[1], critical=critical)
            encoded = json.dumps(payload, ensure_ascii=False, indent=2)
            if len(encoded.encode("utf-8")) > 8192:
                encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            if len(encoded.encode("utf-8")) > 8192:
                raise ValueError("sample metadata is too large")
            image.save(path, format="PNG")
            self._check_stop()
            if attachments:
                evidence_dir.mkdir(exist_ok=False)
                for saved, attached, label in attachments:
                    self._check_stop()
                    attached.save(saved, format="PNG")
            path.with_suffix(".json").write_bytes(encoded.encode("utf-8"))
            self.last_sample_reason = "captured"
            return path
        except Exception as error:
            self.last_sample_reason = "capture_error:" + type(error).__name__
            self._failure(error)
            return None
