"""Preparation flow tests isolate game I/O and checkpoint files.

Only fixture functions/classes are reused; no existing TestCase is inherited or
collected a second time. Physical board changes are independent of cached state.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
_fixture_spec = importlib.util.spec_from_file_location(
    "_currency_wars_preparation_fixture", ROOT / "tests/test_currency_wars_flow.py")
fixture = importlib.util.module_from_spec(_fixture_spec)
sys.modules[_fixture_spec.name] = fixture
_fixture_spec.loader.exec_module(fixture)


class FakeClock:
    def __init__(self):
        self.seconds = 1.0

    def monotonic(self):
        return self.seconds

    def advance(self, seconds):
        self.seconds += seconds

    def time_ns(self):
        return int(self.seconds * 1_000_000_000)


class TimedOperator(fixture.FakeOperator):
    def __init__(self, clock):
        super().__init__()
        self.clock = clock

    def record(self, name, *args, **kwargs):
        super().record(name, *args, **kwargs)
        self.clock.advance(0.02)

    def sleep(self, seconds):
        self.record("sleep", seconds)
        self.clock.advance(seconds)


class CurrencyWarsPreparationTests(unittest.TestCase):
    def setUp(self):
        self.module, self.characters, self.logic, self.module_names = fixture.load_isolated_task()
        self.addCleanup(lambda: [sys.modules.pop(name, None) for name in self.module_names])
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.session_path = Path(temporary.name) / "current_run.json"
        session_module = next(sys.modules[name] for name in self.module_names if name.endswith("_session"))
        self.session_class = session_module.SessionStore
        self.fixture_session_factory = self.module.SessionStore
        self.module.SessionStore = lambda _path, **kwargs: self.session_class(self.session_path, **kwargs)
        self.clock = FakeClock()
        self.module.time = types.SimpleNamespace(monotonic=self.clock.monotonic,
                                                time_ns=self.clock.time_ns)
        self.operator = TimedOperator(self.clock)
        self.task = self.module.CurrencyWars(self.operator, runtimes=1)
        self.task.is_running = True
        self.task.get_coins = Mock(return_value=50)
        self.task.get_level = Mock(return_value=5)
        self.task.handle_special_event = Mock()
        self.task.detect_silver_wolf_lv999 = Mock()
        self.task._set_shop_open = Mock(return_value=True)
        # Board and purchase tests run on a confirmed ordinary preparation.
        self.task._read_preparation_round = Mock(return_value=(2, 1))
        self.task._vision.capture_sample = Mock(return_value=None)
        self.task._vision.begin_sample_scope = Mock()
        self.task.update_max_team_size = Mock()
        self.task.preparation_budget.update(seconds=20, total_seconds=60,
                                            actions=12, recoveries=2, move_retries=1)
        self.physical = {}
        self.drag_baselines = []

    def character(self, name):
        return self.characters.Characters.get_character(name)

    def observation(self, area, index, character=None, *, state=None, evidence="test observation"):
        state = state or (self.logic.SlotState.KNOWN if character else self.logic.SlotState.EMPTY)
        return self.logic.SlotObservation(index, state, character=character,
            occupied=True if state == self.logic.SlotState.KNOWN else
                     False if state == self.logic.SlotState.EMPTY else None,
            evidence=evidence, stars=1 if character else None, revision=1)

    def observe(self, area, index, character=None, *, state=None):
        observed = self.observation(area, index, character, state=state)
        self.task._set_observation(area, observed)
        self.physical[(area, index)] = observed
        return observed

    def empty_board(self):
        for area in ("on_field", "off_field", "in_hand"):
            for index in range(len(getattr(self.task, area + "_area"))):
                self.observe(area, index)
        self.task._field_observed_at = self.clock.monotonic()
        self.task._bench_observed_at = self.clock.monotonic()
        self.task._bench_dirty = False

    def install_board(self, *, unchanged_names=(), unknown_ends=False):
        coordinates = {point: (area, index)
                       for area in ("on_field", "off_field", "in_hand")
                       for index, point in enumerate(getattr(self.task, area + "_area"))}

        def read(area, index, *args, **kwargs):
            self.clock.advance(0.02)
            return self.physical.get((area, index), self.observation(
                area, index, state=self.logic.SlotState.UNKNOWN))

        def drag(from_x, from_y, to_x, to_y, **kwargs):
            self.operator.record("drag", from_x, from_y, to_x, to_y, **kwargs)
            source = coordinates[(from_x, from_y)]
            target = coordinates[(to_x, to_y)]
            before_source, before_target = self.physical[source], self.physical[target]
            self.drag_baselines.append((before_source.character.name,
                source, target, before_target.state.value,
                getattr(before_target.character, "name", None)))
            if unknown_ends:
                for area, index in (source, target):
                    self.physical[(area, index)] = self.observation(
                        area, index, state=self.logic.SlotState.UNKNOWN)
            elif before_source.character.name not in unchanged_names:
                self.physical[source] = replace(before_target, slot_index=source[1])
                self.physical[target] = replace(before_source, slot_index=target[1])
            return True

        def scan_field(*args, **kwargs):
            for area in ("on_field", "off_field"):
                for index in range(len(self.task._observations[area])):
                    self.task._set_observation(area, read(area, index))
            self.task._field_observed_at = self.clock.monotonic()
            # A scan cannot resolve unknown endpoints by clearing a pending flag.
            if self.task._pending_move is None:
                self.task._placement_pending = False
            self.task._reconcile_placed()
            self.task._confirm_main_c_fielded()

        def scan_bench(*args, **kwargs):
            for index in range(len(self.task._observations["in_hand"])):
                self.task._set_observation("in_hand", read("in_hand", index))
            self.task._bench_observed_at = self.clock.monotonic()
            self.task._bench_dirty = False
            self.task._reconcile_placed()

        self.operator.drag_to = Mock(side_effect=drag)
        self.task._observe_slot = Mock(side_effect=read)
        self.task.refresh_character = Mock(side_effect=scan_field)
        self.task.get_in_hand_area = Mock(side_effect=scan_bench)
        return scan_field, scan_bench

    def stage(self, on_field, off_field=(), priority=()):
        self.task.strategy_characters = {name: 2 for name in on_field + tuple(off_field)}
        self.task.formation_config = self.module.FormationConfig({}, {}, {}, (
            self.module.FormationStage("test stage", 0, tuple(on_field), tuple(off_field),
                                       priority=tuple(priority)),
        ))

    def battle_button_available(self):
        box = fixture.FakeBox(source="BATTLE")
        self.operator.wait_any_img = Mock(return_value=(0, box))
        self.operator.wait_img = Mock(return_value=box)
        self.task._wait_battle_entry = Mock(return_value=4)
        return box

    def test_strict_move_needs_both_endpoints_and_does_not_unlock_main_c(self):
        self.empty_board()
        main = self.character("灵砂")
        self.task.main_c = main.name
        self.task.strategy_characters = {main.name: 2}
        self.observe("in_hand", 0, main)
        self.install_board(unknown_ends=True)
        self.assertFalse(self.task.swap_character_between_areas("in_hand", 0, "on_field", 0))
        self.assertEqual(self.task._last_move_result.status, self.module.MoveStatus.INDETERMINATE)
        self.assertTrue(self.task._placement_pending)
        self.assertIsNotNone(self.task._pending_move)
        self.assertFalse(self.task.main_c_first_fielded_confirmed)
        self.assertEqual(len(self.operator.drags()), 1)

    def test_strict_move_distinguishes_unchanged_and_confirmed_change(self):
        self.empty_board()
        character = self.character("爻光")
        self.observe("in_hand", 0, character)
        self.install_board(unchanged_names=(character.name,))
        self.assertFalse(self.task.swap_character_between_areas("in_hand", 0, "on_field", 0))
        self.assertEqual(self.task._last_move_result.status, self.module.MoveStatus.CONFIRMED_UNCHANGED)
        self.assertFalse(self.task._placement_pending)
        self.assertIsNone(self.task._pending_move)
        self.install_board()
        self.assertTrue(self.task.swap_character_between_areas("in_hand", 0, "on_field", 0))
        self.assertEqual(self.task._last_move_result.status, self.module.MoveStatus.CONFIRMED_CHANGED)
        self.assertEqual(self.task._observations["in_hand"][0].state, self.logic.SlotState.EMPTY)
        self.assertEqual(self.task._observations["on_field"][0].character.name, character.name)

    def test_first_unchanged_move_retries_once_then_other_new_card_can_be_fielded(self):
        self.empty_board()
        # One backend endpoint makes exclusions meaningful, without trying
        # another coordinate for the same failed character repeatedly.
        self.task.off_field_area = self.task.off_field_area[:1]
        self.task.off_field_character = self.task.off_field_character[:1]
        self.task._observations["off_field"] = self.task._observations["off_field"][:1]
        self.task.max_team_size = 3
        self.stage(("灵砂", "希儿"), ("千冶·刃",), ("千冶·刃", "希儿", "灵砂"))
        self.observe("on_field", 0, self.character("灵砂"))
        self.observe("off_field", 0, self.character("吉尔伽美什"))
        self.observe("in_hand", 0, self.character("千冶·刃"))
        self.observe("in_hand", 1, self.character("希儿"))
        self.install_board(unchanged_names=("千冶·刃",))
        result = self.task.prepare_for_battle()
        self.assertIn(result.state, (self.module.Readiness.READY, self.module.Readiness.DEGRADED))
        blade_origin = self.task.in_hand_area[0]
        blade_drags = [move for move in self.operator.drags() if tuple(move[:2]) == blade_origin]
        self.assertGreaterEqual(len(blade_drags), 2)
        self.assertLessEqual(len(blade_drags), 4)
        baselines = [entry[1:] for entry in self.drag_baselines if entry[0] == "千冶·刃"]
        self.assertTrue(all(baselines.count(entry) <= 2 for entry in set(baselines)))
        self.assertTrue(any(o.state == self.logic.SlotState.KNOWN and o.character.name == "希儿"
                            for o in self.task._observations["on_field"]))
        self.assertGreaterEqual(result.attempts, 3)
        self.assertIsNone(self.task._pending_move)
        self.assertFalse(self.task._placement_pending)

    def test_unknown_endpoints_block_battle_without_repeating_drag(self):
        self.empty_board()
        self.task.max_team_size = 3
        self.observe("on_field", 0, self.character("灵砂"))
        self.observe("in_hand", 0, self.character("千冶·刃"))
        self.install_board(unknown_ends=True)
        self.assertFalse(self.task.swap_character_between_areas("in_hand", 0, "off_field", 0))
        result = self.task.prepare_for_battle()
        self.assertEqual(result.state, self.module.Readiness.BLOCKED)
        self.assertEqual(len(self.operator.drags()), 1)
        box = self.battle_button_available()
        try:
            answer = self.task.battle()
        except RuntimeError:
            answer = False
        self.assertFalse(answer)
        self.assertFalse(any(name == "click_box" and args and args[0] is box
                             for name, args, _ in self.operator.calls))
        self.assertEqual(len(self.operator.drags()), 1)


    def test_exhausted_readiness_blocks_battle_even_with_frontline_and_no_pending_move(self):
        self.empty_board()
        self.task.max_team_size = 2
        self.task.main_c = "希儿"
        self.stage(("灵砂", "希儿"))
        self.observe("on_field", 0, self.character("灵砂"))
        self.observe("in_hand", 0, self.character("希儿"))
        self.install_board()
        self.task.preparation_budget.update(seconds=1, total_seconds=1)
        self.task._begin_preparation()
        self.clock.advance(2)
        self.assertIsNone(self.task._pending_move)
        self.assertFalse(self.task._placement_pending)
        box = self.battle_button_available()
        with self.assertRaises(RuntimeError):
            self.task.battle()
        self.assertFalse(any(name == "click_box" and args and args[0] is box
                             for name, args, _ in self.operator.calls))
        self.assertEqual(self.operator.drags(), [])

    def test_normal_purchase_batch_fields_before_any_additional_search(self):
        self.empty_board()
        self.task.max_team_size = 2
        self.task.min_level = 5
        self.task.mid_level = 5
        self.stage(("灵砂", "希儿"))
        self.observe("on_field", 0, self.character("灵砂"))
        self.install_board()
        card = self.logic.ShopCard(0, self.character("希儿"), self.task.store_area[0],
                                   raw_text="希儿", price=3, price_evidence="price_badge")
        self.task._scan_store = Mock(side_effect=[
            self.logic.ShopObservation(self.logic.ShopState.READY, (card,)),
            self.logic.ShopObservation(self.logic.ShopState.READY, reason="partial_test_stop")])

        def confirm(*args, **kwargs):
            self.physical[("in_hand", 0)] = self.observation("in_hand", 0, card.character)
            return self.logic.ActionResult.CONFIRMED

        self.task._confirm_purchase = Mock(side_effect=confirm)
        result = self.task.shopping()
        self.assertEqual(result.reason, "partial_store")
        self.assertEqual(result.confirmed_purchases, 1)
        readiness = self.task.prepare_for_battle()
        self.assertNotEqual(readiness.state, self.module.Readiness.BLOCKED)
        self.assertTrue(any(o.state == self.logic.SlotState.KNOWN and o.character.name == "希儿"
                            for o in self.task._observations["on_field"]))
        self.assertEqual(self.task._scan_store.call_count, 2)
        self.assertNotIn("d", self.operator.keys())
        self.assertNotIn("f", self.operator.keys())


    def run_real_loop_purchase(self, *, continuing):
        self.empty_board()
        self.task.max_team_size = 2
        self.task.min_level = self.task.mid_level = 5
        self.task.is_continue = continuing
        self.task._confirmed_battle_count = None if continuing else 0
        self.task._read_preparation_round = Mock(side_effect=lambda:
            (2, 1) if continuing else (1, self.task._confirmed_battle_count + 1))
        self.stage(("灵砂", "希儿"))
        self.observe("on_field", 0, self.character("灵砂"))
        self.install_board()
        self.task.harvest_crystals = Mock()
        self.task.handle_characters_updated = Mock()
        self.task.sell_character = Mock(return_value=self.logic.SellResult(self.logic.ActionResult.CONFIRMED))
        self.task.get_on_field_area = Mock()
        self.task.get_off_field_area = Mock()
        self.task._report_round = Mock()
        self.task.stage_transition = Mock(return_value=True)
        card = self.logic.ShopCard(0, self.character("希儿"), self.task.store_area[0],
                                   raw_text="希儿", price=3, price_evidence="price_badge")
        self.task.shopping_budget["refreshes"] = 0
        self.task._scan_store = Mock(side_effect=[
            self.logic.ShopObservation(self.logic.ShopState.READY, (card,)),
            self.logic.ShopObservation(self.logic.ShopState.EMPTY)])

        def confirm(*args, **kwargs):
            self.physical[("in_hand", 0)] = self.observation("in_hand", 0, card.character)
            return self.logic.ActionResult.CONFIRMED

        self.task._confirm_purchase = Mock(side_effect=confirm)
        events, rosters = [], []
        real_shop, real_prepare = self.task.shopping, self.task.prepare_for_battle

        def shop():
            events.append("shopping")
            return real_shop()

        def prepare():
            events.append("prepare")
            return real_prepare()

        def battle():
            events.append("battle")
            rosters.append({o.character.name for area in ("on_field", "off_field")
                            for o in self.task._observations[area]
                            if o.state == self.logic.SlotState.KNOWN})
            if not continuing and len(rosters) == 1:
                self.task._confirmed_battle_count = 1
                return True
            self.task.is_game_over = True
            return False

        self.task.shopping = Mock(side_effect=shop)
        self.task.prepare_for_battle = Mock(side_effect=prepare)
        self.task.battle = Mock(side_effect=battle)
        self.task.game_loop()
        self.assertEqual(self.task.shopping.call_count, 1)
        self.assertEqual(self.task._confirm_purchase.call_count, 1)
        self.assertEqual(self.task._scan_store.call_count, 2)
        self.assertNotIn("d", self.operator.keys())
        self.assertNotIn("f", self.operator.keys())
        return events, rosters

    def test_new_game_first_hand_does_not_shop_then_next_batch_fields_before_battle(self):
        events, rosters = self.run_real_loop_purchase(continuing=False)
        self.assertEqual(events, ["prepare", "battle", "shopping", "prepare", "battle"])
        self.assertEqual(rosters[0], {"灵砂"})
        self.assertEqual(rosters[1], {"灵砂", "希儿"})

    def test_continued_game_first_preparation_shops_once_and_fields_before_battle(self):
        events, rosters = self.run_real_loop_purchase(continuing=True)
        self.assertEqual(events, ["shopping", "prepare", "battle"])
        self.assertEqual(rosters, [{"灵砂", "希儿"}])

    def test_move_action_budget_prevents_retry_and_blocks_remaining_improvement(self):
        self.empty_board()
        self.task.max_team_size = 2
        self.task.preparation_budget["actions"] = 1
        self.stage(("灵砂", "希儿"))
        self.observe("on_field", 0, self.character("灵砂"))
        self.observe("in_hand", 0, self.character("希儿"))
        self.install_board(unchanged_names=("希儿",))
        result = self.task.prepare_for_battle()
        self.assertEqual(result.state, self.module.Readiness.BLOCKED)
        self.assertEqual(result.attempts, 1)
        self.assertEqual(len(self.operator.drags()), 1)

    def test_recovery_scan_cannot_extend_preparation_deadline_or_reset_counts(self):
        self.task.preparation_budget.update(seconds=2, total_seconds=5, recoveries=2)
        self.task._begin_preparation()
        original_deadline = self.task._preparation_deadline
        self.task.get_in_hand_area = Mock()

        def slow_scan(*args, **kwargs):
            self.clock.advance(2.5)

        self.task.refresh_character = Mock(side_effect=slow_scan)
        self.task._observe_slot = Mock(side_effect=lambda area, index, *args, **kwargs:
                                     self.observation(area, index, state=self.logic.SlotState.UNKNOWN))
        result = self.task.prepare_for_battle()
        self.assertEqual(result.state, self.module.Readiness.BLOCKED)
        self.assertEqual(result.reason, "preparation_time_budget")
        self.assertEqual(self.task._preparation_deadline, original_deadline)
        formation_deadline = self.task._formation_deadline
        recoveries = self.task._preparation_recoveries
        self.task._begin_preparation()
        self.assertEqual(self.task._preparation_deadline, original_deadline)
        self.assertEqual(self.task._formation_deadline, formation_deadline)
        self.assertEqual(self.task._preparation_recoveries, recoveries)
        self.task.prepare_for_battle()
        self.assertEqual(self.task._preparation_recoveries, recoveries)

    def test_formation_timeout_blocks_unknown_field_or_dirty_slot(self):
        self.empty_board()
        self.task.max_team_size = self.task._population_current = 1
        self.stage(("灵砂",))
        self.observe("on_field", 0, self.character("灵砂"))
        self.install_board()
        self.task._begin_preparation()
        self.task._formation_deadline = self.clock.monotonic() - 1
        for unknown in (True, False):
            with self.subTest(unknown=unknown):
                self.observe("on_field", 1,
                             state=self.logic.SlotState.UNKNOWN if unknown else self.logic.SlotState.EMPTY)
                self.task._dirty_slots = set() if unknown else {("on_field", 1)}
                self.assertEqual(self.task._assess_preparation().state, self.module.Readiness.READY)
                prepared = self.task.prepare_for_battle()
                self.assertEqual((prepared.state, prepared.reason, prepared.blocked_reason),
                                 (self.module.Readiness.BLOCKED, "preparation_time_budget",
                                  "field_observation_not_confirmed"))
                self.assertEqual(self.operator.drags(), [])
                battle_box = self.battle_button_available()
                with self.assertRaises(RuntimeError):
                    self.task.battle()
                self.assertFalse(any(name == "click_box" and args and args[0] is battle_box
                                     for name, args, _ in self.operator.calls))
        self.task._observe_slot.assert_not_called()

    def test_battle_button_wait_cannot_cross_total_preparation_deadline(self):
        self.empty_board()
        self.task.max_team_size = self.task._population_current = 1
        self.stage(("灵砂",))
        self.observe("on_field", 0, self.character("灵砂"))
        self.install_board()
        self.task._begin_preparation()
        battle_box = self.battle_button_available()

        def slow_button_read(*args, **kwargs):
            self.clock.advance(self.task.preparation_budget["total_seconds"] + 1)
            return battle_box

        self.operator.wait_img = Mock(side_effect=slow_button_read)
        with self.assertRaisesRegex(RuntimeError, "preparation_total_time_budget"):
            self.task.battle()
        self.assertFalse(any(name == "click_box" and args and args[0] is battle_box
                             for name, args, _ in self.operator.calls))

    def test_layout_change_does_not_compare_or_reuse_old_pending_endpoints(self):
        self.empty_board()
        self.observe("on_field", 0, self.character("灵砂"))
        self.observe("in_hand", 0, self.character("千冶·刃"))
        self.install_board(unknown_ends=True)
        self.assertFalse(self.task.swap_character_between_areas("in_hand", 0, "off_field", 0))
        old_pending = self.task._pending_move
        self.task._layout_revision += 1
        old_x, old_y = self.task.off_field_area[0]
        self.task.off_field_area[0] = (old_x + 0.03, old_y)
        self.task.refresh_backend_character = Mock()
        self.task.get_in_hand_area = Mock()
        self.task._observe_slot = Mock(side_effect=AssertionError("old endpoint read"))
        self.assertFalse(self.task._resolve_pending_move())
        self.assertIs(self.task._pending_move, old_pending)
        self.task._observe_slot.assert_not_called()
        self.task.refresh_backend_character.assert_called_once()
        self.assertEqual(len(self.operator.drags()), 1)

    def test_resume_checkpoint_keeps_cycles_but_does_not_restore_known_slots_or_replay(self):
        fingerprint = hashlib.sha256(b"test strategy").hexdigest()
        store = self.session_class(self.session_path)
        started = store.begin(fingerprint)
        self.assertTrue(started.persisted)
        self.assertTrue(store.record(completed_cycles=9, phase="move_pending",
                                     confirmed_event="main_c_first_fielded",
                                     pending_actions=["swap:in_hand:7:千冶·刃->off_field:1"]))
        self.task._strategy_fingerprint = fingerprint
        self.task.is_continue = True
        self.task._begin_session()
        self.assertEqual(self.task._cycle_number, 9)
        self.assertEqual(self.task._session_store.checkpoint.run_id, started.checkpoint.run_id)
        self.assertTrue(all(o.state == self.logic.SlotState.UNKNOWN
                            for slots in self.task._observations.values() for o in slots))
        self.assertFalse(self.task.main_c_first_fielded_confirmed)
        self.assertIsNone(self.task._pending_move)
        self.assertEqual(self.operator.drags(), [])
        self.assertEqual(self.operator.keys(), [])
        # Historical text may remain until live recovery; it is never a move plan.
        self.assertTrue(all(isinstance(item, str) for item in
                            self.task._session_store.checkpoint.pending_actions))
        self.assertTrue(self.session_path.exists())


    def test_flow_loader_factory_ignores_real_runtime_path(self):
        supplied_path = ROOT / "tasks/currency_wars/state/current_run.json"
        store = self.fixture_session_factory(supplied_path)
        self.assertTrue(store.path.is_relative_to(Path(self.module._session_tempdir.name)))
        self.assertNotEqual(store.path, supplied_path)
        fingerprint = hashlib.sha256(b"fixture strategy").hexdigest()
        self.assertTrue(store.begin(fingerprint).persisted)

    def test_preparation_budget_rejects_unbounded_invalid_values(self):
        for raw in ({"seconds": True}, {"actions": 0}, {"recoveries": -1},
                    {"move_retries": 601}, {"seconds": 20, "total_seconds": 10},
                    {"unknown_budget": 1}, []):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.module.validate_preparation_budget(raw)
        valid = self.module.validate_preparation_budget(
            {"seconds": 1, "total_seconds": 1, "actions": 1,
             "recoveries": 0, "move_retries": 0})
        self.assertEqual(valid["recoveries"], 0)
        self.assertEqual(valid["move_retries"], 0)

    def test_stop_during_preparation_propagates_without_drag_or_battle_click(self):
        self.empty_board()
        self.observe("on_field", 0, self.character("灵砂"))
        self.operator.stop_event.set()
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task.prepare_for_battle()
        self.assertEqual(self.operator.drags(), [])
        self.assertFalse(any(name == "click_box" for name, _, _ in self.operator.calls))


    def install_checkpoint(self, *, phase="battle", cycles=0, pending=()):
        fingerprint = hashlib.sha256(b"metadata strategy").hexdigest()
        self.task._strategy_fingerprint = fingerprint
        self.task._session_store = self.session_class(self.session_path)
        self.assertTrue(self.task._session_store.begin(fingerprint).persisted)
        self.task._cycle_number = cycles
        self.assertTrue(self.task._session_store.record(
            phase=phase, completed_cycles=cycles, pending_actions=pending))
        return fingerprint

    def test_reward_animation_then_ready_reads_health_only_after_animation(self):
        self.install_checkpoint()
        animation = self.module.BattleScreenObservation(
            "result_animation", None, None, "success_header", "挑战成功", "success")
        ready = self.module.BattleScreenObservation(
            "result_ready", (0.5, 0.8), None, "header_and_continue", "挑战成功 继续挑战", "success")
        self.task._vision.read_battle_screen = Mock(side_effect=[animation, ready])
        health = self.module.HealthObservation(62, 100, "two_health_frames", "consistent_health", "62/100")
        self.task._vision.read_squad_health = Mock(return_value=health)
        self.operator.locate = Mock(return_value=None)
        self.task._post_battle_stage = Mock(return_value=None)
        self.assertEqual(self.task._wait_battle_result(), (None, ready.continue_point, False))
        self.assertEqual(self.task._last_battle_outcome, "success")
        self.assertEqual(self.task._last_health_read.current, 62)
        self.task._vision.read_squad_health.assert_called_once_with(self.module.RESULT_HEALTH_ROI)
        self.assertEqual(self.task._session_store.checkpoint.last_outcome, "success")
        self.assertFalse(any(name == "click" for name, _, _ in self.operator.calls))

    def test_health_unknown_on_first_ready_gets_only_one_bounded_retry(self):
        self.install_checkpoint()
        ready = self.module.BattleScreenObservation(
            "result_ready", (0.5, 0.8), None, "failure_header", "挑战失败 继续挑战", "failure")
        unknown = self.module.HealthObservation(None, None, "health_not_confirmed", "animation", "")
        health = self.module.HealthObservation(48, 100, "two_health_frames", "consistent_health", "48/100")
        self.task._vision.read_squad_health = Mock(side_effect=[unknown, health])
        self.task._record_battle_screen(ready)
        self.assertIsNone(self.task._last_health_read.current)
        self.task._record_battle_screen(ready)
        self.task._record_battle_screen(ready)
        self.assertEqual(self.task._vision.read_squad_health.call_count, 2)
        self.assertEqual(self.task._last_health_read.current, 48)
        self.assertEqual(self.task._session_store.checkpoint.last_outcome, "failure")

    def test_fast_continue_paths_record_outcome_and_health_before_return(self):
        self.install_checkpoint()
        button = fixture.FakeBox(source="CONTINUE")
        ready = self.module.BattleScreenObservation(
            "result_ready", (0.5, 0.8), None, "failure_header", "挑战失败 继续挑战", "failure")
        self.task._vision.read_battle_screen = Mock(return_value=ready)
        self.task._vision.read_squad_health = Mock(return_value=self.module.HealthObservation(
            30, 100, "two_health_frames", "consistent_health", "30/100"))
        self.operator.locate_any = Mock(return_value=(2, button))
        self.operator.locate = Mock(side_effect=lambda name, **kwargs:
                                     button if name == self.module.CWIMG.CONTINUE else None)
        self.assertEqual(self.task._wait_battle_entry(), 2)
        self.assertEqual(self.task._wait_battle_result(), (button, None, False))
        self.assertEqual(self.task._last_battle_outcome, "failure")
        self.assertEqual(self.task._last_health_read.current, 30)
        self.task._vision.read_squad_health.assert_called_once()
        self.assertEqual(self.task._session_store.checkpoint.last_outcome, "failure")

    def test_recovery_uses_live_settlement_without_replaying_historical_purchase(self):
        fingerprint = self.install_checkpoint(phase="purchase_pending", cycles=7,
                                              pending=["购买确认：符玄 商店槽位2"])
        original_id = self.task._session_store.checkpoint.run_id
        self.task._session_store = None
        self.task._strategy_fingerprint = fingerprint
        self.task._recovery_page = "settlement"
        self.task.page_locate = Mock(return_value=self.module.CurrencyWarsPage.RECOVERY)
        self.task._wait_battle_result = Mock(return_value=(None, None, True))
        self.task.stage_transition = Mock(return_value=True)
        self.install_board()
        self.assertTrue(self.task.start_game())
        self.assertTrue(self.task.is_continue)
        self.assertEqual(self.task._cycle_number, 7)
        self.assertEqual(self.task._session_store.checkpoint.run_id, original_id)
        self.task._wait_battle_result.assert_called_once_with(in_combat=False)
        self.assertEqual(self.task._session_store.checkpoint.phase, "preparation")
        self.assertEqual(self.task._session_store.checkpoint.pending_actions, ())
        self.assertTrue(all(o.state == self.logic.SlotState.UNKNOWN
                            for slots in self.task._observations.values() for o in slots))
        self.assertIsNone(self.task._pending_move)
        self.assertEqual(self.operator.keys(), [])
        self.assertEqual(self.operator.drags(), [])
        self.assertFalse(any(name in ("click", "click_box", "click_img")
                             for name, _, _ in self.operator.calls))

    def test_missing_equipment_box_is_not_cached_and_can_be_retried(self):
        self.empty_board()
        character = self.character("灵砂")
        self.task.strategy_characters = {character.name: 2}
        observed = self.observe("on_field", 0, character)
        self.task._observe_slot = Mock(return_value=observed)
        self.task._equipment_dirty = False
        self.operator.locate = Mock(return_value=fixture.FakeBox())
        self.operator.locate_any = Mock(return_value=(-1, None))
        for _ in range(2):
            self.task._get_character_in_area(self.task.on_field_area[:1],
                self.task.on_field_character, force=True, equip=True, count_stars=True)
            self.assertNotIn(character.name, self.task._equipment_checked)
        self.assertEqual(self.operator.locate.call_count, 2)
        self.operator.locate_any = Mock(return_value=(0, fixture.FakeBox()))
        self.operator.click_box = Mock(return_value=True)
        self.task._invalidate_equipment_resources("new_reward_after_bounded_failures")
        self.task._get_character_in_area(self.task.on_field_area[:1], self.task.on_field_character,
                                         force=True, equip=True, count_stars=True)
        self.assertNotIn(character.name, self.task._equipment_checked)
        self.task._get_character_in_area(self.task.on_field_area[:1], self.task.on_field_character,
                                         force=True, equip=True, count_stars=True)
        self.assertEqual(self.operator.locate.call_count, 4)


    def test_main_c_known_at_target_with_unknown_source_stays_pending_until_both_confirmed(self):
        self.empty_board()
        self.task.max_team_size = 2
        self.stage(("灵砂", "希儿"))
        self.task.main_c = "希儿"
        self.task.main_c_search_level = 5
        self.observe("on_field", 0, self.character("灵砂"))
        self.observe("in_hand", 0, self.character("希儿"))
        self.install_board()
        real_drag = self.operator.drag_to

        def partially_observed_drag(*args, **kwargs):
            real_drag(*args, **kwargs)
            self.physical[("in_hand", 0)] = self.observation(
                "in_hand", 0, state=self.logic.SlotState.UNKNOWN)
            return True

        self.operator.drag_to = Mock(side_effect=partially_observed_drag)
        self.assertFalse(self.task.swap_character_between_areas("in_hand", 0, "on_field", 1))
        self.assertEqual(self.task._last_move_result.status, self.module.MoveStatus.INDETERMINATE)
        target = self.task._observations["on_field"][1]
        self.assertEqual((target.state, target.character.name), (self.logic.SlotState.KNOWN, "希儿"))
        self.assertEqual(self.task._observations["in_hand"][0].state, self.logic.SlotState.UNKNOWN)
        self.assertFalse(self.task._confirm_main_c_fielded())
        self.assertFalse(self.task._can_upgrade(5))
        self.assertEqual(self.task.prepare_for_battle().state, self.module.Readiness.BLOCKED)
        self.assertIsNotNone(self.task._pending_move)
        self.assertFalse(self.task.main_c_first_fielded_confirmed)
        self.assertEqual(len(self.operator.drags()), 1)
        # A new, positive source-empty observation resolves the same operation.
        self.physical[("in_hand", 0)] = self.observation("in_hand", 0)
        self.assertTrue(self.task._resolve_pending_move())
        self.assertIsNone(self.task._pending_move)
        self.assertTrue(self.task.main_c_first_fielded_confirmed)
        self.assertTrue(self.task._can_upgrade(5))
        self.assertEqual(len(self.operator.drags()), 1)

    def test_surplus_survival_cards_do_not_exhaust_preparation_by_cycling_provider(self):
        self.empty_board()
        self.task.max_team_size = 4
        front = self.characters.Characters.Hyacine
        healer = self.characters.Characters.Huohuo
        provider = self.characters.Characters.FuXuan
        # Reuse an unrelated known front character as the only stage target.
        main = self.characters.Characters.Lingsha
        interim = self.characters.Characters.Gilgamesh
        self.stage((main.name,))
        config = self.task.formation_config
        self.task.formation_config = replace(config,
            roles={"survival": (
                self.module.RoleProvider(provider.name, ("off_field",)),
                self.module.RoleProvider(healer.name, ("on_field", "off_field")),
                self.module.RoleProvider(front.name, ("on_field",)))},
            role_requirements={"survival": self.module.RoleRequirement(
                1, (provider.name,), (healer.name, front.name), "warn_continue")})
        self.observe("on_field", 0, main)
        self.observe("off_field", 0, provider)
        self.observe("off_field", 1, interim)
        self.observe("in_hand", 0, healer)
        self.observe("in_hand", 1, front)
        self.install_board()
        prepared = self.task.prepare_for_battle()
        self.assertNotEqual(prepared.state, self.module.Readiness.BLOCKED)
        self.assertEqual(prepared.attempts, 1)
        self.assertEqual(prepared.moves, 1)
        self.assertEqual(len(self.operator.drags()), 1)
        self.assertEqual(self.task._observations["off_field"][0].character.name, provider.name)
        self.assertEqual(self.task._observations["off_field"][1].character.name, interim.name)
        self.assertEqual(self.task._role_evaluations()["survival"].state, "satisfied")

    def configure_full_protected_role(self, policy):
        self.empty_board()
        self.task.max_team_size = self.task._population_current = 5
        front = ("灵砂", "希儿", "爻光", "昔涟")
        back = ("千冶·刃",)
        for index, name in enumerate(front):
            self.observe("on_field", index, self.character(name))
        self.observe("off_field", 0, self.character(back[0]))
        self.observe("in_hand", 0, self.character("符玄"))
        requirement = self.module.RoleRequirement(1, ("符玄",), (), policy)
        stage = self.module.FormationStage("protected full board", 0, front, back)
        self.task.formation_config = self.module.FormationConfig(
            {}, {}, {name: "银狼" for name in front + back}, (stage,),
            roles={"survival": (self.module.RoleProvider("符玄", ("off_field",)),)},
            role_requirements={"survival": requirement})
        self.task.strategy_characters = {name: 2 for name in front + back}
        self.install_board()
        evaluation = self.task._role_evaluations()["survival"]
        self.assertEqual(evaluation.bench_candidates, ("符玄",))
        self.assertFalse(self.task._role_placement_unresolved(evaluation))
        self.assertIsNone(self.module.plan_formation_move(
            self.task.formation_config, stage, self.task._observations, 5))
        return evaluation

    def test_soft_survival_gap_full_protected_board_can_upgrade_and_battle_degraded(self):
        self.configure_full_protected_role("warn_continue")
        self.task.min_level = self.task.mid_level = 6
        self.task.get_coins = Mock(side_effect=[50, 46])
        self.task.shopping_budget.update(actions=4, experiences=1, refreshes=0)
        self.task._scan_store = Mock(return_value=self.logic.ShopObservation(self.logic.ShopState.READY))
        shop = self.task.shopping()
        self.assertEqual(shop.experience_purchases, 1)
        self.assertEqual(self.operator.keys().count("f"), 1)
        self.assertNotEqual(shop.reason, "role_placement")
        prepared = self.task.prepare_for_battle()
        self.assertEqual(prepared.state, self.module.Readiness.DEGRADED)
        self.assertTrue(any(gap.startswith("role:survival:") for gap in prepared.gaps))
        self.assertEqual(self.operator.drags(), [])
        box = self.battle_button_available()
        self.assertTrue(self.task.battle())
        self.assertEqual(sum(name == "click_box" and args and args[0] is box
                             for name, args, _ in self.operator.calls), 1)

    def test_hard_survival_gap_full_protected_board_blocks_battle(self):
        self.configure_full_protected_role("block")
        prepared = self.task.prepare_for_battle()
        self.assertEqual(prepared.state, self.module.Readiness.BLOCKED)
        self.assertTrue(any(gap.startswith("role:survival:") for gap in prepared.gaps))
        box = self.battle_button_available()
        with self.assertRaises(RuntimeError):
            self.task.battle()
        self.assertEqual(self.operator.drags(), [])
        self.assertFalse(any(name == "click_box" and args and args[0] is box
                             for name, args, _ in self.operator.calls))

    def test_configured_health_roi_is_read_by_real_vision_during_preparation(self):
        roi = [0.10, 0.05, 0.20, 0.15]
        strategy = self.session_path.parent / "health_strategy.json"
        strategy.write_text(json.dumps({"on_field": {"灵砂": 2}, "off_field": {},
                                        "health_roi": roi}, ensure_ascii=False), encoding="utf-8")
        self.task.load_strategy(str(strategy))
        self.empty_board()
        self.observe("on_field", 0, self.character("灵砂"))
        self.install_board()
        self.operator.ocr_results = [([[2, 4], [150, 4], [150, 26], [2, 26]],
                                     "小队生命值72/100", 0.99)]
        result = self.task.prepare_for_battle()
        self.assertNotEqual(result.state, self.module.Readiness.BLOCKED)
        self.assertEqual((self.task._last_health_read.current, self.task._last_health_read.maximum), (72, 100))
        self.assertEqual(self.task._last_health_read.evidence, "two_health_frames")
        reads = [kwargs for name, _, kwargs in self.operator.calls if name == "ocr"]
        self.assertEqual(len(reads), 2)
        for read in reads:
            self.assertEqual(tuple(read[key] for key in ("from_x", "from_y", "to_x", "to_y")), tuple(roi))
        self.task.prepare_for_battle()
        self.assertEqual(sum(name == "ocr" for name, _, _ in self.operator.calls), 2)

    def test_uncached_equipment_signature_is_checked_even_when_global_flag_is_false(self):
        self.task._read_preparation_round = Mock(return_value=(1, 1))
        self.empty_board()
        self.stage(("灵砂",))
        observed = self.observe("on_field", 0, self.character("灵砂"))
        self.install_board()
        self.task._equipment_dirty = False
        self.assertTrue(self.task._needs_equipment_check())
        self.task._equipment_checked["灵砂"] = self.task._equipment_signature(observed)
        self.assertFalse(self.task._needs_equipment_check())
        changed = replace(observed, stars=2, revision=2)
        self.task._set_observation("on_field", changed)
        self.physical[("on_field", 0)] = changed
        self.assertTrue(self.task._needs_equipment_check())
        self.task.harvest_crystals = Mock()
        self.task.handle_characters_updated = Mock()
        self.task.sell_character = Mock(return_value=self.logic.SellResult(self.logic.ActionResult.CONFIRMED))
        self.task.get_on_field_area = Mock()
        self.task.get_off_field_area = Mock()
        def finish_battle():
            self.task.is_game_over = True
            return False
        self.task.battle = Mock(side_effect=finish_battle)
        self.task._process_equipment = Mock()
        self.task.game_loop()
        self.task._process_equipment.assert_called_once_with()
        self.assertFalse(any(call.kwargs.get("equip") for call in self.task.get_on_field_area.call_args_list))
        self.assertFalse(any(call.kwargs.get("equip") for call in self.task.get_off_field_area.call_args_list))

    def run_same_name_merge_purchase(self, merged_stars):
        self.empty_board()
        self.task.max_team_size = 3
        self.task.min_level = self.task.mid_level = 5
        self.task.min_coins = 99
        self.task.shopping_budget.update(actions=4, purchases=3, refreshes=0)
        self.stage(("灵砂",))
        self.observe("on_field", 0, self.character("灵砂"))
        self.observe("in_hand", 0, self.character("灵砂"))
        self.install_board()
        card = self.logic.ShopCard(0, self.character("灵砂"), self.task.store_area[0],
                                   raw_text="灵砂", price=2, price_evidence="price_badge")
        self.task._scan_store = Mock(return_value=self.logic.ShopObservation(self.logic.ShopState.READY, (card,)))

        def confirm(*args, **kwargs):
            self.physical[("on_field", 0)] = replace(self.physical[("on_field", 0)],
                stars=merged_stars, revision=2, evidence="fresh_post_merge")
            self.physical[("in_hand", 0)] = self.observation("in_hand", 0)
            return self.logic.ActionResult.CONFIRMED

        self.task._confirm_purchase = Mock(side_effect=confirm)
        result = self.task.shopping()
        self.assertEqual(result.confirmed_purchases, 1)
        self.task._confirm_purchase.assert_called_once()
        self.assertGreaterEqual(self.task.get_in_hand_area.call_count, 1)
        self.assertEqual(self.task._observations["on_field"][0].stars, merged_stars)
        self.assertEqual(self.task._observations["in_hand"][0].state, self.logic.SlotState.EMPTY)
        self.assertGreaterEqual(self.task._scan_store.call_count, 3)
        self.assertNotIn("d", self.operator.keys())
        self.assertNotIn("f", self.operator.keys())
        return result

    def test_post_purchase_field_two_star_merge_prevents_same_round_same_name_repurchase(self):
        self.run_same_name_merge_purchase(merged_stars=2)

    def test_post_purchase_bench_two_star_merge_prevents_same_name_repurchase(self):
        self.empty_board()
        self.task.min_level = self.task.mid_level = 5
        self.task.min_coins = 99
        self.task.shopping_budget.update(actions=4, purchases=3, refreshes=0)
        self.stage(("希儿", "灵砂"))
        self.observe("on_field", 0, self.character("希儿"))
        self.observe("in_hand", 0, self.character("灵砂"))
        self.observe("in_hand", 1, self.character("灵砂"))
        self.install_board()
        card = self.logic.ShopCard(0, self.character("灵砂"), self.task.store_area[0],
                                   raw_text="灵砂", price=2, price_evidence="price_badge")
        self.task._scan_store = Mock(return_value=self.logic.ShopObservation(self.logic.ShopState.READY, (card,)))

        def merge_on_bench(*args, **kwargs):
            self.physical[("in_hand", 0)] = replace(self.physical[("in_hand", 0)],
                stars=2, revision=2, evidence="fresh_post_merge")
            self.physical[("in_hand", 1)] = self.observation("in_hand", 1)
            return self.logic.ActionResult.CONFIRMED

        self.task._confirm_purchase = Mock(side_effect=merge_on_bench)
        result = self.task.shopping()
        self.assertEqual(result.confirmed_purchases, 1)
        self.task._confirm_purchase.assert_called_once()
        self.assertEqual(self.task._observations["in_hand"][0].stars, 2)
        self.assertGreaterEqual(self.task.get_in_hand_area.call_count, 1)
        self.assertGreaterEqual(self.task._scan_store.call_count, 3)
        self.assertNotIn("d", self.operator.keys())
        self.assertNotIn("f", self.operator.keys())

    def test_post_purchase_unknown_stars_pauses_same_name_repurchase_with_pending_hint(self):
        self.run_same_name_merge_purchase(merged_stars=None)
        self.assertIn("灵砂", self.task._purchase_pending_names)
        # A new shopping call must not forget an unresolved merge's star count.
        again = self.task.shopping()
        self.assertEqual(again.confirmed_purchases, 0)
        self.task._confirm_purchase.assert_called_once()
        self.assertIn("灵砂", self.task._purchase_pending_names)


if __name__ == "__main__":
    unittest.main()
