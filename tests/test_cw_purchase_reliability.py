"""公开整备入口的购后证据回归；不替换视觉或决策方法。"""
from dataclasses import replace

import pytest

from SRACore.util.errors import ThreadStoppedError
from extensions.cw_plus.logic import SlotState
from extensions.cw_plus.preparation import Readiness
from tests.cw_reliability_replay import replay  # noqa: F401


def test_purchase_scan_longer_than_ttl_keeps_its_real_field_receipts(replay):
    replay.operator.ocr_seconds = 65

    result = replay.task.prepare_for_battle()

    assert result.state == Readiness.READY, result
    assert replay.clock.value - 1000 > 60
    assert replay.operator.inputs == []


def seed_structural_empty(replay, evidence="zero_population"):
    for area in ("on_field", "off_field"):
        for index, obs in enumerate(replay.task._observations[area]):
            if obs.state == SlotState.EMPTY:
                replay.task._observations[area][index] = replace(obs, evidence=evidence)
                replay.task._slot_evidence.pop((area, index), None)
                replay.operator.ambiguous_empty.add((area, index))
    replay.task._purchase_scan_baseline = (replay.task._layout_revision,
        {area: list(slots) for area, slots in replay.task._observations.items()})
    # 不画入空标，保证此次识别不能以模板补足基线所没有的逐槽截图收据。
    replay.operator.frame.paste((15, 25, 35), (600, 300, 1200, 650))
    replay.clock.advance(65)


@pytest.mark.parametrize("evidence", ["zero_population", "new_game_empty"])
def test_untouched_structural_empty_is_not_an_expired_ocr_receipt(replay, evidence):
    seed_structural_empty(replay, evidence)

    result = replay.task.prepare_for_battle()

    assert result.state == Readiness.READY, result
    assert replay.operator.inputs == []


def test_dirty_destination_cannot_reuse_an_old_empty_baseline(replay):
    seed_structural_empty(replay)
    replay.task._purchase_pending_names.clear()
    replay.task._purchase_scan_baseline = None
    replay.task._dirty_slots.discard(("in_hand", 0))
    replay.task._dirty_slots.add(("on_field", 2))

    result = replay.task.prepare_for_battle()

    assert result.state == Readiness.BLOCKED, result
    assert replay.operator.inputs == []


def test_full_recovery_keeps_fresh_empty_bench_evidence_even_if_layout_is_missing(replay):
    replay.task._purchase_scan_baseline = (None, {})

    result = replay.task.prepare_for_battle()

    # 此控制帧刻意没有后台边框，不能因备战席已知而跳过布局阻挡。
    assert result.state == Readiness.BLOCKED
    assert "backend_layout_not_confirmed" in {result.reason, result.blocked_reason}
    assert not [slot for slot in replay.operator.slot_clicks
                if slot[0] == "in_hand" and slot not in replay.operator.scene]
    assert replay.operator.inputs == []


@pytest.mark.parametrize("fault", ["unknown", "missing_stars"])
def test_unreadable_purchased_character_never_authorizes_preparation(replay, fault):
    getattr(replay.operator, fault).add(("in_hand", 0))

    result = replay.task.prepare_for_battle()

    assert result.state == Readiness.BLOCKED, result
    assert replay.operator.inputs == []


def test_already_expired_unrelated_identity_must_be_read_again(replay):
    replay.clock.advance(61)
    replay.operator.unknown.add(("on_field", 0))

    result = replay.task.prepare_for_battle()

    assert result.state == Readiness.BLOCKED, result
    assert ("on_field", 0) in replay.operator.slot_clicks
    assert replay.operator.inputs == []


def test_unconfirmed_transaction_blocks_before_any_read_or_input(replay):
    replay.task._preparation_deadline = replay.clock.value + 300
    replay.task._reward_fast_page_ledger = {"pending": {"name": "花火"}}

    result = replay.task.prepare_for_battle()

    assert result.state == Readiness.BLOCKED
    assert result.reason == "purchase_transaction_unconfirmed"
    assert replay.clock.value == 1000
    assert replay.operator.slot_clicks == replay.operator.inputs == []


def test_capture_loss_never_turns_a_purchase_into_ready(replay):
    replay.operator.capture_error = True

    result = replay.task.prepare_for_battle()

    assert result.state == Readiness.BLOCKED, result
    assert replay.operator.inputs == []


def test_stop_during_purchase_ocr_is_propagated_without_replaying_input(replay):
    replay.operator.stop_on_ocr = True

    with pytest.raises(ThreadStoppedError):
        replay.task.prepare_for_battle()

    assert replay.operator.inputs == []
