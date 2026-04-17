from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence


class ShoppableCharacter(Protocol):
    name: str


@dataclass(frozen=True)
class PurchaseAttemptEvaluation:
    succeeded: bool
    should_clear_reserve: bool
    should_reopen_store: bool


def store_has_reserve_full_marker(ocr_results: Sequence[Any] | None) -> bool:
    if not ocr_results:
        return False

    for item in ocr_results:
        if len(item) < 2:
            continue
        text = item[1]
        if isinstance(text, str) and "备" in text.strip():
            return True

    return False


def is_store_scan_valid(ocr_results: Sequence[Any] | None) -> bool:
    if not ocr_results:
        return False

    if store_has_reserve_full_marker(ocr_results):
        return True

    for item in ocr_results:
        if len(item) < 2:
            continue
        text = item[1]
        if isinstance(text, str) and text.strip().isdecimal():
            return True

    return False


def evaluate_purchase_attempt(
    target_index: int,
    target_name: str,
    refreshed_characters: Sequence[ShoppableCharacter],
    reserve_full: bool,
    store_scan_valid: bool,
) -> PurchaseAttemptEvaluation:
    if not store_scan_valid:
        return PurchaseAttemptEvaluation(
            succeeded=False,
            should_clear_reserve=False,
            should_reopen_store=True,
        )

    still_visible = (
        0 <= target_index < len(refreshed_characters)
        and refreshed_characters[target_index].name == target_name
    )

    return PurchaseAttemptEvaluation(
        succeeded=not still_visible,
        should_clear_reserve=still_visible and reserve_full,
        should_reopen_store=False,
    )


def get_pre_refresh_exit_reason(
    coins: int,
    min_coins: int,
    is_overclock: bool,
    pending_post_refresh_scan: bool,
) -> str | None:
    if pending_post_refresh_scan:
        return None

    if coins < 4:
        return f"金币不足4（当前{coins}），退出购物循环"

    if is_overclock:
        return None

    if coins < min_coins:
        return f"当前金币 {coins} 小于最低保留数量 {min_coins}，退出购物循环"

    coins_after_refresh = coins - 6
    if coins_after_refresh < min_coins:
        return f"当前金币 {coins} 在刷新/升级后将低于最低保留数量 {min_coins}，退出购物循环"

    return None


def analyze_purchase_candidates(
    characters: Sequence[ShoppableCharacter],
    strategy_characters: dict[str, int],
) -> tuple[list[tuple[int, ShoppableCharacter, int]], list[tuple[int, ShoppableCharacter, int]]]:
    purchasable: list[tuple[int, ShoppableCharacter, int]] = []
    exhausted: list[tuple[int, ShoppableCharacter, int]] = []

    for index, character in enumerate(characters):
        remaining = strategy_characters.get(character.name)
        if remaining is None:
            continue
        if remaining <= 0:
            exhausted.append((index, character, remaining))
            continue
        purchasable.append((index, character, remaining))

    return purchasable, exhausted
