"""Regressions for batch invalidation and freshly observed role requirements."""
from dataclasses import replace
import unittest
from unittest.mock import Mock

import test_currency_wars_batch_flow as fixture


class ShoppingBatchReviewTests(unittest.TestCase):
    setUp = fixture.ShoppingBatchFlowTests.setUp
    configure = fixture.ShoppingBatchFlowTests.configure
    configure_batch = fixture.ShoppingBatchFlowTests.configure_batch
    character = fixture.ShoppingBatchFlowTests.character
    observe = fixture.ShoppingBatchFlowTests.observe
    empty_board = fixture.ShoppingBatchFlowTests.empty_board
    shop = fixture.ShoppingBatchFlowTests.shop
    card = fixture.ShoppingBatchFlowTests.card
    install_physical_game = fixture.ShoppingBatchFlowTests.install_physical_game
    add_physical_copy = fixture.ShoppingBatchFlowTests.add_physical_copy
    assert_clean_finish = fixture.ShoppingBatchFlowTests.assert_clean_finish

    def test_unowned_price_change_does_not_create_a_pending_purchase(self):
        self.configure_batch()
        name = self.character("银狼LV.999").name
        self.task._observed_prices[name] = 1
        self.task.shopping_budget.update(refreshes=1)
        self.install_physical_game([[self.card("景元")], [self.card("镜流")]])
        scan = self.task._scan_store.side_effect

        def scan_with_changed_price():
            if self.page_index == 1:
                self.task._observed_prices[name] = 3
            return scan()

        self.task._scan_store.side_effect = scan_with_changed_price
        self.task._recheck_purchased_characters = Mock(
            wraps=self.task._recheck_purchased_characters)

        result = self.task.shopping()

        self.assertEqual(result.result, self.logic.ActionResult.CONFIRMED)
        self.assertEqual((result.confirmed_purchases, result.refreshes, result.reason),
                         (0, 1, "refresh_budget"))
        self.task._recheck_purchased_characters.assert_not_called()
        self.assertEqual(self.bench_scans, [])
        self.assertNotIn(name, self.task._purchase_pending_names)
        self.assert_clean_finish()

    def test_space_recheck_reevaluates_role_requirement_before_new_batch(self):
        self.configure_batch()
        flower = self.character("花火")
        healer = self.character("符玄")
        self.observe("off_field", 0, flower, stars=1)
        self.observe("in_hand", 0, flower, stars=1)
        fillers = ("黑塔", "艾丝妲", "景元", "镜流", "娜塔莎", "三月七", "灵砂")
        self.assertEqual(len(self.task._observations["in_hand"]), len(fillers) + 2)
        for index, name in enumerate(fillers, 1):
            self.assertIsNotNone(self.character(name))
            self.observe("in_hand", index, self.character(name), stars=1)
        early = self.module.FormationStage("before_merge", 0, ("佩拉",), (flower.name,))
        late = self.module.FormationStage("after_merge", 0, ("佩拉",), (flower.name,),
            requires_stars={flower.name: 2},
            role_requirements={"survival": self.module.RoleRequirement(
                1, (healer.name,), (), "block")})
        self.task.formation_config = self.module.FormationConfig({}, {}, {}, (early, late),
            roles={"survival": (self.module.RoleProvider(healer.name, ("off_field",), 1),)})
        self.task.strategy_characters = {flower.name: 3}
        self.task.shopping_budget.update(purchases=2, refreshes=0)
        self.install_physical_game([[self.card(flower.name, 0),
                                     self.card(healer.name, 1), self.card(flower.name, 2)]])

        result = self.task.shopping()

        self.assertEqual([name for name, _, _ in self.purchases], [flower.name, healer.name])
        self.assertEqual((result.confirmed_purchases, result.reason), (2, "role_placement"))
        self.assertEqual(self.bench_scans, [(1, 38)])
        self.assertEqual(self.task._observations["off_field"][0].stars, 2)
        self.assertEqual([card.slot_index for card in self.pages[0]], [2])
        self.assertEqual(self.task._preparation_shop_counts["purchases"], 2)
        self.assertFalse(self.shop_open)

    def test_unknown_price_after_confirmed_purchase_rechecks_before_recovery(self):
        self.configure_batch()
        self.task.strategy_characters = {"花火": 2, "符玄": 2}
        self.character("花火").priority = 100
        self.install_physical_game([[self.card("花火", 0), self.card("符玄", 1)]])
        scan = self.task._scan_store.side_effect

        def scan_with_unknown_price():
            offer = scan()
            if self.purchases:
                return replace(offer, cards=tuple(replace(card, price=None) for card in offer.cards))
            return offer

        self.task._scan_store.side_effect = scan_with_unknown_price

        result = self.task.shopping()

        self.assertEqual((result.confirmed_purchases, result.refreshes), (1, 0))
        self.assertEqual(result.result, self.logic.ActionResult.INDETERMINATE)
        self.assertEqual(result.reason, "purchase_evidence_unknown")
        self.assertEqual(self.bench_scans, [(1, 38)])
        self.assertEqual([name for name, _, _ in self.purchases], ["花火"])
        self.assertEqual(self.task._observations["in_hand"][0].stars, 1)
        self.assert_clean_finish()


if __name__ == "__main__":
    unittest.main()
