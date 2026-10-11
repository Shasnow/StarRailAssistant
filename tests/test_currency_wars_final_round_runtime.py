"""Offline final-round regressions against the shipped source code.

The production class and helpers are loaded through the existing isolated flow
loader. Only OCR, input, waits and physical roster observation are fake. No real
game input is sent; every checkpoint is owned by the loader's temporary folder.
These cases exercise decisions and transaction sequencing, not live OCR quality.
"""
from __future__ import annotations

from pathlib import Path
import sys
import time
import unittest
from unittest.mock import Mock, patch

from tests import test_currency_wars_flow as flow


SOURCE_TASKS = Path(__file__).resolve().parents[1] / "tasks/currency_wars"


class BoundedFinalRoundOperator(flow.FakeOperator):
    """80 refreshes require a larger but still explicit finite fake budget."""

    operation_limit = 3000

    def record(self, name, *args, **kwargs):
        self.calls.append((name, args, kwargs))
        if len(self.calls) > self.operation_limit:
            raise flow.OperationBudgetExceeded("Final-round flow exceeded 3000 fake operations")


class CurrencyWarsFinalRoundRuntimeTests(unittest.TestCase):
    character = flow.CurrencyWarsFlowTests.character
    observe = flow.CurrencyWarsFlowTests.observe
    empty_board = flow.CurrencyWarsFlowTests.empty_board
    shop = flow.CurrencyWarsFlowTests.shop

    def setUp(self):
        with patch.object(flow, "TASKS", SOURCE_TASKS):
            self.module, self.characters, self.logic, self.module_names = flow.load_isolated_task()
        self.addCleanup(lambda: [sys.modules.pop(name, None) for name in self.module_names])
        self.assertEqual(Path(self.module.__file__).resolve(), SOURCE_TASKS / "CurrencyWars.py")
        self.assertIn("mandatory-final-round-spending", self.module.CurrencyWars.FLOW_REVISION)
        self.operator = BoundedFinalRoundOperator()
        self.task = self.module.CurrencyWars(self.operator, runtimes=1)
        self.task.is_running = True
        self.empty_board()
        self.task._preparation_deadline = time.monotonic() + 120
        self.task._preparation_round = (3, 7)
        self.task._read_preparation_round = Mock(return_value=(3, 7))
        self.task._set_shop_open = Mock(return_value=True)
        self.task._ensure_shopping_observations = Mock()
        self.task.place_character = Mock()
        self.task.update_max_team_size = Mock()
        self.task.sell_character = Mock(return_value=self.logic.SellResult(self.logic.ActionResult.CONFIRMED))
        self.task.detect_silver_wolf_lv999 = Mock(return_value=False)
        self.task.handle_special_event = Mock()
        self.task._can_upgrade = Mock(return_value=False)
        self.task._vision.capture_sample = Mock()
        self.task._refresh_dirty_field = Mock()
        self.task.strategy_characters = {}
        self.state = dict(level=7, coins=0, xp=0, required=52, page=0, refresh_cost=2)
        self.progress_reads = []
        self.purchase_at_page = None
        self.purchase_price = 1
        self.card_present = False
        self.card_bought = False
        self.task.get_level = Mock(side_effect=lambda: self.state["level"])
        self.task.get_coins = Mock(side_effect=lambda: self.state["coins"])
        self.task._read_experience_progress = Mock(side_effect=self.read_progress)
        self.task._scan_store = Mock(side_effect=self.scan_store)
        self.task._recheck_purchased_characters = Mock(side_effect=self.recheck_purchase)
        self.operator.on_press = self.press
        self.operator.click_point = Mock(side_effect=self.click)

    def read_progress(self, level, *, recognize_cap=False):
        self.assertTrue(recognize_cap)
        self.assertEqual(level, self.state["level"])
        progress = (self.state["xp"], self.state["required"])
        self.progress_reads.append((level, self.state["coins"], progress))
        return progress if self.state["xp"] is not None else None

    def press(self, key):
        if key == "f":
            self.assertGreaterEqual(self.state["coins"], 4)
            self.state["coins"] -= 4
            self.state["xp"] += 4
            if self.state["xp"] >= self.state["required"]:
                self.state["level"] += 1
                self.state["xp"] = 0
                self.state["required"] = {8: 72, 9: 84, 10: 100}.get(self.state["level"], 100)
        elif key == "d":
            self.assertGreaterEqual(self.state["coins"], self.state["refresh_cost"])
            self.state["coins"] -= self.state["refresh_cost"]
            self.state["page"] += 1

    def scan_store(self):
        if self.purchase_at_page == self.state["page"] and not self.card_bought:
            self.card_present = True
        if self.card_present:
            card = self.logic.ShopCard(2, self.character("佩拉"), self.task.store_area[2],
                                       raw_text="佩拉", price=self.purchase_price)
            return self.shop(self.logic.ShopState.READY, card)
        # Alternating non-target cards prove a free refresh changed the page.
        name = "灵砂" if self.state["page"] % 2 else "缇宝"
        card = self.logic.ShopCard(self.state["page"] % 5, self.character(name),
                                  self.task.store_area[self.state["page"] % 5],
                                  raw_text=name, price=5)
        return self.shop(self.logic.ShopState.READY, card)

    def click(self, *args, **kwargs):
        self.operator.record("click", *args, **kwargs)
        if args == self.task.store_area[2] and self.card_present:
            self.assertGreaterEqual(self.state["coins"], self.purchase_price)
            self.state["coins"] -= self.purchase_price
            self.card_present = False
            self.card_bought = True
        return True

    def recheck_purchase(self, names):
        # Only actual successful fake clicks may produce a newly held card.
        if not self.card_bought:
            return False
        self.observe("in_hand", 0, self.character("佩拉"), stars=1)
        self.task._bench_dirty = False
        self.task._dirty_slots.clear()
        self.task._purchase_pending_names.difference_update(names)
        return True

    def configure_purchase(self, *, page=0, price=1):
        self.task.strategy_characters = {"佩拉": 1}
        self.purchase_at_page = page
        self.purchase_price = price

    def test_runtime_revision_and_refresh_limit_are_authoritative(self):
        self.assertEqual(self.task.FINAL_ROUND_REFRESH_LIMIT, 80)
        self.assertEqual(self.task.SHOP_EXPERIENCE_COST, 4)

    def test_seven_to_eight_to_nine_requotes_after_each_level(self):
        self.state.update(level=7, coins=84, xp=48, required=52)
        result = self.task.shopping()
        self.assertEqual(self.state["level"], 9)
        self.assertEqual(self.state["coins"], 0)
        self.assertEqual(result.experience_purchases, 19)
        self.assertEqual(result.refreshes, 4)
        self.assertEqual(self.progress_reads[:3], [(7, 84, (48, 52)), (8, 80, (0, 72)), (9, 8, (0, 84))])
        self.task._can_upgrade.assert_not_called()

    def test_stops_at_eight_when_next_whole_level_is_unaffordable(self):
        self.state.update(level=7, coins=20, xp=48, required=52)
        result = self.task.shopping()
        self.assertEqual(self.state["level"], 8)
        self.assertEqual(result.experience_purchases, 1)
        self.assertEqual(result.refreshes, 8)
        self.assertEqual(self.state["xp"], 0)

    def test_does_not_purchase_partial_level_experience(self):
        self.state.update(level=7, coins=10, xp=0, required=52)
        result = self.task.shopping()
        self.assertEqual(result.experience_purchases, 0)
        self.assertEqual(result.refreshes, 5)
        self.assertEqual(self.state["coins"], 0)

    def test_overrides_target_gate_reserve_and_zero_action_budgets(self):
        self.task.economy_config = self.module.EconomyConfig(999, (self.module.EconomyStage(0, 5, 999),))
        self.task.shopping_budget.update(actions=0, purchases=0, refreshes=0, experiences=0, seconds=0)
        self.state.update(level=7, coins=7, xp=48, required=52)
        self.configure_purchase(price=1)
        result = self.task.shopping()
        self.assertEqual(result.experience_purchases, 1)
        self.assertEqual(result.confirmed_purchases, 1)
        self.assertEqual(result.refreshes, 1)
        self.assertEqual(self.state["coins"], 0)
        self.task._can_upgrade.assert_not_called()

    def test_both_runtime_strategy_configs_apply_mandatory_rule(self):
        for filename in ("himeko_nova_march_pilot_review.json", "silver_wolf_lv999_aha_time_stop.json"):
            with self.subTest(strategy=filename):
                self.task.load_strategy(str(SOURCE_TASKS / "strategies" / filename))
                self.empty_board()
                self.task._preparation_round = (3, 7)
                self.state.update(level=7, coins=4, xp=48, required=52)
                before = self.operator.keys().count("f")
                result = self.task.shopping()
                self.assertEqual(result.experience_purchases, 1)
                self.assertEqual(self.operator.keys().count("f") - before, 1)
                self.assertEqual(self.state["level"], 8)
                self.assertEqual(self.state["coins"], 0)

    def test_level_nine_is_not_treated_as_maximum(self):
        self.state.update(level=9, coins=4, xp=80, required=84)
        result = self.task.shopping()
        self.assertEqual(self.state["level"], 10)
        self.assertEqual(result.experience_purchases, 1)
        self.assertEqual(result.result, self.logic.ActionResult.CONFIRMED)

    def test_free_changing_refreshes_stop_at_eighty(self):
        self.state.update(level=8, coins=4, required=72, refresh_cost=0)
        result = self.task.shopping()
        self.assertEqual(result.reason, "final_round_refresh_limit")
        self.assertEqual(result.refreshes, 80)
        self.assertEqual(self.operator.keys().count("d"), 80)
        self.assertEqual(self.state["coins"], 4)

    def test_paid_refreshes_also_stop_at_eighty(self):
        self.state.update(level=9, coins=200, required=1000)
        result = self.task.shopping()
        self.assertEqual(result.reason, "final_round_refresh_limit")
        self.assertEqual(result.refreshes, 80)
        self.assertEqual(self.state["coins"], 40)

    def test_same_preparation_recovery_preserves_seventy_nine_plus_one_limit(self):
        self.task._preparation_shop_counts["refreshes"] = 79
        self.task._preparation_rewards_collected = True
        self.task._probe_runtime_page = Mock(return_value=("preparation", None))
        self.assertTrue(self.task._recover_runtime_flow(RuntimeError("injected recovery")))
        self.task._begin_preparation()
        self.assertEqual(self.task._preparation_shop_counts["refreshes"], 79)
        self.assertTrue(self.task._preparation_rewards_collected)
        self.state.update(level=8, coins=4, required=72, refresh_cost=0)
        first = self.task.shopping()
        second = self.task.shopping()
        self.assertEqual(first.refreshes, 1)
        self.assertEqual(second.refreshes, 0)
        self.assertEqual(self.operator.keys().count("d"), 1)
        self.assertEqual(self.task._preparation_shop_counts["refreshes"], 80)

    def test_eightieth_refreshed_page_still_buys_demand_card(self):
        self.state.update(level=8, coins=4, required=72, refresh_cost=0)
        self.configure_purchase(page=80, price=1)
        result = self.task.shopping()
        self.assertEqual(result.refreshes, 80)
        self.assertEqual(result.confirmed_purchases, 1)
        self.assertTrue(self.card_bought)
        self.assertEqual(self.state["coins"], 3)
        self.assertEqual(result.reason, "final_round_refresh_limit")

    def test_failed_refresh_return_counts_toward_same_preparation_limit(self):
        self.state.update(level=8, coins=4, required=72, refresh_cost=0)
        self.task._preparation_shop_counts["refreshes"] = 79
        self.operator.press_key = Mock(return_value=False)
        first = self.task.shopping()
        second = self.task.shopping()
        self.assertEqual(first.refreshes, 1)
        self.assertEqual(first.reason, "refresh_click_failed")
        self.assertEqual(second.refreshes, 0)
        self.assertEqual(self.task._preparation_shop_counts["refreshes"], 80)
        self.operator.press_key.assert_called_once_with("d")

    def test_refresh_exception_still_counts_toward_same_preparation_limit(self):
        self.state.update(level=8, coins=4, required=72, refresh_cost=0)
        self.task._preparation_shop_counts["refreshes"] = 79
        self.operator.press_key = Mock(side_effect=RuntimeError("injected input exception"))
        with self.assertRaisesRegex(RuntimeError, "injected input exception"):
            self.task.shopping()
        self.assertEqual(self.task._preparation_shop_counts["refreshes"], 80)
        second = self.task.shopping()
        self.assertEqual(second.refreshes, 0)
        self.operator.press_key.assert_called_once_with("d")

    def test_zero_gold_stops_without_requiring_level_or_experience(self):
        self.state["coins"] = 0
        self.task.get_level = Mock(side_effect=AssertionError("zero gold needs no level read"))
        self.task._read_experience_progress = Mock(side_effect=AssertionError("zero gold needs no XP read"))
        result = self.task.shopping()
        self.assertEqual(result.reason, "final_round_gold_exhausted")
        self.assertEqual(self.operator.keys(), [])

    def test_one_gold_stops_when_no_affordable_card_exists(self):
        self.state["coins"] = 1
        result = self.task.shopping()
        self.assertEqual(result.reason, "final_round_no_affordable_action")
        self.assertEqual(self.state["coins"], 1)
        self.assertEqual(self.operator.keys(), [])
        self.assertEqual(self.progress_reads, [])

    def test_one_gold_buys_a_useful_one_cost_card(self):
        self.state["coins"] = 1
        self.configure_purchase(price=1)
        result = self.task.shopping()
        self.assertEqual(result.confirmed_purchases, 1)
        self.assertEqual(self.state["coins"], 0)
        self.assertEqual(self.operator.keys(), [])

    def test_unknown_experience_requests_bounded_recovery_and_never_battle(self):
        self.state.update(coins=8, xp=None)
        result = self.task.shopping()
        self.assertEqual(result.result, self.logic.ActionResult.INDETERMINATE)
        self.assertEqual(result.reason, "final_round_experience_unknown")
        for _ in range(self.task.preparation_budget["recoveries"]):
            self.assertTrue(self.task._resume_shopping_after(result))
        with self.assertRaisesRegex(RuntimeError, "购物证据恢复无进展"):
            self.task._resume_shopping_after(result)
        self.assertEqual(self.operator.keys(), [])

    def test_unknown_new_level_experience_does_not_spend_unbudgeted_xp(self):
        self.state.update(level=7, coins=12, xp=48, required=52)
        read = self.read_progress

        def unknown_after_upgrade(level, **kwargs):
            return read(level, **kwargs) if level == 7 else None

        self.task._read_experience_progress = Mock(side_effect=unknown_after_upgrade)
        result = self.task.shopping()
        self.assertEqual(result.reason, "final_round_experience_unknown")
        self.assertEqual(result.result, self.logic.ActionResult.INDETERMINATE)
        self.assertEqual(result.experience_purchases, 1)
        self.assertEqual(result.refreshes, 0)
        self.assertEqual(self.state["level"], 8)
        self.assertEqual(self.state["coins"], 8)

    def test_explicit_max_level_still_spends_on_refreshes(self):
        self.state.update(level=10, coins=4, xp=0, required=0)
        result = self.task.shopping()
        self.assertEqual(result.experience_purchases, 0)
        self.assertEqual(result.refreshes, 2)
        self.assertEqual(self.state["coins"], 0)

    def test_partial_shop_page_never_authorizes_refresh(self):
        self.state.update(level=8, coins=4, required=72)
        self.task._scan_store = Mock(return_value=self.logic.ShopObservation(
            self.logic.ShopState.READY, cards=(), reason="partial_missing_slot"))
        result = self.task.shopping()
        self.assertEqual(result.result, self.logic.ActionResult.INDETERMINATE)
        self.assertEqual(result.reason, "partial_store")
        self.assertEqual(self.operator.keys(), [])


if __name__ == "__main__":
    unittest.main()
