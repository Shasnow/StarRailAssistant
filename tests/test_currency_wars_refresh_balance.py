"""Shop refreshes use observed balances and visible progress, never a fee guess."""

from dataclasses import replace
import unittest
from unittest.mock import Mock

import test_currency_wars_flow as fixture
import test_currency_wars_optimization3 as optimization


class RefreshBalanceTests(unittest.TestCase):
    setUp = fixture.CurrencyWarsFlowTests.setUp
    character = fixture.CurrencyWarsFlowTests.character
    observe = fixture.CurrencyWarsFlowTests.observe
    empty_board = fixture.CurrencyWarsFlowTests.empty_board
    shop = fixture.CurrencyWarsFlowTests.shop
    configure = optimization.Optimization3Tests.configure

    def configure_refreshes(self, gold, balance_after, *, all_in=False, same_page=False):
        self.configure(gold=gold, level=9, battles=12)
        if all_in:
            # Test generic configurable all-in balance/cache behavior separately
            # from mandatory 3-7 next-level budgeting and its fixed 80-refresh cap.
            self.task.economy_config = replace(self.task.economy_config, all_in_round=(3, 6))
            self.task._preparation_round = (3, 6)
        self.page = 0
        self.balances = []
        self.offer_target = False
        self.target_bought = False
        self.target = self.character()
        self.target_card = self.logic.ShopCard(2, self.target, self.task.store_area[2], price=4)

        def press(key):
            self.assertEqual(key, "d", "At target level this fixture should only request refreshes")
            self.page += 1
            self.money = balance_after(self.page, self.money)
            self.balances.append(self.money)

        def offer():
            # Only D changes the page; repeated observations do not invent progress.
            name = "佩拉" if same_page or self.page % 2 == 0 else "藿藿"
            filler = self.logic.ShopCard(0, self.character(name), self.task.store_area[0], price=2)
            cards = [filler]
            if self.offer_target and self.page == 1 and not self.target_bought:
                cards.append(self.target_card)
            return self.shop(self.logic.ShopState.READY, *cards)

        self.operator.on_press = press
        self.task._scan_store = Mock(side_effect=offer)

    def test_three_changed_pages_at_52_gold_continue_then_follow_actual_balance(self):
        self.configure_refreshes(52, lambda page, money: money if page <= 3 else money - 2, all_in=True)
        result = self.task.shopping()
        self.assertEqual(self.balances[:4], [52, 52, 52, 50])
        self.assertEqual((result.refreshes, self.money), (29, 0))
        self.assertEqual(result.reason, "roll_reserve_floor")
        self.assertEqual(result.result, self.logic.ActionResult.CONFIRMED)
        self.assertEqual(self.operator.keys(), ["d"] * 29)

    def test_changed_page_can_be_bought_when_refresh_balance_is_unchanged(self):
        self.configure_refreshes(27, lambda page, money: money)
        self.offer_target = True
        physical = {area: list(slots) for area, slots in self.task._observations.items()}

        def click(*coordinates, **kwargs):
            self.operator.record("click", *coordinates, **kwargs)
            self.assertEqual(coordinates, self.target_card.target)
            self.assertEqual(self.page, 1)
            self.assertFalse(self.target_bought)
            self.target_bought = True
            self.money -= self.target_card.price
            physical["in_hand"][0] = self.logic.SlotObservation(0,
                self.logic.SlotState.KNOWN, character=self.target, occupied=True,
                evidence="observed purchase landing", stars=1, revision=2)
            return True

        def read_bench(force):
            for observation in physical["in_hand"]:
                self.task._set_observation("in_hand", observation)
            self.task._bench_dirty = False
            self.task._reconcile_purchase_pending()

        self.operator.click_point = click
        self.task._observe_slot = Mock(side_effect=lambda area, index, **kwargs: physical[area][index])
        self.task.get_in_hand_area = Mock(side_effect=read_bench)
        # Keep the real transaction confirmation: the card disappears and the
        # observed purchase balance changes from 27 to 23 before the next choice.
        result = self.task.shopping()
        self.assertEqual((result.refreshes, result.confirmed_purchases, self.money), (1, 1, 23))
        self.assertEqual(result.reason, "roll_reserve_floor")
        self.assertEqual(self.operator.keys(), ["d"])
        self.assertEqual(self.task._observations["in_hand"][0].character.name, self.target.name)
        self.assertNotIn(self.target.name, self.task._purchase_pending_names)

    def test_regular_two_gold_change_preserves_the_existing_reserve_floor(self):
        self.configure_refreshes(27, lambda page, money: money - 2)
        result = self.task.shopping()
        self.assertEqual((result.refreshes, self.money, result.reason), (1, 25, "roll_reserve_floor"))
        self.assertEqual(self.operator.keys(), ["d"])

    def test_balance_change_other_than_two_gold_drives_the_next_decision(self):
        self.configure_refreshes(29, lambda page, money: money - 3)
        result = self.task.shopping()
        self.assertEqual((result.refreshes, self.money, result.reason), (1, 26, "roll_reserve_floor"))
        self.assertEqual(result.result, self.logic.ActionResult.CONFIRMED)
        self.assertEqual(self.operator.keys(), ["d"])

    def test_increased_balance_can_continue_until_a_later_read_reaches_floor(self):
        self.configure_refreshes(27, lambda page, money: 30 if page == 1 else 25)
        result = self.task.shopping()
        self.assertEqual((result.refreshes, self.money, result.reason), (2, 25, "roll_reserve_floor"))
        self.assertEqual(result.result, self.logic.ActionResult.CONFIRMED)
        self.assertEqual(self.operator.keys(), ["d", "d"])

    def test_unknown_balance_after_a_changed_page_stops_further_inputs(self):
        self.configure_refreshes(29, lambda page, money: None)
        result = self.task.shopping()
        self.assertEqual(result.reason, "unknown_coins_after_refresh")
        self.assertEqual(result.result, self.logic.ActionResult.INDETERMINATE)
        self.assertEqual(self.operator.keys(), ["d"])

    def test_two_unchanged_pages_still_stop_even_when_balance_is_unchanged(self):
        self.configure_refreshes(29, lambda page, money: money, same_page=True)
        result = self.task.shopping()
        self.assertEqual((result.refreshes, result.reason), (2, "refresh_no_progress"))
        self.assertEqual(result.result, self.logic.ActionResult.INDETERMINATE)
        self.assertEqual(self.operator.keys(), ["d", "d"])

    def test_changing_pages_with_unchanged_balance_exhaust_one_cumulative_budget(self):
        self.configure_refreshes(52, lambda page, money: money, all_in=True)
        # The real all-in policy raises these limits once from the observed
        # balance; reopening the shop must not replenish that allowance.
        self.task.shopping_budget.update(actions=5, purchases=5, refreshes=5, experiences=5)
        first = self.task.shopping()
        self.assertEqual((first.refreshes, first.reason), (52, "action_budget"))
        self.assertEqual(self.task._all_in_budget, 53)
        self.assertEqual(self.money, 52)
        self.assertEqual(self.task._preparation_shop_counts["refreshes"], 52)
        second = self.task.shopping()
        self.assertEqual((second.refreshes, second.reason), (0, "action_budget"))
        self.assertEqual(self.task._all_in_budget, 53)
        self.assertEqual(self.operator.keys(), ["d"] * 52)


if __name__ == "__main__":
    unittest.main()
