"""Authenticate the shop-probability dialog from one client screenshot.

This module never captures a screen, runs OCR or sends input. The caller must
OCR ``SHOP_PROBABILITY_TITLE_ROI`` from the same frame, and must re-observe the
page after clicking a returned point. Coordinates exclude the window border.
No guessed title, arbitrary close glyph or text-only match authorizes a click.
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


def _bounds(size, roi):
    width, height = size
    return tuple(round(value * scale) for value, scale in zip(roi, (width, height, width, height)))


def _pixels(image):
    # Pillow 12.2 replaces getdata; older bundled runtimes still expose it.
    method = getattr(image, "get_flattened_data", None)
    return method() if callable(method) else image.getdata()


def _fraction(image, roi, predicate):
    patch = image.crop(_bounds(image.size, roi))
    return sum(predicate(*pixel) for pixel in _pixels(patch)) / (patch.width * patch.height)


def _exact_title(results, size):
    """Only a complete, confident title inside its own crop is accepted."""
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
    """Find the complete four-armed diagonal glyph in the reviewed header ROI."""
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
    # Reject clipped glyphs, a plus, a slash, rectangles and nearby white text.
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


def detect_shop_probability_overlay(image, title_results) -> ShopProbabilityOverlayObservation:
    """Return a close point only for the authenticated probability table.

    ``image`` is a full PIL client screenshot, with a 16:9 game viewport.
    ``title_results`` uses RapidOCR's (quadrilateral, text, confidence) format,
    relative to a crop rounded from ``SHOP_PROBABILITY_TITLE_ROI``. The caller
    supplies OCR; this helper needs only the screenshot's existing PIL methods.
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
        frame = image.convert("RGB")
        blue = lambda r, g, b: b > 140 and b - r > 50 and b - g > 40
        dark = lambda r, g, b: max(r, g, b) <= 70
        white = lambda r, g, b: min(r, g, b) >= 190 and max(r, g, b) - min(r, g, b) <= 45
        if not 0.015 <= _fraction(frame, SHOP_PROBABILITY_TITLE_ROI, white) <= 0.35:
            return rejected("probability_title_pixels_missing")
        # Two separate header bands and the complete black ten-level table
        # keep an OCR hallucination or stale title from authorizing a click.
        if (_fraction(frame, (0.45, 0.222, 0.745, 0.273), blue) < 0.88
                or _fraction(frame, (0.195, 0.258, 0.38, 0.276), blue) < 0.70
                or _fraction(frame, (0.205, 0.301, 0.795, 0.759), dark) < 0.78):
            return rejected("probability_panel_structure_missing")
        # The green/blue/purple/gold column headers are specific to this table.
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
