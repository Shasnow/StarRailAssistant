"""仅恢复经独立证据确认未生效的购买，不处理状态不确定的交易。

普通购买路径提供已有观测；本模块的额外界面读写，仅允许出现在
连续两次确认失败的恢复路径。
"""
from dataclasses import dataclass


def shop_signature(offer):
    state = getattr(getattr(offer, "state", None), "value", None)
    if state != "ready" or getattr(offer, "reason", "").startswith("partial"):
        return None
    return tuple((card.slot_index, card.character.name, card.price) for card in offer.cards)


def reliable_balance(reading, coins):
    return (type(coins) is int and coins >= 0 and reading is not None
            and getattr(reading, "reliable", False) is True
            and type(getattr(reading, "value", None)) is int and reading.value == coins)


def confirmed_noop_receipts(observations, before_coins):
    return (len(observations) == 2 and observations[0] is not None
            and observations[0] == observations[1] and observations[0][1] == before_coins)


def capture_purchase_noop_state(engine, character):
    """仅保存本次输入即将失效的证据，不执行界面读写。"""
    name = character.name
    slots = {(area, index): observation
             for area, observations in engine._observations.items()
             for index, observation in enumerate(observations)
             if observation.character is not None and observation.character.name == name}
    return dict(slots=slots,
        evidence={key: engine._slot_evidence.get(key) for key in slots},
        dirty={key for key in slots if key in engine._dirty_slots},
        bench_dirty=engine._bench_dirty,
        character=character, stars=character.stars,
        pending=name in engine._purchase_pending_names)


# ssyb：价格未知的失败必须核实库存，不能只比余额。
def resolve_page_purchase_noop(engine, ticket):
    """使用与卡片价格相符的证据，结清停滞的本页购买输入。

    正价格购买须由两张新鲜且未变化的完整商店截图，以及独立、可靠
    且未变化的余额证明未生效，之后才能恢复需求目标。免费或价格未知
    的失败须核验真实库存，因为购买或合成成功后卡片仍可能暂时显示。
    其他收据和未解决输入继续保留。
"""
    cycle = getattr(engine, "_active_demand_cycle", None) or {}
    name = ticket["card"].character.name
    earlier = cycle.get("receipts", {}).get(name, 0)
    initial = cycle.get("before", {}).get(name)
    batch_receipt = (ticket["was_pending"] and type(initial) is int
                     and initial >= 0 and type(earlier) is int and earlier > 0)
    before_copies = initial + earlier if batch_receipt else ticket["before_copies"]
    if (not confirmed_noop_receipts(ticket["observations"], ticket["before_coins"])
            or ticket["was_pending"] and not batch_receipt
            or type(before_copies) is not int or before_copies < 0
            or getattr(engine, "_placement_pending", False)
            or getattr(engine, "_pending_move", None) is not None
            or getattr(engine, "_form_change_pending", {})
            or getattr(engine, "_runtime_node_pending", None) is not None):
        return False
    state = ticket["state"]
    name = ticket["card"].character.name
    if batch_receipt or ticket["card"].price is None or ticket["card"].price == 0:
        # 免费购买可能已真实触发合成，但商店画面尚未更新。
        # 因此，余额相同不能证明库存未变化。
        pending_before = set(engine._purchase_pending_names)
        other_pending = pending_before - {name}
        confirmed = (engine._recheck_purchased_characters({name}, allow_verified_absent={name})
                     if before_copies == 0 else engine._recheck_purchased_characters({name}))
        ticket["closed"] = bool(confirmed or getattr(engine, "_coin_shop_open", None) is False)
        engine._purchase_pending_names.update(other_pending)
        actual = engine._held_purchase_copies(name) if confirmed else None
        ticket["inventory_copies"] = actual
        if (not confirmed or type(actual) is not int or engine._bench_dirty
                or actual < before_copies):
            engine._purchase_pending_names.update(pending_before | {name})
            return False
        ticket["inventory_confirmed"] = actual >= before_copies + 1
        if ticket["inventory_confirmed"]:
            engine._purchase_pending_names.add(name)
        elif not state["pending"]:
            engine._purchase_pending_names.discard(name)
        if not ticket["inventory_confirmed"]:
            # 关闭再打开商店时仍保留经独立证据确认的失败槽位，
            # 防止重复购买；仍由现有页面身份与真实刷新规则使缓存失效。
            failed = getattr(engine, "_shop_stall_failed_cards", None)
            if failed is not None:
                card = ticket["card"]
                failed.add((card.slot_index, name, card.price))
        return True
    for (area, index), observation in state["slots"].items():
        current = engine._observations[area][index]
        if current.character is None or current.character.name != name:
            return False
    for key, observation in state["slots"].items():
        area, index = key
        engine._observations[area][index] = observation
        if key in state["dirty"]:
            engine._dirty_slots.add(key)
        else:
            engine._dirty_slots.discard(key)
        evidence = state["evidence"][key]
        if evidence is None:
            engine._slot_evidence.pop(key, None)
        else:
            engine._slot_evidence[key] = evidence
    state["character"].stars = state["stars"]
    engine._bench_dirty = state["bench_dirty"]
    if not state["pending"]:
        engine._purchase_pending_names.discard(name)
    return True


