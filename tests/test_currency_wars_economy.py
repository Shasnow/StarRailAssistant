"""Economy regressions without importing the game, GUI or OCR dependencies."""

from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tasks" / "currency_wars" / "economy.py"
SPEC = importlib.util.spec_from_file_location("_currency_wars_economy_unit", MODULE_PATH)
economy = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = economy
SPEC.loader.exec_module(economy)


def example_config():
    return {
        "enabled": True,
        "purchase_reserve_gold": 5,
        "stages": [
            {"from_battles": 0, "target_level": 5, "reserve_gold": 0},
            {"from_battles": 6, "target_level": 7, "reserve_gold": 20, "upgrade_gold": 60},
            {"from_battles": 12, "target_level": 9, "reserve_gold": 20, "upgrade_gold": 100},
        ],
    }


class EconomyConfigTests(unittest.TestCase):
    def test_missing_or_disabled_preserves_legacy_economy(self):
        for raw in (None, {}, {"enabled": False}, {"stages": []}):
            with self.subTest(raw=raw):
                self.assertIsNone(economy.parse_economy_config(raw))

    def test_defaults_and_input_are_not_mutated(self):
        raw = example_config()
        del raw["purchase_reserve_gold"]
        before = copy.deepcopy(raw)
        config = economy.parse_economy_config(raw, main_c_search_level=5)
        self.assertEqual(config.purchase_reserve_gold, 0)
        self.assertIsNone(config.stages[0].upgrade_gold)
        self.assertEqual(raw, before)

    def test_enabled_flag_and_unknown_fields_are_not_silently_ignored(self):
        for raw in ([], True, {"enabled": 1}, {"enabled": "true"},
                    {"enabled": False, "overflow_gold": 100}):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                economy.parse_economy_config(raw)
        for field in ("roll_from_level", "overflow_gold", "max_level"):
            raw = example_config()
            raw["stages"][0][field] = 7
            with self.subTest(field=field), self.assertRaises(ValueError):
                economy.parse_economy_config(raw)

    def test_enabled_requires_nonempty_complete_stages(self):
        for rows in (None, [], {}, [None], [{"from_battles": 0}]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                economy.parse_economy_config({"enabled": True, "stages": rows})

    def test_numeric_configuration_rejects_booleans_negatives_and_floats(self):
        for field in ("from_battles", "target_level", "reserve_gold", "upgrade_gold"):
            for value in (True, -1, 2.0, "2"):
                raw = example_config()
                raw["stages"][0][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    economy.parse_economy_config(raw)
        for value in (True, -1, 2.0, "2"):
            raw = example_config()
            raw["purchase_reserve_gold"] = value
            with self.subTest(reserve=value), self.assertRaises(ValueError):
                economy.parse_economy_config(raw)

    def test_stage_order_and_supported_levels(self):
        for index, field, value in ((0, "from_battles", 1), (1, "from_battles", 0),
                                    (2, "from_battles", 5), (1, "target_level", 4),
                                    (0, "target_level", 0), (2, "target_level", 21)):
            raw = example_config()
            raw["stages"][index][field] = value
            with self.subTest(index=index, field=field, value=value), self.assertRaises(ValueError):
                economy.parse_economy_config(raw)
        with self.assertRaises(ValueError):
            economy.parse_economy_config(example_config(), max_level=8)

    def test_equal_target_levels_can_change_reserves(self):
        raw = example_config()
        raw["stages"][1]["target_level"] = 5
        self.assertEqual(economy.parse_economy_config(raw).stages[1].reserve_gold, 20)

    def test_main_character_level_conflict_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "main_c_search_level"):
            economy.parse_economy_config(example_config(), main_c_search_level=10)

    def test_different_formation_without_main_character(self):
        raw = example_config()
        for stage, level in zip(raw["stages"], (3, 5, 7)):
            stage["target_level"] = level
        self.assertEqual([stage.target_level for stage in
                          economy.parse_economy_config(raw).stages], [3, 5, 7])


class EconomyStageTests(unittest.TestCase):
    def setUp(self):
        self.config = economy.parse_economy_config(example_config())

    def select(self, **kwargs):
        return economy.select_economy_stage(self.config, **kwargs)

    def test_verified_gold_advances_early_and_can_skip_stages(self):
        self.assertEqual(self.select(confirmed_battle_count=0, coins=60, confirmed_coins=60),
                         economy.EconomyStageSelection(1, "verified_gold"))
        self.assertEqual(self.select(confirmed_battle_count=0, coins=150, confirmed_coins=150).index, 2)

    def test_battle_count_alone_advances_stage(self):
        self.assertEqual(self.select(confirmed_battle_count=6, coins=0).index, 1)
        self.assertEqual(self.select(confirmed_battle_count=12).reason, "battle_count")

    def test_null_upgrade_trigger_only_uses_battles(self):
        raw = example_config()
        for row in raw["stages"]:
            row["upgrade_gold"] = None
        config = economy.parse_economy_config(raw)
        result = economy.select_economy_stage(config, confirmed_battle_count=0,
                                              coins=999, confirmed_coins=999)
        self.assertEqual(result.index, 0)

    def test_unverified_unknown_or_conflicting_gold_does_not_latch(self):
        for coins, confirmed in ((150, None), (150, 15), (None, 150), (True, True), (-1, -1)):
            with self.subTest(coins=coins, confirmed=confirmed):
                self.assertEqual(self.select(confirmed_battle_count=0, coins=coins,
                                             confirmed_coins=confirmed).index, 0)

    def test_spending_does_not_revert_stage_and_new_run_starts_over(self):
        result = self.select(previous_index=2, confirmed_battle_count=0, coins=0, confirmed_coins=0)
        self.assertEqual(result, economy.EconomyStageSelection(2, "restored_stage"))
        self.assertEqual(self.select(confirmed_battle_count=0, coins=0).index, 0)

    def test_old_checkpoint_uses_level_lower_bound_without_inventing_battles(self):
        self.assertEqual(self.select(current_level=7).index, 1)
        self.assertEqual(self.select(current_level=4).index, 0)
        self.assertEqual(self.select(current_level=None).index, 0)
        self.assertEqual(self.select(current_level=7, coins=100, confirmed_coins=100).index, 2)
        self.assertEqual(self.select(current_level=9, confirmed_battle_count=0).index, 0)
        self.assertEqual(self.select(current_level=9, previous_index=0).index, 0)

    def test_bad_restored_index_is_not_applied_to_a_different_table(self):
        for value in (True, -1, 3, "2"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.select(previous_index=value)


class EconomyActionTests(unittest.TestCase):
    def decide(self, **kwargs):
        state = dict(level=6, coins=29, target_level=7, reserve_gold=20,
                     purchase_reserve_gold=5, xp_cost=4, roll_cost=2,
                     has_purchase_targets=True)
        state.update(kwargs)
        return economy.next_economy_action(**state)

    def test_partial_experience_purchase_and_exact_reserve_boundary(self):
        self.assertEqual(self.decide().action, "buy_xp")
        self.assertEqual(self.decide(coins=25).action, "save")
        self.assertEqual(self.decide(coins=28).reason, "xp_reserve_floor")

    def test_not_enough_for_experience_does_not_spend_on_cheaper_roll(self):
        self.assertEqual(self.decide(coins=27), economy.EconomyDecision("save", "xp_reserve_floor"))

    def test_at_or_above_target_roll_has_exact_reserve_boundary(self):
        for level in (7, 9):
            with self.subTest(level=level):
                self.assertEqual(self.decide(level=level, coins=27).action, "roll")
                self.assertEqual(self.decide(level=level, coins=26).reason, "roll_reserve_floor")

    def test_card_purchase_may_spend_purchase_reserve(self):
        self.assertTrue(economy.can_afford_purchase(24, 4, 20))
        self.assertFalse(economy.can_afford_purchase(23, 4, 20))
        for coins, price, reserve in ((None, 4, 20), (24, None, 20), (24, True, 20),
                                       (True, 0, 0), (24, -1, 20), (24, 4, -1)):
            with self.subTest(coins=coins, price=price, reserve=reserve):
                self.assertFalse(economy.can_afford_purchase(coins, price, reserve))

    def test_main_character_search_blocks_upgrade_even_with_high_gold(self):
        result = self.decide(coins=150, target_level=9, reserve_gold=0, first_main_search=True)
        self.assertEqual(result, economy.EconomyDecision("roll", "first_main_search"))
        self.assertEqual(self.decide(coins=1, reserve_gold=0, first_main_search=True).action, "save")
        self.assertEqual(self.decide(coins=2, reserve_gold=0, first_main_search=True).action, "roll")

    def test_first_main_search_uses_all_affordable_gold_despite_daily_purchase_reserve(self):
        for coins in (2, 29, 30, 31):
            with self.subTest(coins=coins):
                result = self.decide(coins=coins, target_level=9, reserve_gold=0,
                                     purchase_reserve_gold=30, first_main_search=True)
                self.assertEqual(result, economy.EconomyDecision("roll", "first_main_search"))
        result = self.decide(coins=1, target_level=9, reserve_gold=0,
                             purchase_reserve_gold=30, first_main_search=True)
        self.assertEqual(result, economy.EconomyDecision("save", "roll_reserve_floor"))

    def test_first_main_search_still_preserves_its_configured_gold(self):
        for coins, expected in ((6, "save"), (7, "roll")):
            with self.subTest(coins=coins):
                result = self.decide(coins=coins, target_level=9, reserve_gold=5,
                                     purchase_reserve_gold=30, first_main_search=True)
                self.assertEqual(result.action, expected)

    def test_daily_purchase_reserve_returns_after_main_search_finishes(self):
        for coins, expected in ((31, "save"), (32, "roll")):
            with self.subTest(coins=coins):
                result = self.decide(level=9, coins=coins, target_level=9, reserve_gold=0,
                                     purchase_reserve_gold=30, first_main_search=False)
                self.assertEqual(result.action, expected)

    def test_first_main_search_keeps_evidence_and_space_requirements(self):
        base = dict(coins=30, target_level=9, reserve_gold=0,
                    purchase_reserve_gold=30, first_main_search=True)
        for values, expected in (({"coins": None}, "recover"),
                                 ({"has_purchase_targets": None}, "recover"),
                                 ({"space_safe": None}, "recover"),
                                 ({"roll_cost": None}, "recover"),
                                 ({"space_safe": False}, "prepare"),
                                 ({"needs_prepare": True}, "prepare")):
            with self.subTest(values=values):
                self.assertEqual(self.decide(**dict(base, **values)).action, expected)

    def test_existing_candidate_is_prepared_before_spending(self):
        self.assertEqual(self.decide(needs_prepare=True).action, "prepare")
        self.assertEqual(self.decide(needs_prepare=True, first_main_search=True).action, "prepare")

    def test_confirmed_procurement_gate_can_roll_below_target(self):
        result = self.decide(upgrade_allowed=False, gate_has_purchase_targets=True)
        self.assertEqual(result, economy.EconomyDecision("roll", "upgrade_gate_procurement"))

    def test_unactionable_or_unknown_gate_does_not_roll(self):
        self.assertEqual(self.decide(upgrade_allowed=False).reason, "gate_blocked_no_actionable_target")
        self.assertEqual(self.decide(upgrade_allowed=None).action, "recover")
        self.assertEqual(self.decide(upgrade_allowed=False, gate_has_purchase_targets=None).action, "recover")

    def test_no_global_demand_or_unreliable_space_prevents_roll(self):
        self.assertEqual(self.decide(level=7, has_purchase_targets=False).reason, "no_purchase_targets")
        self.assertEqual(self.decide(level=7, has_purchase_targets=None).action, "recover")
        self.assertEqual(self.decide(level=7, space_safe=None).action, "recover")
        self.assertEqual(self.decide(level=7, space_safe=False).action, "prepare")

    def test_unknown_observations_and_costs_require_recovery(self):
        for values in ({"level": None}, {"coins": None}, {"coins": True}, {"xp_cost": None},
                       {"level": 7, "roll_cost": None}, {"reserve_gold": True}):
            with self.subTest(values=values):
                self.assertEqual(self.decide(**values).action, "recover")

    def test_upgrade_does_not_require_known_roll_cost_or_current_shop_hit(self):
        self.assertEqual(self.decide(roll_cost=None, has_purchase_targets=False).action, "buy_xp")

    def test_free_action_can_be_chosen_but_still_requires_confirmed_progress(self):
        self.assertEqual(self.decide(coins=25, xp_cost=0).action, "buy_xp")
        self.assertEqual(self.decide(level=7, coins=25, roll_cost=0).action, "roll")


if __name__ == "__main__":
    unittest.main()
