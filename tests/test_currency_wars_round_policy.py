"""Round-triggered economy quotes without UI, input or game dependencies."""

import copy
import importlib.util
from pathlib import Path
import sys
import unittest

from test_currency_wars_economy import economy, example_config


SPEC = importlib.util.spec_from_file_location("_currency_wars_policy_unit",
    Path(__file__).resolve().parents[1] / "tasks/currency_wars/policy.py")
policy = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = policy
SPEC.loader.exec_module(policy)


class PreparationPolicyTextTests(unittest.TestCase):
    def test_round_requires_complete_label_with_supported_dash_variants(self):
        for text in ("3-7", " 3 - 7 ", "3—7", "３－７", "备战阶段 | 3–7", "备战阶段\n3-7"):
            with self.subTest(text=text):
                self.assertEqual(policy.parse_preparation_round(text), (3, 7))

    def test_fraction_population_mixed_labels_and_out_of_range_rounds_are_unknown(self):
        for text in (None, 37, "0/84", "8/9", "3/7", "0-7", "3-0", "3-10", "10-7",
                     "13-7", "3-7-1", "3-7 3-8", "Lv.3-7", "3-7 extra", "3-7 / 8-9"):
            with self.subTest(text=text):
                self.assertIsNone(policy.parse_preparation_round(text))

    def test_experience_uses_adjacent_level_and_fraction_in_real_log_text(self):
        text = "F | 购买经验 | Lv.8 | 58/72 | nder Preset: M | Quality(0.6667)(1280"
        self.assertEqual(policy.parse_experience_progress(text, level=8), (58, 72))
        self.assertEqual(policy.parse_experience_progress("Lv.8\n70 / 72", level=8), (70, 72))
        self.assertEqual(policy.parse_experience_progress("Ｌｖ．８ | ０／７２", level=8), (0, 72))

    def test_experience_never_uses_population_or_mismatched_level(self):
        for text in ("58/72", "Lv.7 | 58/72", "Lv.8 | 人口 | 8/9", "8/9 | Lv.8",
                     "银狼LV.999 | 58/72", "Lv.8 | 70/72 | Lv.9", "Lv.8 | 70/72 | 71/72",
                     "Lv.8 | 72/72", "Lv.8 | 73/72", "Lv.8 | 0/0", "Lv.8 | -1/72",
                     "Lv.8 | 1.5/72"):
            with self.subTest(text=text):
                self.assertIsNone(policy.parse_experience_progress(text, level=8))


