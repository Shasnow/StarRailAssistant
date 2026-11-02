"""用原始计数像素核实 OCR 的裁剪边界，不改写 OCR 字符或分数。"""
from __future__ import annotations

import math
import re


def foreground_pixels(image, *, kind):
    """保留人口栏的亮字及红字，或金币栏随背景变化的黑/白数字。"""
    image = image.convert('RGB')
    width, height = image.size
    pixels = image.load()
    light_background = False
    if kind in ('coins', 'action_cost'):
        probes = [pixels[x, y] for x in (width // 4, width // 2, 3 * width // 4)
                  for y in (0, height - 1)]
        light_background = sum(min(rgb) >= 150 and max(rgb) - min(rgb) <= 45
                               for rgb in probes) >= 3
    selected = set()
    minimum = 90 if kind == 'action_cost' else 150
    for y in range(height):
        for x in range(width):
            red, green, blue = pixels[x, y]
            if kind == 'population':
                # 未满员时计数会变红；保留原亮字规则，并认证红色字形。
                keep = ((green >= 105 and blue - green <= 45)
                        or (red >= 170 and red - green >= 65 and red - blue >= 45))
            elif light_background:
                keep = max(red, green, blue) <= 110 and max(red, green, blue) - min(red, green, blue) <= 40
            else:
                # 无免费刷新时，次数显示为灰字；仍须与深色背景分离。
                keep = min(red, green, blue) >= minimum and max(red, green, blue) - min(red, green, blue) <= 40
            if keep:
                selected.add((x, y))
    return selected


def _glyph_components(points, size):
    width, height = size
    points = set(points)
    components = []
    while points:
        seed = points.pop()
        component, pending = {seed}, [seed]
        while pending:
            x, y = pending.pop()
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                neighbor = x + dx, y + dy
                if neighbor in points:
                    points.remove(neighbor)
                    component.add(neighbor)
                    pending.append(neighbor)
        left, top = min(x for x, y in component), min(y for x, y in component)
        right, bottom = max(x for x, y in component) + 1, max(y for x, y in component) + 1
        # 金币浅色面板的外部深色背景可能落入裁剪；它跨满高度，不是数字。
        if top == 0 and bottom == height and right - left >= width * .2:
            continue
        if len(component) >= 8 and right - left >= 2 and bottom - top >= max(6, min(10, height * .15)):
            components.append((left, top, right, bottom))
    return sorted(components)


# Yukki：裁剪修复只恢复原始像素，不改写识别字符。
def ground_crop_rows(rows, source_image, *, kind, scale=1):
    """单条贴边 OCR 的几何框可由完整原图字形核实；真正截断仍保留未知。

    RapidOCR 可以返回覆盖全图的识别框，也可能把检测框扩到边界。
    只有每个实际字符均有一份连通字形、同一行且四周有原图余量时，
    才用像素框代替这种宽泛的框。阈值、文本、分数均保持原值。
    多条或非数字 OCR 不做替换，也不从杂乱内容中寻找子串。
    """
    evidence = {'bounds_source': 'ocr', 'reason': 'ocr_geometry_unchanged'}
    if not isinstance(rows, (list, tuple)) or len(rows) != 1:
        return rows, evidence
    try:
        box, text, score = rows[0]
        if not isinstance(text, str) or isinstance(score, bool):
            return rows, evidence
        score = float(score)
        if not math.isfinite(score) or not 0 <= score <= 1:
            return rows, evidence
        normalized = re.sub(r'\s+', '', text).translate(str.maketrans('０１２３４５６７８９／', '0123456789/'))
        pattern = r'(?:[0-9]{1,2})?/[0-9]{1,2}' if kind == 'population' else r'[0-9]{1,3}'
        if not re.fullmatch(pattern, normalized):
            return rows, evidence
        if hasattr(box, 'tolist'):
            box = box.tolist()
        if len(box) != 4 or any(len(point) != 2 or any(isinstance(value, bool) for value in point) for point in box):
            return rows, evidence
        points = [(float(x), float(y)) for x, y in box]
        width, height = source_image.size
        if any(not math.isfinite(x) or not math.isfinite(y) or not 0 <= x <= width * scale
               or not 0 <= y <= height * scale for x, y in points):
            return rows, evidence
        original = (min(x for x, y in points), min(y for x, y in points),
                    max(x for x, y in points), max(y for x, y in points))
        touches = (original[0] <= 1 or original[1] <= 1
                   or original[2] >= width * scale - 1 or original[3] >= height * scale - 1)
        if not touches:
            return rows, evidence
        components = _glyph_components(foreground_pixels(source_image, kind=kind), (width, height))
        evidence.update(ocr_box=list(original), glyph_boxes=[list(part) for part in components[:8]])
        if len(components) != len(normalized):
            evidence['reason'] = 'pixel_character_count_unverified'
            return rows, evidence
        left, top = min(part[0] for part in components), min(part[1] for part in components)
        right, bottom = max(part[2] for part in components), max(part[3] for part in components)
        if left < 2 or top < 2 or right > width - 2 or bottom > height - 2:
            evidence['reason'] = 'actual_ink_at_crop_boundary'
            return rows, evidence
        if any(min(part[3], bottom) - max(part[1], top) < .6 * (bottom - top) for part in components):
            evidence['reason'] = 'pixel_characters_not_on_one_row'
            return rows, evidence
        # 每个原始字形必须落在 OCR 的观测区，不能借用另一处数字解释该框。
        if not (original[0] / scale - 3 <= left and right <= original[2] / scale + 3
                and original[1] / scale - 3 <= top and bottom <= original[3] / scale + 3):
            evidence['reason'] = 'pixel_characters_outside_ocr_box'
            return rows, evidence
        new_box = [[x * scale, y * scale] for x, y in
                   ((left, top), (right, top), (right, bottom), (left, bottom))]
        evidence.update(bounds_source='source_pixels', reason='complete_source_pixel_characters',
                        grounded_box=[left * scale, top * scale, right * scale, bottom * scale])
        return [(new_box, text, score)], evidence
    except (TypeError, ValueError, IndexError, OverflowError, AttributeError):
        return rows, evidence
