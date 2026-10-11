"""Regression scenarios found by the October 9 economy workflow review."""
from unittest.mock import Mock
import unittest

import test_currency_wars_optimization3 as fixture


class EconomyReviewTests(unittest.TestCase):
    setUp = fixture.Optimization3Tests.setUp
    character = fixture.Optimization3Tests.character
    observe = fixture.Optimization3Tests.observe
    empty_board = fixture.Optimization3Tests.empty_board
    shop = fixture.Optimization3Tests.shop
    configure = fixture.Optimization3Tests.configure

    def install_purchase_board(self, char, *, merged=False, unreadable=False):
        """Keep the actual board separate from invalidated cached evidence."""
        actual = {area: list(slots) for area, slots in self.task._observations.items()}

        def read_slot(area, index, **kwargs):
            return actual[area][index]

        def read_bench(force):
            for obs in actual["in_hand"]:
                self.task._set_observation("in_hand", obs)
            self.task._bench_dirty = False
            self.task._reconcile_purchase_pending()

        def confirm(*args):
            self.money -= 4
            if unreadable:
                actual["in_hand"][0] = self.logic.SlotObservation(0,
                    self.logic.SlotState.UNKNOWN, evidence="unreadable purchase landing")
            elif merged:
                actual["off_field"][0] = self.logic.SlotObservation(0,
                    self.logic.SlotState.KNOWN, character=char, occupied=True,
                    evidence="confirmed field merge", revision=2, stars=2)
                actual["in_hand"][0] = self.logic.SlotObservation(0,
                    self.logic.SlotState.EMPTY, occupied=False,
                    evidence="confirmed consumed merge material", revision=2)
            else:
                actual["in_hand"][0] = self.logic.SlotObservation(0,
                    self.logic.SlotState.KNOWN, character=char, occupied=True,
                    evidence="confirmed purchase landing", revision=2, stars=1)
            return self.logic.ActionResult.CONFIRMED

        self.task._observe_slot = Mock(side_effect=read_slot)
        self.task.get_in_hand_area = Mock(side_effect=read_bench)
        self.task._confirm_purchase = Mock(side_effect=confirm)
        card = self.logic.ShopCard(2, char, self.task.store_area[2], price=4)
        offers = iter([self.shop(self.logic.ShopState.READY, card)])
        self.task._scan_store = Mock(side_effect=lambda: next(offers, self.shop(self.logic.ShopState.EMPTY)))

    def test_ordinary_purchase_rechecks_without_same_name_offer_then_rolls(self):
        self.configure(gold=80, level=7)
        char = self.character()
        self.observe("off_field", 0, char, stars=1)
        self.install_purchase_board(char)
        self.task.shopping_budget.update(refreshes=1)
        result = self.task.shopping()
        self.assertEqual((result.confirmed_purchases, result.refreshes), (1, 1))
        self.assertEqual(self.money, 74)
        self.assertEqual(self.operator.keys(), ["d"])
        self.assertEqual(self.task._observe_slot.call_args_list[0].args, ("off_field", 0))
        self.assertEqual(self.task._observe_slot.call_count, 1)
        self.assertNotIn(char.name, self.task._purchase_pending_names)

    def test_field_merge_reaches_target_before_another_roll(self):
        self.configure(gold=80, level=7)
        char = self.character()
        self.observe("off_field", 0, char, stars=1)
        self.observe("in_hand", 0, char, stars=1)
        self.install_purchase_board(char, merged=True)
        result = self.task.shopping()
        self.assertEqual((result.confirmed_purchases, result.reason), (1, "no_purchase_targets"))
        self.assertEqual(self.operator.keys(), [])
        self.assertEqual(self.task._observations["off_field"][0].stars, 2)

    def test_new_one_star_goal_on_bench_prevents_unnecessary_rolls(self):
        self.configure(gold=80, level=7)
        char = self.character()
        self.task.strategy_characters = {char.name: 1}
        self.install_purchase_board(char)
        result = self.task.shopping()
        self.assertEqual(result.reason, "no_purchase_targets")
        self.assertEqual(self.operator.keys(), [])
        self.assertEqual(self.task.get_in_hand_area.call_count, 1)

    def test_unreadable_landing_stops_after_two_reads_without_further_spend(self):
        self.configure(gold=80, level=6)
        char = self.character()
        self.observe("off_field", 0, char, stars=1)
        self.install_purchase_board(char, unreadable=True)
        result = self.task.shopping()
        self.assertEqual(result.reason, "purchase_recheck_unknown")
        self.assertEqual(result.result, self.logic.ActionResult.INDETERMINATE)
        self.assertEqual(self.task.get_in_hand_area.call_count, 2)
        self.assertEqual(self.money, 76)
        self.assertEqual(self.operator.keys(), [])
        self.assertIn(char.name, self.task._purchase_pending_names)

    def test_unknown_level_cannot_bypass_first_main_reserve(self):
        self.configure(gold=50, level=None, battles=0)
        char = self.character()
        self.task.main_c = char.name
        self.task.main_c_search_level = 5
        self.task.main_c_search_min_coins = 50
        card = self.logic.ShopCard(2, char, self.task.store_area[2], price=4)
        self.task._scan_store = Mock(return_value=self.shop(self.logic.ShopState.READY, card))
        self.task._confirm_purchase = Mock()
        result = self.task.shopping()
        self.assertEqual(result.reason, "unknown_level")
        self.assertEqual(self.task.get_level.call_count, 2)
        self.task._confirm_purchase.assert_not_called()
        self.assertEqual(self.operator.keys(), [])

    def test_level_retry_restores_main_reserve_before_buying(self):
        self.configure(gold=50, level=5, battles=0)
        char = self.character()
        self.task.main_c = char.name
        self.task.main_c_search_level = 5
        self.task.main_c_search_min_coins = 50
        self.task.get_level = Mock(side_effect=[None, 5])
        card = self.logic.ShopCard(2, char, self.task.store_area[2], price=4)
        self.task._scan_store = Mock(return_value=self.shop(self.logic.ShopState.READY, card))
        self.task._confirm_purchase = Mock()
        result = self.task.shopping()
        self.assertEqual(result.reason, "roll_reserve_floor")
        self.task._confirm_purchase.assert_not_called()
        self.assertEqual(self.operator.keys(), [])

    def test_cleared_full_message_allows_xp_then_requests_placement(self):
        self.configure(gold=80, level=6)
        scans = iter([self.shop(self.logic.ShopState.FULL)])
        self.task._scan_store = Mock(side_effect=lambda: next(scans, self.shop(self.logic.ShopState.EMPTY)))
        def spend(key):
            self.assertEqual(key, "f")
            self.money -= 4
            self.level += 1
        self.operator.on_press = spend
        result = self.task.shopping()
        self.assertEqual((result.experience_purchases, result.refreshes, result.reason),
                         (1, 0, "purchase_space_blocked"))
        self.assertEqual(self.operator.keys(), ["f"])
        self.assertEqual([call.args for call in self.task._set_shop_open.call_args_list[:4]],
                         [(False,), (True,), (False,), (True,)])

    def test_uncleared_full_message_never_sends_economic_input(self):
        self.configure(gold=80, level=6)
        self.task._scan_store = Mock(return_value=self.shop(self.logic.ShopState.FULL))
        result = self.task.shopping()
        self.assertEqual(result.reason, "full_shop_recovery_unknown")
        self.assertEqual(self.task._scan_store.call_count, 3)
        self.assertEqual(self.operator.keys(), [])

    def test_full_bench_at_target_does_not_roll_using_stale_empty_slots(self):
        self.configure(gold=80, level=7)
        scans = iter([self.shop(self.logic.ShopState.FULL)])
        self.task._scan_store = Mock(side_effect=lambda: next(scans, self.shop(self.logic.ShopState.EMPTY)))
        result = self.task.shopping()
        self.assertEqual(result.reason, "purchase_space_blocked")
        self.assertEqual(self.operator.keys(), [])

    def test_full_bench_respects_xp_reserve_floor(self):
        self.configure(gold=28, level=6)
        scans = iter([self.shop(self.logic.ShopState.FULL)])
        self.task._scan_store = Mock(side_effect=lambda: next(scans, self.shop(self.logic.ShopState.EMPTY)))
        self.assertEqual(self.task.shopping().reason, "xp_reserve_floor")
        self.assertEqual(self.operator.keys(), [])

    def test_full_bench_partial_xp_keeps_buying_until_level_increases(self):
        self.configure(gold=80, level=6)
        scans = iter([self.shop(self.logic.ShopState.FULL)])
        self.task._scan_store = Mock(side_effect=lambda: next(scans, self.shop(self.logic.ShopState.EMPTY)))
        def spend(key):
            self.assertEqual(key, "f")
            self.money -= 4
            if self.money == 72:
                self.level += 1
        self.operator.on_press = spend
        result = self.task.shopping()
        self.assertEqual((result.experience_purchases, result.reason), (2, "purchase_space_blocked"))
        self.assertEqual(self.operator.keys(), ["f", "f"])

    def test_full_bench_does_not_bypass_first_main_search_lock(self):
        self.configure(gold=80, level=5)
        self.task.main_c = self.character().name
        self.task.main_c_search_level = 5
        scans = iter([self.shop(self.logic.ShopState.FULL)])
        self.task._scan_store = Mock(side_effect=lambda: next(scans, self.shop(self.logic.ShopState.EMPTY)))
        self.assertEqual(self.task.shopping().reason, "purchase_space_blocked")
        self.assertEqual(self.operator.keys(), [])

    def test_full_bench_unknown_gate_never_uses_xp_or_refresh(self):
        self.configure(gold=80, level=6)
        self.observe("off_field", 0, self.character(), stars=None)
        self.task.formation_config = self.module.FormationConfig({}, {}, {},
            (self.module.FormationStage("early", 0, ("佩拉",), ()),),
            self.module.UpgradeGate(6, {self.character().name: 2}, {}, {}))
        scans = iter([self.shop(self.logic.ShopState.FULL)])
        self.task._scan_store = Mock(side_effect=lambda: next(scans, self.shop(self.logic.ShopState.EMPTY)))
        with self.assertRaisesRegex(RuntimeError, "购物证据恢复无进展"):
            self.task.shopping()
        self.task._scan_store.assert_not_called()
        self.assertEqual(self.operator.keys(), [])


if __name__ == "__main__":
    unittest.main()
