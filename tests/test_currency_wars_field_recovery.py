"""Regression replay of the 2026-10-08 15:44 preparation failure.

The production preparation, slot observation, formation and two-endpoint move
confirmation code runs against an independent physical board. Only game I/O,
positive visual empty evidence and population OCR are controlled. Existing
TestCase classes are composed, never inherited or collected a second time.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import test_currency_wars_preparation as preparation_fixture

ROOT = Path(__file__).resolve().parents[1]
STRATEGY = ROOT / "tests/fixtures/currency_wars_assignment_strategy.json"


class CurrencyWarsFieldRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.case = preparation_fixture.CurrencyWarsPreparationTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.task = self.case.task
        self.module = self.case.module
        self.logic = self.case.logic
        self.characters = self.case.characters.Characters
        self.operator = self.case.operator
        self.task.load_strategy(str(STRATEGY))
        self.task.preparation_budget.update(seconds=20, total_seconds=60,
                                            actions=12, recoveries=2, move_retries=1)

    def install_failure_board(self, *, healer=True, empty_evidence=None, population=None):
        self.case.empty_board()
        C = self.characters
        for index, character in enumerate((C.Evanescia, C.YaoGuang)):
            self.case.observe("on_field", index, character)
        self.case.observe("off_field", 0, C.Mortenax_Blade)
        hand = [C.Sparxie, C.Evanescia, C.Mortenax_Blade, C.YaoGuang, C.Tribbie]
        if healer:
            hand.append(C.Huohuo)
        for index, character in enumerate(hand):
            self.case.observe("in_hand", index, character)
        # The real screenshot has seven empty field slots. Only the cached
        # observation is UNKNOWN; no test helper silently certifies vacancy.
        for area in ("on_field", "off_field"):
            for index, obs in enumerate(self.task._observations[area]):
                if obs.state == self.logic.SlotState.EMPTY:
                    self.task._set_observation(area, replace(
                        obs, state=self.logic.SlotState.UNKNOWN,
                        occupied=None, evidence="unrecognized_name"))
        self.task.max_team_size = 5
        self.task._population_current = 3 if population is None else population
        self.task._placement_pending = False
        self.task._pending_move = None
        self.task._layout_valid = True
        self.task._bench_dirty = False
        self.case.install_board()

        physical_read = self.task._observe_slot.side_effect
        production_observe = self.module.CurrencyWars._observe_slot.__get__(self.task)

        def observe(area, index, *args, **kwargs):
            actual = physical_read(area, index, *args, **kwargs)
            if area in ("on_field", "off_field") and actual.state != self.logic.SlotState.KNOWN:
                return production_observe(area, index, *args, **kwargs)
            return actual

        self.task._observe_slot = Mock(side_effect=observe)
        self.task.refresh_character = Mock(wraps=
            self.module.CurrencyWars.refresh_character.__get__(self.task))
        self.task._vision.slot_is_empty = Mock(return_value=empty_evidence)

        def read_population():
            count = sum(obs.state != self.logic.SlotState.EMPTY
                        for (area, _), obs in self.case.physical.items()
                        if area in ("on_field", "off_field"))
            return SimpleNamespace(current=count if population is None else population,
                capacity=5, evidence="two_population_frames", reason="consistent_population",
                raw_text=f"{count if population is None else population}/5")

        self.task._vision.read_population = Mock(side_effect=read_population)
        self.task.update_max_team_size = self.module.CurrencyWars.update_max_team_size.__get__(self.task)
        return self.task._assess_preparation()

    def assert_no_battle_click(self):
        box = self.case.battle_button_available()
        with self.assertRaises(RuntimeError):
            self.task.battle()
        self.assertFalse(any(name == "click_box" and args and args[0] is box
                             for name, args, _ in self.operator.calls))

    def test_positive_field_empty_evidence_recovers_real_roster_and_fields_both_cards(self):
        initial = self.install_failure_board(empty_evidence=True)
        self.assertEqual((initial.state, initial.reason),
                         (self.module.Readiness.BLOCKED, "role_not_ready"))
        prepared = self.task.prepare_for_battle()
        self.assertNotEqual(prepared.state, self.module.Readiness.BLOCKED)
        self.assertEqual((prepared.moves, prepared.attempts, prepared.recoveries), (2, 2, 1))
        self.assertEqual([entry[0] for entry in self.case.drag_baselines],
                         [self.characters.Huohuo.name, self.characters.Tribbie.name])
        self.assertEqual(self.task._role_evaluations()["survival"].state, "satisfied")
        self.assertEqual(self.task._observations["off_field"][1].character.name,
                         self.characters.Huohuo.name)
        self.assertEqual(self.task._observations["on_field"][2].character.name,
                         self.characters.Tribbie.name)
        self.assertEqual(sum(obs.state == self.logic.SlotState.KNOWN
            for (area, _), obs in self.case.physical.items()
            if area in ("on_field", "off_field")), 5)
        self.assertTrue(any(gap.startswith("stage_missing:") for gap in prepared.gaps))
        self.task._vision.slot_is_empty.assert_called()
        # Already reliable bench observations do not need another full read.
        self.task.get_in_hand_area.assert_not_called()

    def test_already_observed_positive_empty_slots_need_no_recovery(self):
        self.install_failure_board(empty_evidence=True)
        self.task.refresh_character(equip=False)
        self.task.refresh_character.reset_mock()
        prepared = self.task.prepare_for_battle()
        self.assertNotEqual(prepared.state, self.module.Readiness.BLOCKED)
        self.assertEqual((prepared.moves, prepared.attempts, prepared.recoveries), (2, 2, 0))
        self.task.refresh_character.assert_not_called()

    def test_same_unknown_field_after_one_recovery_stops_without_repeating_scans(self):
        initial = self.install_failure_board(empty_evidence=None)
        initial_revision = self.task._snapshot_revision
        prepared = self.task.prepare_for_battle()
        self.assertEqual(prepared.state, self.module.Readiness.BLOCKED)
        self.assertEqual(prepared.reason, "preparation_no_progress")
        self.assertEqual(prepared.blocked_reason, initial.reason)
        self.assertEqual(prepared.recoveries, 1)
        self.assertEqual(prepared.moves, 0)
        self.assertEqual(prepared.attempts, 0)
        self.assertGreater(self.task._snapshot_revision, initial_revision)
        # A reread may replace the diagnostic evidence string while preserving
        # the original role cause and the exact unresolved physical targets.
        self.assertTrue(set(gap for gap in initial.gaps if not gap.startswith("field_unknown:"))
                        .issubset(prepared.gaps))
        self.assertEqual({gap.rsplit(":", 1)[0] for gap in initial.gaps
                          if gap.startswith("field_unknown:")},
                         {gap.rsplit(":", 1)[0] for gap in prepared.gaps
                          if gap.startswith("field_unknown:")})
        self.assertTrue(any(gap.startswith("field_unknown:") for gap in prepared.gaps))
        self.assertEqual(self.operator.drags(), [])
        self.assertEqual(sum(obs.state == self.logic.SlotState.UNKNOWN
            for area in ("on_field", "off_field") for obs in self.task._observations[area]), 7)
        self.assert_no_battle_click()

    def test_timeout_preserves_the_role_blocker_and_unknown_target_details(self):
        initial = self.install_failure_board(empty_evidence=None)
        recover = self.task._recover_preparation_observations

        def slow_recovery(reason):
            recover(reason)
            self.case.clock.advance(self.task.preparation_budget["seconds"] + 1)

        self.task._recover_preparation_observations = Mock(side_effect=slow_recovery)
        prepared = self.task.prepare_for_battle()
        self.assertEqual((prepared.state, prepared.reason),
                         (self.module.Readiness.BLOCKED, "preparation_time_budget"))
        self.assertEqual(prepared.blocked_reason, initial.reason)
        # The deadline assessment uses the latest observations. Rereading may
        # change evidence text; the role cause and unresolved slots must remain.
        self.assertTrue(set(gap for gap in initial.gaps if not gap.startswith("field_unknown:"))
                        .issubset(prepared.gaps))
        self.assertEqual({gap.rsplit(":", 1)[0] for gap in initial.gaps
                          if gap.startswith("field_unknown:")},
                         {gap.rsplit(":", 1)[0] for gap in prepared.gaps
                          if gap.startswith("field_unknown:")})
        self.assertTrue(any(gap.startswith("role:survival:") for gap in prepared.gaps))
        self.assertTrue(any(gap.startswith("field_unknown:") for gap in prepared.gaps))
        self.assertEqual(self.operator.drags(), [])

    def test_timeout_reassesses_roster_confirmed_during_last_recovery(self):
        initial = self.install_failure_board(empty_evidence=True)
        self.assertEqual(initial.state, self.module.Readiness.BLOCKED)
        recover = self.task._recover_preparation_observations

        def finish_recovery(reason):
            recover(reason)
            self.task.place_character()
            self.case.clock.advance(self.task.preparation_budget["seconds"] + 1)

        self.task._recover_preparation_observations = Mock(side_effect=finish_recovery)
        prepared = self.task.prepare_for_battle()
        self.assertEqual((prepared.state, prepared.reason),
                         (self.module.Readiness.DEGRADED, "confirmed_gaps"))
        self.assertEqual(prepared.blocked_reason, "")
        self.assertEqual((prepared.moves, prepared.attempts, prepared.recoveries), (2, 2, 1))
        self.assertEqual(self.task._role_evaluations()["survival"].state, "satisfied")
        self.assertFalse(any(gap.startswith(("role:survival:", "field_unknown:"))
                             for gap in prepared.gaps))
        self.assertEqual(len(self.operator.drags()), 2)
        battle_box = self.case.battle_button_available()
        self.assertTrue(self.task.battle())
        self.assertTrue(any(name == "click_box" and args and args[0] is battle_box
                            for name, args, _ in self.operator.calls))

    def test_total_timeout_blocks_roster_confirmed_during_last_recovery(self):
        self.install_failure_board(empty_evidence=True)
        recover = self.task._recover_preparation_observations

        def finish_recovery(reason):
            recover(reason)
            self.task.place_character()
            self.case.clock.advance(self.task.preparation_budget["total_seconds"] + 1)

        self.task._recover_preparation_observations = Mock(side_effect=finish_recovery)
        prepared = self.task.prepare_for_battle()
        self.assertEqual((prepared.state, prepared.reason, prepared.blocked_reason),
                         (self.module.Readiness.BLOCKED, "preparation_time_budget",
                          "preparation_total_time_budget"))
        self.assertEqual((prepared.moves, prepared.attempts, prepared.recoveries), (2, 2, 1))
        self.assertEqual(self.task._role_evaluations()["survival"].state, "satisfied")
        self.assertEqual(len(self.operator.drags()), 2)
        self.assert_no_battle_click()

    def test_soft_role_without_candidate_does_not_hide_a_held_strategy_card_and_free_population(self):
        initial = self.install_failure_board(healer=False, empty_evidence=None)
        self.assertEqual(self.task._role_evaluations()["survival"].bench_candidates, ())
        self.assertEqual((initial.state, initial.reason),
                         (self.module.Readiness.BLOCKED, "deployment_target_unknown"))
        prepared = self.task.prepare_for_battle()
        self.assertEqual((prepared.state, prepared.reason, prepared.blocked_reason),
            (self.module.Readiness.BLOCKED, "preparation_no_progress", "deployment_target_unknown"))
        self.assertEqual(prepared.recoveries, 1)
        self.assertTrue(any(gap.startswith("field_unknown:") for gap in prepared.gaps))
        self.assertEqual(self.operator.drags(), [])
        self.assert_no_battle_click()

    def test_full_population_with_unidentified_occupant_blocks_until_roster_is_reliably_accounted_for(self):
        self.install_failure_board(healer=False, empty_evidence=None)
        hidden = replace(self.case.physical[("off_field", 0)],
            state=self.logic.SlotState.UNKNOWN, character=None, occupied=True,
            evidence="unrecognized_name", stars=None)
        self.case.physical[("off_field", 0)] = hidden
        self.task._set_observation("off_field", hidden)
        self.task.max_team_size = self.task._population_current = 3
        self.task._vision.read_population = Mock(return_value=SimpleNamespace(
            current=3, capacity=3, evidence="two_population_frames",
            reason="consistent_population", raw_text="3/3"))
        initial = self.task._assess_preparation()
        self.assertEqual((initial.state, initial.reason),
                         (self.module.Readiness.BLOCKED, "deployment_target_unknown"))
        prepared = self.task.prepare_for_battle()
        self.assertEqual((prepared.state, prepared.reason, prepared.blocked_reason),
            (self.module.Readiness.BLOCKED, "preparation_no_progress", "deployment_target_unknown"))
        self.assertEqual(self.task._observations["off_field"][0].state,
                         self.logic.SlotState.UNKNOWN)
        self.assertEqual(self.operator.drags(), [])
        self.assert_no_battle_click()

        # Once all three occupied slots are positively identified, the same
        # full population and protected stage priorities prove that the held
        # card has no legal improvement. A soft gap may then continue.
        self.case.observe("off_field", 0, self.characters.Mortenax_Blade)
        stage = self.module.select_formation_stage(
            self.task.formation_config, self.task._observations, 3)
        self.assertIsNone(self.module.plan_formation_move(
            self.task.formation_config, stage, self.task._observations, 3))
        ready = self.task._assess_preparation()
        self.assertEqual(ready.state, self.module.Readiness.DEGRADED)
        self.assertTrue(any(gap.startswith("stage_missing:") for gap in ready.gaps))
        self.assertEqual(self.operator.drags(), [])

    def test_unread_population_does_not_hide_a_held_strategy_card_with_unknown_targets(self):
        self.install_failure_board(healer=False, empty_evidence=None)
        self.task._population_current = None
        self.task._vision.read_population = Mock(return_value=SimpleNamespace(
            current=None, capacity=None, evidence="two_population_frames",
            reason="population_not_confirmed", raw_text=""))
        initial = self.task._assess_preparation()
        self.assertEqual((initial.state, initial.reason),
                         (self.module.Readiness.BLOCKED, "deployment_target_unknown"))
        prepared = self.task.prepare_for_battle()
        self.assertEqual((prepared.state, prepared.reason, prepared.blocked_reason),
            (self.module.Readiness.BLOCKED, "preparation_no_progress", "deployment_target_unknown"))
        self.assertIsNone(self.task._population_current)
        self.assertEqual(sum(obs.state == self.logic.SlotState.UNKNOWN
            for area in ("on_field", "off_field") for obs in self.task._observations[area]), 7)
        self.assertEqual(self.operator.drags(), [])
        self.assert_no_battle_click()

    def test_positive_target_recovery_can_field_strategy_card_without_a_role_candidate(self):
        self.install_failure_board(healer=False, empty_evidence=True)
        prepared = self.task.prepare_for_battle()
        self.assertNotEqual(prepared.state, self.module.Readiness.BLOCKED)
        self.assertTrue(any(entry[0] == self.characters.Tribbie.name
                            for entry in self.case.drag_baselines))
        self.assertEqual(self.task._observations["on_field"][2].character.name,
                         self.characters.Tribbie.name)
        self.assertEqual(prepared.recoveries, 1)

    def test_explicit_occupied_detection_invalidates_historical_empty_baselines(self):
        self.install_failure_board(empty_evidence=False)
        for evidence in ("new_game_empty", "zero_population"):
            with self.subTest(evidence=evidence):
                baseline = replace(self.case.physical[("on_field", 2)], evidence=evidence)
                self.task._set_observation("on_field", baseline)
                observed = self.task._observe_slot("on_field", 2, count_stars=True)
                self.assertEqual(observed.state, self.logic.SlotState.UNKNOWN)
                self.assertEqual(observed.evidence, "occupied_name_unknown")
                self.task._set_observation("on_field", observed)
        prepared = self.task.prepare_for_battle()
        self.assertEqual(prepared.state, self.module.Readiness.BLOCKED)
        self.assertEqual(self.operator.drags(), [])
        self.assert_no_battle_click()

    def test_zero_population_conflict_cannot_clear_a_live_known_roster(self):
        self.install_failure_board(empty_evidence=None, population=0)
        self.operator.locate_any = Mock(return_value=(0, preparation_fixture.fixture.FakeBox()))
        self.task.update_max_team_size()
        self.assertEqual(sum(obs.state == self.logic.SlotState.KNOWN
            for area in ("on_field", "off_field") for obs in self.task._observations[area]), 3)
        self.assertEqual(sum(obs.state == self.logic.SlotState.UNKNOWN
            for area in ("on_field", "off_field") for obs in self.task._observations[area]), 7)
        prepared = self.task.prepare_for_battle()
        self.assertEqual(prepared.state, self.module.Readiness.BLOCKED)
        self.assertEqual(self.operator.drags(), [])
        self.assertEqual(self.task._population_current, 0)

    def test_direct_placement_rejects_population_conflict_before_trying_any_move(self):
        self.install_failure_board(empty_evidence=True, population=2)
        self.task.refresh_character(equip=False)
        self.task.update_max_team_size()
        self.assertFalse(self.task.place_character())
        self.assertEqual(self.operator.drags(), [])
        self.assertEqual(self.task._population_current, 2)
        self.assertEqual(self.task._preparation_attempts, 0)

    def test_direct_swap_cannot_erase_a_population_conflict_before_reassessment(self):
        self.install_failure_board(empty_evidence=True, population=2)
        self.task.refresh_character(equip=False)
        self.task.update_max_team_size()
        self.assertFalse(self.task.swap_character_between_areas("in_hand", 5, "off_field", 1))
        self.assertEqual(self.operator.drags(), [])
        self.assertEqual(self.task._population_current, 2)
        self.assertEqual(self.task._preparation_attempts, 0)
        self.assertIsNone(self.task._pending_move)
        self.assertEqual(self.task._last_move_result.reason, "population_observation_conflict")

    def test_unidentified_occupant_cannot_be_inferred_empty_from_partial_population(self):
        self.install_failure_board(empty_evidence=None)
        unknown = replace(self.case.physical[("off_field", 0)],
            state=self.logic.SlotState.UNKNOWN, character=None, occupied=True,
            evidence="unrecognized_name", stars=None)
        self.case.physical[("off_field", 0)] = unknown
        self.task._set_observation("off_field", unknown)
        prepared = self.task.prepare_for_battle()
        self.assertEqual(prepared.state, self.module.Readiness.BLOCKED)
        self.assertEqual(self.task._population_current, 3)
        self.assertEqual(self.task._observations["off_field"][0].state,
                         self.logic.SlotState.UNKNOWN)
        self.assertEqual(sum(obs.state == self.logic.SlotState.EMPTY
            for area in ("on_field", "off_field") for obs in self.task._observations[area]), 0)
        self.assertEqual(self.operator.drags(), [])
        self.assert_no_battle_click()

    def test_population_conflict_cannot_turn_unread_slots_empty_or_authorize_battle(self):
        self.install_failure_board(empty_evidence=None, population=2)
        prepared = self.task.prepare_for_battle()
        self.assertEqual(prepared.state, self.module.Readiness.BLOCKED)
        self.assertEqual(self.operator.drags(), [])
        self.assertEqual(sum(obs.state == self.logic.SlotState.EMPTY
            for area in ("on_field", "off_field") for obs in self.task._observations[area]), 0)
        self.assert_no_battle_click()

    def test_population_conflict_blocks_deployment_even_after_positive_empty_detection(self):
        self.install_failure_board(empty_evidence=True, population=2)
        self.task.refresh_character(equip=False)
        prepared = self.task.prepare_for_battle()
        self.assertEqual(prepared.state, self.module.Readiness.BLOCKED)
        self.assertEqual(self.operator.drags(), [])
        self.assertEqual(prepared.moves, 0)
        self.assert_no_battle_click()


if __name__ == "__main__":
    unittest.main()