class RoundEconomyTests(unittest.TestCase):
    def setUp(self):
        raw = example_config()
        raw["all_in_round"] = "3-7"
        self.config = economy.parse_economy_config(raw)

    def decide(self, **overrides):
        args = dict(current_round=(3, 7), level=8, coins=16,
                    experience_current=58, experience_required=72)
        args.update(overrides)
        return economy.evaluate_all_in_policy(self.config, **args)

    def test_configuration_is_optional_and_does_not_mutate_input(self):
        raw = example_config()
        self.assertIsNone(economy.parse_economy_config(raw).all_in_round)
        raw["all_in_round"] = "3-7"
        before = copy.deepcopy(raw)
        self.assertEqual(economy.parse_economy_config(raw).all_in_round, (3, 7))
        self.assertEqual(raw, before)

    def test_configuration_rejects_noncanonical_or_invalid_rounds(self):
        for label in (None, True, 37, (3, 7), "3/7", "03-7", "3-10", "0-7", "3—7", " 3-7 "):
            raw = example_config()
            raw["all_in_round"] = label
            with self.subTest(label=label), self.assertRaisesRegex(ValueError, "all_in_round"):
                economy.parse_economy_config(raw)

    def test_no_configuration_never_changes_existing_stage_reserves(self):
        for config in (None, economy.parse_economy_config(example_config())):
            result = economy.evaluate_all_in_policy(config, current_round=(9, 9), level=9, coins=99)
            self.assertFalse(result.enabled)
            self.assertEqual(result.reason, "policy_disabled")

    def test_exact_whole_upgrade_affordability_breaks_reserve(self):
        self.assertEqual(self.decide(), economy.AllInDecision(True, 9, 16, 4, "all_in_upgrade"))
        result = self.decide(coins=15)
        self.assertFalse(result.enabled)
        self.assertEqual((result.upgrade_cost, result.purchases, result.reason),
                         (16, 4, "upgrade_unaffordable"))

    def test_last_two_experience_points_still_cost_a_full_purchase(self):
        self.assertEqual(self.decide(experience_current=70, coins=4),
                         economy.AllInDecision(True, 9, 4, 1, "all_in_upgrade"))
        self.assertFalse(self.decide(experience_current=70, coins=3).enabled)

    def test_completed_target_has_zero_reserves_without_experience_data(self):
        for level in (9, 10):
            result = self.decide(level=level, coins=0, experience_current=None, experience_required=None)
            self.assertEqual(result, economy.AllInDecision(True, 9, 0, 0, "target_reached"))

    def test_round_order_uses_actual_chapter_and_node(self):
        for current in ((1, 9), (2, 9), (3, 6)):
            with self.subTest(current=current):
                self.assertEqual(self.decide(current_round=current).reason, "before_all_in_round")
        for current in ((3, 7), (3, 8), (4, 1)):
            with self.subTest(current=current):
                self.assertTrue(self.decide(current_round=current).enabled)

    def test_unknown_round_or_coins_cannot_authorize_spending(self):
        for current in (None, "3-7", [3, 7], (True, 7), (0, 7), (3, 10)):
            with self.subTest(current=current):
                self.assertEqual(self.decide(current_round=current).reason, "round_unknown")
        for coins in (None, True, -1, 16.0, "16"):
            with self.subTest(coins=coins):
                self.assertEqual(self.decide(coins=coins).reason, "unknown_coins")

    def test_missing_invalid_or_cross_level_progress_never_guesses_a_quote(self):
        for overrides, reason in ((dict(level=None), "unknown_level"),
                (dict(level=3, coins=999, experience_current=2, experience_required=4),
                 "cross_level_cost_unknown"),
                (dict(experience_current=None), "experience_unknown"),
                (dict(experience_current=True), "experience_unknown"),
                (dict(experience_required=0), "experience_unknown"),
                (dict(experience_current=72), "experience_invalid"),
                (dict(xp_gain=0), "invalid_experience_purchase")):
            with self.subTest(overrides=overrides):
                result = self.decide(**overrides)
                self.assertFalse(result.enabled)
                self.assertIsNone(result.upgrade_cost)
                self.assertEqual(result.reason, reason)

    def test_verified_seven_to_nine_cost_is_a_complete_upgrade_budget(self):
        result = self.decide(level=7, coins=76, experience_current=50, experience_required=52)
        self.assertEqual(result, economy.AllInDecision(True, 9, 76, 19, "all_in_upgrade"))
        self.assertFalse(self.decide(level=7, coins=75, experience_current=50,
                                    experience_required=52).enabled)

    def test_verified_six_to_nine_prices_each_intervening_level(self):
        result = self.decide(level=6, coins=136, experience_current=28, experience_required=40)
        self.assertEqual(result, economy.AllInDecision(True, 9, 136, 34, "all_in_upgrade"))
        quote = economy.experience_cost_to_target(level=6, target_level=9,
            experience_current=28, experience_required=40)
        self.assertEqual(quote.reason, "confirmed_cross_level_cost_bound")

    def test_each_level_is_rounded_without_assuming_experience_carries_over(self):
        quote = economy.experience_cost_to_target(level=4, target_level=6,
            experience_current=5, experience_required=6, xp_gain=3, xp_cost=4)
        # One purchase finishes Lv4, seven finish Lv5. A combined ceil would
        # underquote seven purchases by assuming the spare two XP carry over.
        self.assertEqual((quote.cost, quote.purchases), (32, 8))

    def test_unverified_future_level_stays_unknown_despite_large_wallet(self):
        raw = example_config()
        raw["all_in_round"] = "3-7"
        raw["stages"][-1]["target_level"] = 10
        self.config = economy.parse_economy_config(raw)
        result = self.decide(level=8, coins=999)
        self.assertFalse(result.enabled)
        self.assertIsNone(result.upgrade_cost)
        self.assertEqual(result.reason, "cross_level_cost_unknown")

    def test_live_denominator_conflict_never_uses_old_requirement(self):
        for level, current, required in ((7, 14, 56), (8, 58, 76)):
            with self.subTest(level=level):
                result = self.decide(level=level, coins=999,
                    experience_current=current, experience_required=required)
                self.assertFalse(result.enabled)
                self.assertIsNone(result.upgrade_cost)
                self.assertEqual(result.reason, "experience_table_conflict")

    def test_final_configured_target_is_used_instead_of_hardcoded_nine(self):
        raw = example_config()
        raw["all_in_round"] = "3-7"
        raw["stages"][-1]["target_level"] = 10
        self.config = economy.parse_economy_config(raw)
        self.assertEqual(self.decide(level=9, coins=4, experience_current=80, experience_required=84),
                         economy.AllInDecision(True, 10, 4, 1, "all_in_upgrade"))

    def test_each_quote_uses_current_funds_instead_of_latching_first_affordability(self):
        self.assertTrue(self.decide().enabled)
        self.assertTrue(self.decide(coins=12, experience_current=62).enabled)
        self.assertFalse(self.decide(coins=8, experience_current=62).enabled)

    def test_new_policy_preserves_existing_spending_and_evidence_gates(self):
        decision = self.decide(level=9, coins=2)
        self.assertTrue(decision.enabled)
        kwargs = dict(level=9, coins=2, target_level=decision.target_level,
                      reserve_gold=0, purchase_reserve_gold=0, xp_cost=4, roll_cost=2,
                      has_purchase_targets=True)
        self.assertEqual(economy.next_economy_action(**kwargs).action, "roll")
        kwargs["coins"] = 1
        self.assertEqual(economy.next_economy_action(**kwargs).reason, "roll_reserve_floor")
        kwargs.update(coins=20, has_purchase_targets=None)
        self.assertEqual(economy.next_economy_action(**kwargs).reason, "purchase_targets_unknown")
        kwargs.update(has_purchase_targets=True, space_safe=None)
        self.assertEqual(economy.next_economy_action(**kwargs).reason, "purchase_space_unknown")
        kwargs.update(space_safe=True, has_purchase_targets=False)
        self.assertEqual(economy.next_economy_action(**kwargs).reason, "no_purchase_targets")


if __name__ == "__main__":
    unittest.main()
