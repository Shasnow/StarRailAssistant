"""Task-scoped visual evidence with opt-in, explicitly labelled calibration.

The companion profile contains reviewed real samples for nine bench and five
shop slots. A separate field_profile.json contains reviewed field glyphs for
the fixed four-front/six-back layout. Five-back layouts remain uncalibrated.
A missing/invalid profile always yields UNKNOWN.
Calibration workflow: capture real window images, crop them with
``crop_slot_template``, save explicitly labelled empty/occupied PNG crops, build
entries with ``make_template_entry``, then validate the resulting JSON profile.
The helper cannot decide whether a human's label is correct; real-game review is
still required. This module never imports SRACore or starts a GUI.

Profile schema (all template paths are relative to the profile directory)::

    {"version": 2, "window_size": [1920, 1080],
     "aspect_tolerance": 0.005, "scale_tolerance": 0.01,
     "slots": [{"area": "in_hand", "index": 0, "position": [0.229, 0.844],
       "relative_box": [-0.02, -0.03, 0.02, 0.03],
       "max_mae": 0.035, "min_margin": 0.025, "require_empty_structure": true,
       "empty": [{"path": "empty.png", "label": "empty", "sha256": "..."}],
       "occupied": [{"path": "occupied.png", "label": "occupied", "sha256": "..."}]}]}

Version 1 retains its previous behaviour unless a slot explicitly enables
``require_empty_structure``. Version 2 requires that flag on every slot so older
readers reject the profile instead of silently omitting the structure check.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

ORIGINAL_LEVEL_ROI = (0.05, 0.815, 0.30, 0.87)
EXPANDED_LEVEL_ROI = (0.015, 0.74, 0.335, 0.965)
# The preparation screen's central counter, excluding its person icon and the
# foreground label. This ROI is independent of the shop level/experience text.
POPULATION_ROI = (0.46, 0.185, 0.54, 0.26)
POPULATION_MIN_CONFIDENCE = 0.9
# The success/failure title begins at screen centre before moving to the top.
BATTLE_RESULT_HEADER_ROI = (0.4, 0.17, 0.6, 0.55)
BATTLE_RESULT_ACTION_ROI = (0.35, 0.77, 0.65, 0.90)
# Reviewed result-page label; callers must authenticate that page before use.
# Preparation-page health has no calibrated default ROI.
RESULT_HEALTH_ROI = (0.30, 0.43, 0.47, 0.50)
FINAL_HEALTH_ROI = (0.43, 0.25, 0.57, 0.30)
FINAL_IDENTITY_ROI = (0.30, 0.31, 0.69, 0.39)
# Every entry point uses the same terminal chain, including its first button.
TERMINAL_STATE_ORDER = {
    "final_settle": 0, "final_summary": 1, "final_next_page": 2, "final_return": 3,
}
TERMINAL_STATES = frozenset(TERMINAL_STATE_ORDER)
CRITICAL_SAMPLE_REASONS = frozenset({"battle_entry_timeout", "result_timeout", "startup_page_not_found",
                                    "preparation_not_ready", "placement_failed", "placement_unknown",
                                    "invalid_backend_layout"})
AREAS = {"on_field", "off_field", "in_hand", "store"}


class VisionStoppedError(InterruptedError):
    """Fallback cancellation when no host stop_check callback was supplied."""


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
    """Require exact squad-health context, confidence and bounded nearby digits.

    Bare values, character HP, levels and experience never authenticate health.
    A single displayed value does not imply its maximum or a terminal outcome.
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
                # Small box overlap is common at adjacent glyph boundaries.
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
    """Keep exact, confident words with complete boxes inside their OCR crop."""
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
    """Accept only a complete, confident n/m counter; never infer a missing zero."""
    readings, confident, text_parts = set(), set(), []
    invalid_range = False
    if isinstance(results, (list, tuple)):
        for entry in results:
            if not isinstance(entry, (list, tuple)) or len(entry) != 3 or not isinstance(entry[1], str):
                continue
            raw = entry[1]
            text_parts.append(raw)
            # Width variants and whitespace retain the exact digits and slash;
            # letter O, bare digits and partial counters must remain UNKNOWN.
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
    """Pure crop of an explicitly supplied real window image; no classification."""
    left, top, right, bottom = _box(position, relative_box)
    width, height = window_image.size
    pixels = (round(left * width), round(top * height), round(right * width), round(bottom * height))
    if pixels[2] - pixels[0] < 8 or pixels[3] - pixels[1] < 8:
        raise ValueError("slot crop must be at least 8 by 8 pixels")
    return window_image.crop(pixels).convert("RGB")


