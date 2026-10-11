"""Regressions for bounded last-offer handling and observation reuse."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location(
    "_cw_optimization2_fixture", Path(__file__).with_name("test_currency_wars_flow.py"))
fixture = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = fixture
spec.loader.exec_module(fixture)


class Optimization2Tests(unittest.TestCase):
    setUp = fixture.CurrencyWarsFlowTests.setUp
    character = fixture.CurrencyWarsFlowTests.character
    observe = fixture.CurrencyWarsFlowTests.observe
    empty_board = fixture.CurrencyWarsFlowTests.empty_board
    shop = fixture.CurrencyWarsFlowTests.shop
    card = fixture.CurrencyWarsFlowTests.card
    scan_sequence = fixture.CurrencyWarsFlowTests.scan_sequence
    configure_main_c = fixture.CurrencyWarsFlowTests.configure_main_c

    def tail_offer(self):
        self.empty_board()
        character = self.configure_main_c()
        self.task.min_level = self.task.mid_level = 3
        self.task.shopping_budget.update(actions=3, refreshes=1)
        self.task._confirm_purchase = Mock(return_value=self.logic.ActionResult.CONFIRMED)
        return self.logic.ShopCard(2, character, self.task.store_area[2], price=3)

    def test_last_refresh_can_buy_target_without_another_refresh(self):
        card = self.tail_offer()
        self.scan_sequence(self.shop(self.logic.ShopState.EMPTY), self.shop(self.logic.ShopState.READY, card))
        result = self.task.shopping()
        self.assertEqual((result.refreshes, result.confirmed_purchases), (1, 1))
        self.assertEqual(self.operator.keys(), ["d"])
        self.assertEqual(self.task._scan_store.call_count, 2)

    def test_current_offer_is_bought_before_mid_level_experience(self):
        card = self.tail_offer()
        self.task.mid_level = 7
        self.scan_sequence(self.shop(self.logic.ShopState.EMPTY), self.shop(self.logic.ShopState.READY, card))
        self.assertEqual(self.task.shopping().confirmed_purchases, 1)
        self.assertNotIn("f", self.operator.keys())

    def test_zero_experience_allowance_does_not_drop_refreshed_target(self):
        card = self.tail_offer()
        self.task.mid_level = 7
        self.task.shopping_budget["experiences"] = 0
        self.scan_sequence(self.shop(self.logic.ShopState.EMPTY), self.shop(self.logic.ShopState.READY, card))
        self.assertEqual(self.task.shopping().confirmed_purchases, 1)

    def test_refreshed_price_verified_target_can_buy_with_unknown_level(self):
        card = self.tail_offer()
        self.task.get_level = Mock(side_effect=[5, None])
        self.scan_sequence(self.shop(self.logic.ShopState.EMPTY), self.shop(self.logic.ShopState.READY, card))
        self.assertEqual(self.task.shopping().confirmed_purchases, 1)
        self.assertNotIn("f", self.operator.keys())

    def test_refreshed_target_below_refresh_coin_reserve_still_buys(self):
        card = self.tail_offer()
        self.task.main_c_search_min_coins = 0
        self.task.get_coins = Mock(side_effect=[5, 3, 3])
        self.scan_sequence(self.shop(self.logic.ShopState.EMPTY), self.shop(self.logic.ShopState.READY, card))
        self.assertEqual(self.task.shopping().confirmed_purchases, 1)

    def test_soft_time_boundary_finishes_new_offer_with_same_deadline(self):
        card = self.tail_offer()
        clock = [0]
        def scan():
            if "d" in self.operator.keys():
                clock[0] = 60
                return self.shop(self.logic.ShopState.READY, card)
            return self.shop(self.logic.ShopState.EMPTY)
        self.task._scan_store = Mock(side_effect=scan)
        with patch.object(self.module.time, "monotonic", side_effect=lambda: clock[0]):
            result = self.task.shopping()
        self.assertEqual(result.confirmed_purchases, 1)

    def test_slow_scan_still_allows_confirmed_purchase(self):
        card = self.tail_offer()
        clock = [0]
        def scan():
            clock[0] = 91
            return self.shop(self.logic.ShopState.READY, card)
        self.task._scan_store = Mock(side_effect=scan)
        with patch.object(self.module.time, "monotonic", side_effect=lambda: clock[0]):
            result = self.task.shopping()
        self.assertEqual(result.confirmed_purchases, 1)
        self.assertNotIn("d", self.operator.keys())

    def test_action_budget_reserves_a_purchase_after_refresh(self):
        card = self.tail_offer()
        self.task.shopping_budget["actions"] = 2
        self.scan_sequence(self.shop(self.logic.ShopState.EMPTY), self.shop(self.logic.ShopState.READY, card))
        result = self.task.shopping()
        self.assertEqual((result.refreshes, result.attempted_purchases), (1, 1))

    def test_level_three_prioritizes_minimum_upgrade_with_four_coins(self):
        self.task.min_level = 5
        self.task.get_coins = Mock(return_value=4)
        self.task.get_level = Mock(return_value=3)
        self.task._can_upgrade = Mock(return_value=True)
        self.scan_sequence(self.shop(self.logic.ShopState.EMPTY))
        self.task.shopping()
        self.assertEqual(self.operator.keys(), ["f"])

    def test_equipment_reuses_confirmed_names_and_stars(self):
        self.empty_board()
        char = self.character()
        self.task.strategy_characters = {char.name: 2}
        self.observe("on_field", 0, char, stars=2)
        self.task._observe_slot = Mock(side_effect=AssertionError("Unnecessary character OCR"))
        self.task._process_equipment()
        self.task._observe_slot.assert_not_called()
        self.assertEqual(sum(name == "locate" and args and args[0] == "EQUIPMENT_RECOMMEND" for name, args, _ in self.operator.calls), 1)

    def test_uncertain_equipment_is_bounded_and_new_rewards_enable_retry(self):
        self.empty_board()
        char = self.character()
        self.task.strategy_characters = {char.name: 2}
        self.observe("on_field", 0, char, stars=2)
        for _ in range(5):
            self.task._process_equipment()
        self.assertEqual(sum(name == "locate" and args and args[0] == "EQUIPMENT_RECOMMEND" for name, args, _ in self.operator.calls), 2)
        self.assertNotIn(char.name, self.task._equipment_checked)
        self.task._invalidate_equipment_resources("new_reward")
        self.task._process_equipment()
        self.assertEqual(sum(name == "locate" and args and args[0] == "EQUIPMENT_RECOMMEND" for name, args, _ in self.operator.calls), 3)

    def test_completed_bench_instance_is_retained_but_surplus_can_sell(self):
        self.empty_board()
        char = self.character("火花")
        self.task.strategy_characters = {char.name: 2}
        self.observe("on_field", 0, self.character("银狼LV.999"), stars=1)
        self.task.max_team_size = 1
        self.observe("in_hand", 0, char, stars=2)
        self.observe("in_hand", 2, char, stars=1)
        self.assertEqual([i for i, _ in self.task._sell_candidates()], [2])
        self.task.strategy_characters[char.name] = 3
        self.assertEqual(self.task._sell_candidates(), [])

    def test_pending_merge_or_unknown_stars_protect_all_copies(self):
        self.empty_board()
        char = self.character("火花")
        self.task.strategy_characters = {char.name: 2}
        self.observe("on_field", 0, self.character("银狼LV.999"), stars=1)
        self.task.max_team_size = 1
        self.observe("in_hand", 0, char, stars=2)
        self.observe("in_hand", 2, char, stars=None)
        self.assertEqual(self.task._sell_candidates(), [])
        self.observe("in_hand", 2, char, stars=1)
        self.task._purchase_pending_names.add(char.name)
        self.assertEqual(self.task._sell_candidates(), [])

    def test_population_unknown_is_not_reread_without_an_actual_change(self):
        self.empty_board()
        self.task._vision.read_population = Mock(return_value=self.module.PopulationObservation(None, None, "test", "unknown", ""))
        self.task.update_max_team_size()
        self.task.update_max_team_size()
        self.assertEqual(self.task._vision.read_population.call_count, 1)
        self.observe("on_field", 0, self.character(), stars=1)
        self.task.update_max_team_size()
        self.assertEqual(self.task._vision.read_population.call_count, 2)

    def test_slow_bench_scan_ignores_removed_shop_deadline(self):
        self.empty_board()
        self.task._bench_dirty = True
        self.task._purchase_pending_names.add("火花")
        self.task._shopping_deadline = 1
        self.task._bench_observed_at = 0
        clock = [0]
        def observe(area, index, *args, **kwargs):
            clock[0] = 2
            return self.task._observations[area][index]
        self.task._observe_slot = Mock(side_effect=observe)
        with patch.object(self.module.time, "monotonic", side_effect=lambda: clock[0]):
            self.task.get_in_hand_area(True)
        self.assertEqual(self.task._observe_slot.call_count, 9)
        self.assertFalse(self.task._bench_dirty)
        self.assertEqual(self.task._bench_observed_at, 2)
        self.assertNotIn("火花", self.task._purchase_pending_names)
        self.assertTrue(all(o.state == self.logic.SlotState.EMPTY
                            for o in self.task._observations["in_hand"]))

    def test_equipment_slow_recommendation_lookup_sends_no_late_input(self):
        self.empty_board()
        char = self.character()
        self.task.strategy_characters = {char.name: 2}
        self.observe("on_field", 0, char, stars=2)
        self.task._preparation_deadline = 1
        clock = [0]
        def locate(*args, **kwargs):
            clock[0] = 2
            return fixture.FakeBox()
        self.operator.locate = Mock(side_effect=locate)
        self.operator.click_box = Mock(return_value=True)
        with patch.object(self.module.time, "monotonic", side_effect=lambda: clock[0]):
            self.task._process_equipment()
        self.operator.click_box.assert_not_called()

    def test_free_purchase_requires_both_empty_card_and_exact_zero_deduction(self):
        card = self.logic.ShopCard(2, self.character(), self.task.store_area[2], price=0)
        self.task.get_coins = Mock(return_value=50)
        self.task._scan_store = Mock(return_value=self.shop(self.logic.ShopState.EMPTY))
        self.assertEqual(self.task._confirm_purchase(card, 50), self.logic.ActionResult.CONFIRMED)
        self.task._scan_store = Mock(return_value=self.shop(self.logic.ShopState.READY, card))
        self.assertEqual(self.task._confirm_purchase(card, 50), self.logic.ActionResult.INDETERMINATE)
        self.task.get_coins = Mock(return_value=49)
        self.task._scan_store = Mock(return_value=self.shop(self.logic.ShopState.EMPTY))
        self.assertEqual(self.task._confirm_purchase(card, 50), self.logic.ActionResult.INDETERMINATE)

    def test_old_shop_deadline_does_not_block_per_action_confirmation(self):
        self.task._shopping_deadline = 1
        self.task._can_upgrade = Mock(return_value=True)
        with patch.object(self.module.time, "monotonic", return_value=2):
            self.assertTrue(self.task._buy_experience(3))
            observation = self.task._observe_slot("in_hand", 0, count_stars=True)
        self.assertEqual(observation.state, self.logic.SlotState.UNKNOWN)
        self.assertEqual(self.operator.keys(), ["f"])

    def test_slow_checkpoint_still_allows_purchase(self):
        card = self.tail_offer()
        self.task._scan_store = Mock(return_value=self.shop(self.logic.ShopState.READY, card))
        clock = [0]
        def checkpoint(**kwargs):
            clock[0] = 91
        self.task._record_checkpoint = Mock(side_effect=checkpoint)
        with patch.object(self.module.time, "monotonic", side_effect=lambda: clock[0]):
            result = self.task.shopping()
        self.assertEqual(result.confirmed_purchases, 1)
        self.assertTrue(any(name == "click" and args[:2] == card.target
                            for name, args, _ in self.operator.calls))

    def test_move_retry_key_changes_on_real_stars_but_not_observation_revision(self):
        self.empty_board()
        self.observe("on_field", 0, self.character("绯英"), stars=2)
        self.observe("in_hand", 0, self.character("火花"), stars=1)
        first = self.task._move_key("in_hand", 0, "on_field", 0)
        self.observe("in_hand", 0, self.character("火花"), stars=1)
        self.assertEqual(first, self.task._move_key("in_hand", 0, "on_field", 0))
        self.observe("in_hand", 0, self.character("火花"), stars=2)
        self.assertNotEqual(first, self.task._move_key("in_hand", 0, "on_field", 0))


if __name__ == "__main__":
    unittest.main()
