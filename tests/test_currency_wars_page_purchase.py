"""Shop OCR failures exercised against independent physical card/board state."""

from dataclasses import replace
import unittest
from unittest.mock import Mock

import test_currency_wars_batch_flow as fixture


class PagePurchaseTests(unittest.TestCase):
    setUp = fixture.ShoppingBatchFlowTests.setUp
    configure = fixture.ShoppingBatchFlowTests.configure
    character = fixture.ShoppingBatchFlowTests.character
    observe = fixture.ShoppingBatchFlowTests.observe
    empty_board = fixture.ShoppingBatchFlowTests.empty_board
    shop = fixture.ShoppingBatchFlowTests.shop
    card = fixture.ShoppingBatchFlowTests.card
    add_physical_copy = fixture.ShoppingBatchFlowTests.add_physical_copy
    assert_clean_finish = fixture.ShoppingBatchFlowTests.assert_clean_finish

    def configure_page(self, *, gold=12, level=7, target_level=None, reserve=0,
                       purchase_reserve=5):
        self.configure(gold=gold, level=level)
        self.task.economy_config = self.module.parse_economy_config({
            "enabled": True, "purchase_reserve_gold": purchase_reserve,
            "stages": [{"from_battles": 0, "target_level": target_level or level,
                        "reserve_gold": reserve}],
        })
        self.task.shopping_budget.update(actions=25, refreshes=1, purchases=15,
                                         experiences=1)

    def install_game(self, pages, *, unknown_prices=(), fail_purchase=False):
        # The physical cards retain their real costs. Only their OCR snapshots
        # lose price digits, so this does not accidentally make a card free.
        fixture.ShoppingBatchFlowTests.install_physical_game(
            self, pages, fail_purchase=fail_purchase)
        physical_scan = self.task._scan_store.side_effect

        def scan():
            offer = physical_scan()
            self.events.append(("scan", self.page_index))
            return replace(offer, cards=tuple(
                replace(card, price=None, price_evidence="price_not_associated_with_name")
                if card.character.name in unknown_prices else card
                for card in offer.cards))

        self.task._scan_store.side_effect = scan
        physical_click = self.operator.click_point.side_effect

        def click(x, y, *args, **kwargs):
            card = next((card for card in self.pages[self.page_index]
                         if card.target == (x, y)), None)
            if card is not None and card.price > self.money:
                self.operator.record("click", x, y, *args, **kwargs)
                return True  # The game ignores an unaffordable purchase.
            return physical_click(x, y, *args, **kwargs)

        self.operator.click_point.side_effect = click
        physical_press = self.operator.on_press

        def press(key):
            if key == "f":
                self.assertTrue(self.shop_open)
                self.money -= self.task.SHOP_EXPERIENCE_COST
                self.events.append(("experience", self.money))
            else:
                physical_press(key)

        self.operator.on_press = press
        read_coins = self.task.get_coins.side_effect

        def coins():
            value = read_coins()
            self.events.append(("coins", value))
            return value

        self.task.get_coins.side_effect = coins
        real_recheck = self.task._recheck_purchased_characters

        def recheck(names):
            self.events.append(("recheck", tuple(sorted(names))))
            result = real_recheck(names)
            self.events.append(("rechecked", result))
            return result

        self.task._recheck_purchased_characters = Mock(side_effect=recheck)

        def place():
            self.assertFalse(self.shop_open)
            self.events.append(("place", len(self.purchases)))
            self.task._placement_pending = False

        self.task.place_character = Mock(side_effect=place)
        real_sell = self.task.sell_character

        def sell():
            self.assertFalse(self.shop_open)
            self.events.append(("sell", len(self.purchases)))
            return real_sell()

        self.task.sell_character = Mock(side_effect=sell)

        def drag(source_x, source_y, target_x, target_y):
            self.assertFalse(self.shop_open)
            self.assertEqual((target_x, target_y), (0.05, 0.86))
            index = self.task.in_hand_area.index((source_x, source_y))
            sold = self.physical["in_hand"][index]
            self.assertEqual(sold.state, self.logic.SlotState.KNOWN)
            self.events.append(("sold", sold.character.name, sold.stars))
            self.physical["in_hand"][index] = self.logic.SlotObservation(
                index, self.logic.SlotState.EMPTY, occupied=False,
                evidence="physical sale", revision=4)
            self.money += 1
            return True

        self.task._safe_drag_to = Mock(side_effect=drag)

    def test_logged_march_price_missing_can_buy_and_reconcile(self):
        self.configure_page(gold=12, level=3)
        self.task.strategy_characters = {"三月七": 1}
        self.install_game([[self.card("三月七", 2, price=1)]],
                          unknown_prices={"三月七"})

        result = self.task.shopping()

        self.assertEqual((result.attempted_purchases, result.confirmed_purchases), (1, 1))
        self.assertEqual(result.result, self.logic.ActionResult.CONFIRMED)
        self.assertEqual(self.money, 11)
        self.assertEqual(self.task._observations["in_hand"][0].character.name, "三月七")
        self.assertEqual(self.task._observations["in_hand"][0].stars, 1)
        self.assertNotEqual(result.reason, "purchase_evidence_unknown")
        self.assert_clean_finish()

    def test_free_card_with_visible_price_confirms_without_coin_decrease(self):
        self.configure_page(gold=0)
        self.task.strategy_characters = {"三月七": 1}
        self.install_game([[self.card("三月七", price=0)]])

        result = self.task.shopping()

        self.assertEqual((result.confirmed_purchases, self.money), (1, 0))
        self.assertEqual(self.task._observations["in_hand"][0].character.name, "三月七")
        self.assert_clean_finish()

    def test_unknown_price_free_card_confirms_from_actual_holding_increase(self):
        self.configure_page(gold=0)
        self.task.strategy_characters = {"三月七": 1}
        self.install_game([[self.card("三月七", price=0)]],
                          unknown_prices={"三月七"})

        result = self.task.shopping()

        self.assertEqual((result.attempted_purchases, result.confirmed_purchases), (1, 1))
        self.assertEqual(self.money, 0)
        self.assertEqual(self.task._observations["in_hand"][0].character.name, "三月七")
        self.assert_clean_finish()

    def test_failed_purchase_is_clicked_once_and_never_counted_or_rechecked(self):
        self.configure_page(gold=12)
        self.task.strategy_characters = {"三月七": 1}
        self.task.shopping_budget.update(refreshes=0)
        self.install_game([[self.card("三月七", price=1)]],
                          unknown_prices={"三月七"}, fail_purchase=True)

        result = self.task.shopping()

        self.assertEqual((result.attempted_purchases, result.confirmed_purchases), (1, 0))
        self.assertEqual(self.money, 12)
        self.assertEqual(self.operator.click_point.call_count, 1)
        self.assertEqual(self.operator.keys(), [])
        self.task._recheck_purchased_characters.assert_not_called()
        self.assertNotEqual(result.reason, "purchase_evidence_unknown")
        self.assert_clean_finish()

    def test_disappeared_free_card_without_holding_increase_is_not_confirmed(self):
        self.configure_page(gold=12)
        self.task.strategy_characters = {"三月七": 1}
        self.install_game([[self.card("三月七", price=0)]],
                          unknown_prices={"三月七"})
        self.add_physical_copy = Mock()  # Simulate a false empty shop-slot reading.

        result = self.task.shopping()

        self.assertEqual((result.attempted_purchases, result.confirmed_purchases), (1, 0))
        self.assertEqual(result.result, self.logic.ActionResult.INDETERMINATE)
        self.assertEqual(self.money, 12)
        self.assertEqual(self.operator.keys(), [])
        self.task.place_character.assert_not_called()
        self.task.sell_character.assert_not_called()
        self.assertIn("三月七", self.task._purchase_pending_names)

    def test_unaffordable_unknown_price_does_not_loop_or_spend(self):
        self.configure_page(gold=1)
        self.task.strategy_characters = {"花火": 2}
        self.install_game([[self.card("花火", price=3)]], unknown_prices={"花火"})

        result = self.task.shopping()

        self.assertEqual((result.attempted_purchases, result.confirmed_purchases), (1, 0))
        self.assertEqual(self.money, 1)
        self.assertEqual(self.operator.click_point.call_count, 1)
        self.assertEqual(self.operator.keys(), [])
        self.assertEqual(result.reason, "roll_reserve_floor")
        self.task._recheck_purchased_characters.assert_not_called()
        self.assert_clean_finish()

    def test_stop_after_page_purchase_sends_no_cleanup_or_further_inputs(self):
        self.configure_page(gold=12)
        self.task.strategy_characters = {"三月七": 1, "花火": 2}
        self.install_game([[self.card("三月七", 0, price=1), self.card("花火", 1)]],
                          unknown_prices={"三月七"})
        scan = self.task._scan_store.side_effect
        stopped_at = []

        def scan_and_stop():
            offer = scan()
            if self.purchases:
                self.operator.stop_event.set()
                stopped_at.append(len(self.operator.calls))
            return offer

        self.task._scan_store.side_effect = scan_and_stop
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task.shopping()

        self.assertEqual(len(self.purchases), 1)
        self.assertEqual(len(self.operator.calls), stopped_at[0])
        self.assertEqual(self.operator.keys(), [])
        self.task.place_character.assert_not_called()
        self.task.sell_character.assert_not_called()
        self.assertFalse(self.task._shopping_active)

    def test_multiple_pages_share_one_recheck_before_placement_and_sales(self):
        self.configure_page(gold=20)
        flower = self.character("花火")
        self.observe("off_field", 0, flower, stars=1)
        self.task.strategy_characters = {flower.name: 2, "符玄": 1}
        self.install_game([[self.card(flower.name, 0), self.card(flower.name, 1)],
                           [self.card("符玄", price=1)]])

        result = self.task.shopping()

        self.assertEqual((result.confirmed_purchases, result.refreshes), (3, 1))
        self.assertEqual(self.task._observations["off_field"][0].stars, 2)
        operations = [event[0] for event in self.events]
        self.assertLess(operations.index("refresh"), operations.index("rechecked"))
        self.assertLess(operations.index("rechecked"), operations.index("place"))
        self.assertLess(operations.index("place"), operations.index("sell"))
        first_page_purchases = [index for index, event in enumerate(self.events)
                                if event == ("purchase", flower.name)]
        self.assertNotIn("coins", operations[first_page_purchases[0]:first_page_purchases[-1]])
        self.assertEqual([purchase[2] for purchase in self.purchases], [0, 0, 0])
        self.task._recheck_purchased_characters.assert_called_once()
        self.assert_clean_finish()

    def test_page_overbuy_retains_completed_character_and_sells_only_surplus(self):
        self.configure_page(gold=12)
        flower = self.character("花火")
        self.observe("off_field", 0, flower, stars=1)
        self.task.strategy_characters = {flower.name: 2, "符玄": 2}
        self.install_game([[self.card(flower.name, slot) for slot in range(3)],
                           [self.card("景元")]])

        result = self.task.shopping()

        self.assertEqual((result.confirmed_purchases, result.refreshes), (3, 1))
        self.assertEqual(self.task._observations["off_field"][0].stars, 2)
        self.assertEqual([event for event in self.events if event[0] == "sold"],
                         [("sold", flower.name, 1)])
        self.assertEqual(self.money, 5)  # 12 - 6 + 1 sale - 2 refresh.
        operations = [event[0] for event in self.events]
        self.assertLess(operations.index("sold"), operations.index("refresh"))
        self.assertEqual([purchase[2] for purchase in self.purchases], [0, 0, 0])
        self.assert_clean_finish()

    def test_actual_balance_below_roll_floor_finishes_without_refresh(self):
        self.configure_page(gold=7)
        self.task.strategy_characters = {"三月七": 1, "花火": 2}
        self.install_game([[self.card("三月七", price=1)]],
                          unknown_prices={"三月七"})

        result = self.task.shopping()

        self.assertEqual((result.confirmed_purchases, result.refreshes, self.money), (1, 0, 6))
        self.assertEqual(result.reason, "roll_reserve_floor")
        self.assertEqual(self.operator.keys(), [])
        self.assert_clean_finish()

    def test_positive_hard_reserve_still_requires_a_known_price(self):
        self.configure_page(gold=12, reserve=5)
        self.task.strategy_characters = {"三月七": 1}
        self.install_game([[self.card("三月七", price=1)]],
                          unknown_prices={"三月七"})

        result = self.task.shopping()

        self.assertEqual((result.attempted_purchases, result.confirmed_purchases), (0, 0))
        self.assertEqual(result.reason, "purchase_evidence_unknown")
        self.assertEqual(self.money, 12)
        self.assertEqual(self.operator.click_point.call_count, 0)
        self.assertEqual(self.operator.keys(), [])
        self.assert_clean_finish()

    def test_positive_hard_reserve_still_blocks_a_known_unaffordable_card(self):
        self.configure_page(gold=6, reserve=5)
        self.task.strategy_characters = {"三月七": 1}
        self.install_game([[self.card("三月七", price=2)]])

        result = self.task.shopping()

        self.assertEqual((result.attempted_purchases, result.confirmed_purchases), (0, 0))
        self.assertEqual(result.reason, "roll_reserve_floor")
        self.assertEqual(self.money, 6)
        self.assertEqual(self.operator.click_point.call_count, 0)
        self.assertEqual(self.operator.keys(), [])
        self.assert_clean_finish()

    def test_last_empty_bench_slot_triggers_real_merge_recheck_before_next_card(self):
        self.configure_page(gold=20)
        flower = self.character("花火")
        self.observe("off_field", 0, flower, stars=1)
        self.observe("in_hand", 0, flower, stars=1)
        fillers = ("黑塔", "艾丝妲", "景元", "镜流", "娜塔莎", "三月七", "灵砂")
        for index, name in enumerate(fillers, 1):
            self.observe("in_hand", index, self.character(name), stars=1)
        self.task.strategy_characters = {name: 1 for name in fillers}
        self.task.strategy_characters.update({flower.name: 2, "符玄": 1})
        flower.priority = 100
        self.install_game([[self.card(flower.name, 0), self.card("符玄", 1)]])

        result = self.task.shopping()

        self.assertEqual((result.confirmed_purchases, result.refreshes), (2, 0))
        self.assertEqual([purchase[2] for purchase in self.purchases], [0, 1])
        self.assertEqual(self.bench_scans, [(1, 18), (2, 16)])
        self.assertEqual(self.task._observations["off_field"][0].stars, 2)
        self.assertFalse(any(event[0] == "sold" for event in self.events))
        self.assert_clean_finish()

    def test_action_budget_confirms_first_card_then_stops_and_survives_reentry(self):
        self.configure_page(gold=20)
        self.task.strategy_characters = {"花火": 2}
        self.task.shopping_budget.update(actions=1)
        self.install_game([[self.card("花火", 0), self.card("花火", 1)]])

        result = self.task.shopping()

        self.assertEqual((result.attempted_purchases, result.confirmed_purchases), (1, 1))
        self.assertEqual(result.reason, "action_budget")
        self.assertEqual(self.money, 18)
        self.assertEqual(self.task._preparation_shop_counts["attempts"], 1)
        self.assertEqual(self.task._observations["in_hand"][0].character.name, "花火")
        second = self.task.shopping()
        self.assertEqual((second.attempted_purchases, second.confirmed_purchases), (0, 0))
        self.assertEqual(self.operator.click_point.call_count, 1)
        self.assert_clean_finish()

    def test_full_bench_with_two_confirmed_materials_can_buy_one_merge_then_recheck(self):
        self.configure_page(gold=20)
        flower = self.character("花火")
        self.observe("off_field", 0, flower, stars=1)
        self.observe("in_hand", 0, flower, stars=1)
        fillers = ("黑塔", "艾丝妲", "景元", "镜流", "娜塔莎", "三月七", "灵砂", "杰帕德")
        for index, name in enumerate(fillers, 1):
            self.observe("in_hand", index, self.character(name), stars=1)
        self.task.strategy_characters = {name: 1 for name in fillers}
        self.task.strategy_characters.update({flower.name: 2, "符玄": 1})
        flower.priority = 100
        self.install_game([[self.card(flower.name, 0), self.card("符玄", 1)]])
        add_copy = self.add_physical_copy

        def merge_without_a_temporary_bench_slot(character):
            if not any(obs.state == self.logic.SlotState.EMPTY for obs in self.physical["in_hand"]):
                self.assertEqual(character.name, flower.name)
                self.assertEqual(self.physical["off_field"][0].stars, 1)
                self.assertEqual(self.physical["in_hand"][0].stars, 1)
                self.physical["off_field"][0] = replace(
                    self.physical["off_field"][0], stars=2, evidence="physical full bench merge")
                self.physical["in_hand"][0] = self.logic.SlotObservation(
                    0, self.logic.SlotState.EMPTY, occupied=False,
                    evidence="physical consumed material", revision=3)
                return
            add_copy(character)

        self.add_physical_copy = merge_without_a_temporary_bench_slot
        result = self.task.shopping()

        self.assertEqual((result.confirmed_purchases, result.refreshes), (2, 0))
        self.assertEqual([purchase[2] for purchase in self.purchases], [0, 1])
        self.assertEqual(self.bench_scans, [(1, 18), (2, 16)])
        self.assertEqual(self.task._observations["off_field"][0].stars, 2)
        self.assertFalse(any(event[0] == "sold" for event in self.events))
        self.assert_clean_finish()

    def test_purchase_budget_confirms_first_card_then_stops_and_survives_reentry(self):
        self.configure_page(gold=20)
        self.task.strategy_characters = {"花火": 2}
        self.task.shopping_budget.update(purchases=1)
        self.install_game([[self.card("花火", 0), self.card("花火", 1)]])

        result = self.task.shopping()

        self.assertEqual((result.attempted_purchases, result.confirmed_purchases), (1, 1))
        self.assertEqual(result.reason, "purchase_budget")
        self.assertEqual(self.money, 18)
        self.assertEqual(self.task._preparation_shop_counts["purchases"], 1)
        second = self.task.shopping()
        self.assertEqual((second.attempted_purchases, second.confirmed_purchases), (0, 0))
        self.assertEqual(self.operator.click_point.call_count, 1)
        self.assert_clean_finish()

    def test_failed_first_card_does_not_prevent_successful_second_card_same_name(self):
        self.configure_page(gold=12)
        self.task.strategy_characters = {"花火": 2}
        self.task.shopping_budget.update(refreshes=0)
        self.install_game([[self.card("花火", 0, price=20),
                            self.card("花火", 1, price=2)]], unknown_prices={"花火"})

        result = self.task.shopping()

        self.assertEqual((result.attempted_purchases, result.confirmed_purchases), (2, 1))
        self.assertEqual(self.money, 10)
        self.assertEqual(self.operator.click_point.call_count, 2)
        self.assertEqual(self.task._observations["in_hand"][0].character.name, "花火")
        self.assertEqual([card.slot_index for card in self.pages[0]], [0])
        self.assert_clean_finish()

    def test_failed_second_same_name_card_does_not_clear_first_pending_purchase(self):
        self.configure_page(gold=12)
        self.task.strategy_characters = {"花火": 2}
        self.task.shopping_budget.update(refreshes=0)
        self.install_game([[self.card("花火", 0, price=2),
                            self.card("花火", 1, price=20)]], unknown_prices={"花火"})
        recheck = self.task._recheck_purchased_characters.side_effect

        def verify_pending(names):
            self.assertEqual(self.task._purchase_pending_names, {"花火"})
            return recheck(names)

        self.task._recheck_purchased_characters.side_effect = verify_pending
        result = self.task.shopping()

        self.assertEqual((result.attempted_purchases, result.confirmed_purchases), (2, 1))
        self.assertEqual(self.money, 10)
        self.assertEqual(self.operator.click_point.call_count, 2)
        self.assertEqual(self.task._observations["in_hand"][0].character.name, "花火")
        self.assertEqual([card.slot_index for card in self.pages[0]], [1])
        self.assert_clean_finish()

    def test_unknown_shop_after_click_forces_holdings_recheck_before_another_purchase(self):
        self.configure_page(gold=12)
        self.task.strategy_characters = {"花火": 1, "符玄": 1}
        self.character("花火").priority = 100
        self.install_game([[self.card("花火", 0), self.card("符玄", 1)]])
        scan = self.task._scan_store.side_effect
        unknown_reads = []

        def intermittent_scan():
            offer = scan()
            if len(self.purchases) == 1 and len(unknown_reads) < 2:
                unknown_reads.append(True)
                return self.shop(self.logic.ShopState.UNKNOWN)
            return offer

        self.task._scan_store.side_effect = intermittent_scan
        result = self.task.shopping()

        self.assertEqual((result.confirmed_purchases, result.refreshes), (2, 0))
        self.assertEqual([purchase[2] for purchase in self.purchases], [0, 1])
        self.assertEqual(len(unknown_reads), 2)
        self.assert_clean_finish()

    def test_two_disappeared_same_name_cards_require_two_actual_copies(self):
        self.configure_page(gold=12)
        self.task.shopping_budget.update(refreshes=0)
        self.task.strategy_characters = {"花火": 2}
        self.install_game([[self.card("花火", 0, price=0), self.card("花火", 1, price=0)]],
                          unknown_prices={"花火"})
        add_copy = self.add_physical_copy

        def only_first_reaches_bench(character):
            if len(self.purchases) == 1:
                add_copy(character)

        self.add_physical_copy = only_first_reaches_bench
        result = self.task.shopping()

        self.assertEqual((result.attempted_purchases, result.confirmed_purchases), (2, 0))
        self.assertEqual(result.result, self.logic.ActionResult.INDETERMINATE)
        self.assertEqual(result.reason, "purchase_recheck_unknown")
        self.assertEqual(self.money, 12)
        self.assertEqual(self.operator.keys(), [])
        self.task.place_character.assert_not_called()
        self.task.sell_character.assert_not_called()
        self.assertIn("花火", self.task._purchase_pending_names)

    def test_level_seven_gate_still_blocks_experience_with_two_star_himeko(self):
        self.configure_page(gold=20, target_level=9)
        himeko = self.character("姬子·启行")
        self.observe("on_field", 1, himeko, stars=2)
        self.task.strategy_characters = {himeko.name: 3}
        stage = self.module.FormationStage("himeko", 0, ("佩拉", himeko.name), ())
        self.task.formation_config = self.module.FormationConfig(
            {}, {}, {}, (stage,), self.module.UpgradeGate(7, {himeko.name: 3}, {}, {}))
        self.install_game([[self.card("景元")], [self.card("镜流")]])

        result = self.task.shopping()

        self.assertEqual((result.experience_purchases, result.refreshes), (0, 1))
        self.assertEqual(self.operator.keys(), ["d"])
        self.assert_clean_finish()

    def test_level_seven_gate_allows_experience_after_three_star_is_fielded(self):
        self.configure_page(gold=20, target_level=9)
        himeko = self.character("姬子·启行")
        self.observe("on_field", 1, himeko, stars=3)
        self.task.strategy_characters = {himeko.name: 3}
        stage = self.module.FormationStage("himeko", 0, ("佩拉", himeko.name), ())
        self.task.formation_config = self.module.FormationConfig(
            {}, {}, {}, (stage,), self.module.UpgradeGate(7, {himeko.name: 3}, {}, {}))
        self.install_game([[self.card("景元")]])

        result = self.task.shopping()

        self.assertEqual((result.experience_purchases, result.refreshes), (1, 0))
        self.assertEqual(self.operator.keys(), ["f"])
        self.assertEqual(self.money, 16)
        self.assert_clean_finish()


if __name__ == "__main__":
    unittest.main()
