"""1920×1080 准备页人口计数的单帧证据恢复。

本模块不截图、不等待，也不确认页面身份。调用方必须取得两张新鲜帧并
分别确认；同帧的裁剪、放大和对比度变体只能贡献一次观测。只有 OCR
实际读到的斜线才能分隔人数，绝不将 919 或字母 O 猜成人口计数。
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from .ocr_geometry import foreground_pixels, ground_crop_rows


POPULATION_ROI = (0.46, 0.185, 0.54, 0.26)
# 最后的恢复才补取外围原始像素；正常字形增强仍使用计数区，避免并入图标。
POPULATION_RECOVERY_ROI = (0.425, 0.16, 0.575, 0.28)
MIN_CONFIDENCE = 0.9
_TRANSLATION = str.maketrans("０１２３４５６７８９／", "0123456789/")
_LABELS = frozenset({"人口", "上阵人数", "出战人数", "已上阵"})
_COUNT = re.compile(r"([0-9]{1,2})/([0-9]{1,2})")
_PARTIAL = re.compile(r"/([0-9]{1,2})")
# 连通分析保留过长数字作为边界；最终仍只能接受严格的 1~2 位 n/m。
_FRAGMENT = re.compile(r"(?:[0-9]+(?:/[0-9]*)?|/[0-9]*)")


@dataclass(frozen=True)
class PopulationFrameEvidence:
    current: int | None
    capacity: int | None
    reason: str
    raw_text: str
    attempts: tuple[dict, ...]


@dataclass(frozen=True)
class _Token:
    text: str
    box: tuple[float, float, float, float]
    score: float
    touches_crop_boundary: bool = False
    labelled: bool = False


def _union(tokens):
    return (min(row.box[0] for row in tokens), min(row.box[1] for row in tokens),
            max(row.box[2] for row in tokens), max(row.box[3] for row in tokens))


def _same_row(left, right):
    lh, rh = left.box[3] - left.box[1], right.box[3] - right.box[1]
    overlap = min(left.box[3], right.box[3]) - max(left.box[1], right.box[1])
    return max(lh, rh) <= 2.5 * min(lh, rh) and overlap >= 0.55 * min(lh, rh)


def _adjacent(left, right):
    height = min(left.box[3] - left.box[1], right.box[3] - right.box[1])
    gap = right.box[0] - left.box[2]
    return _same_row(left, right) and -0.15 * height <= gap <= 0.8 * height


def _tokens(results, image_size, crop_box, scale):
    tokens, raw_text = [], []
    for entry in results[:64] if isinstance(results, (list, tuple)) else ():
        if not isinstance(entry, (list, tuple)) or len(entry) != 3 or not isinstance(entry[1], str):
            continue
        raw_text.append(entry[1])
        try:
            if isinstance(entry[2], bool):
                continue
            score = float(entry[2])
            if not math.isfinite(score) or not 0 <= score <= 1:
                continue
            box = entry[0].tolist() if hasattr(entry[0], "tolist") else entry[0]
            if not isinstance(box, (list, tuple)) or len(box) != 4:
                continue
            if any(not isinstance(point, (list, tuple)) or len(point) != 2
                   or any(isinstance(value, bool) for value in point) for point in box):
                continue
            points = tuple(tuple(float(value) for value in point) for point in box)
            if any(not math.isfinite(x) or not math.isfinite(y)
                   or not 0 <= x <= image_size[0] or not 0 <= y <= image_size[1] for x, y in points):
                continue
            local = (min(x for x, _ in points), min(y for _, y in points),
                     max(x for x, _ in points), max(y for _, y in points))
            if local[0] >= local[2] or local[1] >= local[3]:
                continue
            bounds = (crop_box[0] + local[0] / scale, crop_box[1] + local[1] / scale,
                      crop_box[0] + local[2] / scale, crop_box[1] + local[3] / scale)
            normalized = re.sub(r"\s+", "", entry[1]).translate(_TRANSLATION)
            boundary = (local[0] <= 1 or local[1] <= 1
                        or local[2] >= image_size[0] - 1 or local[3] >= image_size[1] - 1)
            tokens.append(_Token(normalized, bounds, score, boundary))
        except (TypeError, ValueError, OverflowError):
            continue
    return tokens, " | ".join(raw_text)[:240]


def _in_population_position(box, labels, *, labelled=False):
    """裸计数须在原计数区；向外恢复还需要附近的明确人口标签。"""
    left, top, right, bottom = box
    width, height = right - left, bottom - top
    x, y = (left + right) / 2, (top + bottom) / 2
    if not (3 <= height <= 72 and width <= (230 if labelled else 210)):
        return False
    core = tuple(value * size for value, size in zip(POPULATION_ROI, (1920, 1080, 1920, 1080)))
    if core[0] <= x <= core[2] and core[1] <= y <= core[3]:
        return True
    # 加宽 ROI 只是取证窗口，不能把窗口中任意 n/m 都认成人口。
    if not (0.445 * 1920 <= x <= 0.555 * 1920 and 0.17 * 1080 <= y <= 0.275 * 1080):
        return False
    if labelled:
        return True
    candidate = _Token("", box, 1.0)
    for label in labels:
        label_height = label.box[3] - label.box[1]
        horizontal_gap = left - label.box[2]
        if (_same_row(label, candidate)
                and -0.2 * min(height, label_height) <= horizontal_gap <= 1.5 * max(height, label_height)):
            return True
        # 标签在计数正上方时，要求明显的横向重叠和相邻行距。
        overlap = min(right, label.box[2]) - max(left, label.box[0])
        vertical_gap = top - label.box[3]
        if overlap >= 0.5 * min(width, label.box[2] - label.box[0]) and 0 <= vertical_gap <= label_height:
            return True
    return False


# ssyb：斜线与相邻数字必须来自同一计数区域。
def _readings(tokens, *, minimum_confidence=MIN_CONFIDENCE):
    """返回同一 OCR 处理内的完整计数与独立上限，不混合处理间的字形。"""
    confident = [token for token in tokens if token.score >= minimum_confidence]
    labels = [token for token in confident
              if not token.touches_crop_boundary and token.text.rstrip(":：") in _LABELS]
    full, capacities, candidates = set(), set(), []
    invalid = False

    def add(text, group, *, labelled=False):
        nonlocal invalid
        if any(token.score < minimum_confidence or token.touches_crop_boundary for token in group):
            return
        match = _COUNT.fullmatch(text)
        partial = _PARTIAL.fullmatch(text)
        if not (match or partial) or not _in_population_position(_union(group), labels, labelled=labelled):
            return
        current = int(match[1]) if match else None
        capacity = int(match[2]) if match else int(partial[1])
        if not 1 <= capacity <= 10 or current is not None and not 0 <= current <= capacity:
            invalid = True
            return
        capacities.add(capacity)
        if current is not None:
            full.add((current, capacity))
        candidates.append({"current": current, "capacity": capacity,
                           "score": min(token.score for token in group),
                           "box": list(_union(group)), "parts": [token.text for token in group]})

    fragments = []
    # 低置信度数字也保留为边界：不能丢掉低置信度首位 1，再把 10/10
    # 的剩余片段认证成 0/10。置信度仅在完整组装后的 add 中决定。
    for token in tokens:
        text = token.text
        labelled = False
        for label in _LABELS:
            if text.startswith(label):
                text = text[len(label):].lstrip(":：")
                labelled = True
                break
        if _FRAGMENT.fullmatch(text):
            fragments.append(_Token(text, token.box, token.score, token.touches_crop_boundary, labelled))

    # 连通片段必须整体解析，不能从 "1 0 / 1 0" 中截取 "0/1"。
    # 每个片段包含真实 OCR 字符，最多五片（10 / 10）。重复/重叠框保持未知。
    fragments.sort(key=lambda token: (token.box[0], token.box[1]))
    components = []
    for token in fragments:
        connected = [index for index, group in enumerate(components)
                     if any(_adjacent(other, token) or _adjacent(token, other) for other in group)]
        if not connected:
            components.append([token])
            continue
        merged = [token]
        for index in reversed(connected):
            merged.extend(components.pop(index))
        components.append(merged)
    for group in components:
        group.sort(key=lambda token: token.box[0])
        if len(group) > 5 or any(not _adjacent(left, right) for left, right in zip(group, group[1:])):
            continue
        text = "".join(token.text for token in group)
        if text.count("/") == 1:
            add(text, group, labelled=any(token.labelled for token in group))
    return full, capacities, invalid, candidates


def _duplicate_counter_boxes(tokens):
    for index, left in enumerate(tokens):
        if left.score < MIN_CONFIDENCE or not _FRAGMENT.fullmatch(left.text):
            continue
        for right in tokens[index + 1:]:
            if right.score < MIN_CONFIDENCE or right.text != left.text:
                continue
            overlap = max(0, min(left.box[2], right.box[2]) - max(left.box[0], right.box[0])) * max(
                0, min(left.box[3], right.box[3]) - max(left.box[1], right.box[1]))
            area = min((left.box[2] - left.box[0]) * (left.box[3] - left.box[1]),
                       (right.box[2] - right.box[0]) * (right.box[3] - right.box[1]))
            if area > 0 and overlap >= .8 * area:
                return True
    return False


# Yukki：同帧变体仅用于恢复文字，不能累计为多帧证据。
def read_population_frame(frame, ocr, check_stop, *, enhance=False, on_attempt=None) -> PopulationFrameEvidence:
    """处理一张完整帧，正常一次 OCR，失败时总计最多三次。

    ``ocr(image)`` 须返回未经置信度过滤的 (box, text, score) 行；本函数
    始终保持 0.9 阈值。``check_stop()`` 在裁剪和 OCR 两侧检查取消。
    current=None、capacity=N 只表示读到了 /N，不是零人口或空槽证据。
    """
    check_stop()
    if getattr(frame, "size", None) != (1920, 1080):
        return PopulationFrameEvidence(None, None, "population_window_profile_mismatch", "", ())
    from PIL import Image, ImageOps

    original = frame.convert("RGB")
    modes = (("population_2x_contrast" if enhance else "population_2x", POPULATION_ROI, 2, "contrast" if enhance else "color"),
             ("population_foreground_3x", POPULATION_ROI, 3, "foreground"),
             ("population_expanded_2x", POPULATION_RECOVERY_ROI, 2, "color"))
    readings, capacities, attempts, raw_parts = set(), set(), [], []
    invalid = False
    duplicate = False
    crop_recovery_needed = False
    low_confidence_seen = False
    for index, (name, roi, scale, processing) in enumerate(modes):
        if crop_recovery_needed and index == 1:
            # 四/五字计数会从中心向两侧增长。补取原图字形，同时避开
            # 左侧随计数一起移动的人口图标，不能把图标的 i 并入 n/m。
            lengths = [len(token.text) for token in tokens if _COUNT.fullmatch(token.text)]
            left = .44 if lengths and max(lengths) == 5 else .45
            name, roi, scale, processing = ("population_counter_expanded_2x",
                (left, .185, .57, .26), 2, "color")
        elif crop_recovery_needed and index == 2:
            name, roi, scale, processing = modes[1]
        elif (low_confidence_seen and index == 2
              and attempts[-1]['geometry'].get('bounds_source') == 'source_pixels'):
            # 原像素已确认完整字形，分数不足时裁去多余背景后重读。
            # 只使用本帧已认证的几何位置，保持分数和双帧门槛。
            parts = attempts[-1]['geometry']['glyph_boxes']
            source_box = attempts[-1]['crop_box']
            bounds = (source_box[0] + max(0, min(part[0] for part in parts) - 2),
                      source_box[1] + max(0, min(part[1] for part in parts) - 2),
                      source_box[0] + min(source_box[2] - source_box[0], max(part[2] for part in parts) + 2),
                      source_box[1] + min(source_box[3] - source_box[1], max(part[3] for part in parts) + 2))
            roi = tuple(value / size for value, size in zip(bounds, (1920, 1080, 1920, 1080)))
            name, scale, processing = "population_grounded_2x", 2, "foreground"
        check_stop()
        crop_box = tuple(round(value * size) for value, size in zip(roi, (1920, 1080, 1920, 1080)))
        source_crop = original.crop(crop_box)
        crop = source_crop
        if processing == "contrast":
            crop = ImageOps.autocontrast(crop.convert("L")).convert("RGB")
        elif processing == "foreground":
            # 只分离原图中的亮色字形；斜线必须由 OCR 实际读出。
            crop = Image.new("L", source_crop.size, 255)
            for point in foreground_pixels(source_crop, kind="population"):
                crop.putpixel(point, 0)
            crop = crop.convert("RGB")
        image = crop.resize((crop.width * scale, crop.height * scale), Image.Resampling.LANCZOS)
        check_stop()
        results = ocr(image)
        check_stop()
        grounded, geometry = ground_crop_rows(results, source_crop, kind="population", scale=scale)
        tokens, raw_text = _tokens(grounded, image.size, crop_box, scale)
        if index == 0:
            # 只有真实字形贴边或局部检测框贴边，才优先补取外围像素。
            # 覆盖整张裁剪的宽泛框先做原计数区增强，不把图标并入恢复。
            crop_recovery_needed = geometry.get("reason") == "actual_ink_at_crop_boundary" or any(
                token.touches_crop_boundary
                and not ((token.box[2] - token.box[0]) >= .9 * source_crop.width
                         and (token.box[3] - token.box[1]) >= .9 * source_crop.height)
                for token in tokens)
        duplicate = duplicate or _duplicate_counter_boxes(tokens)
        found, found_capacities, invalid_range, candidates = _readings(tokens)
        if not found_capacities:
            _, raw_capacities, _, _ = _readings(tokens, minimum_confidence=0.0)
            low_confidence_seen = low_confidence_seen or bool(raw_capacities)
        readings.update(found)
        capacities.update(found_capacities)
        invalid = invalid or invalid_range
        raw_parts.append(raw_text)
        attempts.append({"method": name, "roi": list(roi), "crop_box": list(crop_box),
                         "frame_size": [1920, 1080], "image_size": list(image.size),
                         "text": raw_text, "candidates": candidates,
                         "geometry": geometry, "duplicate_boxes": duplicate,
                         "invalid_range": invalid_range,
                         "rows": [{"text": token.text, "score": token.score, "box": list(token.box),
                                   "touches_crop_boundary": token.touches_crop_boundary}
                                  for token in tokens[:32]]})
        if on_attempt is not None:
            on_attempt(name, image)
        # 多个矛盾读数不能通过后续变体投票抹掉；已完整读出则无需恢复。
        if duplicate or invalid or len(readings) > 1 or len(capacities) > 1:
            break
        if len(readings) == 1:
            current, capacity = next(iter(readings))
            return PopulationFrameEvidence(current, capacity, "complete_population",
                                           " | ".join(raw_parts)[:240], tuple(attempts))
    reason = ("duplicate_population_boxes" if duplicate else
              "invalid_population_range" if invalid else
              "ambiguous_population" if len(readings) > 1 or len(capacities) > 1 else
              "population_current_missing" if len(capacities) == 1 else
              "low_population_confidence" if low_confidence_seen else "population_missing")
    # 人数冲突不抹掉独立且一致的分母；上限仍需由调用方用第二张帧确认。
    capacity = next(iter(capacities)) if not (invalid or duplicate) and len(capacities) == 1 else None
    return PopulationFrameEvidence(None, capacity, reason, " | ".join(raw_parts)[:240], tuple(attempts))
