"""Shop reads are reused only while no event can change their meaning."""
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import test_currency_wars_batch_flow as fixture


class ShopEfficiencyTests(unittest.TestCase):
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

    def use_real_balance_and_level_reads(self):
        """Keep production caches; fake only what the OCR engines observe."""
        def read_level(parser):
            self.events.append(("level", self.level))
            return SimpleNamespace(level=self.level, evidence="test_level",
                                   reason="matched_level_label", raw_text=f"Lv.{self.level}")

        def read_gold(*args, **kwargs):
            self.events.append(("gold", self.money, len(self.purchases)))
            return [(None, str(self.money), 1.0)]

        self.task._vision.read_level = Mock(side_effect=read_level)
        self.operator.ocr = Mock(side_effect=read_gold)
        cls = self.module.CurrencyWars
        self.task.get_level = cls.get_level.__get__(self.task, cls)
        self.task.get_coins = Mock(wraps=cls.get_coins.__get__(self.task, cls))

    def install_silver_event(self, *, bonus=0, reset_stars=False):
        name = "银狼LV.999"

        def event():
            self.events.append(("silver_event", self.money))
            self.money += bonus
            self.task._form_change_pending[name] = 4
            self.task._invalidate_character_evidence(name, "silver_wolf_event")
            self.task._purchase_pending_names.discard(name)
            if reset_stars:
                for area, slots in self.physical.items():
                    for index, obs in enumerate(slots):
                        if obs.character is not None and obs.character.name == name:
                            self.physical[area][index] = replace(obs, stars=1,
                                                                evidence="physical new form")
            return True

        self.task.detect_silver_wolf_lv999 = Mock(side_effect=event)

    def test_silver_wolf_without_event_keeps_two_purchases_in_one_batch(self):
        self.configure_batch(gold=40)
        name = "银狼LV.999"
        self.observe("on_field", 1, self.character(name), stars=1)
        self.task.strategy_characters = {name: 2}
        self.install_physical_game([[self.card(name, 0, 4), self.card(name, 1, 4)]])
        self.task.detect_silver_wolf_lv999 = Mock(return_value=False)
        self.use_real_balance_and_level_reads()

        result = self.task.shopping()

        self.assertEqual(result.confirmed_purchases, 2)
        self.assertEqual(self.task.detect_silver_wolf_lv999.call_count, 2)
        self.assertEqual([p[2] for p in self.purchases], [0, 0])
        self.assertEqual(self.bench_scans, [(2, 32)])
        # Authentication closes panels before reading the preparation's round.
        # The only later close remains the joint two-purchase recheck boundary.
        self.assertEqual(self.close_requests, [0, 2])
        self.assertEqual(self.task._vision.read_level.call_count, 1)
        self.assertLessEqual(self.task.get_coins.call_count, 4)
        self.assert_clean_finish()

    def test_real_silver_event_rechecks_board_and_reads_changed_balance_before_next_card(self):
        self.configure_batch(gold=4, all_in=True)
        silver = self.character("银狼LV.999")
        silver.priority = 1000
        self.character("花火").priority = 0
        self.observe("on_field", 1, silver, stars=1)
        self.task.strategy_characters = {silver.name: 2, "花火": 1}
        self.install_physical_game([[self.card(silver.name, 0, 4), self.card("花火", 1, 4)]])
        self.install_silver_event(bonus=4)
        self.use_real_balance_and_level_reads()

        result = self.task.shopping()

        self.assertEqual(result.confirmed_purchases, 2)
        self.assertEqual([p[0] for p in self.purchases], [silver.name, "花火"])
        self.assertEqual(self.purchases[1][2], 1, "The real event must end the old batch")
        event_index = next(i for i, e in enumerate(self.events) if e[0] == "silver_event")
        next_purchase = next(i for i, e in enumerate(self.events)
                             if e == ("purchase", "花火"))
        self.assertTrue(any(e[:2] == ("gold", 4)
                            for e in self.events[event_index + 1:next_purchase]))
        self.assertGreaterEqual(self.task._vision.read_level.call_count, 2)
        self.assertEqual(self.money, 0)
        self.assertEqual(self.operator.keys(), [])
        self.assert_clean_finish()

    def test_zero_gold_after_form_event_does_not_reopen_finished_shop(self):
        self.configure_batch(gold=4, all_in=True)
        name = "银狼LV.999"
        self.observe("on_field", 1, self.character(name), stars=1)
        self.observe("in_hand", 0, self.character(name), stars=1)
        self.task.strategy_characters = {name: 2}
        self.install_physical_game([[self.card(name, 0, 4)]])
        self.install_silver_event(reset_stars=True)
        self.use_real_balance_and_level_reads()

        result = self.task.shopping()

        self.assertEqual((result.confirmed_purchases, self.money), (1, 0))
        self.assertEqual(self.bench_scans, [(1, 0)])
        self.assertEqual([event for event in self.events if event[0] == "shop"],
                         [("shop", False), ("shop", True), ("shop", False)])
        self.assertEqual(self.operator.keys(), [])
        self.assert_clean_finish()

    def test_event_replaces_confirmed_shop_snapshot_and_new_free_slot_is_not_missed(self):
        self.configure_batch(gold=4, all_in=True)
        name = "银狼LV.999"
        self.observe("on_field", 1, self.character(name), stars=1)
        self.observe("in_hand", 0, self.character(name), stars=1)
        self.task.strategy_characters = {name: 2, "花火": 1}
        self.install_physical_game([[self.card(name, 0, 4)]])
        self.install_silver_event(reset_stars=True)
        handle_event = self.task.detect_silver_wolf_lv999.side_effect

        def replace_shop_during_event():
            result = handle_event()
            # The purchase-confirmation snapshot was EMPTY. An event now makes
            # a free target available at a different physical card position.
            self.pages[self.page_index] = [self.card("花火", 4, 0)]
            return result

        self.task.detect_silver_wolf_lv999.side_effect = replace_shop_during_event
        self.use_real_balance_and_level_reads()

        result = self.task.shopping()

        self.assertEqual((result.confirmed_purchases, self.money), (2, 0))
        self.assertEqual(self.purchases, [(name, 0, 0), ("花火", 4, 1)])
        self.assertEqual(self.operator.keys(), [])
        self.assert_clean_finish()

    def test_zero_balance_still_buys_verified_free_target_on_current_page(self):
        self.configure_batch(gold=0, all_in=True)
        self.task.strategy_characters = {"花火": 1}
        self.install_physical_game([[self.card("花火", 0, 0)]])
        self.use_real_balance_and_level_reads()

        result = self.task.shopping()

        self.assertEqual((result.confirmed_purchases, self.money), (1, 0))
        self.assertEqual(self.operator.keys(), [])
        self.assertEqual(self.bench_scans, [(1, 0)])
        self.assert_clean_finish()

    def test_spending_last_coins_does_not_skip_current_page_free_target(self):
        self.configure_batch(gold=2, all_in=True)
        self.character("花火").priority = 1000
        self.character("符玄").priority = 0
        self.task.strategy_characters = {"花火": 1, "符玄": 1}
        self.install_physical_game([[self.card("花火", 0, 2), self.card("符玄", 1, 0)]])
        self.use_real_balance_and_level_reads()

        result = self.task.shopping()

        self.assertEqual(result.confirmed_purchases, 2)
        self.assertEqual([p[0] for p in self.purchases], ["花火", "符玄"])
        self.assertEqual(self.money, 0)
        self.assertEqual(self.operator.keys(), [])
        self.assertEqual(self.bench_scans, [(2, 0)])
        self.assert_clean_finish()

    def test_roll_floor_does_not_block_affordable_two_gold_card_on_current_page(self):
        self.configure_batch(gold=26)
        self.observe("off_field", 0, self.character("花火"), stars=1)
        self.task.strategy_characters = {"花火": 2}
        self.install_physical_game([[self.card("花火", 0, 2)]])
        self.use_real_balance_and_level_reads()

        result = self.task.shopping()

        self.assertEqual((result.confirmed_purchases, self.money), (1, 24))
        self.assertEqual(result.reason, "roll_reserve_floor")
        self.assertEqual(self.operator.keys(), [])
        self.assertEqual(self.bench_scans, [(1, 24)])
        self.assert_clean_finish()

    def test_stable_roll_batch_reads_level_once_and_reuses_confirmed_balances(self):
        self.configure_batch(gold=8, all_in=True)
        self.task.strategy_characters = {"花火": 2}
        self.install_physical_game([[self.card(name)] for name in
                                   ("景元", "镜流", "黑塔", "艾丝妲", "娜塔莎")])
        self.use_real_balance_and_level_reads()

        result = self.task.shopping()

        self.assertEqual((result.refreshes, self.money), (4, 0))
        self.assertEqual(self.task._vision.read_level.call_count, 1)
        self.assertLessEqual(self.task.get_coins.call_count, 2 + result.refreshes)
        self.assertEqual(self.bench_scans, [])
        self.assert_clean_finish()


if __name__ == "__main__":
    unittest.main()
