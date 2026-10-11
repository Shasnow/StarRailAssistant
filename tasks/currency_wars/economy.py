"""Pure, deterministic economy decisions for Currency Wars.

The caller owns observations, character demand, action confirmation and session
persistence. No decision here clicks the UI or assumes a particular formation.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping


# Confirmed Lv label/progress pairs in runtime/log/SRA20261008.log and
# SRA20261009.log: Lv5 /20 (119 reads), Lv6 /40 (54), Lv7 /52 (89),
# Lv8 /72 (38), with no conflicting denominators. Only these verified
# future-level requirements may supplement the current live observation.
_VERIFIED_EXPERIENCE_REQUIREMENTS = {5: 20, 6: 40, 7: 52, 8: 72}


@dataclass(frozen=True)
class EconomyStage:
    from_battles: int
    target_level: int
    reserve_gold: int
    upgrade_gold: int | None = None


@dataclass(frozen=True)
class EconomyConfig:
    purchase_reserve_gold: int
    stages: tuple[EconomyStage, ...]
    all_in_round: tuple[int, int] | None = None


@dataclass(frozen=True)
class EconomyStageSelection:
    index: int
    reason: str


@dataclass(frozen=True)
class EconomyDecision:
    action: str
    reason: str


@dataclass(frozen=True)
class FinalRoundDecision:
    action: str
    reason: str
    target_level: int | None = None
    upgrade_cost: int | None = None
    purchases: int | None = None


@dataclass(frozen=True)
class ExperienceCost:
    cost: int | None
    purchases: int | None
    reason: str


@dataclass(frozen=True)
class AllInDecision:
    enabled: bool
    target_level: int | None
    upgrade_cost: int | None
    purchases: int | None
    reason: str


def _nonnegative_int(value: Any) -> bool:
    return type(value) is int and value >= 0


def _positive_int(value: Any) -> bool:
    return type(value) is int and value > 0


def _require_nonnegative_int(value: Any, path: str) -> int:
    if not _nonnegative_int(value):
        raise ValueError(f"{path} 必须为非负整数，不能为布尔值")
    return value


def _reject_unknown(raw: Mapping, allowed: set[str], path: str) -> None:
    unknown = set(raw) - allowed
    if unknown:
        names = ", ".join(sorted(str(key) for key in unknown))
        raise ValueError(f"{path} 包含未知字段: {names}")


def parse_economy_config(
    raw: Any, *, main_c_search_level: int | None = None, max_level: int = 20,
) -> EconomyConfig | None:
    """Validate the optional ``economy`` object; None means legacy economy.

    ``main_c_search_level`` is passed only when a main character is configured.
    The level bound matches the existing shop-level parser's supported range.
    A disabled object still rejects misspelled top-level field names and a
    non-boolean enabled flag, but its inactive stage table is not interpreted.
    """
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise ValueError("economy 必须为对象")
    _reject_unknown(raw, {"enabled", "purchase_reserve_gold", "stages", "all_in_round"}, "economy")
    enabled = raw.get("enabled", False)
    if type(enabled) is not bool:
        raise ValueError("economy.enabled 必须为布尔值")
    if not enabled:
        return None
    if not _positive_int(max_level):
        raise ValueError("max_level 必须为正整数")
    if main_c_search_level is not None and not _positive_int(main_c_search_level):
        raise ValueError("main_c_search_level 必须为正整数")
    purchase_reserve = _require_nonnegative_int(
        raw.get("purchase_reserve_gold", 0), "economy.purchase_reserve_gold")
    all_in_round = None
    if "all_in_round" in raw:
        label = raw["all_in_round"]
        if not isinstance(label, str) or re.fullmatch(r"[1-9]-[1-9]", label) is None:
            raise ValueError("economy.all_in_round 必须为 1-9 范围内的关卡编号，例如 3-7")
        all_in_round = tuple(int(part) for part in label.split("-"))
    rows = raw.get("stages")
    if not isinstance(rows, (list, tuple)) or not rows:
        raise ValueError("economy.stages 必须为非空阶段列表")
    stages: list[EconomyStage] = []
    required = {"from_battles", "target_level", "reserve_gold"}
    for index, row in enumerate(rows):
        path = f"economy.stages[{index}]"
        if not isinstance(row, Mapping):
            raise ValueError(f"{path} 必须为对象")
        _reject_unknown(row, required | {"upgrade_gold"}, path)
        missing = required - set(row)
        if missing:
            raise ValueError(f"{path} 缺少字段: {', '.join(sorted(missing))}")
        battles = _require_nonnegative_int(row["from_battles"], f"{path}.from_battles")
        level = row["target_level"]
        if not _positive_int(level) or level > max_level:
            raise ValueError(f"{path}.target_level 必须为 1 到 {max_level} 的整数")
        reserve = _require_nonnegative_int(row["reserve_gold"], f"{path}.reserve_gold")
        trigger = row.get("upgrade_gold")
        if trigger is not None:
            trigger = _require_nonnegative_int(trigger, f"{path}.upgrade_gold")
        if not stages and battles != 0:
            raise ValueError("economy 第一阶段 from_battles 必须为 0")
        if stages and battles <= stages[-1].from_battles:
            raise ValueError("economy 阶段 from_battles 必须严格递增")
        if stages and level < stages[-1].target_level:
            raise ValueError("economy 阶段 target_level 不能下降")
        stages.append(EconomyStage(battles, level, reserve, trigger))
    if main_c_search_level is not None and stages[-1].target_level < main_c_search_level:
        raise ValueError("economy 最后阶段 target_level 不得低于 main_c_search_level")
    return EconomyConfig(purchase_reserve, tuple(stages), all_in_round)


def experience_cost_to_target(
    *, level: int | None, target_level: int, experience_current: int | None = None,
    experience_required: int | None = None, xp_cost: int = 4, xp_gain: int = 4,
) -> ExperienceCost:
    """Bound the whole remaining upgrade using live and verified progress.

    The caller must confirm level and progress together on two stable reads.
    The live denominator must agree with the verified table when present, and
    each future level must be in that table. Round each level up separately:
    the resulting sufficient budget does not assume leftover XP carries over.
    Re-observe after each input instead of treating this quote as a purchase
    count to send blindly. An unknown future level never gets an estimate.
    """
    if not _positive_int(target_level):
        return ExperienceCost(None, None, "invalid_target_level")
    if not _positive_int(level):
        return ExperienceCost(None, None, "unknown_level")
    if level >= target_level:
        return ExperienceCost(0, 0, "target_reached")
    if not _positive_int(xp_cost) or not _positive_int(xp_gain):
        return ExperienceCost(None, None, "invalid_experience_purchase")
    if not _nonnegative_int(experience_current) or not _positive_int(experience_required):
        return ExperienceCost(None, None, "experience_unknown")
    if experience_current >= experience_required:
        return ExperienceCost(None, None, "experience_invalid")
    verified_current = _VERIFIED_EXPERIENCE_REQUIREMENTS.get(level)
    if verified_current is not None and experience_required != verified_current:
        return ExperienceCost(None, None, "experience_table_conflict")
    remaining = [experience_required - experience_current]
    for future_level in range(level + 1, target_level):
        required = _VERIFIED_EXPERIENCE_REQUIREMENTS.get(future_level)
        if required is None:
            return ExperienceCost(None, None, "cross_level_cost_unknown")
        remaining.append(required)
    purchases = sum((required + xp_gain - 1) // xp_gain for required in remaining)
    return ExperienceCost(purchases * xp_cost, purchases,
        "confirmed_experience_cost" if len(remaining) == 1 else "confirmed_cross_level_cost_bound")


def next_final_round_action(
    *, level: int | None, coins: int | None,
    experience_current: int | None = None, experience_required: int | None = None,
    level_capped: bool = False, xp_cost: int = 4, xp_gain: int = 4,
) -> FinalRoundDecision:
    """Spend final-round gold, upgrading only with a complete next-level budget.

    The caller owns round detection and must re-observe after every action.
    Strategy targets, reserves and upgrade gates do not affect this decision.
    """
    if not _positive_int(level) or not _nonnegative_int(coins):
        return FinalRoundDecision("recover", "final_round_unknown_level_or_coins")
    if type(level_capped) is not bool:
        return FinalRoundDecision("recover", "final_round_cap_unknown")
    if not _positive_int(xp_cost) or not _positive_int(xp_gain):
        return FinalRoundDecision("recover", "final_round_invalid_experience_purchase")
    if coins == 0:
        return FinalRoundDecision("save", "final_round_gold_exhausted")
    if level_capped:
        return FinalRoundDecision("shop", "final_round_level_capped")
    if coins < xp_cost:
        return FinalRoundDecision("shop", "final_round_insufficient_xp_gold")
    target_level = level + 1
    cost = experience_cost_to_target(
        level=level, target_level=target_level,
        experience_current=experience_current, experience_required=experience_required,
        xp_cost=xp_cost, xp_gain=xp_gain,
    )
    if cost.cost is None or cost.purchases is None:
        return FinalRoundDecision("recover", "final_round_experience_unknown")
    if coins >= cost.cost:
        return FinalRoundDecision(
            "buy_xp", "final_round_upgrade_affordable",
            target_level, cost.cost, cost.purchases,
        )
    return FinalRoundDecision(
        "shop", "final_round_upgrade_unaffordable",
        target_level, cost.cost, cost.purchases,
    )


def evaluate_all_in_policy(
    config: EconomyConfig | None, *, current_round: tuple[int, int] | None,
    level: int | None, coins: int | None, experience_current: int | None = None,
    experience_required: int | None = None, xp_cost: int = 4, xp_gain: int = 4,
) -> AllInDecision:
    """Allow zero reserves at the configured round, using the final target.

    ``enabled`` authorizes reserve_gold=0 and purchase_reserve_gold=0 only.
    It never overrides unknown roster evidence, placement, or the upgrade gate.
    Coins, round and progress must be freshly confirmed by the caller. Recheck
    after every action; an earlier affordable quote is not a latched budget.
    A rejected override leaves the ordinary staged economy fully available.
    """
    if config is None or config.all_in_round is None:
        return AllInDecision(False, None, None, None, "policy_disabled")
    target = config.stages[-1].target_level
    if (not isinstance(current_round, tuple) or len(current_round) != 2
            or any(type(part) is not int or not 1 <= part <= 9 for part in current_round)):
        return AllInDecision(False, target, None, None, "round_unknown")
    if current_round < config.all_in_round:
        return AllInDecision(False, target, None, None, "before_all_in_round")
    quote = experience_cost_to_target(level=level, target_level=target,
        experience_current=experience_current, experience_required=experience_required,
        xp_cost=xp_cost, xp_gain=xp_gain)
    if quote.cost is None:
        return AllInDecision(False, target, None, None, quote.reason)
    if not _nonnegative_int(coins):
        return AllInDecision(False, target, quote.cost, quote.purchases, "unknown_coins")
    if quote.cost > coins:
        return AllInDecision(False, target, quote.cost, quote.purchases, "upgrade_unaffordable")
    return AllInDecision(True, target, quote.cost, quote.purchases,
        "target_reached" if quote.purchases == 0 else "all_in_upgrade")


def select_economy_stage(
    config: EconomyConfig, *, confirmed_battle_count: int | None = None,
    coins: int | None = None, confirmed_coins: int | None = None,
    previous_index: int | None = None, current_level: int | None = None,
) -> EconomyStageSelection:
    """Choose the highest eligible stage without moving a restored stage back.

    Both coin values must be fresh, equal observations from the same stable
    page with no intervening spend. The caller must not pass cached coins as
    ``confirmed_coins``. A single reading never advances a permanent stage.
    Run ID and strategy fingerprint matching are the caller's responsibility.
    Unknown old-save battle counts use a reliable level only as a lower bound.
    """
    if not config.stages:
        raise ValueError("economy.stages 不能为空")
    if previous_index is not None and (
        not _nonnegative_int(previous_index) or previous_index >= len(config.stages)
    ):
        raise ValueError("active_economy_stage_index 超出当前阶段表范围")
    if previous_index is not None:
        index, reason = previous_index, "restored_stage"
    elif not _nonnegative_int(confirmed_battle_count) and _positive_int(current_level):
        index = max((i for i, stage in enumerate(config.stages)
                     if stage.target_level <= current_level), default=0)
        reason = "legacy_level_lower_bound"
    else:
        index, reason = 0, "initial_stage"
    verified_coins = (_nonnegative_int(coins) and _nonnegative_int(confirmed_coins)
                      and coins == confirmed_coins)
    for candidate, stage in enumerate(config.stages):
        if candidate <= index:
            continue
        by_battles = (_nonnegative_int(confirmed_battle_count)
                      and confirmed_battle_count >= stage.from_battles)
        by_coins = (verified_coins and stage.upgrade_gold is not None
                    and coins >= stage.upgrade_gold)
        if by_battles or by_coins:
            index = candidate
            reason = "battle_count" if by_battles else "verified_gold"
    return EconomyStageSelection(index, reason)


def can_afford_purchase(coins: int | None, price: int | None, reserve_gold: int) -> bool:
    """Only actual card purchases may spend the separate purchase reserve."""
    return (_nonnegative_int(coins) and _nonnegative_int(price)
            and _nonnegative_int(reserve_gold) and coins - price >= reserve_gold)


def next_economy_action(
    *, level: int | None, coins: int | None, target_level: int,
    reserve_gold: int, purchase_reserve_gold: int = 0,
    xp_cost: int | None = None, roll_cost: int | None = None,
    upgrade_allowed: bool | None = True, has_purchase_targets: bool | None = False,
    space_safe: bool | None = True, needs_prepare: bool = False,
    first_main_search: bool = False, gate_has_purchase_targets: bool | None = False,
) -> EconomyDecision:
    """Choose one action after the current shop's affordable targets are bought.

    The caller supplies the effective target and reserve after applying the
    existing first-main-character rules. ``upgrade_allowed=False`` must mean
    a confirmed formation business gate, never a failed click, unknown state,
    or insufficient funds. Only its actionable procurement gap permits rolling
    below target. None expresses unknown gate, demand or space evidence.

    Stop requests, wrong UI and unconfirmed previous actions are handled before
    calling this function. No action count, time budget, or old economy fields
    participate in this decision.
    """
    if not _positive_int(level) or not _nonnegative_int(coins):
        return EconomyDecision("recover", "unknown_level_or_coins")
    if (not _positive_int(target_level) or not _nonnegative_int(reserve_gold)
            or not _nonnegative_int(purchase_reserve_gold)):
        return EconomyDecision("recover", "invalid_economy_limits")
    if needs_prepare:
        return EconomyDecision("prepare", "candidate_needs_preparation")
    floor = reserve_gold + purchase_reserve_gold
    below_target = level < target_level
    if below_target and not first_main_search:
        if type(upgrade_allowed) is not bool:
            return EconomyDecision("recover", "upgrade_gate_unknown")
        if upgrade_allowed:
            if not _nonnegative_int(xp_cost):
                return EconomyDecision("recover", "unknown_xp_cost")
            if coins - xp_cost >= floor:
                return EconomyDecision("buy_xp", "below_target")
            return EconomyDecision("save", "xp_reserve_floor")
        if type(gate_has_purchase_targets) is not bool:
            return EconomyDecision("recover", "upgrade_gate_demand_unknown")
        if not gate_has_purchase_targets:
            return EconomyDecision("save", "gate_blocked_no_actionable_target")
    if type(has_purchase_targets) is not bool:
        return EconomyDecision("recover", "purchase_targets_unknown")
    if not has_purchase_targets:
        return EconomyDecision("save", "no_purchase_targets")
    if type(space_safe) is not bool:
        return EconomyDecision("recover", "purchase_space_unknown")
    if not space_safe:
        return EconomyDecision("prepare", "purchase_space_blocked")
    if not _nonnegative_int(roll_cost):
        return EconomyDecision("recover", "unknown_roll_cost")
    if coins - roll_cost < floor:
        return EconomyDecision("save", "roll_reserve_floor")
    reason = ("first_main_search" if first_main_search else
              "upgrade_gate_procurement" if below_target else "target_reached")
    return EconomyDecision("roll", reason)
