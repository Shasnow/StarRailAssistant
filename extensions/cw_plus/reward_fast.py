"""奖励回合的可选策略与缓存需求；本模块不执行界面输入。"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RewardPurchaseEvidence:
    """单次输入前冻结的事实；后续库存读取不能替代这些购前事实。"""
    preparation_id: object
    page_key: tuple
    action_id: str
    slot_index: int
    name: str
    price: int | None
    price_evidence: str
    before_coins: int
    before_reading: object
    before_copies: int | None
    shop_signature: tuple
    attempted_slots: frozenset
    layout_revision: int
    context_epoch: int


def parse_reward_fast_rounds(data) -> frozenset[tuple[int, int]]:
    """省略或空列表时保持普通准备流程。"""
    if data is None:
        return frozenset()
    if not isinstance(data, list):
        raise ValueError("reward_fast_rounds 必须为回合列表")
    rounds = set()
    for label in data:
        if not isinstance(label, str) or re.fullmatch(r"[1-9]-[1-9]", label) is None:
            raise ValueError("reward_fast_rounds 必须使用 x-y 格式的回合，如 1-8")
        value = tuple(int(part) for part in label.split("-"))
        if value in rounds:
            raise ValueError("reward_fast_rounds 不得重复")
        rounds.add(value)
    return frozenset(rounds)


def is_reward_fast_round(rounds, current_round) -> bool:
    """强制终局运营始终优先于配置的奖励速战。"""
    return (isinstance(current_round, tuple) and len(current_round) == 2
        and all(type(part) is int and 1 <= part <= 9 for part in current_round)
        and current_round != (3, 7) and current_round in rounds)


# Yukki：奖励回合仅复用已确认需求，后续整备再补足完整观测。
def reward_fast_cached_demand(goals, observations) -> dict[str, int]:
    """沿用现有持有记录，未知部分允许少量多买，不触发额外识别。

    这里只生成本页的采购上限；结果不能用于布阵、出售或经验门槛。
    采购后的真实合成及落位留给下一普通准备阶段识别。
    """
    needed = {}
    for name, stars in goals.items():
        if type(stars) is not int or stars < 1:
            continue
        target = 3 ** (min(stars, 3) - 1)
        held = 0
        for slots in observations.values():
            for obs in slots:
                if (getattr(obs, "character", None) is not None
                        and obs.character.name == name
                        and getattr(obs.state, "value", obs.state) == "known"
                        and type(obs.stars) is int and 1 <= obs.stars <= 3):
                    held += 3 ** (obs.stars - 1)
        if held < target:
            needed[name] = target - held
    return needed
