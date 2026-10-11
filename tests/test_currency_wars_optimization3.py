"""Exercise the production shop, battle and equipment integration without UI."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import uuid

import test_currency_wars_flow as fixture
FakeBox = fixture.FakeBox


class Optimization3Tests(unittest.TestCase):
    setUp = fixture.CurrencyWarsFlowTests.setUp
    character = fixture.CurrencyWarsFlowTests.character
    observe = fixture.CurrencyWarsFlowTests.observe
    empty_board = fixture.CurrencyWarsFlowTests.empty_board
    shop = fixture.CurrencyWarsFlowTests.shop
    scan_sequence = fixture.CurrencyWarsFlowTests.scan_sequence

    def configure(self, gold=29, level=6, battles=6):
        self.empty_board()
        self.task.economy_config = self.module.parse_economy_config({"enabled": True,
            "purchase_reserve_gold": 5, "stages": [
            {"from_battles": 0, "target_level": 5, "reserve_gold": 0},
            {"from_battles": 6, "target_level": 7, "reserve_gold": 20, "upgrade_gold": 60},
            {"from_battles": 12, "target_level": 9, "reserve_gold": 20, "upgrade_gold": 100}]})
        self.task._confirmed_battle_count = battles
        self.money = gold
        self.level = level
        self.task.get_coins = Mock(side_effect=lambda: self.money)
        self.task.get_level = Mock(side_effect=lambda: self.level)
        self.task._scan_store = Mock(return_value=self.shop(self.logic.ShopState.EMPTY))
        self.task.strategy_characters = {self.character().name: 2}
        self.observe("on_field", 0, self.character("佩拉"), stars=1)
        self.task._bench_dirty = False
        self.task._placement_pending = False
        def spend(key):
            if key == "f":
                self.money -= 4
            elif key == "d":
                self.money -= 2
        self.operator.on_press = spend

    def test_partial_xp_charge_is_progress_then_saves_at_floor(self):
        self.configure()
        result = self.task.shopping()
        self.assertEqual((result.experience_purchases, result.refreshes, result.reason), (1, 0, "xp_reserve_floor"))
        self.assertEqual(self.money, 25)

    def test_one_gold_short_saves_without_rolling(self):
        self.configure(gold=28)
        self.assertEqual(self.task.shopping().reason, "xp_reserve_floor")
        self.assertEqual(self.operator.keys(), [])

    def test_high_gold_no_main_ignores_old_mid_level_seven(self):
        self.configure(gold=150, level=7, battles=2)
        self.task.shopping_budget.update(experiences=1)
        result = self.task.shopping()
        self.assertEqual((self.task._economy_stage_index, result.experience_purchases), (2, 1))
        self.assertEqual(self.operator.keys(), ["f"])

    def test_main_search_locks_xp_even_with_150_gold(self):
        self.configure(gold=150, level=5, battles=2)
        self.task.main_c = self.character().name
        self.task.main_c_search_level = 5
        self.task.main_c_search_min_coins = 0
        self.task.shopping_budget.update(refreshes=1)
        result = self.task.shopping()
        self.assertEqual((self.task._economy_stage_index, result.refreshes), (2, 1))
        self.assertNotIn("f", self.operator.keys())

    def test_gold_trigger_requires_equal_fresh_read(self):
        self.configure(gold=150, level=7, battles=2)
        self.task.get_coins = Mock(side_effect=[150, 15])
        result = self.task.shopping()
        self.assertEqual(result.reason, "economy_gold_not_confirmed")
        self.assertIsNone(self.task._economy_stage_index)
        self.assertEqual(self.operator.keys(), [])

    def test_stage_does_not_retreat_after_spending(self):
        self.configure(gold=150, level=7, battles=2)
        self.task.shopping_budget.update(experiences=0)
        self.task.shopping()
        self.money = 28
        self.assertEqual(self.task.shopping().reason, "xp_reserve_floor")
        self.assertEqual(self.task._economy_stage_index, 2)

    def test_target_level_rolls_27_but_saves_26(self):
        self.configure(gold=27, level=7)
        self.task.shopping_budget.update(refreshes=1)
        self.assertEqual(self.task.shopping().refreshes, 1)
        self.operator.calls.clear()
        self.money = 26
        self.assertEqual(self.task.shopping().reason, "roll_reserve_floor")
        self.assertEqual(self.operator.keys(), [])

    def test_no_unmet_goals_means_no_refresh(self):
        self.configure(gold=60, level=7)
        self.observe("off_field", 0, self.character(), stars=2)
        self.assertEqual(self.task.shopping().reason, "no_purchase_targets")
        self.assertEqual(self.operator.keys(), [])

    def test_current_card_can_spend_purchase_reserve(self):
        self.configure(gold=24, level=7)
        char = self.character()
        card = self.logic.ShopCard(2, char, self.task.store_area[2], price=4)
        self.task._scan_store = Mock(return_value=self.shop(self.logic.ShopState.READY, card))
        def confirm(*args):
            self.money -= 4
            self.observe("in_hand", 0, char, stars=1)
            return self.logic.ActionResult.CONFIRMED
        self.task._confirm_purchase = Mock(side_effect=confirm)
        self.task.shopping_budget.update(purchases=1)
        result = self.task.shopping()
        self.assertEqual(result.confirmed_purchases, 1)
        self.assertEqual(self.money, 20)
        self.assertEqual(self.operator.keys(), [])

    def test_known_business_gate_gap_allows_procurement_below_target(self):
        self.configure(gold=29, level=6)
        self.task.formation_config = self.module.FormationConfig({}, {}, {}, (self.module.FormationStage("early", 0, ("佩拉",), ()),),
            self.module.UpgradeGate(6, {self.character().name: 2}, {}, {}))
        self.task.shopping_budget.update(refreshes=1)
        result = self.task.shopping()
        self.assertEqual(result.refreshes, 1)
        self.assertNotIn("f", self.operator.keys())

    def test_unknown_gate_stars_does_not_roll(self):
        self.configure(gold=60, level=6)
        self.observe("off_field", 0, self.character(), stars=None)
        self.task.formation_config = self.module.FormationConfig({}, {}, {}, (self.module.FormationStage("early", 0, ("佩拉",), ()),),
            self.module.UpgradeGate(6, {self.character().name: 2}, {}, {}))
        with self.assertRaisesRegex(RuntimeError, "购物证据恢复无进展"):
            self.task.shopping()
        self.task._scan_store.assert_not_called()
        self.assertEqual(self.operator.keys(), [])

    def test_owned_gate_candidate_requests_preparation(self):
        self.configure(gold=29, level=6)
        self.observe("in_hand", 0, self.character(), stars=2)
        self.task.formation_config = self.module.FormationConfig({}, {}, {}, (self.module.FormationStage("early", 0, ("佩拉",), ()),),
            self.module.UpgradeGate(6, {self.character().name: 2}, {}, {}))
        self.assertEqual(self.task.shopping().reason, "candidate_needs_preparation")
        self.assertEqual(self.operator.keys(), [])

    def test_failed_xp_charge_stops_before_second_input(self):
        self.configure()
        self.operator.on_press = lambda _: None
        self.assertEqual(self.task.shopping().reason, "experience_not_confirmed")
        self.assertEqual(self.operator.keys(), ["f"])

    def test_normal_shopping_time_pauses_both_preparation_clocks(self):
        self.configure()
        self.task._preparation_deadline = 300
        self.task._formation_deadline = 120
        clock = [0]
        def spend(key):
            if key == "f":
                self.money -= 4
                clock[0] = 400
        self.operator.on_press = spend
        with patch.object(self.module.time, "monotonic", side_effect=lambda: clock[0]):
            result = self.task.shopping()
        self.assertEqual(result.experience_purchases, 1)
        self.assertEqual((self.task._preparation_deadline, self.task._formation_deadline), (700, 520))

    def test_reopening_shop_does_not_renew_action_allowance(self):
        self.configure(gold=50, level=6)
        self.task.shopping_budget.update(actions=1)
        self.assertEqual(self.task.shopping().experience_purchases, 1)
        self.assertEqual(self.task.shopping().reason, "action_budget")
        self.assertEqual(self.operator.keys(), ["f"])

    def test_equipment_dirty_cannot_bypass_initial_or_one_battle_skip(self):
        self.configure()
        self.task.equipment_interval_battles = 2
        self.task._equip_observation = Mock()
        for count in (0, 1):
            self.task._equipment_battles_since_check = count
            self.task._invalidate_equipment_resources("test reward")
            self.assertFalse(self.task._process_equipment())
        self.task._equip_observation.assert_not_called()

    def test_equipment_due_batch_consumes_interval_without_claiming_effect(self):
        self.configure()
        self.task.equipment_interval_battles = 2
        self.task._equipment_battles_since_check = 2
        self.task._equip_observation = Mock()
        self.assertTrue(self.task._process_equipment())
        self.assertEqual(self.task._equip_observation.call_count, 10)
        self.assertEqual(self.task._equipment_battles_since_check, 0)
        self.assertTrue(self.task._equipment_dirty)
        self.assertFalse(self.task._process_equipment())

    def test_interrupted_equipment_retains_due_and_has_same_prep_retry_limit(self):
        self.configure()
        self.task.equipment_interval_battles = 2
        self.task._equipment_battles_since_check = 2
        self.task._equip_observation = Mock()
        self.task._set_shop_open = Mock(return_value=False)
        for _ in range(3):
            self.assertFalse(self.task._process_equipment())
        self.assertEqual(self.task._equipment_battles_since_check, 2)
        self.assertEqual(self.task._equip_observation.call_count, 20)

    def test_direct_equip_and_refresh_cannot_bypass_interval(self):
        self.configure()
        self.task.equipment_interval_battles = 2
        self.task._vision.capture_layout_failure = Mock()
        self.task.get_on_field_area = Mock()
        self.task.get_off_field_area = Mock()
        self.task._equip_observation("on_field", 0, self.task._observations["on_field"][0])
        self.task.refresh_character(equip=True)
        self.task.get_on_field_area.assert_called_once_with(True, equip=False)
        self.task.get_off_field_area.assert_called_once_with(True, equip=False)
        self.assertFalse(any(name == "locate" and args[0] == self.module.CWIMG.EQUIPMENT_RECOMMEND
                             for name, args, _ in self.operator.calls))

    def configure_battle(self, skip=False):
        self.configure()
        self.task._ensure_battle_roster = Mock(return_value=True)
        button, result = FakeBox(source="BATTLE"), FakeBox(source="CONTINUE")
        self.operator.wait_any_img = Mock(return_value=(1 if skip else 0, button))
        self.operator.wait_img = Mock(return_value=button)
        self.task._wait_battle_entry = Mock(return_value=1)
        self.task._wait_battle_result = Mock(return_value=(result, None, False))
        self.task._confirmed_battle_count = 0
        return result

    def test_actual_settled_battle_counts_once_but_skip_reward_does_not(self):
        self.configure_battle()
        self.assertTrue(self.task.battle())
        self.assertEqual(self.task._confirmed_battle_count, 1)
        self.assertEqual(self.task._equipment_battles_since_check, 1)
        self.assertFalse(self.task._confirm_completed_battle("repeat result"))
        self.configure_battle(skip=True)
        self.assertTrue(self.task.battle())
        self.assertEqual(self.task._confirmed_battle_count, 0)

    def test_unknown_outcome_settlement_still_counts(self):
        self.configure_battle()
        self.task._last_battle_outcome = "unknown"
        self.task.battle()
        self.assertEqual(self.task._confirmed_battle_count, 1)

    def test_failed_battle_entry_does_not_count(self):
        self.configure_battle()
        self.task._wait_battle_entry = Mock(return_value=-1)
        with self.assertRaises(RuntimeError):
            self.task.battle()
        self.assertEqual(self.task._confirmed_battle_count, 0)

    def test_real_count_and_stage_resume_from_same_session(self):
        self.configure()
        self.task._begin_session()
        self.task._pending_battle_id = str(uuid.uuid4())
        self.task._battle_entry_confirmed = True
        self.task._record_checkpoint(pending_battle_id=self.task._pending_battle_id)
        self.task._confirm_completed_battle("test settled battle")
        self.task._economy_context(7, 150)  # current money is 29: unstable, no stage mutation
        self.money = 150
        self.task._economy_context(7, 150)
        self.task.is_continue = True
        self.task._begin_session()
        self.assertEqual((self.task._confirmed_battle_count, self.task._economy_stage_index,
                          self.task._equipment_battles_since_check), (1, 2, 1))

    def test_stable_terminal_records_last_battle_before_finalize(self):
        self.configure_battle()
        self.task._begin_session()
        self.task._pending_battle_id = str(uuid.uuid4())
        self.task._battle_entry_confirmed = True
        self.task._record_checkpoint(pending_battle_id=self.task._pending_battle_id)
        screen = SimpleNamespace(state="final_summary", outcome="success", evidence="stable")
        self.task._record_terminal_screen(screen)
        self.task._session_store.finalize("game_won")
        self.assertEqual(self.task._session_store.checkpoint.confirmed_battle_count, 1)

    def test_different_no_main_stage_table_uses_its_own_level_targets(self):
        self.configure(gold=13, level=3, battles=6)
        self.task.economy_config = self.module.parse_economy_config({"enabled": True,
            "purchase_reserve_gold": 5, "stages": [
            {"from_battles": 0, "target_level": 3, "reserve_gold": 0},
            {"from_battles": 6, "target_level": 5, "reserve_gold": 0},
            {"from_battles": 12, "target_level": 7, "reserve_gold": 0}]})
        result = self.task.shopping()
        self.assertIsNone(self.task.main_c)
        self.assertEqual((self.task._economy_stage_index, result.experience_purchases), (1, 2))
        self.assertEqual(self.operator.keys(), ["f", "f"])

    def test_unconfirmed_current_price_is_reread_then_exits_without_spending(self):
        self.configure()
        card = self.logic.ShopCard(2, self.character(), self.task.store_area[2])
        self.task._scan_store = Mock(return_value=self.shop(self.logic.ShopState.READY, card))
        self.assertEqual(self.task.shopping().reason, "purchase_evidence_unknown")
        self.assertEqual(self.task._scan_store.call_count, 2)
        self.assertEqual(self.operator.keys(), [])

    def test_stop_after_entry_restores_authenticated_pending_battle(self):
        self.configure_battle()
        self.task._begin_session()
        battle_id = str(uuid.uuid4())
        self.task._record_checkpoint(pending_battle_id=battle_id,
            confirmed_event="battle_entered:" + battle_id, phase="combat")
        self.task._record_execution_stop("stopped")
        self.task.is_continue = True
        self.task._begin_session()
        self.assertTrue(self.task._battle_entry_confirmed)
        self.task.refresh_character = Mock()
        self.task._initialize_game()
        self.assertEqual(self.task._confirmed_battle_count, 1)
        self.assertIsNone(self.task._pending_battle_id)

    def test_resume_at_preparation_does_not_replay_or_count_unconfirmed_click(self):
        self.configure_battle()
        self.task._begin_session()
        battle_id = str(uuid.uuid4())
        self.task._record_checkpoint(pending_battle_id=battle_id, phase="battle_entry_pending")
        self.task.is_continue = True
        self.task._begin_session()
        self.task.refresh_character = Mock()
        self.task._initialize_game()
        self.assertEqual(self.task._confirmed_battle_count, 0)
        self.assertIsNone(self.task._pending_battle_id)
        self.assertIsNone(self.task._session_store.checkpoint.pending_battle_id)

    def test_resumed_live_combat_counts_after_confirmed_result_only(self):
        self.configure_battle()
        self.task._begin_session()
        self.task._recovery_page = "combat"
        self.task.stage_transition = Mock(return_value=True)
        self.assertTrue(self.task._recover_live_page())
        self.assertEqual(self.task._confirmed_battle_count, 1)
        self.assertIsNone(self.task._pending_battle_id)

    def test_equipment_checkpoint_completion_and_resume_skip_same_interval(self):
        self.configure()
        self.task._begin_session()
        for _ in range(2):
            self.task._pending_battle_id = str(uuid.uuid4())
            self.task._battle_entry_confirmed = True
            self.task._record_checkpoint(pending_battle_id=self.task._pending_battle_id)
            self.task._confirm_completed_battle("settlement")
        self.task.equipment_interval_battles = 2
        self.task._equip_observation = Mock()
        self.assertTrue(self.task._process_equipment())
        self.assertEqual(self.task._session_store.checkpoint.equipment_batch_state, "completed")
        self.task.is_continue = True
        self.task._begin_session()
        self.assertFalse(self.task._process_equipment())
        self.assertEqual(self.task._equipment_battles_since_check, 0)

    def test_purchase_budget_is_reserved_before_refreshing_new_offer(self):
        self.configure(gold=60,level=7)
        self.task.shopping_budget['purchases']=0
        result=self.task.shopping()
        self.assertEqual(result.reason,'purchase_budget')
        self.assertEqual(self.operator.keys(),[])

    def test_equipment_processes_after_second_and_fourth_actual_battle(self):
        self.configure()
        self.task._begin_session()
        self.task.equipment_interval_battles=2
        self.task._equip_observation=Mock()
        for battle_number in range(1,5):
            self.task._pending_battle_id=str(uuid.uuid4())
            self.task._battle_entry_confirmed=True
            self.task._record_checkpoint(pending_battle_id=self.task._pending_battle_id)
            self.task._confirm_completed_battle('settlement')
            self.task._preparation_deadline=self.task._formation_deadline=None
            self.task._begin_preparation()
            self.task._invalidate_equipment_resources('new battle reward')
            completed=self.task._process_equipment()
            self.assertEqual(completed,battle_number in (2,4))
        self.assertEqual(self.task._equip_observation.call_count,20)
        self.assertEqual(self.task._confirmed_battle_count,4)


if __name__ == "__main__":
    unittest.main()
