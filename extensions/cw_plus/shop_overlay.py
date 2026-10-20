"""使用一张客户区截图认证商店概率对话框。
本模块不截图、不运行 OCR，也不发送输入。
调用方必须对同一帧的 SHOP_PROBABILITY_TITLE_ROI 执行 OCR，并在点击返回点后重新观测页面。
坐标不包含窗口边框。
猜测标题、任意关闭符号或仅文本匹配均不能授权点击。
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re


SHOP_PROBABILITY_TITLE_ROI = (0.195, 0.220, 0.455, 0.278)
_CLOSE_ROI = (0.766, 0.224, 0.795, 0.273)


@dataclass(frozen=True)
class ShopProbabilityOverlayObservation:
    matched: bool
    close_point: tuple[float, float] | None
    evidence: str


@dataclass(frozen=True)
class ShopProbabilityPanelObservation:
    image: object
    frame: object
    present: bool


def _bounds(size, roi):
    width, height = size
    return tuple(round(value * scale) for value, scale in zip(roi, (width, height, width, height)))


def _pixels(image):
    # Pillow 12.2 替换了 getdata；较旧的打包运行时仍提供该方法。
    method = getattr(image, "get_flattened_data", None)
    return method() if callable(method) else image.getdata()


def _fraction(image, roi, predicate):
    patch = image.crop(_bounds(image.size, roi))
    return sum(predicate(*pixel) for pixel in _pixels(patch)) / (patch.width * patch.height)


def _exact_title(results, size):
    """仅接受其独立裁剪区域内完整且高置信度的标题。"""
    if not isinstance(results, (list, tuple)):
        return False
    for entry in results[:24]:
        if not isinstance(entry, (list, tuple)) or len(entry) != 3:
            continue
        box, label, score = entry
        if not isinstance(label, str) or re.sub(r"\s+", "", label) != "商店刷新概率":
            continue
        if isinstance(score, bool):
            continue
        try:
            confidence = float(score)
            if not math.isfinite(confidence) or not 0.95 <= confidence <= 1:
                continue
            box = box.tolist() if hasattr(box, "tolist") else box
            if not isinstance(box, (list, tuple)) or len(box) != 4:
                continue
            if any(not isinstance(point, (list, tuple)) or len(point) != 2
                   or any(isinstance(value, bool) for value in point) for point in box):
                continue
            points = [(float(x), float(y)) for x, y in box]
            if any(not math.isfinite(x) or not math.isfinite(y)
                   or not 0 <= x <= size[0] or not 0 <= y <= size[1] for x, y in points):
                continue
            xs, ys = zip(*points)
            if max(xs) - min(xs) < size[0] * 0.20 or max(ys) - min(ys) < size[1] * 0.15:
                continue
        except (TypeError, ValueError, OverflowError):
            continue
        return True
    return False


def _close_cross(image):
    """在已审核标题区 ROI 中查找完整的四臂对角关闭符号。"""
    left, top, right, bottom = _bounds(image.size, _CLOSE_ROI)
    patch = image.crop((left, top, right, bottom))
    mask = [(index % patch.width, index // patch.width)
            for index, (r, g, b) in enumerate(_pixels(patch))
            if min(r, g, b) >= 180 and max(r, g, b) - min(r, g, b) <= 55]
    if not mask:
        return None
    xs, ys = zip(*mask)
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    width, height = x1 - x0, y1 - y0
    if not (0.014 <= width / image.width <= 0.025
            and 0.025 <= height / image.height <= 0.044
            and 0.8 <= width / height <= 1.25):
        return None
    # 拒绝被截断符号、加号、斜线、矩形及附近的白色文本。
    if x0 <= 0 or y0 <= 0 or x1 >= patch.width - 1 or y1 >= patch.height - 1:
        return None
    points = [((x - x0) / width, (y - y0) / height) for x, y in mask]
    diagonal = sum(min(abs(x - y), abs(x + y - 1)) <= 0.13 for x, y in points)
    if diagonal / len(points) < 0.88 or not 0.08 <= len(mask) / (width * height) <= 0.40:
        return None
    for x_sign, y_sign in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        if sum((x - 0.5) * x_sign > 0.20 and (y - 0.5) * y_sign > 0.20
               for x, y in points) < len(points) * 0.10:
            return None
    return ((left + (x0 + x1) / 2) / image.width,
            (top + (y0 + y1) / 2) / image.height)


def shop_probability_panel_present(image) -> bool:
    """标题 OCR 前检查必要面板结构；不会因此授权任何关闭输入。"""
    return observe_shop_probability_panel(image).present


def observe_shop_probability_panel(image) -> ShopProbabilityPanelObservation:
    """结构和 RGB 转换只属于传入的这一张帧，不跨截图复用。"""
    frame = None
    try:
        width, height = image.size
        if width < 640 or height < 360 or abs(width / height - 16 / 9) > 0.02:
            return ShopProbabilityPanelObservation(image, frame, False)
        frame = image.convert("RGB")
        blue = lambda r, g, b: b > 140 and b - r > 50 and b - g > 40
        dark = lambda r, g, b: max(r, g, b) <= 70
        present = (_fraction(frame, (0.45, 0.222, 0.745, 0.273), blue) >= 0.88
                and _fraction(frame, (0.195, 0.258, 0.38, 0.276), blue) >= 0.70
                and _fraction(frame, (0.205, 0.301, 0.795, 0.759), dark) >= 0.78)
        return ShopProbabilityPanelObservation(image, frame, present)
    except (AttributeError, TypeError, ValueError, ZeroDivisionError):
        return ShopProbabilityPanelObservation(image, frame, False)


# Yukki：概率弹窗的标题和关闭控件须共同通过当前帧检查。
def detect_shop_probability_overlay(image, title_results, *, panel_observation=None) -> ShopProbabilityOverlayObservation:
    """仅为已认证的概率表返回关闭点。
    image 是完整的 PIL 客户区截图，游戏视口为 16:9。
    title_results 使用 RapidOCR 的四边形、文本、置信度格式，坐标相对于由 SHOP_PROBABILITY_TITLE_ROI 取整得到的裁剪区域。
    OCR 由调用方提供；本辅助函数只使用截图已有的 PIL 方法。
    """
    def rejected(reason):
        return ShopProbabilityOverlayObservation(False, None, reason)

    try:
        width, height = image.size
        if (width < 640 or height < 360 or abs(width / height - 16 / 9) > 0.02):
            return rejected("probability_viewport_unsupported")
        title_box = _bounds(image.size, SHOP_PROBABILITY_TITLE_ROI)
        if not _exact_title(title_results, (title_box[2] - title_box[0], title_box[3] - title_box[1])):
            return rejected("probability_exact_title_missing")
        panel = panel_observation
        if not isinstance(panel, ShopProbabilityPanelObservation) or panel.image is not image:
            panel = observe_shop_probability_panel(image)
        frame = panel.frame if panel.frame is not None else image.convert("RGB")
        white = lambda r, g, b: min(r, g, b) >= 190 and max(r, g, b) - min(r, g, b) <= 45
        if not 0.015 <= _fraction(frame, SHOP_PROBABILITY_TITLE_ROI, white) <= 0.35:
            return rejected("probability_title_pixels_missing")
        # 两条独立标题带及完整的黑色十级概率表共同校验，
        # 防止 OCR 幻觉或过期标题授权点击。
        if not panel.present:
            return rejected("probability_panel_structure_missing")
        # 绿、蓝、紫、金色列标题是该概率表的特征。
        columns = (
            ((0.433, 0.308, 0.477, 0.336), lambda r, g, b: g > 110 and r < g * 0.85 and b < g * 0.95),
            ((0.533, 0.308, 0.577, 0.336), lambda r, g, b: b > 130 and b > r * 1.3 and b > g * 1.1),
            ((0.633, 0.308, 0.677, 0.336), lambda r, g, b: r > 90 and b > 130 and b > g * 1.2 and r > g * 1.1),
            ((0.731, 0.308, 0.774, 0.336), lambda r, g, b: r > 150 and g > 80 and r > g and b < g * 0.8),
        )
        if any(_fraction(frame, roi, predicate) < 0.04 for roi, predicate in columns):
            return rejected("probability_columns_missing")
        close_point = _close_cross(frame)
        if close_point is None:
            return rejected("probability_close_cross_missing")
        return ShopProbabilityOverlayObservation(True, close_point, "probability_exact_title_table_and_cross")
    except (AttributeError, TypeError, ValueError, ZeroDivisionError):
        return rejected("probability_frame_invalid")
