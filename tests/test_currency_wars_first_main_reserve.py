"""Missing Himeko may use daily reserved gold through the real shop flow."""

import unittest

import test_currency_wars_purchase_reserve_30 as fixture


class FirstMainReserveTests(unittest.TestCase):
    game = fixture.PurchaseReserveThirtyTests.game

    @staticmethod
    def missing_himeko(case):
        case.task.main_c = "姬子·启行"
        case.task.main_c_search_level = 5
        case.task.main_c_search_min_coins = 0
        case.task.main_c_first_fielded_confirmed = False
        case.task.strategy_characters = {"姬子·启行": 3, "花火": 3}

    def test_missing_himeko_rolls_30_gold_to_zero_and_31_to_one(self):
        for gold in (30, 31):
            with self.subTest(gold=gold):
                case = self.game(gold=gold, level=5, target_level=9,
                                 setup=self.missing_himeko,
                                 pages=lambda game: [[game.card(name)] for name in
                                     ("佩拉", "藿藿") * 8])
                case.task.shopping_budget.update(actions=60, refreshes=60)

                result = case.task.shopping()

                self.assertEqual(result.result, case.logic.ActionResult.CONFIRMED)
                self.assertEqual((result.refreshes, result.experience_purchases), (15, 0))
                self.assertEqual(case.money, gold % 2)
                self.assertEqual(result.reason, "roll_reserve_floor")
                self.assertFalse(case.task.main_c_first_fielded_confirmed)
                case.assert_clean_finish()

    def test_demand_purchase_below_30_does_not_stop_missing_main_search(self):
        case = self.game(gold=7, level=5, target_level=9, setup=self.missing_himeko,
                         pages=lambda game: [[game.card("花火", price=1)],
                                             [game.card("佩拉")], [game.card("藿藿")],
                                             [game.card("佩拉")]])
        case.task.shopping_budget.update(actions=60, refreshes=60)

        result = case.task.shopping()

        self.assertEqual(result.result, case.logic.ActionResult.CONFIRMED)
        self.assertEqual((result.confirmed_purchases, result.refreshes,
                          result.experience_purchases, case.money), (1, 3, 0, 0))
        self.assertEqual(result.reason, "roll_reserve_floor")
        self.assertEqual(case.task._observations["in_hand"][0].character.name, "花火")
        case.assert_clean_finish()

    def test_buying_himeko_hands_off_to_placement_below_30(self):
        case = self.game(gold=4, level=5, target_level=9, setup=self.missing_himeko,
                         pages=lambda game: [[], [game.card("姬子·启行", price=1)]])

        result = case.task.shopping()

        self.assertEqual(result.result, case.logic.ActionResult.CONFIRMED)
        self.assertEqual((result.confirmed_purchases, result.refreshes,
                          result.experience_purchases, case.money), (1, 1, 0, 1))
        self.assertEqual(result.reason, "main_c_placement")
        self.assertEqual(case.task._observations["in_hand"][0].character.name, "姬子·启行")
        self.assertFalse(case.shop_open)
        self.assertFalse(case.task._shopping_active)
        # Handoff preserves the main candidate for preparation to field it.
        self.assertIn("姬子·启行", case.task._purchase_pending_names)

    def test_confirmed_main_fielded_restores_daily_30_gold_floor(self):
        for gold, expected in ((31, 0), (32, 1)):
            with self.subTest(gold=gold):
                def fielded(case):
                    self.missing_himeko(case)
                    case.task.main_c_first_fielded_confirmed = True
                    case.observe("on_field", 1, case.character("姬子·启行"), stars=1)

                case = self.game(gold=gold, level=7, setup=fielded)

                result = case.task.shopping()

                self.assertEqual((result.refreshes, case.money), (expected, gold - expected * 2))
                self.assertEqual(result.reason, "roll_reserve_floor")
                case.assert_clean_finish()


if __name__ == "__main__":
    unittest.main()
