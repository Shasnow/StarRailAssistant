"""Exercise real policy integration with observed rounds and charged inputs."""
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

import test_currency_wars_flow as fixture
import test_currency_wars_optimization3 as optimization


class PolicyFlowTests(unittest.TestCase):
    def setUp(self):
        source_tasks = fixture.ROOT / "tasks" / "currency_wars"
        with patch.object(fixture, "TASKS", source_tasks):
            fixture.CurrencyWarsFlowTests.setUp(self)
        self.assertEqual(Path(self.module.__file__).resolve(),
                         (source_tasks / "CurrencyWars.py").resolve())

    character = fixture.CurrencyWarsFlowTests.character
    observe = fixture.CurrencyWarsFlowTests.observe
    empty_board = fixture.CurrencyWarsFlowTests.empty_board
    shop = fixture.CurrencyWarsFlowTests.shop
    card = fixture.CurrencyWarsFlowTests.card
    configure = optimization.Optimization3Tests.configure

    def configure_policy(self, *, level=8, gold=4, round_label=(3, 7), progress=None):
        self.configure(gold=gold, level=level, battles=12)
        self.task._begin_preparation()
        self.task.economy_config = replace(self.task.economy_config, all_in_round=(3, 7))
        self.task._preparation_round = round_label
        self.experience_requirements = {7: 52, 8: 72, 9: 84, 10: 100}
        self.progress = progress if progress is not None else (
            (70, 72) if level == 8 else (0, self.experience_requirements[level]))

        def read_progress(observed_level, **kwargs):
            self.assertEqual(observed_level, self.level)
            return self.progress

        self.task._read_experience_progress = Mock(side_effect=read_progress)

        def spend(key):
            if key == 'd':
                self.money -= 2
            elif key == 'f':
                self.money -= 4
                current, total = self.progress
                if current + 4 >= total:
                    self.level += 1
                    self.progress = (0, self.experience_requirements[self.level])
                else:
                    self.progress = (current + 4, total)
        self.operator.on_press = spend

    @staticmethod
    def rows(label):
        return [(None, part, 0.99) for part in label.split('|') if part]

    def test_round_accepts_either_layout_with_two_matching_frames(self):
        for labels in (['备战阶段|3-7', '备战阶段', '备战阶段|3-7', '备战阶段'],
                       ['', '备战阶段|3-7', '', '备战阶段|3-7']):
            with self.subTest(labels=labels):
                self.task._preparation_round = None
                self.task._round_read_attempts = 0
                self.operator.ocr = Mock(side_effect=[self.rows(s) for s in labels])
                self.assertEqual(self.task._read_preparation_round(), (3, 7))
                self.assertEqual(self.operator.ocr.call_count, 4)

    def test_round_rejects_missing_heading_conflict_and_changing_layout(self):
        for labels in (['3-7', '', '3-7', ''],
                       ['备战阶段|3-7', '', '备战阶段|3-6', ''],
                       ['备战阶段|3-7', '备战阶段|3-6'] * 2,
                       ['备战阶段|3-7', '', '', '备战阶段|3-7']):
            with self.subTest(labels=labels):
                self.task._preparation_round = None
                self.task._round_read_attempts = 0
                self.operator.ocr = Mock(side_effect=[self.rows(s) for s in labels])
                self.assertIsNone(self.task._read_preparation_round())

    def test_preparation_begin_clears_round_and_budget(self):
        self.task._preparation_round = (3, 7)
        self.task._all_in_budget = 99
        self.task._begin_preparation()
        self.assertIsNone(self.task._preparation_round)
        self.assertIsNone(self.task._all_in_budget)

    def test_experience_needs_agreeing_level_and_fraction_on_two_frames(self):
        self.operator.ocr = Mock(side_effect=[self.rows('Lv.8|70/72')] * 2)
        self.assertEqual(self.task._read_experience_progress(8), (70, 72))
        self.operator.ocr = Mock(side_effect=[self.rows('Lv.8|70/72'), self.rows('Lv.8|66/72')])
        self.assertIsNone(self.task._read_experience_progress(8))
        self.operator.ocr = Mock(side_effect=[self.rows('Lv.7|70/72')] * 2)
        self.assertIsNone(self.task._read_experience_progress(8))

    def test_last_four_gold_upgrade_then_stop_when_gold_exhausted(self):
        self.configure_policy()
        result = self.task.shopping()
        self.assertEqual((self.money, self.level), (0, 9))
        self.assertEqual((result.experience_purchases, result.refreshes), (1, 0))
        self.assertEqual(result.reason, 'final_round_gold_exhausted')
        self.assertEqual(self.operator.keys(), ['f'])

    def test_unaffordable_whole_upgrade_uses_gold_for_refresh_instead(self):
        self.configure_policy(gold=15, progress=(58, 72))
        result = self.task.shopping()
        self.assertEqual(result.experience_purchases, 0)
        self.assertEqual((self.level, result.refreshes, self.money), (8, 7, 1))
        self.assertEqual(self.operator.keys(), ['d'] * 7)
        self.assertEqual(result.reason, 'final_round_no_affordable_action')

    def test_full_upgrade_is_quoted_once_and_charge_confirmed_per_input(self):
        self.configure_policy(gold=16, progress=(58, 72))
        self.task._confirm_experience = Mock(wraps=self.task._confirm_experience)
        result = self.task.shopping()
        self.assertEqual((result.experience_purchases, self.level, self.money), (4, 9, 0))
        self.task._read_experience_progress.assert_called_once_with(8, recognize_cap=True)
        self.assertEqual([call.args for call in self.task._confirm_experience.call_args_list],
                         [(8, 16), (8, 12), (8, 8), (8, 4)])

    def test_unknown_card_price_cannot_block_confirmed_final_upgrade(self):
        self.configure_policy()
        card = self.card()
        self.assertIsNone(card.price)
        self.task._scan_store = Mock(side_effect=[self.shop(self.logic.ShopState.READY, card),
                                                self.shop(self.logic.ShopState.EMPTY)])
        result = self.task.shopping()
        self.assertEqual(result.experience_purchases, 1)
        self.assertEqual(self.operator.keys(), ['f'])

    def test_earlier_nine_keeps_normal_reserve_without_experience(self):
        self.configure_policy(level=9, gold=25, round_label=(3, 6))
        result = self.task.shopping()
        self.assertEqual(result.reason, 'roll_reserve_floor')
        self.assertEqual(self.operator.keys(), [])

    def test_nine_with_unaffordable_next_level_uses_gold_for_refresh(self):
        self.configure_policy(level=9, gold=5, progress=(0, 84))
        result = self.task.shopping()
        self.assertEqual((self.level, result.refreshes, self.money), (9, 2, 1))
        self.assertEqual(self.operator.keys(), ['d', 'd'])
        self.task._read_experience_progress.assert_called_once_with(9, recognize_cap=True)

    def test_unknown_round_requests_recovery_without_spending(self):
        self.configure_policy(level=9, gold=25, round_label=None)
        self.task._round_read_attempts = 2
        result = self.task.shopping()
        self.assertEqual(result.reason, 'final_round_unknown')
        self.assertEqual(result.result, self.logic.ActionResult.INDETERMINATE)
        self.assertEqual(self.operator.keys(), [])

    def test_final_round_can_upgrade_past_configured_target_and_level_nine(self):
        self.configure_policy(level=9, gold=4, progress=(80, 84))
        config = self.task.economy_config
        self.task.economy_config = replace(config, stages=config.stages[:-1] +
            (replace(config.stages[-1], target_level=8),))
        result = self.task.shopping()
        self.assertEqual((result.experience_purchases, self.level, self.money), (1, 10, 0))
        self.assertEqual(self.operator.keys(), ['f'])

    def test_final_round_can_pass_previous_sixty_action_limit(self):
        self.configure_policy(level=9, gold=126, progress=(0, 0))
        # Alternate unrelated offers to provide visible refresh progress.
        counter = [0]
        def offer():
            counter[0] += 1
            return self.shop(self.logic.ShopState.READY,
                self.card('佩拉' if counter[0] % 2 else '藿藿'))
        self.task._scan_store = Mock(side_effect=offer)
        # Keep the fixture's runaway detector; each operation is still bounded.
        result = self.task.shopping()
        self.assertEqual((result.refreshes, self.money), (63, 0))
        self.assertIsNone(self.task._all_in_budget)
        self.assertNotIn('f', self.operator.keys())

    def test_failed_xp_charge_stops_after_one_input(self):
        self.configure_policy()
        self.operator.on_press = lambda key: None
        result = self.task.shopping()
        self.assertEqual(result.reason, 'final_round_upgrade_not_confirmed')
        self.assertEqual(result.result, self.logic.ActionResult.INDETERMINATE)
        self.assertEqual(self.operator.keys(), ['f'])

    def test_second_xp_charge_failure_stops_the_committed_upgrade(self):
        self.configure_policy(gold=16, progress=(58, 72))
        spend = self.operator.on_press
        inputs = [0]

        def first_charge_only(key):
            self.assertEqual(key, 'f')
            inputs[0] += 1
            if inputs[0] == 1:
                spend(key)

        self.operator.on_press = first_charge_only
        self.task._confirm_experience = Mock(wraps=self.task._confirm_experience)

        result = self.task.shopping()

        self.assertEqual((result.experience_purchases, self.level, self.money), (2, 8, 12))
        self.assertEqual(result.result, self.logic.ActionResult.INDETERMINATE)
        self.assertEqual(result.reason, 'final_round_upgrade_not_confirmed')
        self.assertEqual(self.operator.keys(), ['f', 'f'])
        self.assertEqual([call.args for call in self.task._confirm_experience.call_args_list],
                         [(8, 16), (8, 12)])
        self.task._read_experience_progress.assert_called_once_with(8, recognize_cap=True)


if __name__ == '__main__':
    unittest.main()
