from __future__ import annotations

from typing import Protocol, Sequence


class SellableCharacter(Protocol):
    name: str
    priority: int | None
    is_placed: bool


def get_sell_protection_rank(
    character: SellableCharacter,
    strategy_characters: dict[str, int],
) -> int:
    is_strategy = character.name in strategy_characters

    if not is_strategy and not character.is_placed:
        return 0
    if not is_strategy and character.is_placed:
        return 1
    if is_strategy and character.is_placed:
        return 2
    return 3


def build_sell_plan(
    in_hand_characters: Sequence[SellableCharacter | None],
    strategy_characters: dict[str, int],
    force: bool = False,
    target_hand_count: int = 7,
) -> list[tuple[int, SellableCharacter]]:
    current_hand_count = sum(character is not None for character in in_hand_characters)
    need_to_sell = max(0, current_hand_count - target_hand_count)

    if need_to_sell == 0:
        return []

    candidates: list[tuple[int, SellableCharacter]] = []
    for index, character in enumerate(in_hand_characters):
        if character is None:
            continue
        if not force and character.is_placed:
            continue
        candidates.append((index, character))

    candidates.sort(
        key=lambda item: (
            get_sell_protection_rank(item[1], strategy_characters),
            item[1].priority if item[1].priority is not None else 999,
            -item[0],
        )
    )
    return candidates[:need_to_sell]


def settle_sold_character(
    character: SellableCharacter,
    strategy_characters: dict[str, int],
    on_field_characters: Sequence[SellableCharacter | None],
    off_field_characters: Sequence[SellableCharacter | None],
) -> bool:
    refunded = False
    if character.name in strategy_characters:
        strategy_characters[character.name] += 1
        refunded = True

    character.is_placed = any(
        existing is character for existing in [*on_field_characters, *off_field_characters]
    )
    return refunded
