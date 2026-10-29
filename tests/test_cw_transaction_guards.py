"""保留上游已有交易检查；这些控制不是本分支新发明的销售或装备算法。"""
from dataclasses import replace

import pytest

from extensions.cw_plus.characters import Characters
from extensions.cw_plus.logic import ActionResult, SlotObservation, SlotState
from extensions.cw_plus.preparation import Readiness
from tests.cw_reliability_replay import replay  # noqa: F401


def sale_state(replay, *, game_accepts):
    task, operator = replay.task, replay.operator
    character = Characters.get_character("万敌")
    operator.scene[("in_hand", 0)] = character.name, 1
    observation = SlotObservation(0, SlotState.KNOWN, character, True, "name_match", stars=1)
    task._observations["in_hand"][0] = observation
    task.in_hand_character[0] = character
    task._slot_evidence["in_hand", 0] = observation, replay.clock.value
    task._purchase_pending_names.clear()
    task._purchase_scan_baseline = None
    task._dirty_slots.clear()
    task._population_current = task.max_team_size = 3

    def drag_to(*args, **kwargs):
        operator.inputs.append(("drag", args))
        if game_accepts:
            operator.scene.pop(("in_hand", 0))
        return True  # 系统调用完成不等于游戏已经出售。

    operator.drag_to = drag_to


def test_failed_sale_is_reobserved_but_never_dragged_twice(replay):
    sale_state(replay, game_accepts=False)

    result = replay.task.sell_character()

    assert result.result == ActionResult.INDETERMINATE
    assert result.reason == "sale_not_confirmed"
    assert result.attempted == 1 and result.confirmed == 0
    assert len(replay.operator.inputs) == 1


def test_sale_requires_observed_inventory_change(replay):
    sale_state(replay, game_accepts=True)

    result = replay.task.sell_character()

    assert result.result == ActionResult.CONFIRMED
    assert result.attempted == result.confirmed == 1
    assert len(replay.operator.inputs) == 1


@pytest.mark.parametrize("fault", ["unknown_identity", "name_lost_before_drag"])
def test_unknown_sale_source_never_authorizes_drag(replay, fault):
    sale_state(replay, game_accepts=False)
    old = replay.task._observations["in_hand"][0]
    if fault == "unknown_identity":
        replay.task._observations["in_hand"][0] = replace(old, state=SlotState.UNKNOWN)
    else:
        # 已知非攻略余牌仍须在输入前重新读到同一姓名，不能以旧名字出售。
        replay.operator.unknown.add(("in_hand", 0))

    result = replay.task.sell_character()

    assert result.attempted == result.confirmed == 0
    assert replay.operator.inputs == []


def test_unresolved_equipment_receipt_keeps_preparation_blocked(replay):
    task, operator = replay.task, replay.operator
    task._purchase_pending_names.clear()
    task._purchase_scan_baseline = None
    task._dirty_slots.clear()
    task._equipment_choice_pending = {"input_sent": True}

    result = task.prepare_for_battle()

    assert result.state == Readiness.BLOCKED
    assert "page_action_not_confirmed" in {result.reason, result.blocked_reason}
    assert operator.inputs == []
