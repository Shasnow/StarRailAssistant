"""Upload review regressions against independently maintained game state."""

from dataclasses import replace
import unittest

import test_currency_wars_page_purchase as fixture


class UploadShopRegressionTests(unittest.TestCase):
    def game(self):
        case = fixture.PagePurchaseTests()
        case.setUp()
        self.addCleanup(case.doCleanups)
        case.configure_page(gold=40, purchase_reserve=30)
        case.task.shopping_budget.update(refreshes=0, purchases=1)
        return case

    def test_full_bench_skips_nonmerge_card_and_buys_later_merge_target(self):
        case = self.game()
        flower = case.character("花火")
        other = case.character("符玄")
        other.priority = 100
        flower.priority = 1
        case.observe("off_field", 0, flower, stars=1)
        case.observe("in_hand", 0, flower, stars=1)
        fillers = ("黑塔", "艾丝妲", "景元", "镜流", "娜塔莎", "三月七", "灵砂", "杰帕德")
        for index, name in enumerate(fillers, 1):
            case.observe("in_hand", index, case.character(name), stars=1)
        case.task.strategy_characters = {name: 1 for name in fillers}
        case.task.strategy_characters.update({flower.name: 2, other.name: 2})
        case.install_game([[case.card(other.name, 0), case.card(flower.name, 1)]])

        def merge_without_temporary_slot(character):
            self.assertEqual(character.name, flower.name)
            case.physical["off_field"][0] = replace(
                case.physical["off_field"][0], stars=2, evidence="physical full bench merge")
            case.physical["in_hand"][0] = case.logic.SlotObservation(
                0, case.logic.SlotState.EMPTY, occupied=False,
                evidence="physical consumed material", revision=3)

        case.add_physical_copy = merge_without_temporary_slot
        result = case.task.shopping()

        self.assertEqual([purchase[0] for purchase in case.purchases], [flower.name])
        self.assertEqual(result.confirmed_purchases, 1)
        self.assertEqual(case.physical["off_field"][0].stars, 2)
        self.assertEqual(result.refreshes, 0)

    def test_full_bench_with_no_mergeable_targets_sends_no_purchase_or_refresh(self):
        case = self.game()
        fillers = ("黑塔", "艾丝妲", "景元", "镜流", "娜塔莎", "三月七", "灵砂", "杰帕德", "佩拉")
        for index, name in enumerate(fillers):
            case.observe("in_hand", index, case.character(name), stars=1)
        case.task.strategy_characters = {name: 1 for name in fillers}
        case.task.strategy_characters.update({"花火": 2, "符玄": 2})
        case.task.shopping_budget.update(refreshes=5)
        case.install_game([[case.card("符玄", 0), case.card("花火", 1)]])

        result = case.task.shopping()

        self.assertEqual((result.attempted_purchases, result.confirmed_purchases,
                          result.refreshes), (0, 0, 0))
        self.assertEqual(result.reason, "purchase_space_blocked")
        case.operator.click_point.assert_not_called()
        self.assertEqual(case.operator.keys(), [])
        case.assert_clean_finish()


if __name__ == "__main__":
    unittest.main()
