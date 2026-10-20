"""只从同一张客户区截图认证通用装备三选一弹窗，不执行截图或输入。"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import re


EQUIPMENT_CHOICE_TITLE_ROI = (0.53, 0.014, 0.625, 0.097)
_CARD_ROI = (0.30, 0.095, 0.83, 0.285)


@dataclass(frozen=True)
class EquipmentChoiceObservation:
    matched: bool
    present: bool
    cards: tuple[tuple[float, float, float, float], ...]
    choice_point: tuple[float, float] | None
    evidence: str
    appearance: tuple[int, ...] = field(default=(), repr=False)


def _bounds(size, roi):
    width, height = size
    return tuple(round(value * scale) for value, scale in zip(roi, (width, height, width, height)))


def _title_labels(rows, size):
    """完整标题和选择数量必须分别由高置信度、有效坐标的 OCR 行提供。"""
    labels, hinted = set(), False
    for row in rows[:24] if isinstance(rows, (tuple, list)) else ():
        if not isinstance(row, (tuple, list)) or len(row) != 3 or not isinstance(row[1], str):
            continue
        label = re.sub(r"\s+", "", row[1])
        hinted |= "选择装备" in label or "请选择" in label
        if label not in {"选择装备", "请选择1个"} or isinstance(row[2], bool):
            continue
        try:
            confidence = float(row[2])
            if not math.isfinite(confidence) or not 0.95 <= confidence <= 1:
                continue
            box = row[0].tolist() if hasattr(row[0], "tolist") else row[0]
            if len(box) != 4:
                continue
            points = [(float(x), float(y)) for x, y in box]
            if any(not math.isfinite(x) or not math.isfinite(y)
                   or not 0 <= x <= size[0] or not 0 <= y <= size[1] for x, y in points):
                continue
            xs, ys = zip(*points)
            if max(xs) - min(xs) < size[0] * 0.25 or max(ys) - min(ys) < size[1] * 0.10:
                continue
        except (TypeError, ValueError, OverflowError):
            continue
        labels.add(label)
    return labels, hinted


def _card_rectangles(image):
    """查找真实金色四边框；固定区域只限定搜索范围，不产生点击坐标。"""
    width, height = image.size
    left, top, right, bottom = _bounds(image.size, _CARD_ROI)
    pixels = image.load()

    def gold(x, y):
        r, g, b = pixels[x, y]
        return r >= 160 and g >= 125 and r >= g and r - b >= 45 and g - b >= 25

    horizontal = []
    for y in range(top, bottom):
        start, last, gaps = None, None, 0
        for x in range(left, right + 1):
            if x < right and gold(x, y):
                if start is None:
                    start = x
                last, gaps = x, 0
            elif start is not None:
                gaps += 1
                if gaps > 2 or x == right:
                    if 0.10 * width <= last - start <= 0.18 * width:
                        horizontal.append((start, last, y))
                    start, last, gaps = None, None, 0
    groups = []
    for x0, x1, y in horizontal:
        group = next((group for group in groups
                      if abs(group[0][0] - x0) <= 3 and abs(group[0][1] - x1) <= 3), None)
        if group is None:
            groups.append([(x0, x1, y)])
        else:
            group.append((x0, x1, y))
    rectangles = []
    for group in groups:
        upper, lower = min(group, key=lambda line: line[2]), max(group, key=lambda line: line[2])
        x0, x1, y0, y1 = upper[0], upper[1], upper[2], lower[2]
        if not 0.13 * height <= y1 - y0 <= 0.20 * height:
            continue
        # 四边须实际存在，拒绝只有两个水平线、文字或不完整卡框。
        if any(sum(any(gold(x, y) for x in range(max(left, edge - 2), min(right, edge + 3)))
                   for y in range(y0, y1 + 1)) / (y1 - y0 + 1) < 0.90 for edge in (x0, x1)):
            continue
        rectangles.append((x0 / width, y0 / height, x1 / width, y1 / height))
    rectangles.sort()
    return tuple(rectangles)


def _complete_three_cards(rectangles):
    """只有三张等宽、同高且等距的真实四边框才是完整选择区域。"""
    if len(rectangles) != 3:
        return ()
    sizes = [(rect[2] - rect[0], rect[3] - rect[1]) for rect in rectangles]
    gaps = [rectangles[index + 1][0] - rectangles[index][2] for index in (0, 1)]
    if (max(size[0] for size in sizes) - min(size[0] for size in sizes) > 0.008
            or max(size[1] for size in sizes) - min(size[1] for size in sizes) > 0.008
            or max(rect[1] for rect in rectangles) - min(rect[1] for rect in rectangles) > 0.006
            or not all(0.008 <= gap <= 0.035 for gap in gaps)
            or abs(gaps[0] - gaps[1]) > 0.006):
        return ()
    return tuple(rectangles)


def equipment_choice_geometry(image):
    """一次无 OCR 扫描区分完整三卡和已审布局内的一到两张残留卡框。"""
    try:
        width, height = image.size
        if width < 640 or height < 360 or abs(width / height - 16 / 9) > 0.02:
            return None
        rectangles = _card_rectangles(image.convert("RGB"))
        cards = _complete_three_cards(rectangles)
        # 只有已审核三卡位置内的残留完整框才触发标题复核，普通棋盘不读 OCR。
        expected = ((0.3536, 0.1065, 0.4880, 0.2704),
                    (0.5052, 0.1065, 0.6396, 0.2704),
                    (0.6563, 0.1065, 0.7906, 0.2704))
        partial = len(rectangles) in (1, 2) and all(
            any(max(abs(a - b) for a, b in zip(rectangle, target)) <= 0.012
                for target in expected) for rectangle in rectangles)
        return cards, partial
    except (AttributeError, TypeError, ValueError, ZeroDivisionError, IndexError):
        return None


def equipment_choice_cards(image):
    """保持完整三卡预检接口；未认证的部分卡框不能生成选择点。"""
    geometry = equipment_choice_geometry(image)
    return geometry[0] if geometry is not None else None


def _pixels(image):
    method = getattr(image, "get_flattened_data", None)
    return method() if callable(method) else image.getdata()


# ssyb：标题与三张完整装备卡必须在同一截图内成立。
def detect_equipment_choice(image, title_results, *, cards=None, partial=False) -> EquipmentChoiceObservation:
    """标题、数量和三张完整卡框均认证后，才返回最右卡内部的选择点。"""
    def rejected(evidence, present=False, cards=()):
        return EquipmentChoiceObservation(False, present, cards, None, evidence)

    try:
        width, height = image.size
        if width < 640 or height < 360 or abs(width / height - 16 / 9) > 0.02:
            return rejected("equipment_viewport_unsupported", True)
        if title_results is None:
            return rejected("equipment_ocr_unavailable", True)
        # 保留完整分辨率，避免缩小后丢失只占一到两像素的金色边线。
        frame = image.convert("RGB")
        title_box = _bounds(image.size, EQUIPMENT_CHOICE_TITLE_ROI)
        labels, hinted = _title_labels(title_results,
                                      (title_box[2] - title_box[0], title_box[3] - title_box[1]))
        cards = _complete_three_cards(_card_rectangles(frame)) if cards is None else cards
        if labels != {"选择装备", "请选择1个"}:
            if partial and not cards:
                # 局部卡框只在完整装备标题认证后阻挡底层流程，不拦截旧阿哈等其它提示。
                return rejected("equipment_partial_other_title")
            return rejected("equipment_exact_title_missing", hinted or bool(cards), cards)
        if len(cards) != 3:
            return rejected("equipment_three_cards_missing", True)
        title = frame.crop(_bounds(frame.size, EQUIPMENT_CHOICE_TITLE_ROI))
        title_pixels = list(_pixels(title))
        if sum(min(pixel) >= 180 and max(pixel) - min(pixel) <= 45
               for pixel in title_pixels) / len(title_pixels) < 0.018:
            return rejected("equipment_title_pixels_missing", True, cards)
        right = cards[-1]
        point = ((right[0] + right[2]) / 2, (right[1] + right[3]) / 2)
        appearance = tuple(value for pixel in _pixels(frame.crop(_bounds(frame.size, _CARD_ROI))
                           .resize((48, 16))) for value in pixel)
        return EquipmentChoiceObservation(True, True, cards, point,
            "equipment_exact_title_count_and_three_gold_cards", appearance)
    except (AttributeError, TypeError, ValueError, ZeroDivisionError, IndexError):
        return rejected("equipment_frame_invalid", True)


def same_equipment_choice(first, second):
    """两张新鲜帧必须具有稳定卡框和卡片内容，未知帧绝不授权输入。"""
    return (first is not None and second is not None and first.matched and second.matched
            and max(abs(a - b) for left, right in zip(first.cards, second.cards)
                    for a, b in zip(left, right)) <= 0.005
            and len(first.appearance) == len(second.appearance) > 0
            and sum(abs(a - b) for a, b in zip(first.appearance, second.appearance))
                / (255 * len(first.appearance)) <= 0.025)