def image_distance(image_a, image_b):
    """Normalized RGB mean absolute error on a fixed, bounded comparison grid."""
    from PIL import Image
    size = (64, 64)
    a = image_a.convert("RGB").resize(size, Image.Resampling.BILINEAR)
    b = image_b.convert("RGB").resize(size, Image.Resampling.BILINEAR)
    data_a, data_b = a.tobytes(), b.tobytes()
    return sum(abs(left - right) for left, right in zip(data_a, data_b)) / (len(data_a) * 255)


def _rgb_grid(image):
    from PIL import Image
    data = image.convert("RGB").resize((64, 64), Image.Resampling.BILINEAR).tobytes()
    return tuple(tuple(data[offset:offset + 3]) for offset in range(0, len(data), 3))


@dataclass(frozen=True)
class EmptyStructure:
    foreground: tuple[tuple[int, tuple[int, int, int]], ...]
    background: tuple[int, ...]


def _empty_structure(image):
    """Require actual template detail; a flat labelled patch is not evidence."""
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
    """Match relative RGB detail at its labelled positions, tolerating small occlusions."""
    pixels = _rgb_grid(crop)
    # Independent channel medians keep small cursor/animation occlusions from
    # shifting the estimated background colour. Uniform colour always has zero
    # relative contrast and therefore cannot satisfy the foreground check.
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
    """Local brightness removes the field's slowly animated blue background."""
    from PIL import Image, ImageFilter
    gray = image.convert("L").resize((64, 96), Image.Resampling.BILINEAR)
    blurred = gray.filter(ImageFilter.GaussianBlur(3))
    return tuple(a - b for a, b in zip(gray.tobytes(), blurred.tobytes()))


def _field_structure(image):
    # Every band must contain positive detail from the reviewed empty emblem.
    # A flat/gradient blue patch cannot serve as a labelled empty template.
    detail = _field_highpass(image)
    bands = tuple(tuple((index, detail[index]) for index in range(band * 1024, (band + 1) * 1024)
                        if detail[index] >= 3) for band in range(6))
    if any(len(band) < 24 for band in bands):
        raise ValueError("field template lacks complete empty-glyph structure")
    return bands


def _matches_field_structure(crop, structure):
    detail = _field_highpass(crop)
    # Check each section, so isolated stars or a small surviving part of a
    # covered emblem cannot authenticate an entire empty deployment slot.
    return all(sum(max(1, expected * 0.4) <= detail[index] <= expected + 6
                   for index, expected in band) >= 0.65 * len(band)
               for band in structure)


