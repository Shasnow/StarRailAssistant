"""Pure role coverage, shopping needs and protected formation regressions."""

import copy
import json
import unittest
from pathlib import Path

from test_currency_wars_formation import (
    formation, Character, known, empty, unknown, snapshot, apply_move, strategy,
    LV999, EXPERT, BLADE, YAO, YING, TRIB, SPARXIE, SPARKLE, MC, FU,
    FINAL_ON, FINAL_OFF,
)

HUO, WIND = "藿藿", "风堇"


class CurrencyWarsRoleTests(unittest.TestCase):
    def setUp(self):
        self.data = strategy()
        self.characters = {name: Character(name) for name in
                           FINAL_ON + FINAL_OFF + [BLADE, HUO, WIND]}
        self.characters["符玄别名"] = self.characters[FU]
        self.lookup = self.characters.get
        self.data["formation"].update({
            "roles": {"survival": [
                {"name": FU, "area": "off_field", "min_stars": 1},
                {"name": HUO, "area": ["on_field", "off_field"], "min_stars": 1},
                {"name": WIND, "area": "on_field", "min_stars": 1}]},
            "role_requirements": {"survival": {
                "minimum": 1, "candidates": [FU],
                "interim_candidates": [HUO, WIND], "on_missing": "warn_continue"}},
        })
        self.reload()

    def reload(self):
        self.config = formation.validate_formation_config(self.data, self.lookup)
        self.stage = self.config.stages[0]

    def evaluate(self, state):
        return formation.evaluate_role_requirements(self.config, self.stage, state)["survival"]

    def test_optional_roles_do_not_change_legacy_configuration(self):
        config = formation.validate_formation_config(strategy(), self.lookup)
        self.assertEqual(formation.evaluate_role_requirements(config, config.stages[0], snapshot()), {})
        self.assertEqual(formation.role_purchase_targets(None, None, {}), {})
        self.assertEqual(formation.role_protected_names(config, config.stages[0], snapshot()), frozenset())

    def test_global_requirement_is_inherited_with_partial_stage_override(self):
        self.data["formation"]["roles"]["survival"][0]["name"] = "符玄别名"
        self.data["formation"]["stages"][1]["role_requirements"] = {
            "survival": {"on_missing": "block"}}
        self.reload()
        requirement = self.config.stages[1].role_requirements["survival"]
        self.assertEqual(requirement.candidates, (FU,))
        self.assertEqual(requirement.interim_candidates, (HUO, WIND))
        self.assertEqual(requirement.minimum, 1)
        self.assertEqual(requirement.on_missing, "block")
        self.assertEqual(self.stage.role_requirements["survival"].on_missing, "warn_continue")

    def test_bad_role_schema_is_rejected_atomically(self):
        mutations = (
            lambda f: f["roles"]["survival"][0].update({"area": "in_hand"}),
            lambda f: f["roles"]["survival"][0].update({"min_stars": True}),
            lambda f: f["roles"]["survival"].append({"name": "符玄别名"}),
            lambda f: f["role_requirements"]["survival"].update({"candidates": [BLADE]}),
            lambda f: f["role_requirements"]["survival"].update({"interim_candidates": [FU]}),
            lambda f: f["role_requirements"]["survival"].update({"minimum": 4}),
            lambda f: f["role_requirements"]["survival"].update({"on_missing": "guess"}),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                data = copy.deepcopy(self.data)
                mutation(data["formation"])
                with self.assertRaises(ValueError):
                    formation.validate_formation_config(data, self.lookup)
        self.assertEqual(self.config.roles["survival"][0].name, FU)

    def configure_capacity_requirement(self, areas, minimum):
        names = list(self.characters)
        # Each candidate is a unique canonical character, never an alias or a
        # repeated copy that could falsely fill multiple physical positions.
        names = [name for name in names if name != "符玄别名"][:len(areas)]
        self.data["formation"]["roles"]["survival"] = [
            {"name": name, "area": area} for name, area in zip(names, areas)]
        self.data["formation"]["role_requirements"]["survival"] = {
            "minimum": minimum, "candidates": names, "interim_candidates": [],
            "on_missing": "warn_continue"}

    def test_five_front_only_providers_cannot_satisfy_a_five_person_role(self):
        self.configure_capacity_requirement(["on_field"] * 5, 5)
        with self.assertRaisesRegex(ValueError, "前台4槽"):
            self.reload()

    def test_seven_backend_only_providers_cannot_satisfy_a_seven_person_role(self):
        self.configure_capacity_requirement(["off_field"] * 7, 7)
        with self.assertRaisesRegex(ValueError, "后台6槽"):
            self.reload()

    def test_total_role_requirement_above_ten_is_rejected(self):
        self.configure_capacity_requirement([["on_field", "off_field"]] * 11, 11)
        with self.assertRaises(ValueError):
            self.reload()

    def test_mixed_candidates_still_need_a_feasible_area_assignment(self):
        self.configure_capacity_requirement(["on_field"] * 5 + ["off_field"] * 2 +
                                            [["on_field", "off_field"]], 8)
        with self.assertRaisesRegex(ValueError, "分配满足"):
            self.reload()

    def test_dual_area_provider_is_reassigned_to_make_room_for_front_only_units(self):
        self.configure_capacity_requirement([["on_field", "off_field"]] +
                                            ["on_field"] * 4 + ["off_field"] * 5, 10)
        self.reload()
        self.assertEqual(self.stage.role_requirements["survival"].minimum, 10)

    def test_physical_capacity_uses_current_candidates_not_unused_role_definitions(self):
        self.configure_capacity_requirement(["on_field"] * 5 + ["off_field"], 5)
        requirement = self.data["formation"]["role_requirements"]["survival"]
        requirement["candidates"] = requirement["candidates"][:5]
        with self.assertRaisesRegex(ValueError, "分配满足"):
            self.reload()

    def test_global_long_term_role_is_not_limited_by_the_early_stage_roster(self):
        self.configure_capacity_requirement(["on_field"] * 4 + ["off_field"] * 6, 10)
        self.reload()
        self.assertEqual(len(self.stage.on_field + self.stage.off_field), 5)
        self.assertEqual(self.stage.role_requirements["survival"].minimum, 10)

    def test_coverage_has_three_states_and_bench_does_not_count(self):
        self.assertEqual(self.evaluate(snapshot(hand=[FU])).state, "missing")
        uncertain = snapshot(off=[unknown()])
        self.assertEqual(self.evaluate(uncertain).state, "unknown")
        established = snapshot(off=[FU, unknown()], hand=[FU])
        result = self.evaluate(established)
        self.assertEqual(result.state, "satisfied")
        self.assertEqual(result.field_providers, (FU,))
        self.assertEqual(result.bench_candidates, ())
        self.assertEqual(result.purchase_names, ())

    def test_effective_area_and_stars_are_required_and_names_count_once(self):
        self.assertEqual(self.evaluate(snapshot(on=[FU])).state, "missing")
        self.assertEqual(self.evaluate(snapshot(off=[known(FU, stars=None)])).state, "unknown")
        result = self.evaluate(snapshot(off=[FU, FU]))
        self.assertEqual(result.field_providers, (FU,))
        self.data["formation"]["roles"]["survival"][0]["min_stars"] = 2
        self.reload()
        self.assertEqual(self.evaluate(snapshot(off=[FU])).state, "missing")
        self.assertEqual(self.evaluate(snapshot(off=[known(FU, 2)])).state, "satisfied")

    def test_irrelevant_unknown_area_cannot_mask_a_known_backend_gap(self):
        self.data["formation"]["role_requirements"]["survival"]["interim_candidates"] = []
        self.reload()
        state = snapshot(on=[unknown()] * 4)
        self.assertEqual(self.evaluate(state).state, "missing")

    def test_pending_stale_and_npc_evidence_never_certifies_coverage(self):
        for evidence in ("pending_drag", "stale", "event_invalidated", "layout_changed", "strategy_changed"):
            with self.subTest(evidence=evidence):
                self.assertEqual(self.evaluate(snapshot(off=[known(FU, evidence=evidence)])).state, "unknown")
        provider = known(FU)
        provider.character.is_npc = True
        self.assertEqual(self.evaluate(snapshot(off=[provider])).state, "missing")

    def test_current_gap_purchase_needs_stop_after_holding_or_confirming_candidate(self):
        state = snapshot()
        self.assertEqual(formation.role_purchase_targets(self.config, self.stage, state),
                         {FU: 1, HUO: 1, WIND: 1})
        state = snapshot(hand=[WIND])
        self.assertEqual(self.evaluate(state).bench_candidates, (WIND,))
        self.assertEqual(formation.role_purchase_targets(self.config, self.stage, state), {})
        self.assertEqual(formation.role_purchase_targets(self.config, self.stage, snapshot(off=[FU])), {})

    def test_needed_upgrade_material_is_retained_without_hoarding_all_fallbacks(self):
        self.data["formation"]["roles"]["survival"][1]["min_stars"] = 2
        self.reload()
        state = snapshot(on=[HUO], hand=[HUO, WIND])
        self.assertEqual(formation.role_purchase_targets(self.config, self.stage, state), {HUO: 2})
        self.assertEqual(formation.role_protected_names(self.config, self.stage, state), frozenset({HUO}))
        state["on_field"][0].stars = 2
        self.assertEqual(formation.role_purchase_targets(self.config, self.stage, state), {})
        self.assertEqual(formation.role_protected_names(self.config, self.stage, state), frozenset())

    def test_unread_held_stars_pause_duplicate_purchases_but_allow_reobservation(self):
        state = snapshot(hand=[known(HUO, stars=None), WIND])
        self.assertEqual(self.evaluate(state).bench_candidates, (HUO, WIND))
        self.assertEqual(formation.role_purchase_targets(self.config, self.stage, state), {})
        self.assertEqual(formation.role_protected_names(self.config, self.stage, state), frozenset({HUO}))

    def test_last_provider_needs_confirmed_replacement_before_retirement(self):
        before = snapshot(on=[HUO, LV999], hand=[FU])
        after = snapshot(on=[LV999], off=[FU], hand=[HUO])
        decision = formation.formation_change_allowed(self.config, before, after, stage=self.stage)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "preserve_role:survival:1")
        before["off_field"][0] = known(FU)
        self.assertTrue(formation.formation_change_allowed(self.config, before, after, stage=self.stage).allowed)

    def test_partial_existing_coverage_is_protected_even_below_requested_minimum(self):
        self.data["formation"]["role_requirements"]["survival"]["minimum"] = 2
        self.reload()
        before = snapshot(on=[HUO, LV999])
        after = snapshot(on=[LV999])
        self.assertFalse(formation.formation_change_allowed(self.config, before, after, stage=self.stage).allowed)

    def test_stage_narrowing_candidates_does_not_drop_existing_interim_protection(self):
        self.data["formation"]["stages"][1]["role_requirements"] = {
            "survival": {"interim_candidates": []}}
        self.reload()
        stage = self.config.stages[1]
        before = snapshot(on=[HUO, LV999], hand=[FU])
        after = snapshot(on=[LV999], off=[FU], hand=[HUO])
        self.assertEqual(formation.evaluate_role_requirements(self.config, stage, before)["survival"].state,
                         "missing")
        self.assertFalse(formation.formation_change_allowed(self.config, before, after, stage=stage).allowed)
        before["off_field"][0] = known(FU)
        self.assertTrue(formation.formation_change_allowed(self.config, before, after, stage=stage).allowed)

    def test_unread_stars_do_not_unlock_retirement_or_justify_removing_possible_provider(self):
        before = snapshot(on=[HUO, LV999], off=[known(FU, stars=None)])
        after = snapshot(on=[LV999], off=[known(FU, stars=None)], hand=[HUO])
        self.assertFalse(formation.formation_change_allowed(self.config, before, after, stage=self.stage).allowed)
        before = snapshot(on=[known(HUO, stars=None), LV999])
        after = snapshot(on=[LV999], hand=[HUO])
        self.assertEqual(self.evaluate(before).state, "unknown")
        self.assertFalse(formation.formation_change_allowed(self.config, before, after, stage=self.stage).allowed)

    def test_wrong_area_relocation_cannot_retire_effective_provider(self):
        before = snapshot(on=[LV999], off=[FU])
        after = snapshot(on=[LV999, FU])
        self.assertFalse(formation.formation_change_allowed(self.config, before, after, stage=self.stage).allowed)

    def test_gap_planner_deploys_role_candidate_before_an_ordinary_stage_target(self):
        state = snapshot(on=[LV999], hand=[YAO, HUO])
        move = formation.plan_formation_move(self.config, self.stage, state, 3)
        self.assertEqual(state[move.source_area][move.source_index].character.name, HUO)
        self.assertEqual(move.reason, "deploy_role")
        after = apply_move(state, move)
        self.assertEqual(self.evaluate(after).state, "satisfied")

    def test_gap_planner_replaces_junk_without_breaking_established_traits(self):
        state = snapshot(on=[LV999, YAO, YING, "临时前台"], off=[BLADE, "临时后台"], hand=[FU])
        move = formation.plan_formation_move(self.config, self.stage, state, 6)
        self.assertEqual((move.source_area, move.target_area, move.target_index), ("in_hand", "off_field", 1))
        after = apply_move(state, move)
        self.assertEqual(self.evaluate(after).state, "satisfied")
        self.assertEqual(formation.confirmed_trait_counts(self.config, after),
                         formation.confirmed_trait_counts(self.config, state))

    def test_planned_unknown_stars_do_not_become_confirmed_role_coverage(self):
        state = snapshot(on=[LV999], hand=[known(HUO, stars=None)])
        move = formation.plan_formation_move(self.config, self.stage, state, 3)
        self.assertIsNotNone(move)
        after = apply_move(state, move)
        self.assertEqual(self.evaluate(after).state, "unknown")
        after[move.target_area][move.target_index].stars = 1
        self.assertEqual(self.evaluate(after).state, "satisfied")

    def test_role_planner_never_overwrites_unknown_slots_or_repeats_excluded_move(self):
        state = snapshot(on=[LV999, unknown(), unknown(), unknown()], off=[unknown()] * 6, hand=[HUO])
        self.assertIsNone(formation.plan_formation_move(self.config, self.stage, state, 3))
        state = snapshot(on=[LV999], hand=[HUO])
        first = formation.plan_formation_move(self.config, self.stage, state, 3)
        key = (first.source_area, first.source_index, first.target_area, first.target_index)
        alternative = formation.plan_formation_move(self.config, self.stage, state, 3, excluded_moves={key})
        self.assertIsNotNone(alternative)
        self.assertNotEqual((alternative.source_area, alternative.source_index,
                             alternative.target_area, alternative.target_index), key)

    def test_role_fallback_cannot_use_an_area_where_the_provider_has_no_role_effect(self):
        state = snapshot(on=[LV999], off=[unknown()] * 6, hand=[FU])
        self.assertIsNone(formation.plan_formation_move(self.config, self.stage, state, 9))

    def test_surplus_role_candidates_cannot_cause_repeated_provider_retirement(self):
        # This is the real early-stage policy: Fu Xuan supplies survival even
        # though she is not yet a desired stage member. Extra healers do not
        # justify cycling an established provider through the bench.
        state = snapshot(on=[LV999], off=[FU, "temporary backend"], hand=[HUO, WIND])
        seen = set()
        moves = []
        for _ in range(10):
            signature = tuple(tuple(obs.character.name if obs.character else obs.state
                                    for obs in state[area]) for area in formation.ALL_AREAS)
            self.assertNotIn(signature, seen, "planner repeated a confirmed board state")
            seen.add(signature)
            move = formation.plan_formation_move(self.config, self.stage, state, 4)
            if move is None:
                break
            moves.append(move)
            self.assertNotEqual(move.reason, "bench")
            state = apply_move(state, move)
        else:
            self.fail("surplus role candidates exhausted the preparation action budget")
        self.assertEqual(len(moves), 1)
        self.assertEqual(self.evaluate(state).state, "satisfied")
        self.assertEqual(state["off_field"][0].character.name, FU)
        self.assertEqual(state["off_field"][1].character.name, "temporary backend")

    def test_full_board_surplus_role_candidate_does_not_retire_an_effective_provider(self):
        state = snapshot(on=[LV999, HUO], off=[FU], hand=[WIND])
        self.assertIsNone(formation.plan_formation_move(self.config, self.stage, state, 3))
        self.assertEqual(self.evaluate(state).state, "satisfied")

    def test_role_evaluation_and_planning_are_read_only(self):
        state = snapshot(on=[LV999], hand=[HUO])
        original = copy.deepcopy(state)
        self.evaluate(state)
        formation.role_purchase_targets(self.config, self.stage, state)
        formation.role_protected_names(self.config, self.stage, state)
        formation.plan_formation_move(self.config, self.stage, state, 3)
        self.assertEqual(state, original)

    def test_real_silver_wolf_transition_prioritizes_backend_survival_at_six(self):
        # Replay the historical transition separately from the current guide contract.
        path = Path(__file__).resolve().parents[1] / "tests/fixtures/currency_wars_assignment_strategy.json"
        config = formation.validate_formation_config(json.loads(path.read_text(encoding="utf-8-sig")), self.lookup)
        state = snapshot(on=[LV999, YAO, YING, TRIB], off=[BLADE], hand=[FU, SPARKLE])
        stage = formation.select_formation_stage(config, state, 6)
        move = formation.plan_formation_move(config, stage, state, 6)
        self.assertEqual(state[move.source_area][move.source_index].character.name, FU)
        state = apply_move(state, move)
        stage = formation.select_formation_stage(config, state, 7)
        move = formation.plan_formation_move(config, stage, state, 7)
        self.assertEqual(state[move.source_area][move.source_index].character.name, SPARKLE)
        self.assertEqual(formation.select_formation_stage(config, state, 9).min_capacity, 8)
        state["in_hand"][1], state["in_hand"][2] = known(EXPERT), known(SPARXIE)
        self.assertEqual(formation.select_formation_stage(config, state, 9).min_capacity, 8)
        state["in_hand"][2] = known(SPARXIE, stars=2)
        final = formation.select_formation_stage(config, state, 9)
        self.assertEqual(final.on_field, tuple(FINAL_ON))
        self.assertEqual(final.off_field, tuple(FINAL_OFF))


if __name__ == "__main__":
    unittest.main()
