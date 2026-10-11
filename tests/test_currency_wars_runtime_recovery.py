"""Offline runtime recovery regressions; never touch the game or live checkpoint."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import uuid

import test_currency_wars_flow as fixture


class RuntimeRecoveryTests(unittest.TestCase):
    character = fixture.CurrencyWarsFlowTests.character
    observe = fixture.CurrencyWarsFlowTests.observe
    empty_board = fixture.CurrencyWarsFlowTests.empty_board

    def setUp(self):
        fixture.CurrencyWarsFlowTests.setUp(self)
        self.task._vision.capture_sample = Mock(return_value=None)
        self.task._vision.read_battle_screen = Mock(
            return_value=SimpleNamespace(state="unknown"))

    def clicks(self):
        return [(name, args) for name, args, _ in self.operator.calls
                if name in ("click", "click_box", "click_img", "drag", "key")]

    def pages(self, *pages):
        self.task._probe_runtime_page = Mock(side_effect=[page for page in pages for _ in range(2)])

    def start_pending_battle(self, entered=False):
        self.task._begin_session()
        battle_id = str(uuid.uuid4())
        self.task._pending_battle_id = battle_id
        self.task._battle_entry_confirmed = entered
        self.assertTrue(self.task._record_checkpoint(pending_battle_id=battle_id,
                                                     phase="battle_entry_pending"))
        return battle_id

    def configure_loop(self, *, continued=False):
        self.task.is_continue = continued
        self.task._confirmed_battle_count = 0
        # These loop scenarios begin at the confirmed opening preparation.
        self.task._read_preparation_round = Mock(return_value=(1, 1))
        for method in ("harvest_crystals", "get_in_hand_area", "refresh_character",
                       "_refresh_dirty_field", "update_max_team_size", "place_character"):
            setattr(self.task, method, Mock())
        self.task.handle_characters_updated = Mock(side_effect=lambda: setattr(
            self.task, "_empty_roster_needs_shop", True))
        self.task.sell_character = Mock(return_value=self.logic.SellResult(
            self.logic.ActionResult.CONFIRMED, 0, 0, "nothing_to_sell"))
        self.task.prepare_for_battle = Mock(return_value=SimpleNamespace(
            state=self.module.Readiness.READY, reason="ready"))
        self.task._equipment_due = Mock(return_value=False)
        self.task.equipment_interval_battles = None
        self.task.shopping = Mock(return_value=SimpleNamespace(reason="save"))
        self.task._resume_shopping_after = Mock(return_value=False)
        self.task.stage_transition = Mock(return_value=True)
        self.task.reset_character = Mock()

        def end_battle():
            self.task.is_game_over = True
            return True
        self.task.battle = Mock(side_effect=end_battle)

    def configure_due_equipment_scans(self):
        self.empty_board()
        character = self.character()
        self.task.strategy_characters = {character.name: 2}
        self.observe("on_field", 0, character, stars=1)
        self.task.equipment_interval_battles = 2
        self.task._equipment_battles_since_check = 2
        self.task._observe_slot = Mock(side_effect=lambda area, index, *args, **kwargs:
            self.task._observations[area][index])
        self.task._vision.read_backend_layout = Mock(return_value=self.module.LayoutObservation(
            True, tuple(self.task.off_field_area), False, "stable_test_layout"))

        def premature_batch():
            self.task._equipment_battles_since_check = 0
            return True
        self.task._process_equipment = Mock(side_effect=premature_batch)

    def assert_due_equipment_not_processed(self):
        self.task._process_equipment.assert_not_called()
        self.assertEqual(self.task._equipment_battles_since_check, 2)
        self.assertTrue(self.task._equipment_due())
        self.assertEqual(self.clicks(), [])

    def test_recognized_navigation_labels_advance_to_preparation(self):
        for label in ("下一步", "点击屏幕", "进入下阶段", "进入下一阶段"):
            with self.subTest(label=label):
                self.operator.calls.clear()
                advanced = [False]
                box = fixture.FakeBox(600, 700, 120, 40, source=label)
                self.operator.locate = Mock(side_effect=lambda template, **kwargs:
                    fixture.FakeBox() if advanced[0] and template == self.module.CWIMG.PREPARATION_STAGE
                    else None)
                self.operator.ocr_boxes = Mock(side_effect=lambda **kwargs: [] if advanced[0] else [box])

                def click(current_box, **kwargs):
                    self.assertIs(current_box, box)
                    self.operator.record("click_box", current_box, **kwargs)
                    advanced[0] = True
                    return True
                self.operator.click_box = Mock(side_effect=click)
                self.assertTrue(self.task._recover_runtime_flow(RuntimeError("transition missed")))
                self.assertEqual(len(self.clicks()), 1)
                self.assertTrue(self.task._bench_dirty)

    def test_navigation_ocr_requires_one_exact_allowed_label(self):
        self.operator.locate = Mock(return_value=None)
        for labels in (("确认购买",), ("下一步购买",), ("点击屏幕删除",),
                       ("下一步", "进入下阶段")):
            with self.subTest(labels=labels):
                self.operator.ocr_boxes = Mock(return_value=[fixture.FakeBox(source=label) for label in labels])
                self.assertIsNone(self.task._runtime_advance_candidate())
        self.operator.ocr_boxes = Mock(return_value=[fixture.FakeBox(source=" 点击屏幕继续！ ")])
        self.assertEqual(self.task._runtime_advance_candidate()[0], "点击屏幕继续")
        self.assertEqual(self.clicks(), [])

    def test_same_navigation_button_is_clicked_at_most_twice(self):
        page = ("advance", ("下一步", fixture.FakeBox(600, 700, 120, 40)))
        self.task._probe_runtime_page = Mock(return_value=page)
        self.assertFalse(self.task._recover_runtime_flow(RuntimeError("stuck")))
        self.assertEqual(len(self.clicks()), 2)
        self.assertEqual(self.task._probe_runtime_page.call_count, 6)

    def test_unstable_navigation_position_never_clicks(self):
        first = ("advance", ("下一步", fixture.FakeBox(600, 700, 120, 40)))
        moved = ("advance", ("下一步", fixture.FakeBox(650, 700, 120, 40)))
        self.task._probe_runtime_page = Mock(side_effect=[first, moved] * self.task.FLOW_RECOVERY_STEPS)
        self.assertFalse(self.task._recover_runtime_flow(RuntimeError("animation")))
        self.assertEqual(self.clicks(), [])
        self.assertEqual(self.task._probe_runtime_page.call_count, 2 * self.task.FLOW_RECOVERY_STEPS)

    def test_unknown_pages_finish_without_clicking(self):
        self.task._probe_runtime_page = Mock(return_value=("unknown", None))
        self.assertFalse(self.task._recover_runtime_flow(RuntimeError("unknown")))
        self.assertEqual(self.clicks(), [])

    def test_user_stop_is_not_converted_to_recovery_failure(self):
        self.operator.stop_event.set()
        with patch.object(self.module.time, "monotonic", return_value=100):
            with self.assertRaises(self.module.ThreadStoppedError):
                self.task._recover_runtime_flow(RuntimeError("interrupted"))
        self.assertEqual(self.clicks(), [])

    def test_stop_after_confirmation_prevents_click_and_restores_budgets(self):
        page = ("advance", ("下一步", fixture.FakeBox()))
        self.task._preparation_deadline, self.task._formation_deadline = 1000, 900
        def probe():
            self.operator.stop_event.set()
            return page
        self.task._probe_runtime_page = Mock(side_effect=probe)
        with patch.object(self.module.time, "monotonic", return_value=100):
            with self.assertRaises(self.module.ThreadStoppedError):
                self.task._recover_runtime_flow(RuntimeError("interrupted"))
        self.assertEqual((self.task._preparation_deadline, self.task._formation_deadline), (1000, 900))
        self.assertEqual(self.clicks(), [])

    def test_preparation_recovery_preserves_budgets_and_unconfirmed_actions(self):
        self.task._preparation_deadline, self.task._formation_deadline = 1000, 900
        self.task._preparation_recoveries = 2
        self.task._preparation_moves = 3
        self.task._preparation_attempts = 4
        counts = {"purchases": 3, "refreshes": 2, "experiences": 1, "actions": 6}
        self.task._preparation_shop_counts = counts
        self.task._purchase_pending_names = {"灵砂"}
        move = object()
        self.task._pending_move = move
        self.task._placement_pending = True
        for method in ("shopping", "sell_character", "place_character", "reset_character"):
            setattr(self.task, method, Mock())
        self.pages(("preparation", None))
        with patch.object(self.module.time, "monotonic", return_value=100):
            self.assertTrue(self.task._recover_runtime_flow(RuntimeError("purchase confirmation failed")))
        self.assertEqual((self.task._preparation_deadline, self.task._formation_deadline), (1000, 900))
        self.assertEqual((self.task._preparation_recoveries, self.task._preparation_moves,
                          self.task._preparation_attempts), (2, 3, 4))
        self.assertIs(self.task._preparation_shop_counts, counts)
        self.assertEqual(counts, {"purchases": 3, "refreshes": 2, "experiences": 1, "actions": 6})
        self.assertEqual(self.task._purchase_pending_names, {"灵砂"})
        self.assertIs(self.task._pending_move, move)
        self.assertTrue(self.task._placement_pending)
        for method in ("shopping", "sell_character", "place_character", "reset_character"):
            getattr(self.task, method).assert_not_called()
        self.assertEqual(self.clicks(), [])

    def test_recovery_pauses_only_remaining_preparation_and_formation_time(self):
        clock = [100]
        self.task._preparation_deadline, self.task._formation_deadline = 110, 108
        self.pages(("preparation", None))
        def confirm_preparation(_opened):
            clock[0] = 112
            return True
        self.task._set_shop_open.side_effect = confirm_preparation
        with patch.object(self.module.time, "monotonic", side_effect=lambda: clock[0]):
            self.assertTrue(self.task._recover_runtime_flow(RuntimeError("repositioning")))
        self.assertEqual((self.task._preparation_deadline, self.task._formation_deadline), (122, 120))
        self.assertEqual(self.task._preparation_deadline - clock[0], 10)
        self.assertEqual(self.task._formation_deadline - clock[0], 8)

    def test_recovery_never_revives_already_expired_preparation_budgets(self):
        for old_deadlines in ((98, 99), (100, 100)):
            with self.subTest(old_deadlines=old_deadlines):
                clock = [100]
                self.task._preparation_deadline, self.task._formation_deadline = old_deadlines
                self.pages(("preparation", None))
                def confirm_preparation(_opened):
                    clock[0] = 112
                    return True
                self.task._set_shop_open.side_effect = confirm_preparation
                with patch.object(self.module.time, "monotonic", side_effect=lambda: clock[0]):
                    self.assertTrue(self.task._recover_runtime_flow(RuntimeError("expired budget")))
                self.assertEqual((self.task._preparation_deadline, self.task._formation_deadline), old_deadlines)

    def test_unconfirmed_battle_intent_at_preparation_is_cleared_without_count(self):
        self.start_pending_battle(entered=False)
        self.pages(("preparation", None))
        self.assertTrue(self.task._recover_runtime_flow(RuntimeError("battle click timeout")))
        self.assertIsNone(self.task._pending_battle_id)
        self.assertIsNone(self.task._session_store.checkpoint.pending_battle_id)
        self.assertEqual(self.task._confirmed_battle_count, 0)
        self.assertEqual(self.task._equipment_battles_since_check, 0)

    def test_settlement_recovery_counts_original_battle_exactly_once(self):
        battle_id = self.start_pending_battle()
        self.task._wait_battle_result = Mock(return_value=(fixture.FakeBox(source="CONTINUE"), None, False))
        self.pages(("settlement", None), ("preparation", None))
        self.assertTrue(self.task._recover_runtime_flow(RuntimeError("result interrupted")))
        self.assertEqual(self.task._confirmed_battle_count, 1)
        self.assertEqual(self.task._equipment_battles_since_check, 1)
        self.assertEqual(self.task._session_store.checkpoint.last_counted_battle_id, battle_id)
        self.assertIsNone(self.task._pending_battle_id)
        self.task._wait_battle_result.assert_called_once_with(in_combat=False)
        self.pages(("preparation", None))
        self.assertTrue(self.task._recover_runtime_flow(RuntimeError("later recognition failed")))
        self.assertEqual(self.task._confirmed_battle_count, 1)
        self.assertEqual(self.task._equipment_battles_since_check, 1)

    def test_combat_recovery_reuses_pending_battle_id(self):
        battle_id = self.start_pending_battle(entered=True)
        self.task._wait_battle_result = Mock(return_value=(None, None, True))
        self.pages(("combat", None), ("preparation", None))
        self.assertTrue(self.task._recover_runtime_flow(RuntimeError("combat interrupted")))
        self.assertEqual(self.task._session_store.checkpoint.last_counted_battle_id, battle_id)
        self.assertEqual(self.task._confirmed_battle_count, 1)
        self.task._wait_battle_result.assert_called_once_with(in_combat=True)
        self.assertEqual(self.clicks(), [])

    def test_settlement_without_battle_identity_does_not_invent_completed_battle(self):
        self.task._begin_session()
        self.task._wait_battle_result = Mock(return_value=(None, None, True))
        self.pages(("settlement", None), ("preparation", None))
        self.assertTrue(self.task._recover_runtime_flow(RuntimeError("skip reward")))
        self.assertEqual(self.task._confirmed_battle_count, 0)
        self.assertEqual(self.task._equipment_battles_since_check, 0)

    def test_unconfirmed_node_selection_is_not_replayed(self):
        for pending_node, selection_sent in ((self.module.CWIMG.ENCOUNTER_NODE, False), (None, True)):
            with self.subTest(pending_node=pending_node, selection_sent=selection_sent):
                self.task._runtime_node_pending = pending_node
                self.task._last_selection_sent = selection_sent
                self.task.handle_encounter_node = Mock()
                self.task._probe_runtime_page = Mock(return_value=("node", self.module.CWIMG.ENCOUNTER_NODE))
                self.assertFalse(self.task._recover_runtime_flow(RuntimeError("selection unconfirmed")))
                self.task.handle_encounter_node.assert_not_called()
        self.assertEqual(self.clicks(), [])

    def test_repeated_node_runs_handler_only_once(self):
        self.task._probe_runtime_page = Mock(return_value=("node", self.module.CWIMG.ENCOUNTER_NODE))
        self.task.handle_encounter_node = Mock(return_value=False)
        self.assertFalse(self.task._recover_runtime_flow(RuntimeError("node stalled")))
        self.task.handle_encounter_node.assert_called_once_with(None)

    def test_confirmed_different_node_releases_old_selection_without_replaying_it(self):
        self.task._runtime_node_pending = self.module.CWIMG.FORTUNE_TELLER
        self.task._last_selection_sent = True
        self.task._handle_fortune_teller_after_battle = Mock()
        self.task.handle_invest_strategy = Mock(return_value=False)
        self.pages(("node", self.module.CWIMG.SELECT_INVEST_STRATEGY), ("preparation", None))
        self.assertTrue(self.task._recover_runtime_flow(RuntimeError("previous node departure missed")))
        self.task._handle_fortune_teller_after_battle.assert_not_called()
        self.task.handle_invest_strategy.assert_called_once_with(None)
        self.assertFalse(self.task._last_selection_sent)
        self.assertIsNone(self.task._runtime_node_pending)

    def test_same_fortune_node_keeps_pending_selection_and_never_repeats_choice(self):
        self.task._runtime_node_pending = self.module.CWIMG.FORTUNE_TELLER
        self.task._last_selection_sent = True
        self.task._handle_fortune_teller_after_battle = Mock()
        self.task._probe_runtime_page = Mock(return_value=("node", self.module.CWIMG.FORTUNE_TELLER))
        self.assertFalse(self.task._recover_runtime_flow(RuntimeError("fortune choice uncertain")))
        self.task._handle_fortune_teller_after_battle.assert_not_called()
        self.assertTrue(self.task._last_selection_sent)
        self.assertEqual(self.task._runtime_node_pending, self.module.CWIMG.FORTUNE_TELLER)

    def test_plain_next_step_is_navigation_and_not_terminal_result(self):
        self.operator.locate = Mock(return_value=fixture.FakeBox())
        self.task.handle_game_over = Mock()
        self.assertFalse(self.task.handle_next_step())
        self.task.handle_game_over.assert_not_called()
        self.assertEqual(len(self.clicks()), 1)
        self.assertEqual(self.task._confirmed_battle_count, 0)

    def test_layout_failure_only_refreshes_backend_on_recovery(self):
        self.task._layout_valid = False
        self.task.refresh_character = Mock()
        self.task.get_on_field_area = Mock()
        self.task.refresh_backend_character = Mock(side_effect=lambda **kwargs: setattr(self.task, "_layout_valid", True))
        self.pages(("preparation", None))
        self.assertTrue(self.task._recover_runtime_flow(RuntimeError("backend layout")))
        self.task.refresh_backend_character.assert_called_once_with(equip=False, recover_layout=True)
        self.task.refresh_character.assert_not_called()
        self.task.get_on_field_area.assert_not_called()

    def test_continued_initialization_does_not_consume_due_equipment_batch(self):
        self.configure_due_equipment_scans()
        self.task.is_continue = True
        self.assertTrue(self.task._initialize_game())
        self.assert_due_equipment_not_processed()

    def test_full_character_refresh_only_marks_due_equipment_without_processing(self):
        self.configure_due_equipment_scans()
        self.task.refresh_character(equip=True)
        self.assert_due_equipment_not_processed()
        self.assertTrue(self.task._equipment_dirty)

    def test_direct_frontline_scan_cannot_bypass_due_equipment_batch_order(self):
        self.configure_due_equipment_scans()
        self.task.get_on_field_area(force=True, equip=True)
        self.assert_due_equipment_not_processed()
        self.assertTrue(self.task._equipment_dirty)

    def test_game_loop_consumes_due_equipment_only_after_shopping_and_final_preparation(self):
        self.configure_loop(continued=True)
        self.empty_board()
        self.task._confirmed_battle_count = 2
        self.task.equipment_interval_battles = 2
        self.task._equipment_battles_since_check = 2
        del self.task._equipment_due
        order = []
        self.task.shopping.side_effect = lambda: order.append("shopping") or SimpleNamespace(reason="save")
        ready = SimpleNamespace(state=self.module.Readiness.READY, reason="ready")
        self.task.prepare_for_battle.side_effect = lambda: order.append("final_preparation") or ready
        self.task._assess_preparation = Mock(return_value=ready)
        self.task._equip_observation = Mock()
        process_equipment = self.task._process_equipment
        def equip():
            order.append("equipment")
            self.assertEqual(self.task._equipment_battles_since_check, 2)
            return process_equipment()
        self.task._process_equipment = Mock(side_effect=equip)
        end_battle = self.task.battle.side_effect
        self.task.battle.side_effect = lambda: order.append("battle") or end_battle()
        self.assertTrue(self.task.game_loop())
        self.assertEqual(order, ["shopping", "final_preparation", "equipment", "battle"])
        self.task._process_equipment.assert_called_once()
        self.assertEqual(self.task._equipment_battles_since_check, 0)

    def test_first_preparation_does_not_shop_even_when_empty_roster_flag_is_set(self):
        self.configure_loop()
        self.assertTrue(self.task.game_loop())
        self.task.shopping.assert_not_called()
        self.task.battle.assert_called_once()

    def test_continued_game_shops_on_first_local_preparation(self):
        self.configure_loop(continued=True)
        self.task._confirmed_battle_count = None
        self.assertTrue(self.task.game_loop())
        self.task.shopping.assert_called_once()

    def test_known_zero_battle_resume_still_skips_shopping_before_actual_first_battle(self):
        self.configure_loop(continued=True)
        self.assertTrue(self.task.game_loop())
        self.task.shopping.assert_not_called()

    def test_same_round_recovery_does_not_reset_or_advance_cycle(self):
        self.configure_loop()
        self.task.harvest_crystals.side_effect = [RuntimeError("temporary OCR"), None]
        self.pages(("preparation", None))
        original_battle = self.task.battle.side_effect
        def battle():
            self.task.reset_character.assert_not_called()
            return original_battle()
        self.task.battle.side_effect = battle
        self.assertTrue(self.task.game_loop())
        self.assertEqual(self.task._cycle_number, 0)
        self.task.shopping.assert_not_called()
        self.task.reset_character.assert_called_once()

    def test_repeated_same_round_errors_exhaust_two_recoveries(self):
        self.configure_loop()
        self.task.harvest_crystals.side_effect = RuntimeError("persistent failure")
        self.task._recover_runtime_flow = Mock(return_value=True)
        with self.assertRaisesRegex(RuntimeError, "persistent failure"):
            self.task.game_loop()
        self.assertEqual(self.task._recover_runtime_flow.call_count, 2)
        self.assertEqual(self.task.harvest_crystals.call_count, 3)
        self.assertEqual(self.task._cycle_number, 0)
        self.task.battle.assert_not_called()

    def test_recovered_real_battle_advances_cycle_and_enables_next_preparation_shop(self):
        self.configure_loop()
        self.task.harvest_crystals.side_effect = [RuntimeError("battle transition failure"), None]
        def recover(error, attempt):
            self.task._pending_battle_id = str(uuid.uuid4())
            self.task._battle_entry_confirmed = True
            self.assertTrue(self.task._confirm_completed_battle("recovered_settlement"))
            return True
        self.task._recover_runtime_flow = Mock(side_effect=recover)
        self.assertTrue(self.task.game_loop())
        self.assertEqual(self.task._cycle_number, 1)
        self.task.shopping.assert_called_once()

    def test_recovery_budget_is_renewed_after_each_of_three_confirmed_battles(self):
        self.configure_loop()
        self.task._begin_session()
        completed = []
        self.task._probe_runtime_page = Mock(return_value=("preparation", None))
        self.task._recover_runtime_flow = Mock(wraps=self.task._recover_runtime_flow)

        def battle():
            if len(completed) == 3:
                self.task.is_game_over = True
                return True
            battle_id = str(uuid.uuid4())
            self.task._pending_battle_id = battle_id
            self.task._battle_entry_confirmed = True
            self.assertTrue(self.task._record_checkpoint(pending_battle_id=battle_id))
            self.assertTrue(self.task._confirm_completed_battle("settlement_before_transition_failure"))
            completed.append(battle_id)
            return True

        def transition():
            if self.task.is_game_over:
                return True
            raise RuntimeError("transition recognition failed after a real battle")

        self.task.battle.side_effect = battle
        self.task.stage_transition.side_effect = transition
        self.assertTrue(self.task.game_loop())
        self.assertEqual(self.task._confirmed_battle_count, 3)
        self.assertEqual(self.task._equipment_battles_since_check, 3)
        self.assertEqual(self.task._cycle_number, 3)
        self.assertEqual(self.task._recover_runtime_flow.call_count, 3)
        self.assertEqual(self.task._session_store.checkpoint.last_counted_battle_id, completed[-1])
        self.assertEqual(len(set(completed)), 3)

    def test_game_loop_user_stop_never_attempts_recovery(self):
        self.configure_loop()
        self.task.harvest_crystals.side_effect = self.module.ThreadStoppedError("stopped")
        self.task._recover_runtime_flow = Mock()
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task.game_loop()
        self.task._recover_runtime_flow.assert_not_called()
        self.task.battle.assert_not_called()


if __name__ == "__main__":
    unittest.main()
