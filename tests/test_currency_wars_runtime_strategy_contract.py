"""Current lineup contracts from the shipped source JSON and code.

Historical assignment samples live in tests/fixtures and have their own feature
tests. These offline cases use real current configurations and confirmed fake
rosters; no game input or live checkpoint is touched.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from tests import test_currency_wars_flow as flow


SOURCE_TASKS = Path(__file__).resolve().parents[1] / "tasks/currency_wars"
SILVER = "silver_wolf_lv999_aha_time_stop.json"
HIMEKO = "himeko_nova_march_pilot_review.json"
LV999, EXPERT, BLADE = "银狼LV.999", "银狼", "千冶·刃"
YAO, YING, FIRE, SPARKLE = "爻光", "绯英", "火花", "花火"
TRIB, MC, FU = "缇宝", "开拓者", "符玄"
FINAL_ON = (LV999, FIRE, EXPERT, TRIB)
FINAL_OFF = (YAO, YING, SPARKLE, MC, FU)


class RuntimeStrategyContractTests(unittest.TestCase):
    character = flow.CurrencyWarsFlowTests.character
    observe = flow.CurrencyWarsFlowTests.observe
    empty_board = flow.CurrencyWarsFlowTests.empty_board

    def setUp(self):
        with patch.object(flow, "TASKS", SOURCE_TASKS):
            self.module, self.characters, self.logic, self.module_names = flow.load_isolated_task()
        self.addCleanup(lambda: [sys.modules.pop(name, None) for name in self.module_names])
        self.assertEqual(Path(self.module.__file__).resolve(), SOURCE_TASKS / "CurrencyWars.py")
        self.task = self.module.CurrencyWars(flow.FakeOperator(), runtimes=1)
        self.load(SILVER)

    def load(self, filename):
        path = SOURCE_TASKS / "strategies" / filename
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        self.task.load_strategy(str(path))
        self.assertEqual(self.task._strategy_path, path)
        expected_hash = hashlib.sha256(json.dumps(data, ensure_ascii=False,
            sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        self.assertEqual(self.task._strategy_fingerprint, expected_hash)
        self.empty_board()
        return data

    def populate(self, *, front=(), back=(), hand=(), stars=1):
        self.empty_board()
        for area, names in (("on_field", front), ("off_field", back), ("in_hand", hand)):
            for index, name in enumerate(names):
                self.observe(area, index, self.character(name), stars=stars)
        return self.task._observations

    def resolve(self, capacity=9, previous=None):
        return self.module.resolve_effective_targets(self.task.formation_config,
            self.task._observations, capacity, previous)

    def test_both_current_runtime_configs_load_and_validate(self):
        for filename, main, goal in ((SILVER, LV999, 2), (HIMEKO, "姬子·启行", 3)):
            with self.subTest(strategy=filename):
                self.load(filename)
                self.assertEqual(self.task.main_c, main)
                self.assertEqual(self.task.strategy_characters[main], goal)
                self.assertEqual(self.task.main_c_search_level, 5)
                self.assertIsNotNone(self.task.formation_config)
                self.assertIsNotNone(self.task.economy_config)
                self.assertEqual(self.task.equipment_interval_battles, 2)

    def test_current_silver_uses_stages_without_regional_assignments(self):
        config = self.task.formation_config
        self.assertEqual(config.assignment_groups, {})
        self.assertEqual(config.position_rules, ())
        self.assertEqual([stage.min_capacity for stage in config.stages], [0, 6, 7, 8, 9, 9])

    def test_yaoguang_stays_front_at_seven_and_eight(self):
        self.populate(front=(LV999, YAO, YING, TRIB), back=(BLADE, SPARKLE, FU), hand=(FIRE,))
        for capacity in (7, 8):
            with self.subTest(capacity=capacity):
                targets = self.resolve(capacity)
                self.assertIn(YAO, targets.stage.on_field)
                self.assertNotIn(YAO, targets.stage.off_field)
                self.assertIn(YING, targets.stage.off_field)
                self.assertNotIn(FIRE, targets.stage.on_field)

    def test_one_star_fire_and_expert_activate_final_stage_only_at_nine(self):
        self.populate(front=(LV999, YAO, YING, TRIB), back=(BLADE, SPARKLE, FU, MC),
                      hand=(EXPERT, FIRE), stars=1)
        for capacity in (7, 8):
            self.assertNotEqual(self.resolve(capacity).stage.name, "最终四前台五后台")
        target = self.resolve(9)
        self.assertEqual(target.stage.name, "最终四前台五后台")
        self.assertEqual(target.stage.on_field, FINAL_ON)
        self.assertEqual(target.stage.off_field, FINAL_OFF)
        self.assertEqual(target.stage.requires_stars, {})

    def test_final_stage_requires_both_expert_and_fire(self):
        for hand in ((), (EXPERT,), (FIRE,)):
            with self.subTest(hand=hand):
                self.populate(front=(LV999, YAO, YING, TRIB), back=(BLADE, SPARKLE, FU, MC), hand=hand)
                self.assertEqual(self.resolve(9).stage.name, "九人口保留猎手等待火花")

    def test_unknown_or_stale_final_candidate_cannot_activate_stage(self):
        for name in (EXPERT, FIRE):
            for state, evidence in ((self.logic.SlotState.UNKNOWN, "unrecognized"),
                                    (self.logic.SlotState.KNOWN, "stale")):
                with self.subTest(name=name, state=state):
                    self.populate(front=(LV999, YAO, YING, TRIB), back=(BLADE, SPARKLE, FU, MC),
                                  hand=(EXPERT, FIRE))
                    index = 0 if name == EXPERT else 1
                    self.task._observations["in_hand"][index] = replace(
                        self.task._observations["in_hand"][index], state=state, evidence=evidence)
                    self.assertEqual(self.resolve(9).stage.name, "九人口保留猎手等待火花")

    def test_final_stage_keeps_fire_front_and_ying_back_together(self):
        self.populate(front=FINAL_ON, back=FINAL_OFF)
        target = self.resolve()
        self.assertEqual(target.stage.on_field, FINAL_ON)
        self.assertEqual(target.stage.off_field, FINAL_OFF)
        self.assertEqual(len(set(target.stage.on_field + target.stage.off_field)), 9)
        self.assertEqual(self.module.confirmed_trait_counts(self.task.formation_config,
            self.task._observations), {"欢愉": 5, "星核猎手": 2, "量子同频": 4})

    def test_one_star_final_activation_does_not_reduce_two_star_purchase_goals(self):
        self.populate(front=FINAL_ON, back=FINAL_OFF, stars=1)
        targets = self.resolve()
        self.assertEqual(targets.stage.name, "最终四前台五后台")
        goals, unknown = self.task._economy_unmet_goals()
        self.assertFalse(unknown)
        for name in FINAL_ON + FINAL_OFF:
            self.assertEqual(goals[name], 2)

    def test_silver_level_seven_gate_needs_fielded_main_and_actual_four_cost(self):
        self.populate(front=(LV999,), stars=1)
        for price, allowed in ((None, False), (3, False), (4, True), (5, True)):
            with self.subTest(price=price):
                prices = {} if price is None else {LV999: price}
                decision = self.module.stage_upgrade_allowed(self.task.formation_config,
                    self.task._observations, 7, prices)
                self.assertEqual(decision.allowed, allowed)
        self.populate(hand=(LV999,), stars=2)
        self.assertFalse(self.module.stage_upgrade_allowed(self.task.formation_config,
            self.task._observations, 7, {LV999: 4}).allowed)

    def test_below_level_seven_silver_price_gate_is_inactive(self):
        self.populate()
        self.assertTrue(self.module.stage_upgrade_allowed(self.task.formation_config,
            self.task._observations, 6, {}).allowed)

    def test_fielded_main_plus_bench_copy_keeps_procurement_active_for_price_gate(self):
        self.populate(front=(LV999,), hand=(LV999,), stars=1)
        self.task._observed_prices[LV999] = 3
        allowed, actionable, needs_prepare, reason = self.task._economy_upgrade_gate(7, {LV999: 2})
        self.assertFalse(allowed)
        self.assertTrue(actionable)
        self.assertFalse(needs_prepare)
        self.assertEqual(reason, "core_price:" + LV999 + ":4")

    def test_blade_cannot_be_retired_before_expert_is_fielded(self):
        before = self.populate(front=(LV999,), back=(BLADE,), hand=(EXPERT,))
        after = {area: list(slots) for area, slots in before.items()}
        after["off_field"][0], after["in_hand"][1] = after["in_hand"][1], after["off_field"][0]
        decision = self.module.formation_change_allowed(self.task.formation_config, before, after)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "protect:" + BLADE + ":until:" + EXPERT)

    def test_blade_can_be_retired_after_expert_is_reliably_fielded(self):
        before = self.populate(front=(LV999, EXPERT), back=(BLADE,))
        after = {area: list(slots) for area, slots in before.items()}
        after["off_field"][0], after["in_hand"][0] = after["in_hand"][0], after["off_field"][0]
        self.assertTrue(self.module.formation_change_allowed(self.task.formation_config, before, after).allowed)

    def test_established_four_quantum_members_cannot_drop_to_three(self):
        before = self.populate(front=FINAL_ON, back=FINAL_OFF)
        after = {area: list(slots) for area, slots in before.items()}
        after["on_field"][3], after["in_hand"][0] = after["in_hand"][0], after["on_field"][3]
        decision = self.module.formation_change_allowed(self.task.formation_config, before, after)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "preserve:量子同频:4")

    def test_final_stage_without_qualified_survival_requests_hard_block(self):
        self.populate(front=FINAL_ON, back=(YAO, YING, SPARKLE, MC))
        stage = self.resolve().stage
        evaluation = self.module.evaluate_role_requirements(self.task.formation_config,
            stage, self.task._observations)["survival"]
        self.assertEqual(evaluation.on_missing, "block")
        self.assertNotEqual(evaluation.state, "satisfied")

    def test_himeko_level_seven_gate_requires_three_star_fielded_main(self):
        self.load(HIMEKO)
        for stars, allowed in ((1, False), (2, False), (3, True)):
            with self.subTest(stars=stars):
                self.populate(front=("姬子·启行",), stars=stars)
                self.assertEqual(self.module.stage_upgrade_allowed(self.task.formation_config,
                    self.task._observations, 7).allowed, allowed)

    def test_himeko_welt_transition_requires_both_available_final_characters(self):
        self.load(HIMEKO)
        self.populate(front=("姬子·启行", "星期日", SPARKLE),
                      back=("三月七", "刻律德菈", FU, BLADE, TRIB))
        self.assertEqual(self.resolve().stage.name, "九人口补缇宝等瓦尔特")
        self.observe("in_hand", 0, self.character(MC), stars=1)
        self.assertEqual(self.resolve().stage.name, "九人口补缇宝等瓦尔特")
        self.observe("in_hand", 1, self.character("瓦尔特"), stars=1)
        final = self.resolve().stage
        self.assertEqual(final.name, "九人口瓦尔特换星期日")
        self.assertIn("瓦尔特", final.on_field)
        self.assertNotIn("星期日", final.on_field)


if __name__ == "__main__":
    unittest.main()
