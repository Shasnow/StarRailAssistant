"""The 30-gold XP/refresh floor and cross-page settlement use real shop flow."""

import unittest
from unittest.mock import Mock

import test_currency_wars_page_purchase as fixture


class PurchaseReserveThirtyTests(unittest.TestCase):
    def game(self, *, gold, level=7, target_level=None, pages=None, setup=None):
        case = fixture.PagePurchaseTests()
        case.setUp()
        self.addCleanup(case.doCleanups)
        case.configure_page(gold=gold, level=level, target_level=target_level,
                            reserve=0, purchase_reserve=30)
        case.task.min_coins = 30
        case.task.strategy_characters = {"花火": 3}
        if setup is not None:
            setup(case)
        case.install_game([[], []] if pages is None else pages(case))
        return case

    def test_experience_requires_at_least_34_gold(self):
        for gold, expected in ((33, 0), (34, 1)):
            with self.subTest(gold=gold):
                case = self.game(gold=gold, level=6, target_level=9)

                result = case.task.shopping()

                self.assertEqual(result.result, case.logic.ActionResult.CONFIRMED)
                self.assertEqual(result.experience_purchases, expected)
                self.assertEqual(result.refreshes, 0)
                self.assertEqual(case.operator.keys(), ["f"] * expected)
                self.assertEqual(case.money, gold - expected * 4)
                self.assertEqual(result.reason, "xp_reserve_floor")
                case.assert_clean_finish()

    def test_refresh_requires_at_least_32_gold(self):
        for gold, expected in ((31, 0), (32, 1)):
            with self.subTest(gold=gold):
                case = self.game(gold=gold)

                result = case.task.shopping()

                self.assertEqual(result.result, case.logic.ActionResult.CONFIRMED)
                self.assertEqual(result.refreshes, expected)
                self.assertEqual(result.experience_purchases, 0)
                self.assertEqual(case.operator.keys(), ["d"] * expected)
                self.assertEqual(case.money, gold - expected * 2)
                self.assertEqual(result.reason, "roll_reserve_floor")
                case.assert_clean_finish()

    def test_needed_purchase_can_cross_floor_then_stops_refresh_and_experience(self):
        for level, target, reason in ((7, 7, "roll_reserve_floor"),
                                      (6, 9, "xp_reserve_floor")):
            with self.subTest(level=level, target=target):
                case = self.game(gold=31, level=level, target_level=target,
                                 pages=lambda game: [[game.card("花火", price=2)]])

                result = case.task.shopping()

                self.assertEqual(result.result, case.logic.ActionResult.CONFIRMED)
                self.assertEqual((result.attempted_purchases, result.confirmed_purchases), (1, 1))
                self.assertEqual(case.money, 29)
                self.assertEqual((result.refreshes, result.experience_purchases), (0, 0))
                self.assertEqual(case.operator.keys(), [])
                self.assertEqual(result.reason, reason)
                self.assertEqual(case.task._observations["in_hand"][0].character.name, "花火")
                self.assertEqual(case.task._recheck_purchased_characters.call_count, 1)
                case.assert_clean_finish()

    def test_cross_page_buys_keep_shop_open_until_30_gold_then_recheck_once(self):
        case = self.game(gold=36, pages=lambda game: [
            [game.card("花火", slot=0, price=2)],
            [game.card("花火", slot=1, price=2)],
        ])
        # The reserve, rather than an input/refresh allowance, ends this cycle.
        case.task.shopping_budget.update(refreshes=10)

        result = case.task.shopping()

        self.assertEqual(result.result, case.logic.ActionResult.CONFIRMED)
        self.assertEqual((result.confirmed_purchases, result.refreshes), (2, 1))
        self.assertEqual(case.money, 30)
        self.assertEqual(result.experience_purchases, 0)
        self.assertEqual(result.reason, "roll_reserve_floor")
        self.assertEqual([purchase[2] for purchase in case.purchases], [0, 0])
        self.assertEqual(case.bench_scans, [(2, 30)])
        self.assertEqual(case.task._recheck_purchased_characters.call_count, 1)
        events = [event[0] for event in case.events]
        self.assertLess(events.index("refresh"), events.index("recheck"))
        case.assert_clean_finish()

    def test_cross_page_himeko_merge_unlocks_experience_only_after_actual_recheck(self):
        def configure_himeko(case):
            himeko = case.character("姬子·启行")
            case.observe("on_field", 1, himeko, stars=2)
            case.observe("in_hand", 0, himeko, stars=2)
            case.observe("in_hand", 1, himeko, stars=1)
            case.task.main_c = himeko.name
            case.task.main_c_first_fielded_confirmed = True
            case.task.strategy_characters = {himeko.name: 3}
            stage = case.module.FormationStage("himeko", 0, ("佩拉", himeko.name), ())
            case.task.formation_config = case.module.FormationConfig(
                {}, {}, {}, (stage,), case.module.UpgradeGate(7, {himeko.name: 3}, {}, {}))

        case = self.game(gold=40, level=7, target_level=9, setup=configure_himeko,
                         pages=lambda game: [
                             [game.card("姬子·启行", slot=0, price=1)],
                             [game.card("姬子·启行", slot=1, price=1)],
                         ])
        case.task.shopping_budget.update(refreshes=10)
        press = case.operator.on_press

        def require_confirmed_three_stars_before_experience(key):
            if key == "f":
                self.assertEqual(case.task._observations["on_field"][1].stars, 3)
                self.assertEqual(case.task._recheck_purchased_characters.call_count, 1)
                case.task.place_character.assert_called_once()
            press(key)

        case.operator.on_press = require_confirmed_three_stars_before_experience

        result = case.task.shopping()

        self.assertEqual(result.result, case.logic.ActionResult.CONFIRMED)
        self.assertEqual((result.confirmed_purchases, result.refreshes,
                          result.experience_purchases), (2, 1, 1))
        self.assertEqual(case.money, 32)  # 40 - 1 - 2 refresh - 1 - 4 XP.
        self.assertEqual(result.reason, "xp_reserve_floor")
        self.assertEqual(case.operator.keys(), ["d", "f"])
        self.assertEqual([purchase[2] for purchase in case.purchases], [0, 0])
        self.assertEqual(case.bench_scans, [(2, 36)])
        self.assertEqual(case.task._recheck_purchased_characters.call_count, 1)
        self.assertEqual(case.physical["on_field"][1].stars, 3)
        self.assertEqual(case.task._observations["on_field"][1].stars, 3)
        events = [event[0] for event in case.events]
        self.assertLess(events.index("refresh"), events.index("recheck"))
        self.assertLess(events.index("rechecked"), events.index("place"))
        self.assertLess(events.index("place"), events.index("experience"))
        case.assert_clean_finish()

    def test_stop_during_boundary_recheck_records_each_purchase_input_once(self):
        case = self.game(gold=31,
                         pages=lambda game: [[game.card("花火", price=2)]])
        prior = dict(attempts=4, purchases=2, refreshes=1, experiences=1)
        case.task._preparation_shop_counts = dict(prior)
        recheck = case.task._recheck_purchased_characters
        stopped_at = []

        def stop_during_recheck(names):
            case.operator.stop_event.set()
            stopped_at.append(len(case.operator.calls))
            return recheck(names)

        case.task._recheck_purchased_characters = Mock(side_effect=stop_during_recheck)
        with self.assertRaises(case.module.ThreadStoppedError):
            case.task.shopping()

        self.assertEqual(len(case.purchases), 1)
        self.assertEqual(case.task._preparation_shop_counts,
                         dict(prior, attempts=5))
        self.assertEqual(len(case.operator.calls), stopped_at[0])
        self.assertEqual(case.operator.keys(), [])
        case.task.place_character.assert_not_called()
        case.task.sell_character.assert_not_called()
        self.assertFalse(case.task._shopping_active)

    def test_stop_after_boundary_confirmation_records_input_and_purchase_once(self):
        case = self.game(gold=31,
                         pages=lambda game: [[game.card("花火", price=2)]])
        stopped_at = []

        def stop_before_placement():
            case.operator.stop_event.set()
            stopped_at.append(len(case.operator.calls))

        case.task.place_character = Mock(side_effect=stop_before_placement)
        with self.assertRaises(case.module.ThreadStoppedError):
            case.task.shopping()

        self.assertEqual(len(case.purchases), 1)
        self.assertEqual(case.task._preparation_shop_counts,
                         dict(attempts=1, purchases=1, refreshes=0, experiences=0))
        self.assertEqual(len(case.operator.calls), stopped_at[0])
        self.assertEqual(case.operator.keys(), [])
        case.task.sell_character.assert_not_called()
        self.assertFalse(case.task._shopping_active)


if __name__ == "__main__":
    unittest.main()