def _safe_template_path(base_dir, relative):
    if not isinstance(relative, str) or not relative:
        raise ValueError("template path must be relative")
    base = Path(base_dir).resolve()
    path = (base / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(base) or path.suffix.lower() != ".png":
        raise ValueError("template must be a PNG inside the profile directory")
    return path


def make_template_entry(area: str, index: int, position, relative_box,
                        empty_path: str, occupied_path: str, profile_dir: Path,
                        *, max_mae: float = 0.035, min_margin: float = 0.025,
                        require_empty_structure: bool = False) -> dict:
    """Describe two existing, explicitly labelled PNG crops without writing files."""
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
    # Positive/negative acceptance regions must be separated even at their edges.
    if min(image_distance(a, b) for a in groups["empty"] for b in groups["occupied"]) <= 2 * max_mae + margin:
        raise ValueError("empty and occupied examples are not sufficiently separated")
    structures = tuple(_empty_structure(image) for image in groups["empty"]) if require_structure else ()
    return SlotProfile(entry["area"], index, position, tuple(relative_box),
                       float(max_mae), float(margin), groups["empty"], groups["occupied"],
                       require_structure, structures)


def validate_profile(profile: Mapping[str, Any], base_dir: Path) -> VisionProfile:
    """Load checksum-verified examples; reject missing labels or ambiguous classes."""
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
    """Field glyph profiles are separate from legacy bench/shop calibration."""
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
        # Reject broad crops that could authenticate only surrounding scenery.
        left, top, right, bottom = _box(slot.position, slot.relative_box)
        if not (40 <= (right-left)*1920 <= 70 and 85 <= (bottom-top)*1080 <= 120):
            raise ValueError("field crop must isolate the empty emblem")
        slots[key] = replace(slot, field_structures=tuple(_field_structure(image)
                                                        for image in slot.empty_images))
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
        self._critical_reserve = 0  # Legacy flat sampling keeps its old total cap.
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
        self.last_battle_attempts = []
        self.last_health_attempts = []
        self.last_layout_diagnostics = {}

    def read_backend_layout(self, previous_positions, *, recover=False):
        """Observe a complete row; recovery needs two consecutive stable frames."""
        api = getattr(self, "layout_api", None)
        if api is None:
            from tasks.currency_wars.layout import (LayoutObservation, backend_rectangle_candidates,
                                                   layout_diagnostics, revalidate_backend_layout,
                                                   validate_backend_layout)
        else:
            (LayoutObservation, backend_rectangle_candidates, layout_diagnostics,
             revalidate_backend_layout, validate_backend_layout) = api
        self._check_stop()
        self.last_layout_diagnostics = {}
        window = (self.operator.window_context.width, self.operator.window_context.height)

        def read_once(previous):
            self._check_stop()
            self._backend_support_diagnostics = None
            if recover:
                frame = self.operator.screenshot()
                self._check_stop()
                if frame is None or tuple(frame.size) != tuple(window):
                    return LayoutObservation(False, reason="recovery_window_mismatch"), {}
                boxes = backend_rectangle_candidates(frame, previous_positions=previous)
                complete = validate_backend_layout(boxes, window, previous_positions=previous)
                if complete.valid and len(complete.positions) == 7:
                    observation = (replace(complete, protected_slots=(6,))
                        if self._authenticated_backend_support(frame, complete.positions) else
                        replace(complete, valid=False, reason="backend_support_not_authenticated"))
                elif len(previous) == 7 or self._authenticated_backend_support(frame, ()):
                    observation = replace(complete, valid=False, reason="backend_support_row_incomplete")
                else:
                    observation = (revalidate_backend_layout(boxes, window, previous_positions=previous)
                                   if previous and len(previous) != 7 else complete)
            else:
                boxes = self.operator.rectangle_detect(120, 150, 130, 150,
                    from_x=0.1, from_y=0.52, to_x=0.86, to_y=0.7, trace=False)
                observation = validate_backend_layout(boxes, window, previous_positions=previous)
                if ((observation.reason == "row_boundary_incomplete" and len(boxes) == 6)
                        or observation.valid and len(observation.positions) in (5, 7)
                        or len(previous) == 7):
                    # The external detector misses a support border joined to
                    # its equipment icons. Authenticate the complete visible
                    # seven-slot row and its locked occupant on this frame.
                    capture = getattr(self.operator, "screenshot", None)
                    frame = capture() if callable(capture) else None
                    self._check_stop()
                    if frame is not None and tuple(frame.size) == tuple(window):
                        candidates = backend_rectangle_candidates(frame, previous_positions=previous)
                        complete = validate_backend_layout(candidates, window, previous_positions=previous)
                        if complete.valid and len(complete.positions) == 7:
                            boxes = candidates
                            observation = (replace(complete, protected_slots=(6,))
                                if self._authenticated_backend_support(frame, complete.positions) else
                                replace(complete, valid=False, reason="backend_support_not_authenticated"))
                        elif len(previous) == 7 or self._authenticated_backend_support(frame, ()):
                            observation = replace(complete, valid=False, reason="backend_support_row_incomplete")
                    if observation.valid and len(observation.positions) == 7 and not observation.protected_slots:
                        observation = replace(observation, valid=False, reason="backend_support_not_authenticated")
                    if observation.valid and len(previous) == 7 and len(observation.positions) != 7:
                        observation = replace(observation, valid=False, reason="backend_support_row_incomplete")
            details = layout_diagnostics(boxes, window, previous_positions=previous_positions)
            details.update(evidence=observation.reason, layout_recovery=recover,
                           layout_protected_slots=list(observation.protected_slots))
            if self._backend_support_diagnostics is not None:
                details["layout_support_authentication"] = dict(self._backend_support_diagnostics)
            return observation, details

        try:
            if recover:
                # A missed anchor breaks the evidence streak, but does not
                # consume the whole recovery after only one bad frame.
                # Each accepted slot still needs a real border on both frames.
                previous = None
                saw_valid = False
                last = LayoutObservation(False, reason="layout_unknown")
                for attempt in range(4):
                    if attempt:
                        self.operator.sleep(0.2)
                        self._check_stop()
                    # Keep the original anchors fixed across attempts so
                    # several unstable candidates cannot walk the row away.
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
                            and all(abs(a - b) <= 0.002
                                for old, new in zip(previous.positions, current.positions)
                                for a, b in zip(old, new)))
                        if stable:
                            return previous
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
            if first.changed or first.protected_slots:
                self.operator.sleep(0.2)
                self._check_stop()
                second, second_details = read_once(first.positions)
                self.last_layout_diagnostics.update(layout_second_evidence=second.reason,
                    layout_second_boxes=second_details.get("layout_boxes", []),
                    layout_second_positions=list(second.positions),
                    layout_second_support_authentication=second_details.get("layout_support_authentication"))
                if (not second.valid or second.changed
                        or second.protected_slots != first.protected_slots):
                    return replace(first, valid=False, reason="layout_not_stable")
            return first
        except Exception as error:
            self._failure(error)
            self.last_layout_diagnostics.update(evidence="layout_observation_failed",
                                                error_type=type(error).__name__)
            return LayoutObservation(False, reason="layout_observation_failed")

    def _authenticated_backend_support(self, frame, positions):
        """Match a reviewed support portrait and its lock at the real last border.

        Border geometry alone does not establish occupancy or identity. Both
        checksum-verified source crops must match at one common translation on
        each confirming frame. Equipment badges can extend the detected border
        without moving the portrait: the 1-7 failure moved its centre down 2px.
        """
        diagnostics = {"reason": "invalid_support_geometry", "search_radius_px": 10}
        self._backend_support_diagnostics = diagnostics
        if (positions and len(positions) != 7) or tuple(frame.size) != (1920, 1080):
            return False
        try:
            from PIL import Image
            diagnostics["reason"] = "invalid_support_profile"
            path = self.profile_path.with_name("backend_locked_support.json")
            raw = json.loads(path.read_text(encoding="utf-8"))
            if (raw.get("kind") != "reviewed_locked_backend_support"
                    or raw.get("window_size") != [1920, 1080]
                    or {entry.get("kind") for entry in raw.get("templates", [])} != {"portrait", "lock"}):
                return False
            # An empty positions argument only checks the reviewed support ROI
            # for evidence that a putative five-slot subset is incomplete. It
            # cannot authenticate layout coordinates or grant an NPC slot.
            reference_position = _point(raw["position"])
            position = _point(positions[-1]) if positions else reference_position
            pixel_shift = (round((position[0] - reference_position[0]) * frame.width),
                           round((position[1] - reference_position[1]) * frame.height))
            diagnostics["border_shift_px"] = list(pixel_shift)
            templates = []
            for entry in raw["templates"]:
                self._check_stop()
                asset = _safe_template_path(path.parent, entry["path"])
                if hashlib.sha256(asset.read_bytes()).hexdigest() != entry["sha256"]:
                    return False
                threshold = entry["max_mae"]
                if not _number(threshold) or not 0 < threshold <= 0.035:
                    return False
                with Image.open(asset) as source:
                    template = source.convert("RGB").copy()
                reference_box = _box(reference_position, entry["relative_box"])
                pixels = tuple(round(value * (frame.width if i % 2 == 0 else frame.height))
                               for i, value in enumerate(reference_box))
                if (pixels[2] - pixels[0], pixels[3] - pixels[1]) != template.size:
                    return False
                templates.append((entry["kind"], pixels, template, threshold))
            # Preserve calibrated crop dimensions and appearance thresholds.
            # Only a 10px border-centre correction per axis is allowed, smaller than
            # one card. Portrait and lock cannot select unrelated alignments.
            radius = diagnostics["search_radius_px"]
            offsets = sorted(((dx, dy) for dx in range(-radius, radius + 1)
                              for dy in range(-radius, radius + 1)),
                             key=lambda offset: (abs(offset[0]) + abs(offset[1]), offset))
            diagnostics["reason"] = "portrait_or_lock_not_matched"
            best_score = float("inf")
            for dx, dy in offsets:
                self._check_stop()
                shift_x, shift_y = pixel_shift[0] + dx, pixel_shift[1] + dy
                distances, scores = {}, []
                for kind, pixels, template, threshold in templates:
                    crop_box = (pixels[0] + shift_x, pixels[1] + shift_y,
                                pixels[2] + shift_x, pixels[3] + shift_y)
                    if not (0 <= crop_box[0] < crop_box[2] <= frame.width
                            and 0 <= crop_box[1] < crop_box[3] <= frame.height):
                        break
                    distance = image_distance(frame.crop(crop_box).convert("RGB"), template)
                    distances[kind] = round(distance, 6)
                    scores.append(distance / threshold)
                if len(scores) != len(templates):
                    continue
                score = max(scores)
                if score < best_score:
                    best_score = score
                    diagnostics.update(alignment_offset_px=[dx, dy], distances=distances)
                if score <= 1:
                    diagnostics["reason"] = "portrait_and_lock_matched"
                    return True
            return False
        except Exception as error:
            diagnostics.update(reason="support_authentication_error", error_type=type(error).__name__)
            self._failure(error)
            return False

    def capture_layout_failure(self, reason, metadata=None, *, terminal=False):
        """Keep one bounded history sample per subtype plus the latest failure.

        The fixed latest pair is independent of history quotas, including after
        reopening a run. Terminal evidence has its own fixed pair, so routine
        failures never replace the last failure that actually stopped execution.
        """
        self._check_stop()
        if not isinstance(reason, str) or not reason or len(reason) > 160 or type(terminal) is not bool:
            self.last_sample_reason = "invalid_sample_request"
            return None
        details = dict(self.last_layout_diagnostics)
        if isinstance(metadata, Mapping):
            details.update(metadata)
        details["evidence"] = reason
        if not terminal:
            self.capture_sample("invalid_backend_layout_" + reason[:100], details, critical=True)
        if not self.max_samples:
            self.last_sample_reason = "sampling_disabled"
            return None
        try:
            image = self.operator.screenshot()
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
            if len(encoded) > 8192:
                raise ValueError("sample metadata is too large")
            self.sample_dir.mkdir(parents=True, exist_ok=True)
            image.save(path, format="PNG")
            self._check_stop()
            path.with_suffix(".json").write_text(encoded, encoding="utf-8")
            self.last_sample_reason = "captured_latest"
            return path
        except Exception as error:
            self.last_sample_reason = "capture_error:" + type(error).__name__
            self._failure(error)
            return None

    @staticmethod
    def _sample_metadata(metadata):
        allowed = {"area", "index", "position", "roi", "evidence", "ocr_attempts", "profile_status", "error_type",
                   "source_area", "source_index", "target_area", "target_index", "source_position", "target_position",
                   "source_name", "target_name", "observed_source_name", "observed_target_name", "layout_positions",
                   "layout_boxes", "layout_version", "snapshot_revision", "action_result", "outcome", "state",
                   "layout_centers", "layout_gaps", "layout_median_gap", "layout_candidate_count",
                   "previous_layout_positions", "layout_window_size", "layout_recovery", "layout_second_evidence",
                   "layout_second_boxes", "layout_second_positions", "layout_protected_slots",
                   "layout_support_authentication", "layout_second_support_authentication", "population_reason"}
        payload = {key: value for key, value in (metadata.items() if isinstance(metadata, Mapping) else ()) if key in allowed}
        if "ocr_attempts" in payload:
            attempts = payload["ocr_attempts"]
            payload["ocr_attempts"] = [
                {key: value for key, value in attempt.items()
                 if key in {"method", "roi", "level", "current", "maximum", "capacity", "text", "reason",
                            "frame_size", "scores"}}
                for attempt in (attempts[:3] if isinstance(attempts, (list, tuple)) else ()) if isinstance(attempt, Mapping)]
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

    def _engine_ocr(self, image, *, minimum_confidence=None):
        self._check_stop()
        output = self.operator.ocr_engine(image, use_det=True, use_cls=False, use_rec=True)
        self._check_stop()
        if hasattr(output, "txts"):
            if output.txts is None:
                return None
            threshold = (getattr(self.operator, "ocr_confidence", 0.7)
                         if minimum_confidence is None else minimum_confidence)
            return [(box.tolist() if hasattr(box, "tolist") else box, text, float(score))
                    for box, text, score in zip(output.boxes, output.txts, output.scores)
                    if (score > threshold if minimum_confidence is None else score >= threshold)]
        if isinstance(output, tuple) and len(output) == 2:
            return output[0]  # Older RapidOCR tuple output.
        return output if isinstance(output, list) else None

    def read_population(self, *, enhance=False) -> PopulationObservation:
        """Require two independent, agreeing frames, with at most two OCR calls.

        This only reads the counter. The caller must verify the preparation page
        before using a zero as evidence that deployment slots are empty.
        """
        answers, attempts = [], []
        frame_sizes = []
        has_engine = callable(getattr(self.operator, "ocr_engine", None))
        for frame in range(2):
            self._check_stop()
            mode = ("population_contrast_2x" if enhance else "population_2x") if has_engine else (
                "population_gray" if enhance else "population_color")
            frame_size = None
            try:
                if has_engine:
                    from PIL import Image, ImageOps
                    image = self.operator.screenshot(**self._roi_args(POPULATION_ROI))
                    self._check_stop()
                    image = image.convert("RGB")
                    frame_size = image.size
                    frame_sizes.append(frame_size)
                    if enhance:
                        image = ImageOps.autocontrast(image.convert("L")).convert("RGB")
                    # Use identical preprocessing on each NEW frame. The raw
                    # first frame frequently missed a counter that 2x reads.
                    image = image.resize((image.width * 2, image.height * 2), Image.Resampling.LANCZOS)
                    # Collect raw evidence once; keep low-confidence noise out
                    # of the decision while retaining it in diagnostics below.
                    results = self._engine_ocr(image, minimum_confidence=0.0)
                else:
                    # Keep raw OCR evidence; confidence and population range
                    # are checked by parse_population below.
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
                answers.append(answer)
                attempts.append({"method": mode, "roi": list(POPULATION_ROI),
                                 "frame_size": list(frame_size) if frame_size else None,
                                 "current": answer.current, "capacity": answer.capacity,
                                 "text": answer.raw_text, "reason": answer.reason,
                                 "scores": [float(row[2]) for row in (results or ())
                                            if isinstance(row, (list, tuple)) and len(row) == 3
                                            and _number(row[2])][:16]})
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
        self.capture_sample("unknown_population", {"ocr_attempts": attempts, "roi": list(POPULATION_ROI),
                                                   "population_reason": reason})
        return PopulationObservation(None, None, "two_population_frames", reason, raw_text)

    def _terminal_template_point(self, frame, name):
        """Match a reviewed action template against this exact result frame."""
        try:
            import cv2
            import numpy as np
        except ImportError:
            # Without the template runtime, terminal actions stay unavailable.
            # This must not disable ordinary, fully authenticated OCR controls.
            return None
        from PIL import Image

        path = Path(__file__).resolve().parents[2] / "resources/img/currency_wars" / name
        if abs(frame.width / frame.height - 16 / 9) > 0.02 or not path.is_file():
            return None
        with Image.open(path) as source:
            template = source.convert("RGB")
        scale = frame.width / 1920
        if abs(scale - 1) > 0.001:
            template = template.resize((max(1, round(template.width * scale)),
                                        max(1, round(template.height * scale))))
        x, y, right, bottom = (round(v * (frame.width if i % 2 == 0 else frame.height))
                               for i, v in enumerate(BATTLE_RESULT_ACTION_ROI))
        region = cv2.cvtColor(np.asarray(frame.crop((x, y, right, bottom))), cv2.COLOR_RGB2GRAY)
        pattern = cv2.cvtColor(np.asarray(template), cv2.COLOR_RGB2GRAY)
        if pattern.shape[0] > region.shape[0] or pattern.shape[1] > region.shape[1]:
            return None
        _, score, _, point = cv2.minMaxLoc(cv2.matchTemplate(region, pattern, cv2.TM_CCOEFF_NORMED))
        if not math.isfinite(score) or score < 0.90:
            return None
        return ((x + point[0] + template.width / 2) / frame.width,
                (y + point[1] + template.height / 2) / frame.height)

    def read_battle_screen(self, frame=None) -> BattleScreenObservation:
        """Read title/action from one frame; a terminal template allows one extra identity OCR.

        A result title authenticates completed combat even while rewards animate.
        Controls only receive a point when their own exact label and box exist on
        that same frame; an isolated action label never authenticates a result.
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
            self._check_stop()
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
            # Later terminal pages have no combat title. Authenticate their own
            # exact action label and template, never a stored pending click.
            action_labels = {text for text, _ in regions[1][0]}
            # This is a finished run awaiting an explicit settlement click,
            # not a reward animation that will eventually show Continue.
            # "挑战结束" carries no win/loss evidence of its own.
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
            # The real final screenshot's action OCR reads only “下一”. The
            # strong template plus two summary labels authenticate that page;
            # an isolated NEXT_STEP (also used during startup) is insufficient.
            point = self._terminal_template_point(frame, "next_step.png")
            if point is not None:
                pixels = tuple(round(v * (width if i % 2 == 0 else height))
                               for i, v in enumerate(FINAL_IDENTITY_ROI))
                crop = frame.crop(pixels)
                lines, raw = _battle_result_lines(self._engine_ocr(crop, minimum_confidence=0.9), crop.size)
                self._check_stop()
                attempts.append({"method": "final_identity", "roi": list(FINAL_IDENTITY_ROI),
                                 "text": raw, "reason": "summary_labels"})
                if {"对局评价", "当前职级"} <= {text for text, _ in lines}:
                    return BattleScreenObservation("final_summary", None, None,
                        "same_frame_final_header_labels_and_next_step", (raw_text + " | " + raw)[:480],
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

    def read_squad_health(self, roi=None) -> HealthObservation:
        """Read only an explicitly configured label ROI, with two agreeing frames.

        No default preparation ROI is guessed. ``RESULT_HEALTH_ROI`` is opt-in
        after the caller authenticates the result page; it is not a page detector.
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
            # The reviewed terminal label includes a heart glyph. Upscaling
            # merges its label box over the digits; keep native crops for both
            # independent terminal frames instead of weakening box validation.
            upscale = has_engine and frame == 1 and tuple(roi) != FINAL_HEALTH_ROI
            method = "health_2x" if upscale else "health_color"
            try:
                size = None
                if has_engine:
                    from PIL import Image
                    image = self.operator.screenshot(**self._roi_args(roi))
                    self._check_stop()
                    image = image.convert("RGB")
                    if upscale:
                        image = image.resize((image.width * 2, image.height * 2), Image.Resampling.LANCZOS)
                    size = image.size
                    # Preserve low-confidence conflicts for the pure parser.
                    rows = self._engine_ocr(image, minimum_confidence=0.0)
                else:
                    rows = self.operator.ocr(**self._roi_args(roi), grayscale=False, confidence=0.0, trace=False)
                    context = getattr(self.operator, "window_context", None)
                    width, height = getattr(context, "width", None), getattr(context, "height", None)
                    if _number(width) and _number(height) and width > 0 and height > 0:
                        size = (round(roi[2] * width) - round(roi[0] * width),
                                round(roi[3] * height) - round(roi[1] * height))
                self._check_stop()
                answer = parse_squad_health(rows, image_size=size, evidence=method)
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
        """At most three attempts; population and bare digits remain parser-rejected."""
        attempts = []
        last = parse_shop_level(None)
        modes = (("original_gray", ORIGINAL_LEVEL_ROI), ("expanded_color", EXPANDED_LEVEL_ROI),
                 ("expanded_2x", EXPANDED_LEVEL_ROI))
        for mode, roi in modes:
            self._check_stop()
            try:
                if mode == "expanded_2x":
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
                    self.last_level_attempts = attempts
                    return last
            except Exception as error:
                self._failure(error)
                attempts.append({"method": mode, "reason": type(error).__name__})
        self.last_level_attempts = attempts
        self.capture_sample("unknown_level", {"ocr_attempts": attempts, "roi": list(EXPANDED_LEVEL_ROI)})
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

    def _matching_field_profile(self, area, index, position, selected):
        """Select only an explicitly reviewed layout at its calibrated anchor."""
        slot = selected.slots.get((area, index)) if selected is not None else None
        if slot is not None and all(abs(a - b) <= 0.002 for a, b in zip(position, slot.position)):
            return selected
        if area != "off_field":
            return selected
        self._check_stop()
        path = self.profile_path.with_name("field_profile_locked_support.json")
        try:
            stat = path.stat()
            if stat.st_size > 256 * 1024:
                return selected
            stamp = stat.st_mtime_ns, stat.st_size
            cached = getattr(self, "_support_field_profile", None)
            if cached is None or getattr(self, "_support_field_stamp", None) != stamp:
                cached = validate_field_profile(json.loads(path.read_text(encoding="utf-8")), path.parent)
                self._support_field_profile = cached
                self._support_field_stamp = stamp
            slot = cached.slots.get((area, index))
            if slot is not None and all(abs(a - b) <= 0.002 for a, b in zip(position, slot.position)):
                return cached
        except Exception as error:
            self._failure(error)
        return selected

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
                    and _matches_field_structure(crop, structure)
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
        """Require the reviewed lock silhouette, not merely a dark rectangle."""
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
        """Authenticate unavailable bench slots on two fresh, matching frames.

        Absence of a match means UNKNOWN, never an available slot. A later
        unlocked slot must be classified again by the normal vacancy reader.
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
        """Classify several slots from the same two calibrated window frames.

        Positions may be an indexed sequence or an index-to-position mapping.
        Each slot retains its own unknown result; occupancy does not establish
        a character's identity. Callers must authenticate the visible page.
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
                for index, (selected, slot, position) in candidates.items():
                    self._check_stop()
                    try:
                        if not self._window_matches(image, selected):
                            observed[index].append(None)
                            reasons[index] = "window_profile_mismatch"
                            continue
                        anchor = slot.position if slot.field_structures else position
                        crop = crop_slot_template(image, anchor, slot.relative_box)
                        observed[index].append(self._classify(crop, slot))
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
            profile = self._matching_field_profile(area, index, position, profile)
            slot = profile.slots.get((area, index))
            if slot is None or any(abs(a - b) > 0.002 for a, b in zip(position, slot.position)):
                self.last_slot_reason = "uncalibrated_slot"
                self.capture_sample("uncalibrated_slot", {"area": area, "index": index, "position": position})
                return None
            answers = []
            for frame in range(2):
                self._check_stop()
                image = self.operator.screenshot()
                self._check_stop()
                if not self._window_matches(image, profile):
                    self.last_slot_reason = "window_profile_mismatch"
                    self.capture_sample("window_profile_mismatch", {"area": area, "index": index})
                    return None
                # Geometry is checked above; field glyph sampling then uses the
                # reviewed fixed anchor, avoiding contour-centre pixel jitter.
                anchor = slot.position if slot.field_structures else position
                crop = crop_slot_template(image, anchor, slot.relative_box)
                answer = self._classify(crop, slot)
                if answer is None:
                    self.last_slot_reason = "ambiguous_slot"
                    self.capture_sample("ambiguous_slot", {"area": area, "index": index, "position": position})
                    return None
                answers.append(answer)
                if frame == 0:
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
        """Select a bounded session/run directory without deleting prior samples.

        Reopening the same scope preserves memory and on-disk quotas. Omitting
        this API retains legacy flat-directory/max_samples behaviour. The root
        task owns real session/run identifiers; this reader does not infer a game.
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
                       critical: bool = False) -> Path | None:
        """Capture the game window within run/reason quotas and critical reserve.

        Failed capture attempts consume their quota too. ``last_sample_reason``
        explains every None return, so an old directory cap is never silent.
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
            image = self.operator.screenshot()
            self._check_stop()
            if image is None:
                self.last_sample_reason = "screenshot_unavailable"
                return None
            self.sample_dir.mkdir(parents=True, exist_ok=True)
            path = self.sample_dir / f"{time.time_ns()}_{safe_reason}.png"
            payload.update(reason=str(reason)[:80], window_size=list(image.size),
                           profile_status=self.profile_status, image_file=path.name,
                            calibration_status="unlabelled_requires_review")
            if self._sample_scope is not None:
                payload.update(session_id=self._sample_scope[0], run_id=self._sample_scope[1], critical=critical)
            encoded = json.dumps(payload, ensure_ascii=False, indent=2)
            if len(encoded) > 8192:
                raise ValueError("sample metadata is too large")
            image.save(path, format="PNG")
            self._check_stop()
            path.with_suffix(".json").write_text(encoded, encoding="utf-8")
            self.last_sample_reason = "captured"
            return path
        except Exception as error:
            self.last_sample_reason = "capture_error:" + type(error).__name__
            self._failure(error)
            return None
