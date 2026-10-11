"""Real shopping batches against separate physical shop and board snapshots."""
from dataclasses import replace
import unittest
from unittest.mock import Mock

import test_currency_wars_optimization3 as fixture


class ShoppingBatchFlowTests(unittest.TestCase):
    setUp = fixture.Optimization3Tests.setUp
    configure = fixture.Optimization3Tests.configure
    character = fixture.Optimization3Tests.character
    observe = fixture.Optimization3Tests.observe
    empty_board = fixture.Optimization3Tests.empty_board
    shop = fixture.Optimization3Tests.shop

    def configure_batch(self, *, gold=40, all_in=False):
        # The game loop starts the preparation before shopping/placement.
        self.task._begin_preparation()
        self.configure(gold=gold, level=9 if all_in else 7,
                       battles=19 if all_in else 6)
        self.task._preparation_round = (2, 1)
        if all_in:
            # Exercise configurable batch all-in separately from mandatory 3-7 shopping.
            self.task.economy_config = replace(self.task.economy_config, all_in_round=(3, 6))
            self.task._preparation_round = (3, 6)
        self.task.shopping_budget.update(actions=25, refreshes=15, purchases=15)

    def card(self, name, slot=0, price=2):
        return self.logic.ShopCard(slot, self.character(name), self.task.store_area[slot],
                                   price=price, price_evidence="same_slot_independent_digit")

    def install_physical_game(self, pages, *, fail_purchase=False,
                              stop_after=None, unknown_stars=()):
        # Purchases change only these physical snapshots. Production invalidation,
        # reconciliation and the final board scan must update cached observations.
        self.physical = {area: list(slots) for area, slots in self.task._observations.items()}
        self.pages = [list(cards) for cards in pages]
        self.page_index = 0
        self.shop_open = False
        self.events = []
        self.purchases = []
        self.bench_scans = []
        # The shop entry authenticates the closed preparation before reading its round.
        self.close_requests = []
        self.stop_calls = None
        self.task._open_supply_items = Mock()

        def set_shop(opened):
            self.task._check_stop()
            self.shop_open = opened
            self.events.append(("shop", opened))
            if not opened:
                self.close_requests.append(len(self.purchases))
            return True

        def scan_store():
            self.task._check_stop()
            self.assertTrue(self.shop_open)
            cards = self.pages[self.page_index]
            return self.shop(self.logic.ShopState.READY if cards else self.logic.ShopState.EMPTY,
                             *cards)

        def read_slot(area, index, *args, **kwargs):
            self.task._check_stop()
            self.assertFalse(self.shop_open)
            self.events.append(("read", area, index, len(self.purchases)))
            observed = self.physical[area][index]
            if observed.character is not None and observed.character.name in unknown_stars:
                return replace(observed, stars=None)
            return observed

        real_bench_scan = self.task.get_in_hand_area

        def read_bench(force=False):
            self.bench_scans.append((len(self.purchases), self.money))
            return real_bench_scan(force)

        real_click = self.operator.click_point

        def click(x, y, *args, **kwargs):
            self.task._check_stop()
            real_click(x, y, *args, **kwargs)
            if not self.shop_open:
                return True
            card = next((c for c in self.pages[self.page_index] if c.target == (x, y)), None)
            if card is None or fail_purchase:
                return True
            self.money -= card.price
            self.pages[self.page_index].remove(card)
            self.purchases.append((card.character.name, card.slot_index, len(self.bench_scans)))
            self.events.append(("purchase", card.character.name))
            self.add_physical_copy(card.character)
            return True

        def press(key):
            self.task._check_stop()
            self.assertTrue(self.shop_open)
            self.assertEqual(key, "d", "Target-level shopping must not buy experience")
            self.money -= 2
            self.page_index = min(self.page_index + 1, len(self.pages) - 1)
            self.events.append(("refresh", self.money))

        self.task._set_shop_open = Mock(side_effect=set_shop)
        self.task._scan_store = Mock(side_effect=scan_store)
        self.task._observe_slot = Mock(side_effect=read_slot)
        self.task.get_in_hand_area = Mock(side_effect=read_bench)
        self.operator.click_point = Mock(side_effect=click)
        self.operator.on_press = press
        if stop_after is not None:
            real_confirmation = self.task._confirm_purchase

            def confirm_then_stop(card, coins):
                result = real_confirmation(card, coins)
                if len(self.purchases) == stop_after:
                    self.operator.stop_event.set()
                    self.stop_calls = len(self.operator.calls)
                return result

            self.task._confirm_purchase = Mock(side_effect=confirm_then_stop)

    def add_physical_copy(self, character):
        empty_index = next(index for index, obs in enumerate(self.physical["in_hand"])
                           if obs.state == self.logic.SlotState.EMPTY)
        self.physical["in_hand"][empty_index] = self.logic.SlotObservation(
            empty_index, self.logic.SlotState.KNOWN, character=character,
            occupied=True, evidence="physical purchase", revision=2, stars=1)
        for stars in (1, 2):
            copies = [(area, index) for area, slots in self.physical.items()
                      for index, obs in enumerate(slots)
                      if obs.character is character and obs.stars == stars]
            while len(copies) >= 3:
                anchor_area, anchor_index = copies[0]
                self.physical[anchor_area][anchor_index] = replace(
                    self.physical[anchor_area][anchor_index], stars=stars + 1,
                    evidence="physical merge", revision=3)
                for area, index in copies[1:3]:
                    self.physical[area][index] = self.logic.SlotObservation(
                        index, self.logic.SlotState.EMPTY, occupied=False,
                        evidence="physical consumed material", revision=3)
                copies = copies[3:]

    def assert_clean_finish(self):
        self.assertFalse(self.shop_open)
        self.assertFalse(self.task._shopping_active)
        self.assertFalse(self.task._purchase_pending_names)
        self.task._open_supply_items.assert_not_called()

    def test_same_page_buys_two_materials_then_rechecks_once_without_fourth_copy(self):
        self.configure_batch()
        char = self.character("花火")
        self.observe("off_field", 0, char, stars=1)
        self.task.strategy_characters = {char.name: 2}
        self.install_physical_game([[self.card(char.name, i) for i in range(3)]])

        result = self.task.shopping()

        self.assertEqual((result.confirmed_purchases, result.refreshes, result.reason),
                         (2, 0, "no_purchase_targets"))
        self.assertEqual([p[2] for p in self.purchases], [0, 0])
        self.assertEqual(self.bench_scans, [(2, 36)])
        self.assertEqual([c.slot_index for c in self.pages[0]], [2])
        self.assertEqual(self.task._observations["off_field"][0].stars, 2)
        self.assertEqual(self.close_requests, [0, 2])
        self.assert_clean_finish()

    def test_cross_page_materials_keep_shop_open_until_joint_recheck(self):
        self.configure_batch()
        char = self.character("花火")
        self.observe("off_field", 0, char, stars=1)
        self.task.strategy_characters = {char.name: 2}
        self.install_physical_game([[self.card(char.name)], [self.card(char.name, 1)]])

        result = self.task.shopping()

        self.assertEqual((result.confirmed_purchases, result.refreshes), (2, 1))
        self.assertEqual([p[2] for p in self.purchases], [0, 0])
        self.assertEqual(self.bench_scans, [(2, 34)])
        self.assertEqual(self.close_requests, [0, 2])
        self.assert_clean_finish()

    def test_all_in_rechecks_once_after_rolling_to_coin_floor(self):
        self.configure_batch(gold=8, all_in=True)
        char = self.character("花火")
        self.observe("off_field", 0, char, stars=1)
        self.task.strategy_characters = {char.name: 2, "符玄": 2}
        self.install_physical_game([
            [self.card(char.name, 0), self.card(char.name, 1)],
            [self.card("景元")], [self.card("镜流")]])

        result = self.task.shopping()

        self.assertEqual((result.confirmed_purchases, result.refreshes, self.money), (2, 2, 0))
        self.assertEqual(result.reason, "roll_reserve_floor")
        self.assertEqual(self.bench_scans, [(2, 0)])
        self.assertEqual(self.close_requests, [0, 2])
        self.assert_clean_finish()

    def test_multiple_characters_share_final_board_scan(self):
        self.configure_batch(gold=40)
        for index, name in enumerate(("花火", "符玄")):
            self.observe("off_field", index, self.character(name), stars=1)
        self.task.strategy_characters = {"花火": 2, "符玄": 2}
        self.install_physical_game([[self.card("花火", 0), self.card("符玄", 1),
                                     self.card("花火", 2), self.card("符玄", 3)]])

        result = self.task.shopping()

        self.assertEqual(result.confirmed_purchases, 4)
        self.assertEqual([p[2] for p in self.purchases], [0, 0, 0, 0])
        self.assertEqual(self.bench_scans, [(4, 32)])
        self.assertEqual([self.task._observations["off_field"][i].stars for i in (0, 1)], [2, 2])
        self.assert_clean_finish()

    def test_conservative_space_exhaustion_rechecks_real_merge_before_more_purchases(self):
        self.configure_batch(gold=40)
        self.observe("off_field", 0, self.character("花火"), stars=1)
        for index, name in enumerate(("佩拉", "黑塔", "艾丝妲", "景元", "镜流", "娜塔莎", "三月七")):
            self.observe("in_hand", index, self.character(name), stars=1)
        self.task.strategy_characters = {"花火": 2, "符玄": 1}
        self.install_physical_game([[self.card("花火", 0), self.card("花火", 1)],
                                    [self.card("符玄", 0)]])

        result = self.task.shopping()

        self.assertEqual(result.confirmed_purchases, 3)
        self.assertEqual([p[2] for p in self.purchases], [0, 0, 1])
        self.assertEqual(self.bench_scans, [(2, 36), (3, 32)])
        self.assertEqual(self.task._observations["off_field"][0].stars, 2)
        self.assert_clean_finish()

    def test_stop_after_second_confirmation_preserves_pending_without_final_inputs(self):
        self.configure_batch()
        self.observe("off_field", 0, self.character("花火"), stars=1)
        self.task.strategy_characters = {"花火": 2}
        self.install_physical_game([[self.card("花火", 0), self.card("花火", 1)]], stop_after=2)

        with self.assertRaises(self.module.ThreadStoppedError):
            self.task.shopping()

        self.assertEqual(len(self.purchases), 2)
        self.assertEqual(len(self.operator.calls), self.stop_calls)
        self.assertEqual(self.close_requests, [0])
        self.assertEqual(self.bench_scans, [])
        self.assertIn("花火", self.task._purchase_pending_names)
        self.assertFalse(self.task._shopping_active)
        self.assertEqual(self.task._preparation_shop_counts["purchases"], 2)

    def test_unconfirmed_transaction_never_retries_click_or_continues_spending(self):
        self.configure_batch()
        self.observe("off_field", 0, self.character("花火"), stars=1)
        self.task.strategy_characters = {"花火": 2}
        self.install_physical_game([[self.card("花火", 0), self.card("花火", 1)]],
                                   fail_purchase=True)

        result = self.task.shopping()

        self.assertEqual((result.attempted_purchases, result.confirmed_purchases), (1, 0))
        self.assertEqual(result.reason, "purchase_not_confirmed")
        self.assertEqual(result.result, self.logic.ActionResult.INDETERMINATE)
        self.assertEqual(self.money, 40)
        self.assertEqual(self.operator.click_point.call_count, 1)
        self.assertEqual(self.operator.keys(), [])
        self.assertEqual(self.bench_scans, [])
        self.assertIn("花火", self.task._purchase_pending_names)

    def test_unreadable_final_stars_keeps_pending_and_reports_recheck_unknown(self):
        self.configure_batch()
        self.observe("off_field", 0, self.character("花火"), stars=1)
        self.task.strategy_characters = {"花火": 2}
        self.install_physical_game([[self.card("花火", 0), self.card("花火", 1)]],
                                   unknown_stars={"花火"})

        result = self.task.shopping()

        self.assertEqual(result.confirmed_purchases, 2)
        self.assertEqual(result.result, self.logic.ActionResult.INDETERMINATE)
        self.assertEqual(result.reason, "purchase_recheck_unknown")
        self.assertEqual(self.bench_scans, [(2, 36), (2, 36)])
        self.assertEqual([p[2] for p in self.purchases], [0, 0])
        self.assertIn("花火", self.task._purchase_pending_names)
        self.assertEqual(self.operator.keys(), [])


if __name__ == "__main__":
    unittest.main()
