"""Page cleanup consumes preparation time without renewing shopping allowances."""

from dataclasses import replace
import unittest
from unittest.mock import Mock, patch

import test_currency_wars_page_purchase as fixture


class PageCleanupTimingTests(unittest.TestCase):
    setUp = fixture.PagePurchaseTests.setUp
    configure = fixture.PagePurchaseTests.configure
    configure_page = fixture.PagePurchaseTests.configure_page
    character = fixture.PagePurchaseTests.character
    observe = fixture.PagePurchaseTests.observe
    empty_board = fixture.PagePurchaseTests.empty_board
    shop = fixture.PagePurchaseTests.shop
    card = fixture.PagePurchaseTests.card
    install_game = fixture.PagePurchaseTests.install_game
    add_physical_copy = fixture.PagePurchaseTests.add_physical_copy
    assert_clean_finish = fixture.PagePurchaseTests.assert_clean_finish

    def test_slow_shop_preserves_remaining_deadlines_but_cleanup_consumes_them(self):
        clock = [100.0]
        with patch.object(self.module.time, "monotonic", side_effect=lambda: clock[0]):
            self.task._begin_preparation()
            self.task._preparation_round = (2, 1)
            self.configure_page(gold=12)
            self.task._preparation_deadline = 110.0
            self.task._formation_deadline = 108.0
            self.task.strategy_characters = {"三月七": 1}
            self.install_game([[self.card("三月七", price=1)]])
            scan_store = self.task._scan_store.side_effect

            def slow_scan():
                clock[0] += 10.0
                return scan_store()

            self.task._scan_store.side_effect = slow_scan
            place = self.task.place_character.side_effect

            def timed_place():
                # Both original deadlines expired during OCR. Their original
                # remaining allowance must already be restored before movement.
                self.assertEqual(clock[0], 120.0)
                self.assertEqual(self.task._preparation_deadline, 130.0)
                self.assertEqual(self.task._formation_deadline, 128.0)
                place()
                clock[0] += 2.0

            self.task.place_character.side_effect = timed_place
            sell = self.task.sell_character.side_effect

            def timed_sell():
                self.assertEqual(self.task._preparation_deadline - clock[0], 8.0)
                self.assertEqual(self.task._formation_deadline - clock[0], 6.0)
                result = sell()
                clock[0] += 3.0
                return result

            self.task.sell_character.side_effect = timed_sell
            coins = self.task.get_coins.side_effect
            final_read_delayed = []

            def slow_final_balance():
                if self.task.sell_character.call_count and not final_read_delayed:
                    final_read_delayed.append(True)
                    clock[0] += 4.0
                return coins()

            self.task.get_coins.side_effect = slow_final_balance

            result = self.task.shopping()

            self.assertEqual(result.confirmed_purchases, 1)
            self.assertEqual(self.task._scan_store.call_count, 2)
            self.task.place_character.assert_called_once()
            self.task.sell_character.assert_called_once()
            self.assertEqual(clock[0], 129.0)
            # OCR took 24 seconds and cleanup took 5. Only OCR is credited,
            # once, so the original 10/8-second allowances now have 5/3 left.
            self.assertEqual(self.task._preparation_deadline, 134.0)
            self.assertEqual(self.task._formation_deadline, 132.0)
            self.assertEqual(self.task._preparation_deadline - clock[0], 5.0)
            self.assertEqual(self.task._formation_deadline - clock[0], 3.0)
            self.assertIsNone(self.task._shopping_clock_started)
            self.assert_clean_finish()

    def test_page_cleanup_and_next_shop_do_not_renew_preparation_or_all_in_budgets(self):
        self.task._begin_preparation()
        self.configure_page(gold=10, purchase_reserve=0)
        # Configurable all-in keeps its batch allowance; mandatory 3-7 has its own rule.
        self.task.economy_config = replace(self.task.economy_config, all_in_round=(3, 6))
        self.task._preparation_round = (3, 6)
        self.task._all_in_budget = 3
        self.task.shopping_budget.update(actions=3, purchases=3, refreshes=2)
        prior = dict(attempts=2, purchases=2, refreshes=0, experiences=0)
        self.task._preparation_shop_counts = dict(prior)
        self.task._preparation_attempts = 7
        self.task._preparation_moves = 3
        flower = self.character("花火")
        self.observe("off_field", 0, flower, stars=1)
        self.task.strategy_characters = {flower.name: 2}
        self.install_game([[self.card(flower.name, 0), self.card(flower.name, 1)]])
        # Exercise the real placement entry point, including _begin_preparation.
        # An existing fielded copy means the new material needs no board movement.
        real_place = self.module.CurrencyWars.place_character.__get__(self.task)
        self.task.place_character = Mock(wraps=real_place)

        first = self.task.shopping()
        calls_after_first = self.operator.click_point.call_count
        second = self.task.shopping()

        self.assertEqual((first.attempted_purchases, first.confirmed_purchases), (1, 1))
        self.assertEqual((second.attempted_purchases, second.confirmed_purchases), (0, 0))
        self.assertEqual((first.reason, second.reason), ("action_budget", "action_budget"))
        self.assertEqual(self.operator.click_point.call_count, calls_after_first)
        self.assertEqual(self.operator.keys(), [])
        self.assertEqual(self.task._preparation_shop_counts,
                         dict(prior, attempts=3, purchases=3))
        self.assertEqual(self.task._all_in_budget, 3)
        self.assertEqual(self.task._preparation_round, (3, 6))
        self.assertEqual(self.task._preparation_attempts, 7)
        self.assertEqual(self.task._preparation_moves, 3)
        self.task.place_character.assert_called_once()
        self.assert_clean_finish()


if __name__ == "__main__":
    unittest.main()
