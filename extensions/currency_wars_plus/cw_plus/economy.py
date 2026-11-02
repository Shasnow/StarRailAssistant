"""货币战争的纯函数经济决策，结果具有确定性。
观测、角色需求、动作确认和会话持久化由调用方负责。
这里的决策不会点击界面，也不假定具体阵容。
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping


# 已核实的商店等级标签与经验进度分母：
# 五级为 20，六级为 40，七级为 52，八级为 72。
# 这些固定需求只补充后续等级，当前等级仍使用实时观测。
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


# ssyb：经济字段先严格校验，再生成不含界面输入的决策。
def parse_economy_config(
    raw: Any, *, main_c_search_level: int | None = None, max_level: int = 20,
) -> EconomyConfig | None:
    """验证可选的 economy 对象；None 表示沿用旧版经济逻辑。
    仅在配置主力角色时传入 main_c_search_level。
    等级边界与现有商店等级解析器支持的范围一致。
    即便对象已禁用，也会拒绝拼错的顶层字段名和非布尔类型的 enabled 标志，但不解释未启用的阶段表。
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
    """结合实时与已验证进度，为剩余整级升级计算预算边界。
    调用方必须通过两次稳定读取一起确认等级和进度。
    实时分母须与已验证表中同等级记录一致，每个后续等级也必须存在于该表。
    各等级分别向上取整，因此足够的预算不假定剩余经验能结转。
    每次输入后重新观测，不能把报价当成可盲发的购买次数。
    未知后续等级绝不估算。
    """
    if not _positive_int(target_level):
        return ExperienceCost(None, None, "invalid_target_level")
    if not _positive_int(level):
        return ExperienceCost(None, None, "unknown_level")
    if level >= target_level:
        return ExperienceCost(0, 0, "target_reached")
    if not _nonnegative_int(xp_cost) or not _positive_int(xp_gain):
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
    """在最终回合花完金币，仅在预算足够完成下一整级时升级。
    回合检测由调用方负责，每次动作后都必须重新观测。
    攻略目标、金币保留量和升级门槛不影响此决策。
    """
    if not _positive_int(level) or not _nonnegative_int(coins):
        return FinalRoundDecision("recover", "final_round_unknown_level_or_coins")
    if type(level_capped) is not bool:
        return FinalRoundDecision("recover", "final_round_cap_unknown")
    if not _nonnegative_int(xp_cost) or not _positive_int(xp_gain):
        return FinalRoundDecision("recover", "final_round_invalid_experience_purchase")
    if coins == 0 and (xp_cost != 0 or level_capped):
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
    """在配置的回合允许零保留金币，并使用最终目标。
    enabled 仅授权 reserve_gold=0 与 purchase_reserve_gold=0；不能覆盖未知的角色证据、布阵规则或升级门槛。
    金币、回合和进度须由调用方刚刚确认。
    每次动作后重新检查；先前可负担的报价不能作为锁定预算。
    覆盖规则被拒绝时，常规分阶段经济逻辑仍完整可用。
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
    confirmed_battle_lower_bound: int = 0,
    coins: int | None = None, confirmed_coins: int | None = None,
    previous_index: int | None = None, current_level: int | None = None,
    recheck_level_lower_bound: bool = False,
) -> EconomyStageSelection:
    """选择满足条件的最高阶段，且不使已恢复的阶段回退。
    两个金币值必须来自同一稳定页面的新鲜且相等的观测，中间不能发生支出。
    调用方不能把缓存金币传入 confirmed_coins。
    单次读取不能推进持久阶段。
    局次 ID 与攻略指纹匹配由调用方负责。
    总历史未知时，新增已完成战斗的下界可证明阶段门槛已经满足。
    等级复核须由调用方认证新鲜读数，不从等级或关卡反推战斗数。
    """
    if not config.stages:
        raise ValueError("economy.stages 不能为空")
    if not _nonnegative_int(confirmed_battle_lower_bound):
        raise ValueError("confirmed_battle_lower_bound 必须为非负整数")
    if (_nonnegative_int(confirmed_battle_count)
            and confirmed_battle_lower_bound > confirmed_battle_count):
        raise ValueError("confirmed_battle_lower_bound 不得大于已知总场次")
    if type(recheck_level_lower_bound) is not bool:
        raise ValueError("recheck_level_lower_bound 必须为布尔值")
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
    if (recheck_level_lower_bound and not _nonnegative_int(confirmed_battle_count)
            and _positive_int(current_level)):
        by_level = max((i for i, stage in enumerate(config.stages)
                        if stage.target_level <= current_level), default=0)
        if by_level > index:
            index, reason = by_level, "rechecked_level_lower_bound"
    verified_coins = (_nonnegative_int(coins) and _nonnegative_int(confirmed_coins)
                      and coins == confirmed_coins)
    for candidate, stage in enumerate(config.stages):
        if candidate <= index:
            continue
        by_battles = (_nonnegative_int(confirmed_battle_count)
                      and confirmed_battle_count >= stage.from_battles)
        by_lower_bound = confirmed_battle_lower_bound >= stage.from_battles
        by_coins = (verified_coins and stage.upgrade_gold is not None
                    and coins >= stage.upgrade_gold)
        if by_battles or by_lower_bound or by_coins:
            index = candidate
            reason = ("battle_count" if by_battles else
                      "battle_lower_bound" if by_lower_bound else "verified_gold")
    return EconomyStageSelection(index, reason)


def can_afford_purchase(coins: int | None, price: int | None, reserve_gold: int) -> bool:
    """只有真实的角色购买才能使用独立的购买保留金币。"""
    return (_nonnegative_int(coins) and _nonnegative_int(price)
            and _nonnegative_int(reserve_gold)
            and (price == 0 or coins - price >= reserve_gold))


# Yukki：保留金币、需求与升级门槛共同约束下一步动作。
def next_economy_action(
    *, level: int | None, coins: int | None, target_level: int,
    reserve_gold: int, purchase_reserve_gold: int = 0,
    xp_cost: int | None = None, roll_cost: int | None = None,
    upgrade_allowed: bool | None = True, has_purchase_targets: bool | None = False,
    space_safe: bool | None = True, needs_prepare: bool = False,
    first_main_search: bool = False, gate_has_purchase_targets: bool | None = False,
    first_main_purchase_reserve_gold: int = 0,
) -> EconomyDecision:
    """当前商店中可负担的目标购买完后，选择一个动作。
    调用方应在应用现有首个主力角色规则后提供实际目标与保留量。
    upgrade_allowed=False 必须代表已确认的阵容业务门槛，不能代表点击失败、状态未知或金币不足。
    只有可实际采购补齐的缺口才允许在未达等级目标时刷新。
    None 表示门槛、需求或空间证据未知。
    停止请求、错误界面和前一动作未确认的情况须在调用前处理。
    动作次数、时间预算或旧经济字段均不参与此决策。
    """
    if not _positive_int(level) or not _nonnegative_int(coins):
        return EconomyDecision("recover", "unknown_level_or_coins")
    if (not _positive_int(target_level) or not _nonnegative_int(reserve_gold)
            or not _nonnegative_int(purchase_reserve_gold)
            or not _nonnegative_int(first_main_purchase_reserve_gold)):
        return EconomyDecision("recover", "invalid_economy_limits")
    if needs_prepare:
        return EconomyDecision("prepare", "candidate_needs_preparation")
    # 首次主力搜索有独立买牌预算：只约束刷新，不提高实际买牌保留线。
    # 首次上场确认后，恢复常规购买预算。
    floor = reserve_gold + (first_main_purchase_reserve_gold if first_main_search else purchase_reserve_gold)
    below_target = level < target_level
    if below_target and not first_main_search:
        if type(upgrade_allowed) is not bool:
            return EconomyDecision("recover", "upgrade_gate_unknown")
        if upgrade_allowed:
            if not _nonnegative_int(xp_cost):
                return EconomyDecision("recover", "unknown_xp_cost")
            # 明确观测到的免费输入不会继续降低已经偏低的余额。
            # 上方的阵容门槛仍然适用。
            if xp_cost == 0 or coins - xp_cost >= floor:
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
    if roll_cost != 0 and coins - roll_cost < floor:
        return EconomyDecision("save", "roll_reserve_floor")
    reason = ("first_main_search" if first_main_search else
              "upgrade_gate_procurement" if below_target else "target_reached")
    return EconomyDecision("roll", reason)
