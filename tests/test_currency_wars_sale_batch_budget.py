"""A completed sale batch must not trigger page recovery for remaining surplus."""

import unittest
from unittest.mock import Mock, patch

import test_currency_wars_flow as fixture


class SaleBatchBudgetTests(unittest.TestCase):
    setUp = fixture.CurrencyWarsFlowTests.setUp
    character = fixture.CurrencyWarsFlowTests.character
    observe = fixture.CurrencyWarsFlowTests.observe
    empty_board = fixture.CurrencyWarsFlowTests.empty_board
    install_local_sale_board = fixture.CurrencyWarsFlowTests.install_local_sale_board

    def configure_sale(self):
        self.empty_board()
        self.task.max_team_size = 1
        self.task._population_current = 1
        self.observe("on_field", 0, self.character(), stars=1)
        self.observe("in_hand", 0, self.character("佩拉"), stars=1)
        self.observe("in_hand", 1, self.character("椒丘"), stars=1)
        return self.install_local_sale_board()

    def test_budget_after_confirmed_sale_defers_remaining_card_and_next_batch_resumes(self):
        sold = self.configure_sale()
        clock = [0.0]
        confirm = self.task._confirm_sale

        def slow_confirm(*args):
            result = confirm(*args)
            clock[0] += 31
            return result

        self.task._confirm_sale = Mock(side_effect=slow_confirm)
        with patch.object(self.module.time, "monotonic", side_effect=lambda: clock[0]):
            result = self.task.sell_character()
            self.assertEqual(result.result, self.logic.ActionResult.CONFIRMED)
            self.assertEqual((result.attempted, result.confirmed), (1, 1))
            self.assertEqual(result.reason, "cleanup_deferred_time_budget")
            self.assertEqual(sold, {0})
            self.assertEqual(self.task.in_hand_character[1].name, "椒丘")
            resumed = self.task.sell_character()

        self.assertEqual(resumed.result, self.logic.ActionResult.CONFIRMED)
        self.assertEqual(resumed.confirmed, 1)
        self.assertEqual(sold, {0, 1})
        self.task.get_in_hand_area.assert_not_called()

    def test_budget_during_next_source_read_keeps_prior_sales_confirmed(self):
        sold = self.configure_sale()
        clock = [0.0]
        observe = self.task._observe_slot.side_effect

        def slow_next_source(area, index, **kwargs):
            result = observe(area, index, **kwargs)
            if index == 1:
                clock[0] = 31.0
            return result

        self.task._observe_slot.side_effect = slow_next_source
        with patch.object(self.module.time, "monotonic", side_effect=lambda: clock[0]):
            result = self.task.sell_character()

        self.assertEqual(result.result, self.logic.ActionResult.CONFIRMED)
        self.assertEqual((result.attempted, result.confirmed), (1, 1))
        self.assertEqual(result.reason, "cleanup_deferred_time_budget")
        self.assertEqual(sold, {0})
        self.task.get_in_hand_area.assert_not_called()

    def test_budget_during_first_source_read_does_not_send_a_drag(self):
        sold = self.configure_sale()
        clock = [0.0]

        def slow_coins():
            clock[0] = 31.0
            return 50

        self.task.get_coins = Mock(side_effect=slow_coins)
        with patch.object(self.module.time, "monotonic", side_effect=lambda: clock[0]):
            result = self.task.sell_character()

        self.assertEqual(result.result, self.logic.ActionResult.CONFIRMED)
        self.assertEqual((result.attempted, result.confirmed), (0, 0))
        self.assertEqual(sold, set())
        self.assertEqual(self.task.in_hand_character[0].name, "佩拉")

    def test_unconfirmed_drag_remains_indeterminate_even_after_budget(self):
        self.configure_sale()
        clock = [0.0]

        def uncertain_confirmation(*args):
            clock[0] = 31.0
            return self.logic.ActionResult.INDETERMINATE

        self.task._confirm_sale = Mock(side_effect=uncertain_confirmation)
        with patch.object(self.module.time, "monotonic", side_effect=lambda: clock[0]):
            result = self.task.sell_character()

        self.assertEqual(result.result, self.logic.ActionResult.INDETERMINATE)
        self.assertEqual((result.attempted, result.confirmed), (1, 0))
        self.assertEqual(result.reason, "sale_not_confirmed")
        self.assertEqual(len(self.operator.drags()), 1)
        self.task.get_in_hand_area.assert_not_called()


if __name__ == "__main__":
    unittest.main()
