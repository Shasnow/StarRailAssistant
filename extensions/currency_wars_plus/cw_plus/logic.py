"""货币战争的观测与配置纯辅助函数。
本模块刻意不依赖 GUI、OCR 引擎、游戏核心或可变注册表。
调用方提供白名单查询，并负责所有观测状态。
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping, Sequence

CharacterLookup = Callable[[str], Any | None]

# 仅收录实际观测到的明确 OCR 错误；规范名称仍须经白名单批准。
_OCR_NAME_ALIASES = {"干冶·刃": "千冶·刃"}


class SlotState(str, Enum):
    UNKNOWN = "unknown"
    EMPTY = "empty"
    KNOWN = "known"
    LOCKED = "locked"  # 明确不可用；既不是占位角色，也不是空位。


@dataclass(frozen=True)
class SlotObservation:
    slot_index: int
    state: SlotState
    character: Any | None = None
    occupied: bool | None = None
    evidence: str = ""
    revision: int = 0
    stars: int | None = None


class ShopState(str, Enum):
    UNKNOWN = "unknown"
    READY = "ready"
    FULL = "full"
    EMPTY = "empty"


@dataclass(frozen=True)
class ShopCard:
    slot_index: int
    character: Any
    target: tuple[float, float]
    raw_text: str = ""
    price: int | None = None
    price_evidence: str = ""


@dataclass(frozen=True)
class ShopObservation:
    state: ShopState
    cards: tuple[ShopCard, ...] = ()
    reason: str = ""


class ActionResult(str, Enum):
    CONFIRMED = "confirmed"
    FAILED = "failed"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True)
class SellResult:
    result: ActionResult
    attempted: int = 0
    confirmed: int = 0
    reason: str = ""


@dataclass(frozen=True)
class ShoppingResult:
    result: ActionResult
    attempted_purchases: int = 0
    confirmed_purchases: int = 0
    refreshes: int = 0
    experience_purchases: int = 0
    reason: str = ""


@dataclass(frozen=True)
class _Token:
    text: str
    box: tuple[float, float, float, float] | None


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _tokens(results: Any) -> tuple[list[_Token], bool]:
    """返回清理后的文本项，以及是否遇到格式错误的 OCR 项。"""
    if not isinstance(results, (list, tuple)):
        return [], results is not None
    tokens: list[_Token] = []
    malformed = False
    for item in results:
        if not isinstance(item, (list, tuple)) or len(item) < 2 or not isinstance(item[1], str):
            malformed = True
            continue
        text = "".join(item[1].split())
        if not text:
            continue
        box = None
        points = item[0]
        if isinstance(points, (list, tuple)) and len(points) >= 2:
            if all(isinstance(p, (list, tuple)) and len(p) >= 2
                   and _finite_number(p[0]) and _finite_number(p[1]) for p in points):
                xs = [float(p[0]) for p in points]
                ys = [float(p[1]) for p in points]
                if max(xs) > min(xs) and max(ys) > min(ys):
                    box = min(xs), min(ys), max(xs), max(ys)
        tokens.append(_Token(text, box))
    return tokens, malformed


def _reading_order(tokens: Sequence[_Token]) -> list[_Token]:
    """将重叠文本按行分组，再逐行从左到右读取。"""
    if any(token.box is None for token in tokens):
        return list(tokens)
    rows: list[list[_Token]] = []
    for token in sorted(tokens, key=lambda t: (t.box[1], t.box[0])):
        for row in rows:
            anchor = row[0].box
            overlap = min(anchor[3], token.box[3]) - max(anchor[1], token.box[1])
            min_height = min(anchor[3] - anchor[1], token.box[3] - token.box[1])
            if overlap >= min_height * 0.5:
                row.append(token)
                break
        else:
            rows.append([token])
    return [token for row in rows for token in sorted(row, key=lambda t: t.box[0])]


def _adjacent(left: _Token, right: _Token) -> bool:
    """仅拼接相邻片段，绝不拼接相距较远的角色名。"""
    if left.box is None or right.box is None:
        return False
    a, b = left.box, right.box
    height = max(a[3] - a[1], b[3] - b[1])
    overlap_y = min(a[3], b[3]) - max(a[1], b[1])
    if overlap_y >= min(a[3] - a[1], b[3] - b[1]) * 0.25:
        return -height <= b[0] - a[2] <= max(12.0, height * 2)
    overlap_x = min(a[2], b[2]) - max(a[0], b[0])
    return (0 <= b[1] - a[3] <= height
            and (overlap_x > 0 or abs(a[0] - b[0]) <= height))


def _character_key(character: Any) -> str:
    return str(getattr(character, "name", character))


def _resolve_name_details(tokens: Sequence[_Token], lookup: CharacterLookup) -> tuple[Any | None, str, tuple[_Token, ...]]:
    """优先使用完整白名单名称，并拒绝相互冲突的名称片段。"""
    ordered = _reading_order(tokens)
    if not ordered:
        return None, "no_text", ()
    if len(ordered) > 32:
        return None, "too_many_name_fragments", ()

    matches: list[tuple[frozenset[int], Any]] = []
    # 第一轮保留完整名称中的数字；第二轮可排除
    # 独立价格，但不能移除 OCR 文本项内部的数字。
    sequences = [list(range(len(ordered)))]
    without_prices = [i for i, token in enumerate(ordered) if not token.text.isdecimal()]
    if without_prices != sequences[0]:
        sequences.append(without_prices)

    for sequence in sequences:
        for start in range(len(sequence)):
            text = ""
            indices: list[int] = []
            for end in range(start, min(len(sequence), start + 12)):
                index = sequence[end]
                if indices and not _adjacent(ordered[indices[-1]], ordered[index]):
                    break
                text += ordered[index].text
                indices.append(index)
                if len(text) > 96:
                    break
                character = lookup(text)
                if character is None and text in _OCR_NAME_ALIASES:
                    character = lookup(_OCR_NAME_ALIASES[text])
                if character is not None:
                    matches.append((frozenset(indices), character))

    if not matches:
        return None, "no_whitelist_match", ()
    # 例如拆开的“银狼”与“LV.999”会解析为完整名称，
    # 即使“银狼”本身也是有效白名单项。
    maximal = [
        match for match in matches
        if not any(match[0] < other[0] for other in matches)
    ]
    keys = {_character_key(character) for _, character in maximal}
    if len(keys) != 1:
        return None, "conflicting_names", ()

    covered = frozenset().union(*(indices for indices, _ in maximal))
    if any(i not in covered and any(ch.isalpha() for ch in token.text)
           for i, token in enumerate(ordered)):
        return None, "unmatched_name_fragment", ()
    return maximal[0][1], "", tuple(ordered[i] for i in sorted(covered))


def _resolve_name(tokens: Sequence[_Token], lookup: CharacterLookup) -> tuple[Any | None, str]:
    return _resolve_name_details(tokens, lookup)[:2]


# Yukki：识别结果先经过角色白名单与相邻文本约束。
def parse_character_name(results: Any, lookup: CharacterLookup) -> Any | None:
    """依据所提供白名单解析 OCR 片段，不修改数据。
    None、噪声、未知名称或歧义名称返回 None；这不能证明槽位为 EMPTY。
    白名单明确允许时支持完整英文或数字名称；调用方须排除受污染的注册表数据。
    拼接拆分名称必须有空间框；完整文本项即使没有框也可以查询。
    """
    tokens, malformed = _tokens(results)
    if malformed:
        return None
    return _resolve_name(tokens, lookup)[0]



def _parse_card_price(
    tokens: Sequence[_Token], name_tokens: Sequence[_Token],
    slot_bounds: tuple[float, float] | None = None,
) -> tuple[int | None, str]:
    """仅读取同一角色槽位内独立且无歧义的价格。
    输入必须是角色名与价格的裁剪区域。
    已被名称覆盖的片段，包括拆开的 LV.999 中的 999，绝不是价格候选。
    关联由几何位置建立，不使用 Character.cost 或先前观测价格。
    """
    remaining = [token for token in tokens if token not in name_tokens and token.text.isdecimal()]
    if not remaining:
        return None, "price_not_observed"
    if not name_tokens or any(token.box is None for token in (*name_tokens, *remaining)):
        return None, "price_geometry_missing"

    # 重复 OCR 框可能重复同一数字；位置不同或
    # 金额冲突时仍有歧义，即使预期费用相同。
    unique: list[_Token] = []
    for token in remaining:
        for previous in unique:
            a, b = token.box, previous.box
            intersection = max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(
                0.0, min(a[3], b[3]) - max(a[1], b[1]))
            small_area = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
            if token.text == previous.text and intersection >= small_area * 0.8:
                break
        else:
            unique.append(token)
    if len(unique) != 1:
        return None, "ambiguous_price_digits"

    token = unique[0]
    if len(token.text) > 2:
        return None, "price_out_of_range"
    value = int(token.text)
    # 明确的免费价格零仍有效；不能因 OCR 缺失而推断免费。
    if not 0 <= value <= 99:
        return None, "price_out_of_range"
    price_box = token.box
    if slot_bounds is not None and not (slot_bounds[0] <= price_box[0] < price_box[2] <= slot_bounds[1]):
        return None, "price_outside_slot"
    name_left = min(t.box[0] for t in name_tokens)
    name_right = max(t.box[2] for t in name_tokens)
    name_top = min(t.box[1] for t in name_tokens)
    name_bottom = max(t.box[3] for t in name_tokens)
    height = max(t.box[3] - t.box[1] for t in name_tokens)
    price_height = price_box[3] - price_box[1]
    for name in name_tokens:
        box = name.box
        overlap_x = min(price_box[2], box[2]) - max(price_box[0], box[0])
        overlap_y = min(price_box[3], box[3]) - max(price_box[1], box[1])
        if overlap_x > 0 and overlap_y > 0:
            return None, "price_overlaps_name"
    vertical_overlap = min(price_box[3], name_bottom) - max(price_box[1], name_top)
    horizontal_gap = max(name_left - price_box[2], price_box[0] - name_right, 0.0)
    vertical_gap = max(name_top - price_box[3], price_box[1] - name_bottom, 0.0)
    aligned_row = vertical_overlap >= min(height, price_height) * 0.25
    # 真实角色的价格固定在右侧，与名称长度无关。
    # 仅在整框位于槽位内部后才允许使用该固定区域；
    # 不能搜索相邻槽位，也不能选择全局最近数字。
    # 购买点中点可能位于名称字形左缘内部一至两个像素。
    # 小幅字形边缘容差不能放宽数字包含或分组要求。
    name_edge_slack = min(height / 4, (slot_bounds[1] - slot_bounds[0]) * 0.03) if slot_bounds else 0
    fixed_price_area = (slot_bounds is not None
                        and slot_bounds[0] - name_edge_slack <= name_left <= name_right <= price_box[0]
                        and price_box[0] >= slot_bounds[0] + (slot_bounds[1] - slot_bounds[0]) * 2 / 3)
    same_row = aligned_row and (horizontal_gap <= height * 3 or fixed_price_area)
    adjacent_row = (vertical_gap <= max(height, price_height) * 1.5
                    and max(name_left, price_box[0]) < min(name_right, price_box[2]))
    if not same_row and not adjacent_row:
        return None, "price_not_associated_with_name"
    return value, "same_slot_independent_digit"


def _bench_full(tokens: Sequence[_Token]) -> bool:
    texts = [token.text for token in tokens]
    texts.append("".join(token.text for token in _reading_order(tokens)))
    markers = ("备战席已满", "备战席满员", "备战席已达上限", "备战区已满")
    return any(marker in text for marker in markers for text in texts)


def scan_store_cards(
    results: Any,
    lookup: CharacterLookup,
    store_area: Sequence[tuple[float, float]],
    width: int | float,
    crop_from_x: float = 0.19,
    crop_to_x: float = 0.88,
) -> ShopObservation:
    """将 OCR 裁剪区域内的框映射到真实商店槽位，不压缩空缺。
    OCR 没有文本绝不能证明商店为空。
    EMPTY 仅用于明确的外部观测。
    未知角色可与可操作的已知角色共存；同槽名称冲突或几何歧义会使本轮扫描失效。
    """
    tokens, malformed = _tokens(results)
    if _bench_full(tokens):
        return ShopObservation(ShopState.FULL, reason="bench_full_message")
    if malformed:
        return ShopObservation(ShopState.UNKNOWN, reason="malformed_ocr")
    if not tokens:
        return ShopObservation(ShopState.UNKNOWN, reason="no_ocr_text")
    if all(not any(ch.isalpha() for ch in token.text) for token in tokens):
        return ShopObservation(ShopState.UNKNOWN, reason="prices_or_symbols_only")
    if not _finite_number(width) or width <= 0:
        return ShopObservation(ShopState.UNKNOWN, reason="invalid_window_width")
    if not _finite_number(crop_from_x) or not 0 <= crop_from_x <= 1:
        return ShopObservation(ShopState.UNKNOWN, reason="invalid_crop_origin")
    if not _finite_number(crop_to_x) or not crop_from_x < crop_to_x <= 1:
        return ShopObservation(ShopState.UNKNOWN, reason="invalid_crop_end")
    try:
        targets = tuple((float(p[0]), float(p[1])) for p in store_area
                        if len(p) == 2 and all(_finite_number(v) for v in p))
        if len(targets) != len(store_area) or not targets:
            return ShopObservation(ShopState.UNKNOWN, reason="invalid_store_area")
    except (TypeError, ValueError, IndexError):
        return ShopObservation(ShopState.UNKNOWN, reason="invalid_store_area")
    if any(not 0 <= coordinate <= 1 for target in targets for coordinate in target):
        return ShopObservation(ShopState.UNKNOWN, reason="invalid_store_area")

    sorted_slots = sorted(range(len(targets)), key=lambda i: targets[i][0])
    xs = [targets[i][0] for i in sorted_slots]
    if any(b - a <= 0 for a, b in zip(xs, xs[1:])):
        return ShopObservation(ShopState.UNKNOWN, reason="duplicate_store_centers")
    boundaries = [(a + b) / 2 for a, b in zip(xs, xs[1:])]
    left_edge = max(crop_from_x, xs[0] - (xs[1] - xs[0]) / 2) if len(xs) > 1 else crop_from_x
    # 最后购买点不是最后角色的中心；其真实价格
    # 超出外推的 .86 边界，但仍在已审核的 .88 OCR 裁剪区内。
    right_edge = crop_to_x
    slot_edges = [left_edge, *boundaries, right_edge]
    slot_bounds = {slot: ((slot_edges[i] - crop_from_x) * width,
                          (slot_edges[i + 1] - crop_from_x) * width)
                   for i, slot in enumerate(sorted_slots)}
    grouped: dict[int, list[_Token]] = {}
    for token in tokens:
        if token.box is None:
            return ShopObservation(ShopState.UNKNOWN, reason="missing_ocr_geometry")
        box = token.box
        if box[0] < 0 or box[1] < 0:
            return ShopObservation(ShopState.UNKNOWN, reason="invalid_ocr_geometry")
        center = crop_from_x + (box[0] + box[2]) / (2 * width)
        if not left_edge <= center <= right_edge:
            # 价格位于角色名区域外不会造成问题；但缺少
            # 合理角色位置的名称绝不能使其他角色槽位发生偏移。
            if token.text.isdecimal():
                continue
            return ShopObservation(ShopState.UNKNOWN, reason="ocr_outside_store")
        if any(abs(center - boundary) <= 0.5 / width for boundary in boundaries):
            if token.text.isdecimal():
                continue
            return ShopObservation(ShopState.UNKNOWN, reason="ambiguous_slot_boundary")
        order_index = sum(center > boundary for boundary in boundaries)
        slot_index = sorted_slots[order_index]
        grouped.setdefault(slot_index, []).append(token)

    cards: list[ShopCard] = []
    unknown_names = False
    for slot_index in sorted(grouped):
        slot_tokens = grouped[slot_index]
        character, reason, name_tokens = _resolve_name_details(slot_tokens, lookup)
        if reason in ("conflicting_names", "unmatched_name_fragment"):
            return ShopObservation(ShopState.UNKNOWN, reason="conflicting_slot_names")
        if character is None:
            if any(any(ch.isalpha() for ch in token.text) for token in slot_tokens):
                unknown_names = True
            continue
        price, price_evidence = _parse_card_price(slot_tokens, name_tokens, slot_bounds[slot_index])
        cards.append(ShopCard(slot_index, character, targets[slot_index],
                              "".join(token.text for token in _reading_order(slot_tokens)),
                              price, price_evidence))
    if not cards:
        return ShopObservation(ShopState.UNKNOWN, reason="no_known_store_cards")
    return ShopObservation(ShopState.READY, tuple(cards),
                           "partial_unrecognized_cards" if unknown_names else "")


def validate_main_c_config(
    strategy: Mapping[str, Any],
    lookup: CharacterLookup,
) -> tuple[str | None, int]:
    """返回规范化的 main_c 与 main_c_search_level，或拒绝无效设置。
    main_c 可选；若提供，必须解析为已知角色且存在于 on_field 或 off_field，别名按规范名称比较。
    """
    if not isinstance(strategy, Mapping):
        raise ValueError("攻略配置必须是对象")
    main_c_search_level = strategy.get("main_c_search_level", 5)
    if type(main_c_search_level) is not int or main_c_search_level <= 0:
        raise ValueError("main_c_search_level 必须为正整数，不能为布尔值")

    main_c = strategy.get("main_c")
    if main_c is None:
        return None, main_c_search_level
    if not isinstance(main_c, str) or not main_c.strip():
        raise ValueError("main_c 必须为已知角色的非空名称，或省略")
    character = lookup("".join(main_c.split()))
    if character is None:
        raise ValueError(f"main_c 不是已知角色：{main_c}")
    canonical_name = _character_key(character)
    members: set[str] = set()
    for area_name in ("on_field", "off_field"):
        area = strategy.get(area_name, {})
        if not isinstance(area, Mapping):
            raise ValueError(f"{area_name} 必须为角色到目标星级的映射")
        for name in area:
            if isinstance(name, str):
                member = lookup("".join(name.split()))
                if member is not None:
                    members.add(_character_key(member))
    if canonical_name not in members:
        raise ValueError(f"main_c 必须存在于 on_field 或 off_field：{canonical_name}")
    return canonical_name, main_c_search_level
@dataclass(frozen=True)
class LevelObservation:
    level: int | None
    raw_text: str
    reason: str
    evidence: str = ""


@dataclass(frozen=True)
class PurchaseDecision:
    can_buy: bool
    reason: str
    details: dict[str, Any]


# ssyb：商店等级与经验分母分别解析，不能互相替代。
def parse_shop_level(
    results: Any, min_level: int = 1, max_level: int = 20,
) -> LevelObservation:
    """读取明确的商店等级标签，绝不读取人口或经验数字。
    调用方须裁剪并确认商店界面。
    本解析器不回退使用队伍人数、裸数字、分数或先前观测。
    相邻 OCR 片段可拼接，但未绑定或相互冲突的标签仍为未知。
    """
    if (type(min_level) is not int or type(max_level) is not int
            or min_level < 1 or max_level < min_level):
        raise ValueError("Invalid shop-level range")
    raw_text = " | ".join(item[1] for item in results
                          if isinstance(item, (list, tuple)) and len(item) > 1
                          and isinstance(item[1], str)) if isinstance(results, (list, tuple)) else ""
    tokens, malformed = _tokens(results)
    if malformed:
        return LevelObservation(None, raw_text, "malformed_ocr")
    if not tokens:
        return LevelObservation(None, raw_text, "no_ocr_text")
    ordered = _reading_order([
        _Token(unicodedata.normalize("NFKC", token.text), token.box) for token in tokens
    ])
    # Unicode 单词边界排除“银狼LV.999”等角色名称。
    label = re.compile(r"(?<![\w])(?:LV[.:]?|(?:商店)?等级[:.]?)([0-9]+)(?![0-9./])", re.I)
    marker = re.compile(r"(?:LV[.:]?|等级)", re.I)
    forbidden = re.compile(r"(?:人口|人数|队伍|上阵|角色|人物|经验|EXP)[:：.]?$", re.I)

    def non_shop_context(text: str) -> bool:
        # 商店独立购买按钮可能与其上方或旁边的等级标签相接。
        # 只有这一精确的界面标签可豁免；经验、人口和
        # 角色上下文仍须拒绝附近带标签的数字。
        return (text.rstrip(":：.") != "购买经验"
                and bool(forbidden.search(text)))

    values: set[int] = set()
    rejection = ""
    saw_marker = False
    for start in range(len(ordered)):
        text = ""
        for end in range(start, min(start + 6, len(ordered))):
            if end > start and not _adjacent(ordered[end - 1], ordered[end]):
                break
            text += ordered[end].text
            saw_marker = saw_marker or bool(marker.search(text))
            match = label.search(text)
            if match is None:
                continue
            prefix = text[:match.start()]
            previous = ordered[start - 1] if start > 0 else None
            if non_shop_context(prefix) or (
                not prefix and previous is not None and _adjacent(previous, ordered[start])
                and non_shop_context(previous.text)
            ):
                rejection = "non_shop_level_context"
                break
            if end + 1 < len(ordered) and _adjacent(ordered[end], ordered[end + 1]):
                following = ordered[end + 1].text
                if following.startswith("/") or (
                    following.isdecimal() and ordered[end].text.isdecimal()
                ):
                    rejection = "ambiguous_numeric_context"
                    break
            value = int(match.group(1))
            if not min_level <= value <= max_level:
                rejection = "level_out_of_range"
            else:
                values.add(value)
            # 不能将相邻经验或人口数字附加到
            # 已经完整的带标签等级上。
            break
    if rejection:
        return LevelObservation(None, raw_text, rejection)
    if len(values) > 1:
        return LevelObservation(None, raw_text, "conflicting_level_labels")
    if values:
        return LevelObservation(values.pop(), raw_text, "matched_level_label", "explicit_level_label")
    return LevelObservation(None, raw_text,
                            "label_without_valid_value" if saw_marker else "missing_level_label")


def evaluate_purchase(
    card: ShopCard, *, target_stars: int | None,
    confirmed_stars: int | None = None, stars_fresh: bool = False,
    star_source: str = "", star_revision: int | None = None,
    bench_copies: int = 0, pending_purchase: bool = False,
    coins: int | None = None, slot_available: bool | None = None,
    protected: bool = False, require_price: bool = False,
) -> PurchaseDecision:
    """依据观测解释一次目标角色决策，不使用静态费用。
    未知等级不是参数：调用方单独禁用 D/F，并通过 require_price=True 要求可靠价格。
    备战区容量未知不能证明 FULL；调用方确认 READY 和真实商店槽位。
    备战区副本仅用于解释，其计数不能证明星级进展。
    """
    trustworthy_stars = (stars_fresh is True and type(confirmed_stars) is int
                         and 1 <= confirmed_stars <= 3)
    valid_price = type(card.price) is int and card.price >= 0
    valid_coins = type(coins) is int and coins >= 0
    details = {
        "slot_index": card.slot_index,
        "character_name": _character_key(card.character),
        "price": card.price if valid_price else None,
        "price_evidence": card.price_evidence,
        "target_stars": target_stars,
        "confirmed_stars": confirmed_stars,
        "stars_fresh": stars_fresh,
        "stars_trusted": trustworthy_stars,
        "star_source": star_source,
        "star_revision": star_revision,
        "bench_copies": bench_copies,
        "pending_purchase": pending_purchase,
        "coins": coins if valid_coins else None,
        "slot_available": slot_available,
        "protected": protected,
        "require_price": require_price,
    }

    def decision(can_buy: bool, reason: str) -> PurchaseDecision:
        return PurchaseDecision(can_buy, reason, {**details, "reason": reason})

    if target_stars is None:
        return decision(False, "not_in_strategy")
    if type(target_stars) is not int or not 1 <= target_stars <= 3:
        return decision(False, "invalid_target_stars")
    if protected:
        return decision(False, "protected")
    if pending_purchase:
        return decision(False, "purchase_pending")
    if trustworthy_stars and confirmed_stars >= target_stars:
        return decision(False, "target_reached")
    if slot_available is False:
        return decision(False, "bench_full")
    if not valid_coins:
        return decision(False, "unknown_coins")
    if require_price and not valid_price:
        return decision(False, "unknown_price")
    if valid_price and card.price > coins:
        return decision(False, "insufficient_coins")
    return decision(True, "eligible" if valid_price else "eligible_price_unknown")
