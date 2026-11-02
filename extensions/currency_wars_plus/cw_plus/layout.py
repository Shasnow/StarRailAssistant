"""纯几何校验；接受矩形绝不能证明槽位占用状态。"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import median
from typing import Any, Sequence
from types import SimpleNamespace

BACKEND_LAYOUT_ROI = (0.1, 0.52, 0.86, 0.7)
# 数量只受几何边界限制，不再把某一种支援数量当成固定布局。
# 十二槽是当前 ROI、最小框宽和最小间距能容纳的居中行的物理上限；
# 每次观测还须按实际框宽、间距和完整行边界校验。
MIN_BACKEND_SLOTS = 5
MAX_BACKEND_SLOTS = 12
BACKEND_STEP_RANGE = (0.058, 0.086)


@dataclass(frozen=True)
class LayoutObservation:
    valid: bool
    positions: tuple[tuple[float, float], ...] = ()
    changed: bool = False
    reason: str = "layout_unknown"
    boxes: tuple[tuple[float, float, float, float], ...] = ()
    protected_slots: tuple[int, ...] = ()
    # 几何和身份是独立证据。Vision 仅在完整行通过双帧确认后
    # 向动作层授予 geometry_valid；protected_slots 只含支援头像+通用站位角标认证的支援。
    geometry_valid: bool = False
    unknown_protected_slots: tuple[int, ...] = ()
    ordinary_count_confirmed: bool = False
    ordinary_slots: tuple[int, ...] = ()
    ordinary_count: int | None = None


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


# ssyb：几何完整性与占用状态分开判定。
def validate_backend_layout(boxes: Sequence[Any], window_size, *,
                            previous_positions=(), expected_count=None) -> LayoutObservation:
    """验证由真实矩形组成、数量随可见边界变化的完整居中行。
    调用方替换布局前还须要求帧稳定，且 changed 为真时必须使观测失效。
    行中心校验会拒绝六槽行丢失任一边缘后形成的连续五框子集；间隔校验会拒绝内部缺失。
    尺寸按宿主的 1920x1080 矩形检测器缩放，不来自已校准的 EMPTY 模板。
    """
    def reject(reason, rectangles=()):
        return LayoutObservation(False, reason=reason, boxes=tuple(rectangles))

    if (not isinstance(window_size, (list, tuple)) or len(window_size) != 2
            or not all(_finite(v) and v > 0 for v in window_size)):
        return reject("invalid_window_size")
    width, height = window_size
    if abs(width / height - 1920 / 1080) > 0.02:
        return reject("unsupported_window_aspect")
    if expected_count is not None and (type(expected_count) is not int
                                       or not MIN_BACKEND_SLOTS <= expected_count <= MAX_BACKEND_SLOTS):
        return reject("invalid_expected_count")
    if (not isinstance(boxes, (list, tuple))
            or not MIN_BACKEND_SLOTS <= len(boxes) <= MAX_BACKEND_SLOTS):
        return reject("incomplete_slot_count")
    if expected_count is not None and len(boxes) != expected_count:
        return reject("unexpected_slot_count")
    rectangles = []
    for box in boxes:
        values = tuple(getattr(box, key, None) for key in ("left", "top", "width", "height"))
        if not all(_finite(v) for v in values):
            return reject("invalid_rectangle")
        left, top, bw, bh = values
        if not (120 * width / 1920 <= bw <= 150 * width / 1920
                and 130 * height / 1080 <= bh <= 150 * height / 1080):
            return reject("invalid_rectangle_size")
        if not (BACKEND_LAYOUT_ROI[0] * width <= left < left + bw <= BACKEND_LAYOUT_ROI[2] * width
                and BACKEND_LAYOUT_ROI[1] * height <= top < top + bh <= BACKEND_LAYOUT_ROI[3] * height):
            return reject("rectangle_outside_roi")
        rectangles.append(tuple(float(v) for v in values))
    rectangles.sort(key=lambda box: box[0] + box[2] / 2)
    centers = tuple((left + bw / 2, top + bh / 2) for left, top, bw, bh in rectangles)
    row_y = median(y for _, y in centers)
    if max(y for _, y in centers) - min(y for _, y in centers) > 0.008 * height:
        return reject("row_not_aligned", rectangles)
    if abs(row_y / height - 0.62) > 0.015:
        return reject("row_anchor_mismatch", rectangles)
    gaps = [centers[i + 1][0] - centers[i][0] for i in range(len(centers) - 1)]
    if min(gaps) < median(box[2] for box in rectangles) * 0.55:
        return reject("duplicate_rectangles", rectangles)
    if any(left + bw - next_left > 0.15 * min(bw, next_bw)
           for (left, _, bw, _), (next_left, _, next_bw, _) in zip(rectangles, rectangles[1:])):
        return reject("overlapping_rectangles", rectangles)
    step = median(gaps)
    if (not BACKEND_STEP_RANGE[0] <= step / width <= BACKEND_STEP_RANGE[1]
            or any(abs(gap - step) > step * 0.12 for gap in gaps)):
        return reject("non_contiguous_slots", rectangles)
    if abs((centers[0][0] + centers[-1][0]) / (2 * width) - 0.5) > 0.015:
        return reject("row_boundary_incomplete", rectangles)
    # 已通过同行校验后，所有动作使用共同的行锚点。占用卡片的
    # 内外边框会令单框高度抖动，不能把这类轮廓抖动当作整行移位。
    positions = tuple((x / width, row_y / height) for x, _ in centers)
    if (not isinstance(previous_positions, (list, tuple))
            or any(not isinstance(p, (list, tuple)) or len(p) != 2
                   or not all(_finite(v) and 0 <= v <= 1 for v in p) for p in previous_positions)):
        return reject("invalid_previous_positions", rectangles)
    changed = (len(previous_positions) != len(positions)
               or any(abs(a - b) > 0.002 for old, new in zip(previous_positions, positions)
                      for a, b in zip(old, new)))
    return LayoutObservation(True, positions, changed, "layout_changed" if changed else "layout_unchanged",
                             tuple(rectangles))


def layout_diagnostics(boxes, window_size, *, previous_positions=()):
    """有界的几何证据，包括被拒绝或缺槽的候选。"""
    raw = []
    for box in boxes if isinstance(boxes, (list, tuple)) else ():
        values = [getattr(box, key, None) for key in ("left", "top", "width", "height")]
        if all(_finite(value) for value in values):
            raw.append(values)
    ordered = sorted(raw, key=lambda box: box[0] + box[2] / 2)
    centers = [[x + w / 2, y + h / 2] for x, y, w, h in ordered]
    gaps = [b[0] - a[0] for a, b in zip(centers, centers[1:])]
    return {"layout_boxes": raw[:24], "layout_centers": centers[:24],
            "layout_gaps": gaps[:23], "layout_median_gap": median(gaps) if gaps else None,
            "layout_candidate_count": len(boxes) if isinstance(boxes, (list, tuple)) else None,
            "previous_layout_positions": list(previous_positions) if isinstance(previous_positions, (list, tuple)) else [],
            "layout_window_size": list(window_size) if isinstance(window_size, (list, tuple)) else []}


def revalidate_backend_layout(candidates, window_size, *, previous_positions):
    """每个旧锚点都须有新矩形，且须通过原有整行校验。
    旧坐标仅定位候选簇，绝不合成框或证明占用。
    同锚点嵌套轮廓去重；相互竞争的不同中心、缺失锚点和偏移行均拒绝。
    调用方还须要求两张独立稳定帧。
    """
    if (not isinstance(previous_positions, (list, tuple))
            or not MIN_BACKEND_SLOTS <= len(previous_positions) <= MAX_BACKEND_SLOTS
            or any(not isinstance(point, (list, tuple)) or len(point) != 2
                   or not all(_finite(value) and 0 <= value <= 1 for value in point)
                   for point in previous_positions)):
        return LayoutObservation(False, reason="recovery_requires_confirmed_layout")
    if (not isinstance(window_size, (list, tuple)) or len(window_size) != 2
            or not all(_finite(value) and value > 0 for value in window_size)):
        return LayoutObservation(False, reason="invalid_window_size")
    if not isinstance(candidates, (list, tuple)) or len(candidates) > 128:
        return LayoutObservation(False, reason="recovery_invalid_candidates")
    width, height = window_size
    usable = []
    for box in candidates:
        values = tuple(getattr(box, key, None) for key in ("left", "top", "width", "height"))
        if all(_finite(value) for value in values):
            x, y, w, h = values
            if 120 * width / 1920 <= w <= 150 * width / 1920 and 130 * height / 1080 <= h <= 150 * height / 1080:
                usable.append((box, (x + w / 2) / width, (y + h / 2) / height))
    selected = []
    for px, py in previous_positions:
        local = [(box, x, y) for box, x, y in usable if abs(x - px) <= 0.006 and abs(y - py) <= 0.006]
        if not local:
            return LayoutObservation(False, reason="recovery_missing_anchor")
        if (max(x for _, x, _ in local) - min(x for _, x, _ in local) > 0.003
                or max(y for _, _, y in local) - min(y for _, _, y in local) > 0.003):
            return LayoutObservation(False, reason="recovery_ambiguous_anchor")
        # 保留最外层真实轮廓，绝不补出缺失矩形。
        selected.append(max(local, key=lambda item: item[0].width * item[0].height)[0])
    # 旧布局不能裁掉同排新出现的支援槽位。否则恢复会把完整新行中的
    # 居中旧子集重新认证，保护列表和人口数也会一并沿用错误旧值。
    row_y = median(point[1] for point in previous_positions)
    for box, x, y in usable:
        if (BACKEND_LAYOUT_ROI[0] * width <= box.left < box.left + box.width <= BACKEND_LAYOUT_ROI[2] * width
                and BACKEND_LAYOUT_ROI[1] * height <= box.top < box.top + box.height <= BACKEND_LAYOUT_ROI[3] * height
                and abs(y - row_y) <= 0.008
                and not any(abs(x - px) <= 0.006 and abs(y - py) <= 0.006
                            for px, py in previous_positions)):
            return LayoutObservation(False, reason="recovery_unexpected_anchor")
    return validate_backend_layout(selected, window_size, previous_positions=previous_positions,
                                   expected_count=len(previous_positions))


def current_backend_extent_matches(image, positions, *, previous_positions=()):
    """缩行由当前像素证明，不由历史人数批准或否决。
    独立遍历整幅图和旧锚点，避免把漏检的居中子集误当作完整新行。
    调用者还必须在第二张新鲜帧上获得相同几何和支援证据。
    """
    candidates = backend_rectangle_candidates(image, previous_positions=previous_positions)
    actual = validate_backend_layout(candidates, image.size, previous_positions=positions,
                                     expected_count=len(positions))
    return actual.valid and not actual.changed


def backend_probe_positions(boxes, window_size):
    """根据新鲜可见的行锚点，提出缺失边框的搜索位置。
    这些位置不能认证布局；每个候选槽位仍须检测到自己的真实边框，并在两帧上通过整行几何校验。
    """
    if (not isinstance(window_size, (list, tuple)) or len(window_size) != 2
            or not all(_finite(value) and value > 0 for value in window_size)
            or not isinstance(boxes, (list, tuple)) or len(boxes) > 128):
        return ()
    width, height = window_size
    centers, widths = [], []
    for box in boxes:
        values = tuple(getattr(box, key, None) for key in ("left", "top", "width", "height"))
        if not all(_finite(value) for value in values):
            continue
        x, y, bw, bh = values
        if not (120 * width / 1920 <= bw <= 150 * width / 1920
                and 130 * height / 1080 <= bh <= 150 * height / 1080
                and BACKEND_LAYOUT_ROI[0] * width <= x < x + bw <= BACKEND_LAYOUT_ROI[2] * width
                and BACKEND_LAYOUT_ROI[1] * height <= y < y + bh <= BACKEND_LAYOUT_ROI[3] * height):
            continue
        centers.append(((x + bw / 2) / width, (y + bh / 2) / height))
        widths.append(bw / width)
    centers.sort()
    unique = []
    for point in centers:
        if not any(max(abs(point[i] - old[i]) for i in (0, 1)) <= 0.002 for old in unique):
            unique.append(point)
    if not 4 <= len(unique) <= MAX_BACKEND_SLOTS:
        return ()
    if (max(y for _, y in unique) - min(y for _, y in unique) > 0.008
            or abs(median(y for _, y in unique) - 0.62) > 0.015):
        return ()
    gaps = [b[0] - a[0] for a, b in zip(unique, unique[1:])]
    # 缺失多个内部边框时，中位间距本身也可能是步长的整数倍。
    # 只使用与全部可见锚点一致的栅格，优先选择有最多直接相邻证据的步长。
    lattices = []
    for gap in gaps:
        for divisor in range(1, MAX_BACKEND_SLOTS):
            estimate = gap / divisor
            if not BACKEND_STEP_RANGE[0] <= estimate <= BACKEND_STEP_RANGE[1]:
                continue
            multiples = [round(value / estimate) for value in gaps]
            if any(not 1 <= value < MAX_BACKEND_SLOTS for value in multiples):
                continue
            step = median(value / multiple for value, multiple in zip(gaps, multiples))
            if (not BACKEND_STEP_RANGE[0] <= step <= BACKEND_STEP_RANGE[1]
                    or sum(multiples) + 1 > MAX_BACKEND_SLOTS
                    or any(abs(value - multiple * step) > step * 0.12
                           for value, multiple in zip(gaps, multiples))):
                continue
            error = sum(abs(value - multiple * step) / step for value, multiple in zip(gaps, multiples))
            lattices.append((multiples.count(1), -error, step, multiples))
    if not lattices:
        return ()
    _, _, step, multiples = max(lattices, key=lambda item: item[:2])
    # 使用实测宽度留出边框空间。探针可以搜索完整可见范围内的两侧，
    # 无须先猜测普通角色数或支援数量；没有边框的探针不会生成槽位。
    half_width = median(widths) / 2
    left_limit = BACKEND_LAYOUT_ROI[0] + half_width
    right_limit = BACKEND_LAYOUT_ROI[2] - half_width
    physical_limit = min(MAX_BACKEND_SLOTS, math.floor((right_limit - left_limit) / step) + 1)
    if sum(multiples) + 1 > physical_limit:
        return ()
    probes = [unique[0]]
    for left, right, multiple in zip(unique, unique[1:], multiples):
        for part in range(1, multiple + 1):
            probes.append(tuple(left[i] + (right[i] - left[i]) * part / multiple for i in (0, 1)))
    row_y = median(y for _, y in unique)
    left_probes, right_probes = [], []
    for distance in range(1, physical_limit):
        px = unique[0][0] - distance * step
        if px < left_limit:
            break
        left_probes.append((px, row_y))
    for distance in range(1, physical_limit):
        px = unique[-1][0] + distance * step
        if px > right_limit:
            break
        right_probes.append((px, row_y))
    probes = list(reversed(left_probes)) + probes + right_probes
    if len(probes) > physical_limit:
        return ()
    return tuple(probes)


# Yukki：遮挡恢复须保留真实边缘片段与相邻卡片证据。
def _occluded_backend_candidates(image, red, edges, boxes, origin):
    """小卡片遮住下沿时，只使用当前帧仍可见的四边证据。

    至少三个完整槽框提供同行上下沿；独立检测的小卡片只解释遮挡，
    不能生成槽位。每个补读候选仍须有完整上沿、可见侧边和真实下沿片段。
    """
    import cv2
    import numpy as np

    width, height = image.size
    sx, sy = width / 1920, height / 1080
    left, top = origin
    row = [b for b in boxes if abs((b.top + b.height / 2) / height - 0.62) <= 0.015]
    # 嵌套轮廓不提供独立的同行证据。
    distinct = []
    for box in sorted(row, key=lambda box: box.width * box.height, reverse=True):
        if not any(abs(box.left + box.width / 2 - old.left - old.width / 2) <= 4 * sx
                   for old in distinct):
            distinct.append(box)
    if len(distinct) < 3:
        return []
    row_top = median(b.top for b in distinct)
    row_bottom = median(b.top + b.height - 1 for b in distinct)
    if (max(b.top for b in distinct) - min(b.top for b in distinct) > 3 * sy
            or max(b.top + b.height for b in distinct) - min(b.top + b.height for b in distinct) > 3 * sy):
        return []
    # 下沿附近的独立小卡片有自己的深色四边，大小不同于后台槽框。
    full = np.asarray(image.convert('RGB'))
    x0, y0, x1, y1 = round(0.1 * width), round(row_bottom - 35 * sy), round(0.86 * width), round(row_bottom + 80 * sy)
    crop = full[max(0, y0):min(height, y1), x0:x1]
    dark = cv2.inRange(crop, np.array([0, 0, 0]), np.array([80, 80, 100]))
    mini_contours, _ = cv2.findContours(dark, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    mini = []
    for contour in mini_contours:
        x, y, w, h = cv2.boundingRect(contour)
        x, y = x + x0, y + max(0, y0)
        if (70 * sx <= w <= 82 * sx and 82 * sy <= h <= 94 * sy
                and row_bottom - 30 * sy <= y <= row_bottom - 12 * sy
                and cv2.contourArea(contour) >= 0.85 * w * h):
            mini.append((x, y, w, h))
    mini.sort()
    if not 3 <= len(mini) <= 9:
        return []
    if (max(y for _, y, _, _ in mini) - min(y for _, y, _, _ in mini) > 3 * sy
            or any(not 78 * sx <= b[0] - a[0] <= 98 * sx for a, b in zip(mini, mini[1:]))):
        return []
    occluded = np.zeros_like(red)
    for x, y, w, h in mini:
        ax, ay = max(0, x - left - 2), max(0, y - top - 2)
        bx, by = min(red.shape[1], x + w - left + 2), min(red.shape[0], y + h - top + 2)
        if ax < bx and ay < by:
            occluded[ay:by, ax:bx] = 255
    radius = max(1, round(2 * sx))
    support = cv2.dilate(red | edges, np.ones((2 * radius + 1, 2 * radius + 1), np.uint8))

    def witnessed(a, b, minimum):
        points = np.rint(np.linspace(a, b, 160)).astype(int)
        if any(not (0 <= x < red.shape[1] and 0 <= y < red.shape[0]) for x, y in points):
            return False
        visible = [(x, y) for x, y in points if not occluded[y, x]]
        # 侧边至少 2/3 可见；下沿至少六个独立像素必须实际存在。
        unique = set(visible)
        return (len(visible) >= minimum and len(unique) >= 6 * sx
                and sum(bool(support[y, x]) for x, y in visible) >= 0.95 * len(visible))

    # 剔除已认证遮挡物本身的像素，避免它与红框相连成为同一轮廓。
    visible_red = red.copy()
    visible_red[occluded != 0] = 0
    visible_contours, _ = cv2.findContours(visible_red, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    result = []
    for contour in visible_contours:
        x, y, w, h = cv2.boundingRect(contour)
        if not (120 * sx <= w <= 150 * sx and 90 * sy <= h <= 150 * sy
                and abs(y + top - row_top) <= 2 * sy):
            continue
        hull = cv2.convexHull(contour)
        polygon = cv2.approxPolyDP(hull, 0.015 * cv2.arcLength(hull, True), True).reshape(-1, 2)
        if len(polygon) != 4:
            continue
        upper = sorted(polygon.tolist(), key=lambda p: p[1])[:2]
        lower = sorted(polygon.tolist(), key=lambda p: p[1])[2:]
        lt, rt = sorted(upper)
        lb, rb = sorted(lower)
        if (abs(lt[1] + top - row_top) > 2 * sy or abs(rt[1] + top - row_top) > 2 * sy
                or min(lb[1] - lt[1], rb[1] - rt[1]) < 90 * sy):
            continue
        bottom = row_bottom - top
        lbx = lt[0] + (bottom - lt[1]) * (lb[0] - lt[0]) / (lb[1] - lt[1])
        rbx = rt[0] + (bottom - rt[1]) * (rb[0] - rt[0]) / (rb[1] - rt[1])
        low_left, low_right = (lbx, bottom), (rbx, bottom)
        bx0, bx1 = min(lt[0], lbx), max(rt[0], rbx)
        bw, bh = bx1 - bx0 + 1, row_bottom - row_top + 1
        if not (120 * sx <= bw <= 150 * sx and 130 * sy <= bh <= 150 * sy):
            continue
        if any(abs(box.left + box.width / 2 - (bx0 + bx1) / 2 - left) <= 6 * sx
               and abs(box.top + box.height / 2 - row_top - bh / 2) <= 6 * sy for box in boxes):
            continue
        if (witnessed(lt, rt, 150) and witnessed(lt, low_left, 105)
                and witnessed(rt, low_right, 105) and witnessed(low_left, low_right, 7)):
            result.append(SimpleNamespace(left=bx0 + left, top=row_top, width=bw, height=bh))
    return result


def supplement_backend_dark_borders(image, existing_boxes):
    """失败三次后补读同一帧的深色内框，不重复灰度/Hough 检测。"""
    import cv2
    import numpy as np
    width, height = image.size
    left, top, right, bottom = (int(BACKEND_LAYOUT_ROI[i] * (width if i % 2 == 0 else height))
                               for i in range(4))
    rgb = np.asarray(image.convert("RGB").crop((left, top, right, bottom)))
    boxes = list(existing_boxes)
    # 蓝紫动态光效会连接灰度轮廓，卡片的深色内框仍然完整。
    # 仅补充缺失的真实内框；既不缩小尺寸下限，也不按旧锚点合成矩形。
    # 同时要求轮廓面积、四/五边形和每段周长的像素支持。
    dark = (np.max(rgb, axis=2) < 160).astype(np.uint8) * 255
    dark_contours, _ = cv2.findContours(dark, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    # 与下面斜边恢复相同的三像素边缘邻域，容纳透视与抗锯齿。
    dark_radius = max(1, round(3 * width / 1920))
    dark_support = cv2.dilate(dark, np.ones((2 * dark_radius + 1, 2 * dark_radius + 1), np.uint8))
    for contour in dark_contours:
        x, y, w, h = cv2.boundingRect(contour)
        if not (120 * width / 1920 <= w <= 150 * width / 1920
                and 130 * height / 1080 <= h <= 150 * height / 1080):
            continue
        center = ((left + x + w / 2) / width, (top + y + h / 2) / height)
        if any(abs((box.left + box.width / 2) / width - center[0]) <= 0.006
               and abs((box.top + box.height / 2) / height - center[1]) <= 0.006 for box in boxes):
            continue
        if cv2.contourArea(contour) < 0.8 * w * h:
            continue
        hull = cv2.convexHull(contour)
        polygon = cv2.approxPolyDP(hull, 0.015 * cv2.arcLength(hull, True), True).reshape(-1, 2)
        if len(polygon) not in (4, 5):
            continue
        supported = True
        for start, end in zip(polygon, np.roll(polygon, -1, axis=0)):
            points = np.rint(np.linspace(start, end, 80)).astype(int)
            samples = [bool(dark_support[py, px]) for px, py in points]
            if sum(samples) < 72 or any(sum(samples[i:i+20]) < 16 for i in range(0, 80, 20)):
                supported = False
                break
        if supported:
            boxes.append(SimpleNamespace(left=left + x, top=top + y, width=w, height=h))
    return boxes


# ssyb：候选矩形仍需后续双帧认证才能用于实际槽位。
def backend_rectangle_candidates(image, *, previous_positions=(), deep_recheck=False):
    """在一张真实的完整窗口截图上使用另一种轮廓提取方式。
    RETR_LIST 保留嵌套在相连外层轮廓内的角色边框。
    这仅生成证据；revalidate_backend_layout 仍拒绝缺失锚点或不连续行。
    OpenCV 是已有运行时依赖。
    """
    import cv2
    import numpy as np
    width, height = image.size
    left, top, right, bottom = (int(BACKEND_LAYOUT_ROI[i] * (width if i % 2 == 0 else height))
                               for i in range(4))
    rgb = np.asarray(image.convert("RGB").crop((left, top, right, bottom)))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 30, 90, apertureSize=3, L2gradient=True)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if 120 * width / 1920 <= w <= 150 * width / 1920 and 130 * height / 1080 <= h <= 150 * height / 1080:
            boxes.append(SimpleNamespace(left=left + x, top=top + y, width=w, height=h))
    # 备战区满员时使用的红色边框或条纹，亮度接近紫色场地区域。
    # 寻找真实边框前保留其颜色；
    # 灰度轮廓路径可能漏掉全部三个未占用的后台槽位。
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    # 红框随场地透明度呈现 160..179 的色相；完整边缘检查仍独立执行。
    red = (cv2.inRange(hsv, np.array([0, 90, 110]), np.array([15, 255, 255]))
           | cv2.inRange(hsv, np.array([160, 90, 110]), np.array([179, 255, 255])))
    colour_contours, _ = cv2.findContours(red, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    radius = max(1, round(2 * width / 1920))
    border_support = cv2.dilate(red | edges, np.ones((2 * radius + 1, 2 * radius + 1), np.uint8))
    for contour in colour_contours:
        x, y, w, h = cv2.boundingRect(contour)
        if not (120 * width / 1920 <= w <= 150 * width / 1920
                and 130 * height / 1080 <= h <= 150 * height / 1080):
            continue
        hull = cv2.convexHull(contour)
        polygon = cv2.approxPolyDP(hull, 0.015 * cv2.arcLength(hull, True), True).reshape(-1, 2)
        # 小型支援头像可能截去一个角，留下五个顶点。
        # 每段周长仍须有新鲜的视觉边缘证据；
        # 仅用凸包补闭合缺失边，不能认证边框。
        if len(polygon) not in (4, 5) or cv2.contourArea(polygon) < 0.8 * w * h:
            continue
        supported = True
        for start, end in zip(polygon, np.roll(polygon, -1, axis=0)):
            points = np.rint(np.linspace(start, end, 80)).astype(int)
            samples = [bool(border_support[py, px]) for px, py in points]
            if sum(samples) < 72 or any(sum(samples[i:i+20]) < 16 for i in range(0, 80, 20)):
                supported = False
                break
        if supported:
            boxes.append(SimpleNamespace(left=left + x, top=top + y, width=w, height=h))
    boxes.extend(_occluded_backend_candidates(image, red, edges, boxes, (left, top)))
    if deep_recheck:
        boxes = supplement_backend_dark_borders(image, boxes)
    # 装备图标可能将已占用角色连接到外层轮廓，
    # 即使使用 RETR_LIST 也可能隐藏其外接矩形。旧锚点缺失时，
    # 须有真实的上下边线，以及两侧边缘的连续证据。
    # 不能根据旧坐标推断任何缺失边框。
    probes = list(previous_positions)
    for point in backend_probe_positions(boxes, (width, height)):
        if not any(max(abs(point[i] - old[i]) for i in (0, 1)) <= 0.002 for old in probes):
            probes.append(point)
    for point in probes:
        if (not isinstance(point, (list, tuple)) or len(point) != 2
                or not all(_finite(value) and 0 <= value <= 1 for value in point)):
            continue
        px, py = point
        if any(abs((box.left + box.width / 2) / width - px) <= 0.006
               and abs((box.top + box.height / 2) / height - py) <= 0.006 for box in boxes):
            continue
        cx, cy = px * width - left, py * height - top
        x0, x1 = max(0, round(cx - 85 * width / 1920)), min(edges.shape[1], round(cx + 85 * width / 1920))
        y0, y1 = max(0, round(cy - 80 * height / 1080)), min(edges.shape[0], round(cy + 80 * height / 1080))
        local = edges[y0:y1, x0:x1]
        if not local.size:
            continue
        lines = cv2.HoughLinesP(local, 1, np.pi / 180, threshold=max(15, round(35 * width / 1920)),
                               minLineLength=round(105 * width / 1920), maxLineGap=round(8 * width / 1920))
        horizontal = []
        for lx1, ly1, lx2, ly2 in lines[:, 0] if lines is not None else ():
            if abs(int(ly2) - int(ly1)) <= max(1, round(height / 1080)):
                horizontal.append((min(int(lx1), int(lx2)) + x0,
                                   max(int(lx1), int(lx2)) + x0,
                                   (int(ly1) + int(ly2)) / 2 + y0))
        candidates = []
        radius = max(1, round(3 * width / 1920))

        def side_supported(ax, ay, bx, by):
            support = []
            for xx, yy in zip(np.linspace(ax, bx, 80), np.linspace(ay, by, 80)):
                xi, yi = round(float(xx)), round(float(yy))
                support.append(bool(edges[yi, max(0, xi-radius):min(edges.shape[1], xi+radius+1)].any()))
            return sum(support) >= 72 and all(sum(support[i:i+20]) >= 16 for i in range(0, 80, 20))

        for tx1, tx2, ty in horizontal:
            for bx1, bx2, by in horizontal:
                bw, bh = max(tx2, bx2) - min(tx1, bx1) + 1, by - ty + 1
                if not (120 * width / 1920 <= bw <= 150 * width / 1920
                        and 130 * height / 1080 <= bh <= 150 * height / 1080):
                    continue
                center_x, center_y = (min(tx1, bx1) + max(tx2, bx2)) / 2, (ty + by) / 2
                if abs(center_x - cx) > 0.006 * width or abs(center_y - cy) > 0.006 * height:
                    continue
                if side_supported(tx1, ty, bx1, by) and side_supported(tx2, ty, bx2, by):
                    candidates.append(SimpleNamespace(left=min(tx1, bx1) + left, top=ty + top,
                                                      width=bw, height=bh))
        if not candidates:
            # 左上装备徽标可能将上边缘截成短线。
            # 使用观测到的斜侧边定位其角点，然后要求
            # 四段完整周长都有新鲜的边缘支持。
            # 旧锚点或外推侧边几何都不能作为证据。
            lines = cv2.HoughLinesP(local, 1, np.pi / 180, threshold=max(15, round(25 * width / 1920)),
                                   minLineLength=round(70 * width / 1920), maxLineGap=round(8 * width / 1920))
            horizontal, sides = [], []
            for ax, ay, bx, by in lines[:, 0] if lines is not None else ():
                ax, ay, bx, by = int(ax) + x0, int(ay) + y0, int(bx) + x0, int(by) + y0
                if abs(by - ay) <= max(1, round(height / 1080)):
                    horizontal.append((min(ax, bx), max(ax, bx), (ay + by) / 2))
                elif abs(by - ay) >= 70 * height / 1080 and abs(bx - ax) <= 0.25 * abs(by - ay):
                    sides.append((ax, ay, bx, by))
            edge_radius = max(1, round(2 * width / 1920))

            def perimeter_supported(ax, ay, bx, by):
                support = []
                for xx, yy in zip(np.linspace(ax, bx, 80), np.linspace(ay, by, 80)):
                    xi, yi = round(float(xx)), round(float(yy))
                    if not (0 <= xi < edges.shape[1] and 0 <= yi < edges.shape[0]):
                        return False
                    support.append(bool(edges[max(0, yi-edge_radius):min(edges.shape[0], yi+edge_radius+1),
                                              max(0, xi-edge_radius):min(edges.shape[1], xi+edge_radius+1)].any()))
                return sum(support) >= 72 and all(sum(support[i:i+20]) >= 16 for i in range(0, 80, 20))

            tolerance = 5 * width / 1920
            for tx1, tx2, ty in horizontal:
                for bx1, bx2, by in horizontal:
                    bh = by - ty + 1
                    if not (130 * height / 1080 <= bh <= 150 * height / 1080
                            and bx2 - bx1 >= 105 * width / 1920):
                        continue
                    supported_sides = []
                    for ax, ay, bx, end_y in sides:
                        if min(ay, end_y) < ty - 8 * height / 1080 or max(ay, end_y) > by + 8 * height / 1080:
                            continue
                        xt = ax + (ty - ay) * (bx - ax) / (end_y - ay)
                        xb = ax + (by - ay) * (bx - ax) / (end_y - ay)
                        if perimeter_supported(xt, ty, xb, by):
                            supported_sides.append((xt, xb))
                    for lt, lb in supported_sides:
                        for rt, rb in supported_sides:
                            if not (105 * width / 1920 <= rt - lt <= 150 * width / 1920
                                    and 105 * width / 1920 <= rb - lb <= 150 * width / 1920):
                                continue
                            if abs(lb - bx1) > tolerance or abs(rb - bx2) > tolerance:
                                continue
                            if (tx1 < lt - tolerance or tx2 > rt + tolerance
                                    or tx2 - tx1 < 0.55 * (rt - lt)
                                    or min(abs(tx1 - lt), abs(tx2 - rt)) > tolerance):
                                continue
                            bw = max(rt, rb) - min(lt, lb) + 1
                            center_x, center_y = (min(lt, lb) + max(rt, rb)) / 2, (ty + by) / 2
                            if not (120 * width / 1920 <= bw <= 150 * width / 1920):
                                continue
                            if abs(center_x - cx) > 0.006 * width or abs(center_y - cy) > 0.006 * height:
                                continue
                            if perimeter_supported(lt, ty, rt, ty) and perimeter_supported(lb, by, rb, by):
                                candidates.append(SimpleNamespace(left=min(lt, lb) + left, top=ty + top,
                                                                  width=bw, height=bh))
        if candidates:
            boxes.append(min(candidates, key=lambda box: abs((box.left + box.width / 2) / width - px)
                             + abs((box.top + box.height / 2) / height - py)))
    # RETR_LIST 会返回同一边框的两侧；只保留真实轮廓。
    # 整行校验仍拒绝确实缺失或偏移的槽位。
    unique = []
    for box in sorted(boxes, key=lambda b: b.width * b.height, reverse=True):
        center = ((box.left + box.width / 2) / width, (box.top + box.height / 2) / height)
        if not any(max(abs(center[i] - old[i]) for i in (0, 1)) <= 0.002
                   or (outer.left <= box.left and outer.top <= box.top
                       and box.left + box.width <= outer.left + outer.width
                       and box.top + box.height <= outer.top + outer.height)
                   for outer, old in unique):
            unique.append((box, center))
    return [box for box, _ in unique]
