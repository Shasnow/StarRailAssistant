"""Generic assignment regressions using a frozen, explicit historical sample.

The sample's regional carry and seven-population migration exercise configurable
planner features. Current shipped lineup choices have a separate source contract.
"""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

import test_currency_wars_formation as fixture

ROOT = Path(__file__).resolve().parents[1]
ASSIGNMENT_STRATEGY = ROOT / "tests/fixtures/currency_wars_assignment_strategy.json"
_spec = importlib.util.spec_from_file_location(
    "_currency_wars_assignments_source", ROOT / "tasks/currency_wars/formation.py")
formation = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = formation
_spec.loader.exec_module(formation)


class AssignmentTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(ASSIGNMENT_STRATEGY.read_text(encoding="utf-8-sig"))
        names = set(self.data["on_field"]) | set(self.data["off_field"]) | {"藿藿", "风堇"}
        self.characters = {n: fixture.Character(n) for n in names}
        self.config = formation.validate_formation_config(self.data, self.characters.get)

    def board(self, fire_stars=2, ying_stars=2):
        return fixture.snapshot(
            [fixture.known(fixture.YING, ying_stars), fixture.known(fixture.YAO, 2),
             fixture.known(fixture.LV999, 1), fixture.known(fixture.TRIB, 2)],
            [fixture.known(fixture.BLADE, 2), fixture.known(fixture.SPARKLE, 2), fixture.known(fixture.FU, 2)],
            [fixture.known(fixture.SPARXIE, fire_stars)])

    def resolve(self, state, capacity=7, previous=None):
        return formation.resolve_effective_targets(self.config, state, capacity, previous)

    def test_real_seven_population_board_replaces_carry_and_migrates_in_two_confirmed_moves(self):
        state, previous, performed = self.board(), None, []
        for _ in range(8):
            target = self.resolve(state, previous=previous)
            previous = target
            plan = formation.plan_formation_sequence(self.config, target.stage, state, 7)
            if not plan:
                break
            self.assertTrue(formation.validate_formation_sequence(self.config, target.stage, state, 7, plan))
            for move in plan:
                after = fixture.apply_move(state, move)
                self.assertTrue(formation.formation_change_allowed(self.config, state, after, target.stage).allowed)
                self.assertEqual(len(formation._field_names(after)), 7)
                state = after
                performed.append(move)
        self.assertEqual(len(performed), 2)
        self.assertEqual({formation._name(o) for o in state["on_field"] if formation._name(o)},
                         {fixture.LV999, fixture.SPARXIE, fixture.TRIB})
        self.assertEqual({formation._name(o) for o in state["off_field"] if formation._name(o)},
                         {fixture.BLADE, fixture.YAO, fixture.SPARKLE, fixture.FU})
        self.assertIn(fixture.YING, [formation._name(o) for o in state["in_hand"]])
        self.assertEqual(formation.confirmed_trait_counts(self.config, state), {"欢愉": 3, "星核猎手": 2})
        for _ in range(5):
            previous = self.resolve(state, previous=previous)
            self.assertIsNone(formation.plan_formation_move(self.config, previous.stage, state, 7))

    def test_one_star_or_unknown_fire_does_not_replace_two_star_incumbent(self):
        for stars in (1, None):
            with self.subTest(stars=stars):
                state = self.board(stars)
                target = self.resolve(state)
                self.assertEqual(target.assignments["secondary_dps"], fixture.YING)
                self.assertIn(fixture.YAO, target.stage.off_field)
                self.assertNotIn(fixture.SPARXIE, target.stage.on_field)
                move = formation.plan_formation_move(self.config, target.stage, state, 7)
                self.assertEqual((move.source_area, move.source_index, move.target_area),
                                 ("on_field", 1, "off_field"))
                after = fixture.apply_move(state, move)
                self.assertEqual(formation._name(after["on_field"][0]), fixture.YING)
                self.assertEqual(formation._name(after["in_hand"][0]), fixture.SPARXIE)

    def test_yaoguang_migration_needs_no_fire_or_expert_at_seven_to_nine_population(self):
        for capacity in (7, 8, 9):
            with self.subTest(capacity=capacity):
                state = self.board()
                state["in_hand"][0] = fixture.empty()
                target = self.resolve(state, capacity)
                self.assertEqual(target.assignments["secondary_dps"], fixture.YING)
                self.assertIn(fixture.YAO, target.stage.off_field)
                move = formation.plan_formation_move(self.config, target.stage, state, capacity)
                self.assertEqual((move.source_area, move.source_index, move.target_area),
                                 ("on_field", 1, "off_field"))

    def test_does_not_replace_three_star_incumbent_with_two_star_challenger(self):
        target = self.resolve(self.board(2, 3))
        self.assertEqual(target.assignments["secondary_dps"], fixture.YING)

    def test_unknown_incumbent_stars_freeze_replacement_and_request_observation(self):
        target = self.resolve(self.board(2, None))
        self.assertEqual(target.assignments["secondary_dps"], fixture.YING)
        self.assertTrue(any(g.startswith("assignment_stars_unknown:") for g in target.gaps))

    def test_temporary_hidden_selected_challenger_keeps_intent_not_known_identity(self):
        state = self.board()
        prior = self.resolve(state)
        state["in_hand"][0] = fixture.unknown()
        current = self.resolve(state, previous=prior)
        self.assertEqual(current.assignments["secondary_dps"], fixture.SPARXIE)
        self.assertTrue(current.gaps)
        self.assertEqual(state["in_hand"][0].state, "unknown")

    def test_reliably_absent_selected_challenger_can_fall_back(self):
        state = self.board()
        prior = self.resolve(state)
        state["in_hand"][0] = fixture.empty()
        current = self.resolve(state, previous=prior)
        self.assertEqual(current.assignments["secondary_dps"], fixture.YING)

    def test_locked_or_npc_challenger_is_not_selected(self):
        for attribute in ("is_locked", "is_npc"):
            state = self.board()
            setattr(state["in_hand"][0].character, attribute, True)
            self.assertEqual(self.resolve(state).assignments["secondary_dps"], fixture.YING)

    def test_equal_rank_and_stars_keep_incumbent(self):
        self.data["formation"]["assignment_groups"]["secondary_dps"]["candidates"][0]["rank"] = 100
        self.config = formation.validate_formation_config(self.data, self.characters.get)
        self.assertEqual(self.resolve(self.board()).assignments["secondary_dps"], fixture.YING)

    def test_seven_population_migration_does_not_require_expert_or_nine_population(self):
        target = self.resolve(self.board())
        self.assertEqual(target.base_stage_name, "七人口补齐后台")
        self.assertIn(fixture.YAO, target.stage.off_field)
        self.assertNotIn(fixture.EXPERT, target.stage.on_field)

    def test_early_frontline_and_capacity_gate_keep_yaoguang_front(self):
        target = self.resolve(self.board(), capacity=6)
        self.assertIn(fixture.YAO, target.stage.on_field)

    def test_configurable_early_backend_does_not_move_only_frontline(self):
        rule = self.data["formation"]["position_rules"][0]
        rule.update(min_capacity=0, requires_assignment={})
        self.config = formation.validate_formation_config(self.data, self.characters.get)
        state = fixture.snapshot([fixture.YAO], [fixture.BLADE], [])
        self.assertIn(fixture.YAO, self.resolve(state, 3).stage.on_field)
        state["on_field"][1] = fixture.known(fixture.YING)
        self.assertIn(fixture.YAO, self.resolve(state, 3).stage.off_field)

    def test_final_group_is_regional_fire_front_and_ying_back_can_coexist(self):
        state = self.board()
        state["in_hand"][1] = fixture.known(fixture.EXPERT, 2)
        target = self.resolve(state, 9)
        self.assertEqual(target.base_stage_name, "最终四前台五后台")
        self.assertIn(fixture.SPARXIE, target.stage.on_field)
        self.assertIn(fixture.YING, target.stage.off_field)
        self.assertEqual(len(set(target.stage.on_field + target.stage.off_field)), 9)

    def test_unqualified_fire_cannot_activate_final_stage_by_name_alone(self):
        state = self.board(1)
        state["in_hand"][1] = fixture.known(fixture.EXPERT, 2)
        self.assertEqual(self.resolve(state, 9).base_stage_name, "八人口保生存待最终角色")

    def test_final_intent_survives_temporarily_unknown_expert(self):
        state = self.board()
        state["in_hand"][1] = fixture.known(fixture.EXPERT, 2)
        prior = self.resolve(state, 9)
        state["in_hand"][1] = fixture.unknown()
        target = self.resolve(state, 9, previous=prior)
        self.assertEqual(target.base_stage_name, prior.base_stage_name)
        self.assertTrue(any(g.startswith("stage_evidence_unknown:") for g in target.gaps))

    def test_purchase_and_reserve_targets_preserve_future_candidate_but_not_double_front_goal(self):
        target = self.resolve(self.board())
        self.assertEqual(target.purchase_targets[fixture.SPARXIE], 2)
        self.assertEqual(target.reserve_targets[fixture.YING], 2)
        self.assertNotIn(fixture.YING, target.stage.on_field)

    def test_plan_stops_when_endpoint_identity_or_stars_change(self):
        state = self.board()
        target = self.resolve(state)
        plan = formation.plan_formation_sequence(self.config, target.stage, state, 7)
        self.assertTrue(formation.validate_formation_sequence(self.config, target.stage, state, 7, plan))
        changed = copy.deepcopy(state)
        move = plan[0]
        changed[move.source_area][move.source_index].stars = None
        self.assertFalse(formation.validate_formation_sequence(self.config, target.stage, changed, 7, plan))
        changed[move.source_area][move.source_index] = fixture.unknown()
        self.assertFalse(formation.validate_formation_sequence(self.config, target.stage, changed, 7, plan))

    def alternate_endpoint_board(self):
        state = self.board()
        state["on_field"][1], state["off_field"][3] = fixture.empty(), fixture.known(fixture.YAO, 2)
        # An available fourth configured trait member means retiring Ying for
        # one step preserves the real three-member threshold.
        state["off_field"][1] = fixture.known(fixture.MC, 2)
        state["off_field"][1].character.positioning = 2
        state["in_hand"][0].character.positioning = 1
        return state

    def test_two_step_plan_uses_safe_bench_then_alternate_front_endpoint(self):
        state = self.alternate_endpoint_board()
        target = self.resolve(state)
        excluded = {("in_hand", 0, "on_field", 0)}
        self.assertIsNone(formation._plan_greedy_formation_move(self.config, target.stage, state, 7,
                                                              excluded_moves=excluded))
        plan = formation.plan_formation_sequence(self.config, target.stage, state, 7, excluded_moves=excluded)
        self.assertEqual(len(plan), 2)
        self.assertEqual((plan[0].source_name, plan[0].target_area), (fixture.YING, "in_hand"))
        self.assertEqual((plan[1].source_name, plan[1].target_area, plan[1].target_index),
                         (fixture.SPARXIE, "on_field", 1))
        self.assertTrue(all(move.requires_completion for move in plan))
        self.assertTrue(formation.validate_formation_sequence(self.config, target.stage, state, 7, plan,
                                                              excluded_moves=excluded))
        for move in plan:
            after = fixture.apply_move(state, move)
            self.assertTrue(formation.formation_change_allowed(self.config, state, after, target.stage).allowed)
            self.assertLessEqual(len(formation._field_names(after)), 7)
            state = after

    def test_three_step_plan_keeps_trait_threshold_and_restores_temporary_target(self):
        state = self.alternate_endpoint_board()
        state["off_field"][1] = fixture.known(fixture.SPARKLE, 2)
        state["off_field"][1].character.positioning = 2
        target = self.resolve(state)
        excluded = {("in_hand", 0, "on_field", 0)}
        self.assertEqual(formation.plan_formation_sequence(self.config, target.stage, state, 7,
            excluded_moves=excluded, max_moves=2), ())
        plan = formation.plan_formation_sequence(self.config, target.stage, state, 7, excluded_moves=excluded)
        self.assertEqual(len(plan), 3)
        self.assertEqual(plan[0].source_name, fixture.TRIB)
        for i, move in enumerate(plan):
            self.assertTrue(formation.validate_formation_sequence(self.config, target.stage, state, 7,
                plan[i:], excluded_moves=excluded))
            after = fixture.apply_move(state, move)
            self.assertTrue(formation.formation_change_allowed(self.config, state, after, target.stage).allowed)
            self.assertGreaterEqual(formation.confirmed_trait_counts(self.config, after)["欢愉"], 3)
            state = after
        self.assertIn(fixture.TRIB, [formation._name(o) for o in state["on_field"]])
        self.assertIn(fixture.SPARXIE, [formation._name(o) for o in state["on_field"]])

    def test_plan_cannot_invent_bench_space(self):
        state = self.alternate_endpoint_board()
        state["on_field"][0].character.positioning = 1
        state["in_hand"][1:] = [fixture.unknown() for _ in state["in_hand"][1:]]
        target = self.resolve(state)
        plan = formation.plan_formation_sequence(self.config, target.stage, state, 7,
            excluded_moves={("in_hand", 0, "on_field", 0)})
        self.assertEqual(plan, ())

    def test_failed_group_endpoint_does_not_evict_an_unrelated_required_unit(self):
        state = self.board()
        target = self.resolve(state)
        plan = formation.plan_formation_sequence(self.config, target.stage, state, 7,
            excluded_moves={("in_hand", 0, "on_field", 0)})
        for move in plan:
            if move.source_area == "in_hand" and move.source_name == fixture.SPARXIE:
                self.assertIn(move.target_name, (None, fixture.YING, fixture.SPARXIE))

    def test_unknown_backend_does_not_become_free_migration_destination(self):
        state = self.board()
        for i in range(3, 6):
            state["off_field"][i] = fixture.unknown()
        target = self.resolve(state)
        move = formation.plan_formation_move(self.config, target.stage, state, 7)
        if move is not None:
            self.assertFalse(move.target_area == "off_field" and move.target_index >= 3)

    def test_same_name_higher_star_group_copy_can_replace_lower_field_copy(self):
        state = self.board()
        state["on_field"][0] = fixture.known(fixture.SPARXIE, 1)
        target = self.resolve(state)
        moves = []
        for _ in range(4):
            move = formation.plan_formation_move(self.config, target.stage, state, 7)
            if move is None:
                break
            moves.append(move)
            state = fixture.apply_move(state, move)
        field = [o for o in state["on_field"] if formation._name(o) == fixture.SPARXIE]
        self.assertEqual([o.stars for o in field], [2])
        self.assertLessEqual(len(moves), 2)

    def test_configuration_rejects_invalid_or_conflicting_seats(self):
        mutations = [
            lambda d: d["formation"]["assignment_groups"]["secondary_dps"].update(count=2),
            lambda d: d["formation"]["assignment_groups"]["secondary_dps"].update(area="in_hand"),
            lambda d: d["formation"]["assignment_groups"]["secondary_dps"]["candidates"][0].update(min_stars=0),
            lambda d: d["formation"]["assignment_groups"]["secondary_dps"]["candidates"][0].update(name="not a character"),
            lambda d: d["formation"]["assignment_groups"].update(duplicate=copy.deepcopy(d["formation"]["assignment_groups"]["secondary_dps"])),
            lambda d: d["formation"]["position_rules"][0].update(name=fixture.SPARXIE),
            lambda d: d["formation"]["position_rules"][0].update(requires_assignment={"missing": fixture.SPARXIE}),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                data = copy.deepcopy(self.data)
                mutation(data)
                with self.assertRaises(ValueError):
                    formation.validate_formation_config(data, self.characters.get)


if __name__ == "__main__":
    unittest.main()
