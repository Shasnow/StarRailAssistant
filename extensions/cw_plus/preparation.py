"""不导入游戏或 GUI 的准备阶段结果与有界决策。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class MoveStatus(StrEnum):
    CONFIRMED_CHANGED = "confirmed_changed"
    CONFIRMED_UNCHANGED = "confirmed_unchanged"
    INDETERMINATE = "indeterminate"
    REJECTED = "rejected"


@dataclass(frozen=True)
class MoveResult:
    status: MoveStatus
    reason: str
    source: tuple[str, int] | None = None
    target: tuple[str, int] | None = None

    def __bool__(self) -> bool:
        return self.status == MoveStatus.CONFIRMED_CHANGED


class Readiness(StrEnum):
    READY = "ready"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class PreparationResult:
    state: Readiness
    reason: str
    moves: int = 0
    attempts: int = 0
    recoveries: int = 0
    gaps: tuple[str, ...] = ()
    blocked_reason: str = ""

    def __bool__(self) -> bool:
        return self.state != Readiness.BLOCKED


def observation_identity(observation: Any) -> tuple[str, str | None] | None:
    """识别可靠占位、空位及不可用的锁定槽位。
    LOCKED 是完整棋盘证据，但绝不是合法移动端点。
    """
    state = getattr(getattr(observation, "state", None), "value", None)
    if state is None:
        state = getattr(observation, "state", None)
    if getattr(observation, "evidence", "") in {
        "pending_drag", "stale", "observation_error", "event_invalidated", "layout_changed", "strategy_changed",
    } or getattr(observation, "stale", False):
        return None
    if state == "empty":
        return "empty", None
    if state == "locked":
        return "locked", None
    name = getattr(getattr(observation, "character", None), "name", None)
    if state == "known" and isinstance(name, str) and name.strip() and not name.isdecimal():
        return "known", name
    return None


def _recovery_observation(observation: Any) -> tuple:
    """冻结与决策有关的值，绝不保存可变角色对象。"""
    state = getattr(observation, "state", None)
    state = getattr(state, "value", state)
    character = getattr(observation, "character", None)
    position = getattr(character, "position", None)
    positioning = getattr(character, "positioning", None)
    return (
        getattr(observation, "slot_index", None), state,
        getattr(character, "name", None), observation_identity(observation),
        getattr(observation, "stars", None), getattr(observation, "occupied", None),
        bool(getattr(character, "is_locked", False)),
        bool(getattr(character, "is_npc", False)),
        getattr(position, "value", position),
        getattr(positioning, "value", positioning),
    )


# ssyb：恢复签名包含未完成动作，防止无进展地重复输入。
def recovery_signature(observations: Any, *, layout_revision: int,
                       layout_valid: bool, capacity: int | None,
                       population: int | None, dirty_slots=(), bench_dirty=False,
                       placement_pending=False, pending_move=None,
                       excluded_moves=()) -> tuple:
    """描述恢复进展，不能把读取次数当成进展。
    状态、身份、可靠证据、星级和未解决事项会影响签名；观测修订号、时间戳及同一 UNKNOWN 槽位的不同错误文本不会。
    动作尝试和恢复预算由调用方负责：待处理或脏标志保持不变，本身不能算进展。
    """
    roster = tuple((area, tuple(_recovery_observation(observation)
                               for observation in observations[area]))
                   for area in sorted(observations))
    pending = None
    if pending_move is not None:
        pending = (
            tuple(pending_move.get("source", ())),
            tuple(pending_move.get("target", ())),
            _recovery_observation(pending_move.get("source_before")),
            _recovery_observation(pending_move.get("target_before")),
            pending_move.get("layout"),
            tuple(tuple(point) for point in pending_move.get("positions", ())),
        )
    return (
        roster, layout_revision, bool(layout_valid), capacity, population,
        tuple(sorted(tuple(slot) for slot in dirty_slots)), bool(bench_dirty),
        bool(placement_pending), pending,
        tuple(sorted(tuple(move) for move in excluded_moves)),
    )


def classify_move(source_before: Any, target_before: Any,
                  source_after: Any, target_after: Any) -> MoveResult:
    before = observation_identity(source_before), observation_identity(target_before)
    after = observation_identity(source_after), observation_identity(target_after)
    if None in before or None in after:
        return MoveResult(MoveStatus.INDETERMINATE, "move_endpoints_not_confirmed")
    if any(identity[0] == "locked" for identity in before + after):
        return MoveResult(MoveStatus.INDETERMINATE, "move_endpoint_locked")
    if before[0] == before[1] and before[0][0] == "known" and after == before:
        old_stars = tuple(getattr(obs, "stars", None) for obs in (source_before, target_before))
        new_stars = tuple(getattr(obs, "stars", None) for obs in (source_after, target_after))
        if any(type(stars) is not int or not 1 <= stars <= 3 for stars in old_stars + new_stars):
            return MoveResult(MoveStatus.INDETERMINATE, "same_name_stars_not_confirmed")
        if new_stars == old_stars:
            return MoveResult(MoveStatus.CONFIRMED_UNCHANGED, "move_confirmed_unchanged")
        if new_stars == old_stars[::-1]:
            return MoveResult(MoveStatus.CONFIRMED_CHANGED, "both_star_endpoints_confirmed")
        return MoveResult(MoveStatus.INDETERMINATE, "same_name_star_endpoints_conflict")
    if after == before:
        return MoveResult(MoveStatus.CONFIRMED_UNCHANGED, "move_confirmed_unchanged")
    if after == (before[1], before[0]):
        return MoveResult(MoveStatus.CONFIRMED_CHANGED, "both_endpoints_confirmed")
    return MoveResult(MoveStatus.INDETERMINATE, "move_endpoints_conflict")


def validate_preparation_budget(raw: Any) -> dict[str, int]:
    result = {"seconds": 120, "actions": 20, "recoveries": 2,
              "move_retries": 1, "total_seconds": 300, "field_refresh_seconds": 60,
              "confirmation_seconds": 30}
    if raw is None:
        return result
    if not isinstance(raw, dict) or not raw.keys() <= result.keys():
        raise ValueError("preparation_budget 必须是有效的预算对象")
    for name, value in raw.items():
        minimum = 0 if name in {"recoveries", "move_retries"} else 1
        if type(value) is not int or not minimum <= value <= 600:
            raise ValueError(f"preparation_budget.{name} 无效")
        result[name] = value
    if result["seconds"] > result["total_seconds"]:
        raise ValueError("preparation_budget.seconds 不能超过 total_seconds")
    if "confirmation_seconds" not in raw:
        result["confirmation_seconds"] = min(result["confirmation_seconds"], result["total_seconds"])
    if result["confirmation_seconds"] > result["total_seconds"]:
        raise ValueError("preparation_budget.confirmation_seconds 不能超过 total_seconds")
    return result
