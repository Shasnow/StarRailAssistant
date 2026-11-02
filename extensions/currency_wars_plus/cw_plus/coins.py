"""不依赖 GUI 或 OCR 的金币观测与交易检查。
下文的置信度是 OCR 引擎的分数，绝不是估算概率。
截图、面板状态、日志和恢复由调用方负责。
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Any, Sequence


EXPANDED_COIN_ROI = (0.815, 0.824, 0.89, 0.881)
CLOSED_COIN_ROI = (0.815, 0.824, 0.89, 0.881)
EXPERIENCE_COST_ROI = (0.158, 0.900, 0.185, 0.938)
# 展开商店右侧 D 刷新按钮中的实际价格；余额上方的弯箭头数值是利息。
REFRESH_COST_ROI = (0.846, 0.475, 0.870, 0.515)


@dataclass(frozen=True)
class CoinRoi:
    roi: tuple[float, float, float, float]
    reason: str
    anchored: bool
    # 含已审核的深色轮廓；恢复裁剪可包含图标，数值框不能与它重叠。
    icon_exclusion_right: float | None = None


@dataclass(frozen=True)
class CoinCandidate:
    raw_text: str
    value: int | None
    confidence: float | None
    bounds: tuple[float, float, float, float] | None
    issues: tuple[str, ...] = ()


@dataclass(frozen=True)
class CoinRead:
    value: int | None
    reason: str
    source: str = "unknown"
    confidence: float | None = None
    reliable: bool = False
    candidates: tuple[CoinCandidate, ...] = ()


@dataclass(frozen=True)
class CoinChange:
    accepted: bool | None
    delta: int | None
    reason: str


@dataclass(frozen=True)
class ActionCostRead:
    cost: int
    reason: str
    observation: CoinRead
    free_count: int | None = None
    reliable: bool = False


def _frame_pixels(frame):
    """接受 PIL 图像或遵循 RGB 数组协议的对象，无须导入这两类依赖。"""
    if hasattr(frame, "getpixel"):
        width, height = frame.size
        return width, height, frame.getpixel
    shape = getattr(frame, "shape", ())
    if len(shape) >= 3 and shape[2] >= 3:
        height, width = shape[:2]
        return int(width), int(height), lambda point: frame[point[1], point[0]]
    return None


def coin_roi_evidence(shop_open: bool, frame: Any = None) -> CoinRoi:
    """先定位任一面板的金币图标，再裁剪数字。
    数字位数变化时，图标和金额会一起移动；固定向右裁剪会截掉真实两位或三位金额的首位。
    垂直搜索排除金额上方的利息预估。
    未找到图标锚点时，回退裁剪保留整个金额并报告不确定性。
    输入必须为 RGB；BGR 数组须由调用方转换。
    """
    if type(shop_open) is not bool:
        raise ValueError("shop_open must be a confirmed boolean")
    state = "expanded" if shop_open else "closed"
    fallback = CoinRoi(EXPANDED_COIN_ROI if shop_open else CLOSED_COIN_ROI,
                       state + "_anchor_unknown", False)
    if frame is None:
        return fallback
    pixels = _frame_pixels(frame)
    if pixels is None:
        return fallback
    width, height, pixel = pixels
    if width <= 0 or height <= 0:
        return fallback
    mask = set()
    for y in range(int(height * 0.832), min(height, math.ceil(height * 0.88))):
        for x in range(int(width * 0.815), min(width, math.ceil(width * 0.89))):
            rgb = pixel((x, y))
            if not hasattr(rgb, "__len__") or len(rgb) < 3:
                return fallback
            red, green, blue = (int(channel) for channel in rgb[:3])
            # 观测到的金色像素，不包含白色或黑色的数字字形。
            if red >= 150 and green >= 95 and blue <= 130 and red >= green and green >= blue + 25:
                mask.add((x, y))
    largest = set()
    while mask:
        seed = mask.pop()
        component, pending = {seed}, [seed]
        while pending:
            x, y = pending.pop()
            for dx, dy in ((-1, -1), (0, -1), (1, -1), (-1, 0),
                           (1, 0), (-1, 1), (0, 1), (1, 1)):
                neighbor = (x + dx, y + dy)
                if neighbor in mask:
                    mask.remove(neighbor)
                    component.add(neighbor)
                    pending.append(neighbor)
        if len(component) > len(largest):
            largest = component
    minimum_pixels = max(8, math.ceil(20 * width * height / (1920 * 1080)))
    if len(largest) < minimum_pixels:
        return fallback
    right = max(x for x, _ in largest) + 1
    left = min(x for x, _ in largest)
    top = min(y for _, y in largest)
    bottom = max(y for _, y in largest)
    # 孤立线条或接触金额区域右边界的连通部分不能作为图标。
    if (right - left < max(3, width * 0.004) or bottom - top < max(3, height * 0.006)
            or right >= width * 0.88):
        return fallback
    # 保存的画面中，深色抗锯齿轮廓最多超出金色连通填充区域四个像素。
    # 在 1920 像素宽度下，留出六个像素即可避开该轮廓。
    digit_left = (right + max(1, round(width * 6 / 1920))) / width
    icon_exclusion_right = (right + max(1, round(width * 4 / 1920))) / width
    return CoinRoi((digit_left, 0.824, 0.89, 0.881), state + "_icon_anchor", True,
                   icon_exclusion_right)


def coin_roi(shop_open: bool, frame: Any = None) -> tuple[float, float, float, float]:
    return coin_roi_evidence(shop_open, frame).roi


def coin_recovery_roi(region: CoinRoi, frame: Any) -> CoinRoi:
    """从原始截图向左补回真实像素，不能给已裁掉数字的图片补白。

    扩展范围仍留在余额行内，图标与余额的位置在同一帧上确定。
    缺少图标锚点时保留未知，绝不凭两次同值读数授予可靠性。
    """
    size = getattr(frame, "size", None)
    if (not isinstance(size, (tuple, list)) or len(size) != 2
            or not all(type(value) is int and value > 0 for value in size)):
        return CoinRoi((region.roi[0], 0.818, region.roi[2], 0.890),
                       region.reason + ":anchor_unknown:vertical_fallback", False)
    left = max(EXPANDED_COIN_ROI[0], region.roi[0] - 24 / size[0])
    anchored = (region.anchored and type(region.icon_exclusion_right) in (int, float)
                and math.isfinite(region.icon_exclusion_right)
                and 0 <= region.icon_exclusion_right < region.roi[2])
    return CoinRoi((left, 0.818, region.roi[2], 0.890),
                   region.reason + ("" if anchored else ":anchor_unknown") + ":horizontal_recovery",
                   anchored, region.icon_exclusion_right if anchored else None)


def ground_coin_rows(rows, source_crop, *, kind="coins"):
    """数字边界核实只适用于可读取像素的原图；旧图像适配器沿用原框。"""
    if not callable(getattr(source_crop, "getpixel", None)):
        return rows, {"bounds_source": "ocr", "reason": "source_pixels_unavailable"}
    from .ocr_geometry import ground_crop_rows
    return ground_crop_rows(rows, source_crop, kind=kind)


# Yukki：金币取值须结合原始像素与独立帧的一致性。
def select_coin_read(ocr_results, *, roi_size: tuple[int, int] | None = None,
                     source: str = "unknown", minimum_confidence: float = 0.7,
                     max_digits: int = 3, numeric_x_min: float | None = None) -> CoinRead:
    """优先选择完整的数字框，再考虑被截断或置信度低的 OCR 候选。
    存在冲突或较弱的读数仍保留候选，以便结合其他截图或交易证据核实。
    不会改写首位数字。
    """
    candidates = []
    for item in ocr_results or ():
        issues = []
        try:
            box, raw, score = item
        except (TypeError, ValueError):
            candidates.append(CoinCandidate(str(item), None, None, None, ("malformed_ocr",)))
            continue
        raw = str(raw)
        text = raw.strip()
        value = int(text) if text.isdecimal() else None
        if value is None:
            issues.append("not_numeric")
        elif len(text) > max_digits:
            issues.append("digit_count_unverified")
        try:
            confidence = float(score) if not isinstance(score, bool) else None
            if confidence is not None and (not math.isfinite(confidence) or not 0 <= confidence <= 1):
                confidence = None
        except (TypeError, ValueError, OverflowError):
            confidence = None
        if confidence is None:
            issues.append("confidence_unknown")
        elif confidence < minimum_confidence:
            issues.append("low_confidence")
        bounds = None
        try:
            points = [(float(p[0]), float(p[1])) for p in box]
            if len(points) < 4 or not all(math.isfinite(v) for p in points for v in p):
                raise ValueError("invalid_box")
            bounds = (min(p[0] for p in points), min(p[1] for p in points),
                      max(p[0] for p in points), max(p[1] for p in points))
            if bounds[0] >= bounds[2] or bounds[1] >= bounds[3]:
                raise ValueError("empty_box")
            if roi_size is not None and (bounds[0] <= 0 or bounds[1] <= 0
                    or bounds[2] >= roi_size[0] - 1 or bounds[3] >= roi_size[1] - 1):
                issues.append("box_at_crop_boundary")
            if numeric_x_min is not None and (not math.isfinite(numeric_x_min)
                                              or bounds[0] < numeric_x_min):
                issues.append("icon_overlap")
        except (TypeError, ValueError, IndexError, OverflowError):
            bounds = None
            issues.append("bounds_unknown")
        if "anchor_unknown" in source:
            issues.append("icon_not_excluded")
        candidates.append(CoinCandidate(raw, value, confidence, bounds, tuple(issues)))
    # 扩大裁剪后，图标可能被 OCR 合并成前导数字；这样的候选不参与金额选择。
    numeric = [c for c in candidates if c.value is not None and "icon_overlap" not in c.issues]
    if not numeric:
        return CoinRead(None, "no_numeric_candidate", source, candidates=tuple(candidates))
    best_rank = max(_candidate_rank(candidate) for candidate in numeric)
    best = [candidate for candidate in numeric if _candidate_rank(candidate) == best_rank]
    best_score = best[0].confidence
    if len({c.value for c in best}) > 1:
        return CoinRead(None, "conflicting_candidates", source, best_score,
                        candidates=tuple(candidates))
    selected = best[0]
    return CoinRead(selected.value, "numeric_box_confirmed" if not selected.issues else
                    "uncertain:" + ",".join(selected.issues), source, selected.confidence,
                    not selected.issues, tuple(candidates))


def _candidate_rank(candidate):
    # 几何位置与 OCR 高置信度读数矛盾：该读数包含了被部分裁入的图标。
    return (not any(issue in candidate.issues for issue in
                    ("bounds_unknown", "box_at_crop_boundary")),
            "icon_not_excluded" not in candidate.issues,
            "digit_count_unverified" not in candidate.issues,
            "low_confidence" not in candidate.issues and "confidence_unknown" not in candidate.issues,
            candidate.confidence if candidate.confidence is not None else -1)


def select_action_cost(ocr_results, *, action: str, default_cost: int,
                       roi_size: tuple[int, int] | None = None,
                       source: str = "unknown", minimum_confidence: float = 0.9) -> ActionCostRead:
    """读取经验或刷新按钮内的实际价格，零元必须来自价格本身。
    证据不确定时保留默认预算。
    每次经济输入后重新观测；利息、余额和次数不能用作费用。
    这仅是价格证据，不能证明动作成功。
    """
    if action not in ("experience", "refresh"):
        raise ValueError("Unknown action")
    if type(default_cost) is not int or default_cost < 0:
        raise ValueError("default_cost must be a nonnegative integer")
    observation = select_coin_read(ocr_results, roi_size=roi_size, source=source,
                                   minimum_confidence=minimum_confidence)
    complete = [candidate for candidate in observation.candidates
                if candidate.value is not None and not candidate.issues]
    if len({candidate.value for candidate in complete}) > 1:
        return ActionCostRead(default_cost, "default_cost:conflicting_numeric_values", observation)
    if not observation.reliable or not complete:
        return ActionCostRead(default_cost, "default_cost:" + observation.reason, observation)
    return ActionCostRead(observation.value, "observed_" + action + "_price", observation,
                          reliable=True)


# ssyb：交易方向与实际差额共同决定余额是否可信。
def validate_coin_change(before: int | None, after: int | None, *,
                         expected_spend: int | None = None, expected_income: int | None = None,
                         allow_zero: bool = True) -> CoinChange:
    """验证一次独立的付费或免费动作；证据未知不等于动作失败。"""
    if expected_spend is not None and expected_income is not None:
        raise ValueError("Specify either spend or income")
    for value in (expected_spend, expected_income):
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError("Expected amounts must be nonnegative integers")
    if (type(before) is not int or type(after) is not int or before < 0 or after < 0):
        return CoinChange(None, None, "balance_unknown")
    delta = after - before
    if delta == 0 and allow_zero:
        return CoinChange(True, delta, "zero_consumption_or_income")
    expected = (-expected_spend if expected_spend is not None else expected_income)
    if expected is None:
        return CoinChange(None, delta, "expected_change_unknown")
    if delta == expected:
        return CoinChange(True, delta, "expected_spend" if expected_spend is not None else "expected_income")
    return CoinChange(False, delta, "unexpected_change")


def choose_coin_read(reads: Sequence[CoinRead], *, before: int | None = None,
                     expected_spend: int | None = None, expected_income: int | None = None,
                     allow_zero: bool = True) -> CoinRead:
    """合并读数，优先使用可靠且符合交易变化的证据。
    before 必须是此前验证过的余额，不能是另一条可疑 OCR 结果。
    免费动作仍需要调用方提供界面、角色或经验变化的证据；仅金额相同不能证明输入成功。
    """
    available = [read for read in reads if read.value is not None]
    all_candidates = tuple(c for read in reads for c in read.candidates)
    if not available:
        return CoinRead(None, "no_available_read", candidates=all_candidates)
    def rank(read):
        change = validate_coin_change(before, read.value, expected_spend=expected_spend,
                                      expected_income=expected_income, allow_zero=allow_zero)
        # 明确的支出或收入变化比仅符合零金额变化更有说服力。
        # 完整且不含图标的图像证据，仍强于被截断但恰好符合假定费用的候选。
        # 不能仅因金额差符合预期费用，就提高被截断候选的可信度。
        transaction_rank = (3 if change.accepted is True and change.delta != 0 else
                            2 if change.accepted is True else 1 if change.accepted is None else 0)
        selected = [candidate for candidate in read.candidates if candidate.value == read.value
                    and candidate.confidence == read.confidence]
        evidence = max((_candidate_rank(candidate) for candidate in selected),
                       default=(read.reliable, read.reliable, read.reliable, read.reliable,
                                read.confidence if read.confidence is not None else -1))
        return (*evidence[:3], transaction_rank, read.reliable, *evidence[3:])
    best_rank = max(rank(read) for read in available)
    best = [read for read in available if rank(read) == best_rank]
    if len({read.value for read in best}) > 1:
        return CoinRead(None, "conflicting_readings", candidates=all_candidates)
    selected = best[0]
    change = validate_coin_change(before, selected.value, expected_spend=expected_spend,
                                  expected_income=expected_income, allow_zero=allow_zero)
    reason = selected.reason
    if change.accepted is False:
        reason = "transaction_mismatch:" + reason
    elif change.accepted is True:
        reason = "transaction_compatible:" + reason
    return replace(selected, reason=reason, candidates=all_candidates,
                   reliable=selected.reliable and change.accepted is not False)