def purchase_noop_evidence(card, before_offer, after_offer, before_coins, coins,
                           before_reading, after_reading, *, allow_zero_unpriced=False):
    """要求完整页面保持不变，并取得独立且可靠的余额读数。

    免费或价格未知的卡片，只能明确选择跳过当前页，不能进入严格的
    付费购买重建路径。卡片被替换或消失、文字识别不完整、余额不足，
    或余额发生任何变化，都不能授权该恢复。完整页面检查也能发现
    其他自动操作造成的商店变化。
"""
    valid_price = (type(card.price) is int and card.price > 0 or allow_zero_unpriced
                   and (card.price is None or type(card.price) is int and card.price >= 0))
    if (not valid_price or type(before_coins) is not int or before_coins < 0
            or card.price is not None and before_coins < card.price
            or not reliable_balance(before_reading, before_coins)
            or not reliable_balance(after_reading, coins) or coins != before_coins):
        return None
    signature = shop_signature(before_offer)
    if signature is None or signature != shop_signature(after_offer):
        return None
    target = (card.slot_index, card.character.name, card.price)
    if sum(entry == target for entry in signature) != 1:
        return None
    return signature, before_coins


@dataclass(frozen=True)
class StallDecision:
    status: str
    reason: str
    offer: object = None
    coins: int | None = None
    cost: int | None = None


# Yukki：恢复本页只结清证据，不授予额外刷新或经验输入。
def prepare_stalled_shop_rebuild(engine, card, *, before_coins, before_copies,
                                 was_pending, observations, actions, purchases,
                                 refreshes, limits, reserve, opening_allowed):
    """核实付费购买未生效并返回当前页，不执行经济操作输入。

    调用方跳过失败槽位后继续普通经济策略。保留已有关键字参数以兼容
    旧调用方；此辅助函数不授权刷新或购买经验，也不检查对应费用与预算。
    """
    if (was_pending or type(before_copies) is not int or before_copies < 0
            or not confirmed_noop_receipts(observations, before_coins)):
        return StallDecision("uncertain", "purchase_not_confirmed")
    name = card.character.name
    if (getattr(engine, "_placement_pending", False)
            or getattr(engine, "_pending_move", None) is not None
            or getattr(engine, "_form_change_pending", {})
            or getattr(engine, "_runtime_node_pending", None) is not None):
        return StallDecision("uncertain", "purchase_not_confirmed")
    # 丢弃商店页前，先结清本次和前序批次收据。
    names = set(engine._purchase_pending_names) | {name}
    confirmed = (engine._recheck_purchased_characters(names, allow_verified_absent={name})
                 if before_copies == 0 else engine._recheck_purchased_characters(names))
    if not confirmed:
        engine._purchase_pending_names.update(names)
        return StallDecision("uncertain", "purchase_recheck_unknown")
    # 重新开店后的上下文也通过认证之前，继续保留此收据。
    # 后续恢复读写发生停止或异常时，也不能静默清除此收据。
    engine._purchase_pending_names.add(name)
    actual = engine._held_purchase_copies(name)
    if type(actual) is not int or actual != before_copies or engine._bench_dirty:
        engine._purchase_pending_names.add(name)
        return StallDecision("uncertain", "purchase_stall_inventory_changed")
    if engine._purchase_pending_names - {name}:
        engine._purchase_pending_names.add(name)
        return StallDecision("uncertain", "purchase_recheck_unknown")
    if not engine._set_shop_open(True):
        engine._purchase_pending_names.add(name)
        return StallDecision("uncertain", "shop_not_open_after_recheck")
    # 重新开店与角色核验期间，其他自动购买行为可能改变商店。
    offer = engine._scan_store()
    coins = engine.get_coins()
    if (shop_signature(offer) != observations[0][0] or coins != before_coins
            or not reliable_balance(engine._last_coin_observation, coins)):
        engine._purchase_pending_names.add(name)
        engine._invalidate_roster_evidence("shop_stall_context_changed")
        return StallDecision("uncertain", "purchase_stall_context_changed")
    engine._purchase_pending_names.discard(name)
    engine._purchase_before_copies.pop(name, None)
    engine._record_checkpoint(phase="preparation", pending_actions=[])
    return StallDecision("noop", "purchase_stall_verified_noop", offer, coins)
