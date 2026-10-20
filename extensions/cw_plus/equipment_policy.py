"""已上场角色装备检查的纯配置与排序逻辑。"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Callable, Mapping, Sequence


@dataclass(frozen=True)
class EquipmentConfig:
    priority_characters: tuple[str, ...]
    others_from_round: tuple[int, int]
    interval_battles: int


def _round(value: Any) -> tuple[int, int] | None:
    if isinstance(value, str):
        match = re.fullmatch(r"([1-9])-([1-9])", value)
        return (int(match[1]), int(match[2])) if match else None
    if (isinstance(value, (tuple, list)) and len(value) == 2
            and all(type(part) is int and 1 <= part <= 9 for part in value)):
        return tuple(value)
    return None


def parse_equipment_config(raw: Any, lookup: Callable[[str], Any] | None = None) -> EquipmentConfig | None:
    """None 保留旧版装备行为；配置了策略后执行严格校验。"""
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise ValueError("equipment 必须为对象")
    if set(raw) - {"priority_characters", "others_from_round", "interval_battles"}:
        raise ValueError("equipment 包含未知字段")
    names = raw.get("priority_characters")
    if not isinstance(names, (list, tuple)) or not names:
        raise ValueError("equipment.priority_characters 必须为非空角色列表")
    canonical = []
    for name in names:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("equipment.priority_characters 必须为有效角色名称")
        name = name.strip()
        if lookup is not None:
            character = lookup(name)
            if (character is None or getattr(character, "is_locked", False)
                    or getattr(character, "is_npc", False)):
                raise ValueError("equipment.priority_characters 包含未知或不可操作角色：" + name)
            name = character.name
        if name in canonical:
            raise ValueError("equipment.priority_characters 不得重复角色或别名")
        canonical.append(name)
    raw_round = raw.get("others_from_round")
    first_round = _round(raw_round)
    if not isinstance(raw_round, str) or first_round is None:
        raise ValueError("equipment.others_from_round 必须为有效关卡，例如 3-4")
    interval = raw.get("interval_battles", 2)
    if type(interval) is not int or interval <= 0:
        raise ValueError("equipment.interval_battles 必须为正整数")
    return EquipmentConfig(tuple(canonical), first_round, interval)


# Yukki：装备顺序只覆盖已确认上场的角色。
def allowed_order(config: EquipmentConfig | None, deployed_eligible_names: Sequence[str],
                  round_label: Any = None) -> tuple[str, ...]:
    """筛选已上场且符合条件的角色名称，再把优先角色排在前面。
    上场、身份、装备需求和回合证据由调用方负责。
    回合未知时，仅允许配置的优先角色。
    此函数不会引入备战区或缺失角色；未配置策略时不会改变旧版顺序。
    """
    if config is None:
        return tuple(deployed_eligible_names)
    names = tuple(dict.fromkeys(deployed_eligible_names))
    priority = tuple(name for name in config.priority_characters if name in names)
    current_round = _round(round_label)
    if current_round is None or current_round < config.others_from_round:
        return priority
    return priority + tuple(name for name in names if name not in priority)
