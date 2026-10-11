"""Runtime preparation replay of generic assignments using a frozen sample.

The physical board is independent of cache. The historical sample intentionally
retains multi-step assignment features absent from the current guide's lineup.
"""
from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import test_currency_wars_preparation as preparation_fixture

ROOT = Path(__file__).resolve().parents[1]
SOURCE_TASKS = ROOT / "tasks/currency_wars"
ASSIGNMENT_STRATEGY = ROOT / "tests/fixtures/currency_wars_assignment_strategy.json"


class AssignmentFlowTests(unittest.TestCase):
    def setUp(self):
        self.case = preparation_fixture.CurrencyWarsPreparationTests()
        with patch.object(preparation_fixture.fixture, "TASKS", SOURCE_TASKS):
            self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.task, self.module, self.logic = self.case.task, self.case.module, self.case.logic
        self.assertEqual(Path(self.module.__file__).resolve(), SOURCE_TASKS / "CurrencyWars.py")
        self.task.load_strategy(str(ASSIGNMENT_STRATEGY))
        self.case.empty_board()
        for area, names in {
            "on_field": ["绯英", "爻光", "银狼LV.999", "缇宝"],
            "off_field": ["千冶·刃", "花火", "符玄"],
            "in_hand": ["火花"],
        }.items():
            for i, name in enumerate(names):
                obs = self.case.observe(area, i, self.case.character(name))
                obs = replace(obs, stars=1 if name == "银狼LV.999" else 2)
                self.case.physical[(area, i)] = obs
                self.task._set_observation(area, obs)
        self.task.max_team_size = self.task._population_current = 7
        self.task.main_c_first_fielded_confirmed = True
        self.task._placement_pending = False
        self.task._layout_valid = True
        self.task._bench_dirty = False
        self.case.install_board()

    def queue_two_safe_steps(self):
        """Supply a valid two-step path to exercise the production plan executor."""
        stage = self.task._formation_stage()
        first = self.module.plan_formation_sequence(self.task.formation_config, stage,
                                                    self.task._observations, 7)[0]
        after = {area: list(slots) for area, slots in self.task._observations.items()}
        after[first.source_area][first.source_index], after[first.target_area][first.target_index] = (
            after[first.target_area][first.target_index], after[first.source_area][first.source_index])
        second = self.module.plan_formation_sequence(self.task.formation_config, stage, after, 7)[0]
        plan = tuple(replace(move, requires_completion=True) for move in (first, second))
        self.assertTrue(self.module.validate_formation_sequence(
            self.task.formation_config, stage, self.task._observations, 7, plan))
        self.task._formation_plan, self.task._formation_plan_stage = plan, stage
        return plan

    def test_actual_prepare_places_two_star_fire_and_moves_yaoguang_once(self):
        prepared = self.task.prepare_for_battle()
        self.assertEqual(prepared.state, self.module.Readiness.READY)
        self.assertEqual((prepared.moves, prepared.attempts, prepared.recoveries), (2, 2, 0))
        self.assertEqual({o.character.name for o in self.task._observations["on_field"]
                          if o.state == self.logic.SlotState.KNOWN}, {"银狼LV.999", "火花", "缇宝"})
        self.assertIn("爻光", [o.character.name for o in self.task._observations["off_field"]
                              if o.state == self.logic.SlotState.KNOWN])
        self.assertEqual(len(self.case.operator.drags()), 2)
        self.assertEqual(self.task.prepare_for_battle().state, self.module.Readiness.READY)
        self.assertEqual(len(self.case.operator.drags()), 2)

    def test_persistent_safe_two_step_plan_confirms_every_endpoint_and_finishes(self):
        self.queue_two_safe_steps()
        prepared = self.task.prepare_for_battle()
        self.assertEqual(prepared.state, self.module.Readiness.READY)
        self.assertEqual(prepared.moves, 2)
        self.assertFalse(self.task._formation_plan_incomplete)
        self.assertEqual(self.task._formation_plan, ())

    def test_production_executes_generated_three_step_plan_after_failed_direct_endpoint(self):
        yao = self.task._observations["on_field"][1]
        vacant = self.task._observations["off_field"][3]
        for area, index, obs in (("on_field", 1, vacant), ("off_field", 3, yao)):
            observed = replace(obs, slot_index=index)
            self.task._set_observation(area, observed)
            self.case.physical[(area, index)] = observed
        failed = self.task._move_key("in_hand", 0, "on_field", 0)
        self.task._move_failures[failed] = self.task.preparation_budget["move_retries"] + 1
        stage = self.task._formation_stage()
        plan = self.module.plan_formation_sequence(self.task.formation_config, stage,
            self.task._observations, 7, excluded_moves=self.task._excluded_moves())
        self.assertEqual(len(plan), 3)
        actual_swap = self.task.swap_character_between_areas

        def checked_swap(*args, **kwargs):
            changed = actual_swap(*args, **kwargs)
            if changed:
                counts = self.module.confirmed_trait_counts(self.task.formation_config, self.task._observations)
                self.assertGreaterEqual(counts["欢愉"], 3)
                self.assertGreaterEqual(counts["星核猎手"], 2)
                self.assertEqual(self.task._role_evaluations()["survival"].state, "satisfied")
                self.assertLessEqual(self.task.current_team_size, 7)
            return changed

        self.task.swap_character_between_areas = checked_swap
        prepared = self.task.prepare_for_battle()
        self.assertEqual(prepared.state, self.module.Readiness.READY)
        self.assertEqual((prepared.moves, prepared.recoveries), (3, 0))
        self.assertEqual(len(self.case.operator.drags()), 3)
        self.assertEqual({o.character.name for o in self.task._observations["on_field"]
                          if o.state == self.logic.SlotState.KNOWN}, {"银狼LV.999", "火花", "缇宝"})

    def test_second_step_unknown_keeps_first_confirmed_move_and_blocks_battle(self):
        self.queue_two_safe_steps()
        physical_drag = self.case.operator.drag_to.side_effect

        def drag(*args, **kwargs):
            result = physical_drag(*args, **kwargs)
            if len(self.case.drag_baselines) == 2:
                _, source, target, *_ = self.case.drag_baselines[-1]
                for area, index in (source, target):
                    self.case.physical[(area, index)] = self.case.observation(
                        area, index, state=self.logic.SlotState.UNKNOWN)
            return result

        self.case.operator.drag_to = Mock(side_effect=drag)
        prepared = self.task.prepare_for_battle()
        self.assertEqual(prepared.state, self.module.Readiness.BLOCKED)
        self.assertEqual(prepared.moves, 1)
        self.assertEqual(len(self.case.operator.drags()), 2)
        self.assertIsNotNone(self.task._pending_move)
        box = self.case.battle_button_available()
        with self.assertRaises(RuntimeError):
            self.task.battle()
        self.assertFalse(any(name == "click_box" and args and args[0] is box
                             for name, args, _ in self.case.operator.calls))

    def test_stop_after_first_confirmed_plan_step_does_not_send_second_drag(self):
        self.queue_two_safe_steps()
        actual_swap = self.task.swap_character_between_areas

        def swap(*args, **kwargs):
            result = actual_swap(*args, **kwargs)
            self.case.operator.stop_event.set()
            return result

        self.task.swap_character_between_areas = swap
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task.prepare_for_battle()
        self.assertEqual(len(self.case.operator.drags()), 1)
        self.assertTrue(self.task._formation_plan_incomplete)

    def test_unknown_challenger_stars_keep_incumbent_while_yaoguang_migrates_independently(self):
        observed = replace(self.task._observations["in_hand"][0], stars=None)
        self.case.physical[("in_hand", 0)] = observed
        self.task._set_observation("in_hand", observed)
        prepared = self.task.prepare_for_battle()
        self.assertNotEqual(prepared.state, self.module.Readiness.BLOCKED)
        self.assertEqual(prepared.moves, 1)
        self.assertEqual(self.case.operator.drags(), [
            (*self.task.on_field_area[1], *self.task.off_field_area[3])])
        self.assertEqual(self.case.drag_baselines, [
            ("爻光", ("on_field", 1), ("off_field", 3), "empty", None)])
        self.assertEqual(self.task._observations["on_field"][0].character.name, "绯英")
        self.assertEqual(self.task._observations["on_field"][1].state, self.logic.SlotState.EMPTY)
        self.assertEqual(self.task._observations["off_field"][3].character.name, "爻光")
        self.assertEqual(self.case.physical[("off_field", 3)].character.name, "爻光")
        self.assertEqual(self.case.physical[("on_field", 1)].state, self.logic.SlotState.EMPTY)
        self.assertEqual(self.task._observations["in_hand"][0].character.name, "火花")
        self.assertIsNone(self.task._observations["in_hand"][0].stars)

    def test_production_replaces_same_name_one_star_field_card_with_two_star_bench_card(self):
        low = replace(self.task._observations["in_hand"][0], slot_index=0, stars=1)
        self.task._set_observation("on_field", low)
        self.case.physical[("on_field", 0)] = low
        prepared = self.task.prepare_for_battle()
        self.assertEqual(prepared.state, self.module.Readiness.READY)
        self.assertEqual(prepared.moves, 2)
        self.assertEqual(self.task._observations["on_field"][0].stars, 2)
        self.assertEqual(self.task._observations["in_hand"][0].stars, 1)
        bench_reads = [call for call in self.task._observe_slot.call_args_list
                       if call.args[:2] == ("in_hand", 0)]
        self.assertTrue(bench_reads)
        self.assertTrue(all(call.kwargs.get("count_stars") is True for call in bench_reads))

    def test_same_name_exchange_requires_two_reliable_star_endpoints(self):
        high = self.task._observations["in_hand"][0]
        low = replace(high, stars=1)
        self.assertEqual(self.module.classify_move(high, low, low, high).status,
                         self.module.MoveStatus.CONFIRMED_CHANGED)
        self.assertEqual(self.module.classify_move(high, low, high, low).status,
                         self.module.MoveStatus.CONFIRMED_UNCHANGED)
        self.assertEqual(self.module.classify_move(high, high, high, high).status,
                         self.module.MoveStatus.CONFIRMED_UNCHANGED)
        for unknown in (replace(low, stars=None), replace(low, stars=3)):
            self.assertEqual(self.module.classify_move(high, low, unknown, high).status,
                             self.module.MoveStatus.INDETERMINATE)
        self.assertEqual(self.module.classify_move(replace(high, stars=None), low, low, high).status,
                         self.module.MoveStatus.INDETERMINATE)


if __name__ == "__main__":
    unittest.main()
