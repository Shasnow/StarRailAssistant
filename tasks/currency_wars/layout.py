"""Pure geometry checks; accepted rectangles never prove slot occupancy."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import median
from typing import Any, Sequence
from types import SimpleNamespace

BACKEND_LAYOUT_ROI = (0.1, 0.52, 0.86, 0.7)


@dataclass(frozen=True)
class LayoutObservation:
    valid: bool
    positions: tuple[tuple[float, float], ...] = ()
    changed: bool = False
    reason: str = "layout_unknown"
    boxes: tuple[tuple[float, float, float, float], ...] = ()
    protected_slots: tuple[int, ...] = ()


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_backend_layout(boxes: Sequence[Any], window_size, *,
                            previous_positions=(), expected_count=None) -> LayoutObservation:
    """Validate one complete, centred row of five, six or seven rectangles.

    The caller must also require stable frames before replacing its layout and
    must invalidate observations when ``changed`` is true. The row-centre check
    rejects a contiguous five-box subset caused by losing either edge of a six
    slot row; gap checks reject interior omissions. Dimensions are scaled from
    the host's 1920x1080 rectangle detector, not calibrated EMPTY templates.
    """
    def reject(reason, rectangles=()):
        return LayoutObservation(False, reason=reason, boxes=tuple(rectangles))

    if (not isinstance(window_size, (list, tuple)) or len(window_size) != 2
            or not all(_finite(v) and v > 0 for v in window_size)):
        return reject("invalid_window_size")
    width, height = window_size
    if abs(width / height - 1920 / 1080) > 0.02:
        return reject("unsupported_window_aspect")
    if expected_count is not None and (type(expected_count) is not int or expected_count not in (5, 6, 7)):
        return reject("invalid_expected_count")
    if not isinstance(boxes, (list, tuple)) or len(boxes) not in (5, 6, 7):
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
    if not 0.058 <= step / width <= 0.086 or any(abs(gap - step) > step * 0.12 for gap in gaps):
        return reject("non_contiguous_slots", rectangles)
    if abs((centers[0][0] + centers[-1][0]) / (2 * width) - 0.5) > 0.015:
        return reject("row_boundary_incomplete", rectangles)
    positions = tuple((x / width, y / height) for x, y in centers)
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
    """Bounded geometry evidence, including rejected/missing-slot candidates."""
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
    """Require a fresh rectangle at every old anchor and the original full-row gate.

    Old coordinates only locate candidate clusters; they never synthesize boxes
    or prove occupancy. Nested contours at the same anchor are de-duplicated;
    competing distinct centres, missing anchors and shifted rows are rejected.
    Callers additionally require two independent stable frames.
    """
    if (not isinstance(previous_positions, (list, tuple)) or len(previous_positions) not in (5, 6, 7)
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
        # Keep the outermost actual contour; never fill a missing rectangle.
        selected.append(max(local, key=lambda item: item[0].width * item[0].height)[0])
    return validate_backend_layout(selected, window_size, previous_positions=previous_positions,
                                   expected_count=len(previous_positions))


def backend_probe_positions(boxes, window_size):
    """Propose missing-border search locations from fresh visible row anchors.

    These positions never certify a layout: every proposed slot must still
    produce its own actual border and pass full-row geometry on two frames.
    """
    width, height = window_size
    centers = sorted(((b.left + b.width / 2) / width, (b.top + b.height / 2) / height)
                     for b in boxes)
    unique = []
    for point in centers:
        if not any(max(abs(point[i] - old[i]) for i in (0, 1)) <= 0.002 for old in unique):
            unique.append(point)
    if not 4 <= len(unique) <= 7:
        return ()
    if (max(y for _, y in unique) - min(y for _, y in unique) > 0.008
            or abs(median(y for _, y in unique) - 0.62) > 0.015):
        return ()
    gaps = [b[0] - a[0] for a, b in zip(unique, unique[1:])]
    step = median(gaps)
    if not 0.058 <= step <= 0.086:
        return ()
    multiples = [round(gap / step) for gap in gaps]
    if (any(n not in (1, 2) or abs(gap - n * step) > step * 0.12
            for gap, n in zip(gaps, multiples)) or sum(multiples) + 1 not in (5, 6, 7)):
        return ()
    row_center = (unique[0][0] + unique[-1][0]) / 2
    extension = (len(unique) == 6 and sum(multiples) == 5
                 and abs(row_center + step / 2 - 0.5) <= 0.008)
    both_edges = (len(unique) == 5 and sum(multiples) == 4
                  and abs(row_center - 0.5) <= 0.008)
    if abs(row_center - 0.5) > 0.015 and not extension:
        return ()
    probes = [unique[0]]
    for left, right, n in zip(unique, unique[1:], multiples):
        for part in range(1, n + 1):
            probes.append(tuple(left[i] + (right[i] - left[i]) * part / n for i in (0, 1)))
    if extension:
        # Search for a real right-hand border. A proposed seventh anchor alone
        # never authenticates either the layout or the protected occupant.
        probes.append((unique[-1][0] + step, unique[-1][1]))
    elif both_edges:
        # A genuine five-slot row and the middle five of a seven-slot row
        # share these centres. Search both sides without inventing borders.
        probes.insert(0, (unique[0][0] - step, unique[0][1]))
        probes.append((unique[-1][0] + step, unique[-1][1]))
    return tuple(probes)


def backend_rectangle_candidates(image, *, previous_positions=()):
    """Alternative contour retrieval on one real full-window screenshot.

    RETR_LIST retains card borders nested inside a connected exterior contour.
    This only generates evidence; revalidate_backend_layout still rejects any
    missing anchor or non-contiguous row. OpenCV is an existing runtime dependency.
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
    # Equipment icons can connect an occupied card to an exterior contour and
    # hide its bounding rectangle even in RETR_LIST. At a missing old anchor,
    # require real top/bottom lines plus continuous evidence on both side edges.
    # No missing border is inferred from the old coordinate.
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
        if lines is None:
            continue
        horizontal = []
        for lx1, ly1, lx2, ly2 in lines[:, 0]:
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
        if candidates:
            boxes.append(min(candidates, key=lambda box: abs((box.left + box.width / 2) / width - px)
                             + abs((box.top + box.height / 2) / height - py)))
    # RETR_LIST returns both sides of one border. Keep actual contours only;
    # full-row validation still rejects a genuinely missing or displaced slot.
    unique = []
    for box in sorted(boxes, key=lambda b: b.width * b.height, reverse=True):
        center = ((box.left + box.width / 2) / width, (box.top + box.height / 2) / height)
        if not any(max(abs(center[i] - old[i]) for i in (0, 1)) <= 0.002 for _, old in unique):
            unique.append((box, center))
    return [box for box, _ in unique]
