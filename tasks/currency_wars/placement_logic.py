from __future__ import annotations

from collections.abc import Collection, Sequence


PlacementEntry = tuple[str | None, str, bool]


def build_placement_plan(
    in_hand_entries: Sequence[PlacementEntry],
    strategy_on_field_names: Collection[str],
    strategy_off_field_names: Collection[str],
) -> tuple[list[int], list[int]]:
    front_strategy: list[int] = []
    front_filler: list[int] = []
    back_strategy: list[int] = []
    back_filler: list[int] = []

    for index, (name, position, is_placed) in enumerate(in_hand_entries):
        if name is None or is_placed:
            continue

        if position != "off":
            if name in strategy_on_field_names:
                front_strategy.append(index)
            else:
                front_filler.append(index)

        if position != "on":
            if name in strategy_off_field_names:
                back_strategy.append(index)
            else:
                back_filler.append(index)

    return front_strategy + front_filler, back_strategy + back_filler


def should_auto_equip_character(
    character_name: str | None,
    strategy_character_names: Collection[str],
) -> bool:
    return character_name is not None and character_name in strategy_character_names
