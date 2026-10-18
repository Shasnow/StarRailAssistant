"""完整棋盘观测之间使用的保守购买账本。
调用方创建批次前须验证观测身份及新鲜度，且只记录已确认的一星购买。
这里的计数用于购物决策，不能作为角色所在位置或是否自动合成的观测。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


def _valid_name(name: Any) -> bool:
    return isinstance(name, str) and bool(name.strip())


def _target_copies(goal: Any) -> int | None:
    return 3 ** (goal - 1) if type(goal) is int and 1 <= goal <= 3 else None


@dataclass
# ssyb：批次账本估算剩余需求，真实库存仍由调用方重新读取。
class ShoppingBatch:
    _copies: dict[str, int]
    _remaining_spaces: int
    _pending_names: set[str] = field(default_factory=set)
    _pending_count: int = 0

    @classmethod
    def from_observations(cls, observations: Mapping[str, Sequence[Any]]) -> ShoppingBatch | None:
        """复制完整棋盘快照，拒绝任何身份或星级未知的项。
        槽位状态可为字符串，也可为具有 value 的枚举。
        证据有效性由调用方负责；本模块刻意不依赖运行时。
        只有已确认 EMPTY 的备战区槽位增加购买空间。
        已确认 LOCKED 槽位没有角色，也不提供购买空间。
        已确认 NPC 不参与购买副本计数，也不要求不存在的星级证据。
        """
        areas = ("on_field", "off_field", "in_hand")
        if not isinstance(observations, Mapping) or any(area not in observations for area in areas):
            return None
        copies: dict[str, int] = {}
        spaces = 0
        for area in areas:
            slots = observations[area]
            if not isinstance(slots, Sequence) or isinstance(slots, (str, bytes)):
                return None
            for observation in slots:
                state = getattr(observation, "state", None)
                state = getattr(state, "value", state)
                if isinstance(state, str):
                    state = state.lower()
                if state == "empty":
                    spaces += area == "in_hand"
                    continue
                if state == "locked":
                    continue
                if state != "known":
                    return None
                character = getattr(observation, "character", None)
                name = getattr(character, "name", None)
                if getattr(character, "is_npc", False):
                    if (not _valid_name(name) or name.strip().isdecimal()
                            or getattr(observation, "occupied", None) is False
                            or getattr(observation, "stale", False)
                            or getattr(observation, "evidence", "") in {
                                "pending_drag", "stale", "observation_error", "event_invalidated",
                                "layout_changed", "layout_unconfirmed", "strategy_changed",
                            }):
                        return None
                    continue
                count = _target_copies(getattr(observation, "stars", None))
                if not _valid_name(name) or count is None:
                    return None
                copies[name] = copies.get(name, 0) + count
        return cls(copies, spaces)

    @property
    def space_safe(self) -> bool:
        return self._remaining_spaces > 0

    @property
    def pending_names(self) -> set[str]:
        return set(self._pending_names)

    @property
    def pending_count(self) -> int:
        return self._pending_count

    def missing_goals(self, goals: Mapping[str, int]) -> dict[str, int]:
        """即使安全购买空间耗尽，也返回未满足的目标。"""
        missing = {}
        for name, goal in goals.items():
            count = _target_copies(goal)
            if not _valid_name(name) or count is None:
                raise ValueError("Shopping goals require character names and stars from 1 to 3")
            if self._copies.get(name, 0) < count:
                missing[name] = goal
        return missing

    def can_buy(self, name: str, goal: int) -> bool:
        count = _target_copies(goal)
        return bool(self.space_safe and _valid_name(name) and count is not None
                    and self._copies.get(name, 0) < count)

    def record_purchase(self, name: str) -> None:
        """记录一笔已确认的一星交易，消耗一个安全槽位。
        即使预计购买会触发角色合成，也会消耗槽位。
        只有新观测能确认空间释放并开启下一批次。
        """
        if not _valid_name(name):
            raise ValueError("A confirmed purchase requires a character name")
        if not self.space_safe:
            raise ValueError("No confirmed bench space remains in this batch")
        self._copies[name] = self._copies.get(name, 0) + 1
        self._remaining_spaces -= 1
        self._pending_names.add(name)
        self._pending_count += 1
