"""Replay configured fillers and the Jade/Sparkle board from the October 11 log."""
import copy
import json
from pathlib import Path
import unittest

import test_currency_wars_formation as fixture

formation = fixture.formation
MAIN, SUNDAY, MARCH = "姬子·启行", "星期日", "三月七"
JADE, SPARKLE, TRIB, BLADE = "翡翠", "花火", "缇宝", "千冶·刃"


class ConfiguredInterimTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / (
            "tasks/currency_wars/strategies/himeko_nova_march_pilot_review.json")
        self.data = json.loads(path.read_text(encoding="utf-8-sig"))
        self.characters = {name: fixture.Character(name) for area in formation.FIELD_AREAS
                           for name in self.data[area]}
        self.config = formation.validate_formation_config(self.data, self.characters.get)

    def board(self, hand=(), capacity=5, sparkle_fielded=False):
        off = [fixture.known(MARCH, 2), BLADE, JADE]
        if sparkle_fielded:
            off.append(SPARKLE)
        state = fixture.snapshot([MAIN, SUNDAY], off, hand)
        for area in formation.ALL_AREAS:
            for obs in state[area]:
                if obs.character and obs.character.name in (SPARKLE, JADE):
                    obs.character.positioning = 2
        return state, formation.select_formation_stage(self.config, state, capacity)

    def finish(self, state, stage, capacity):
        moves = []
        for _ in range(8):
            plan = formation.plan_formation_sequence(self.config, stage, state, capacity)
            if not plan:
                return state, moves
            self.assertTrue(formation.validate_formation_sequence(
                self.config, stage, state, capacity, plan))
            for index, move in enumerate(plan):
                self.assertTrue(formation.validate_formation_sequence(
                    self.config, stage, state, capacity, plan[index:]))
                after = fixture.apply_move(state, move)
                self.assertTrue(formation.formation_change_allowed(self.config, state, after, stage).allowed)
                state = after
                moves.append(move)
        self.fail("configured filler moves did not converge")

    def test_early_sparkle_uses_root_front_even_with_backend_default(self):
        state, stage = self.board([SPARKLE], capacity=6)
        move = formation.plan_formation_move(self.config, stage, state, 6)
        self.assertEqual((move.source_name, move.target_area), (SPARKLE, "on_field"))

    def test_full_population_future_target_retires_jade_across_areas(self):
        state, stage = self.board([SPARKLE])
        original = copy.deepcopy(state)
        plan = formation.plan_formation_sequence(self.config, stage, state, 5)
        self.assertEqual(len(plan), 2)
        self.assertTrue(all(move.requires_completion for move in plan))
        self.assertEqual(plan[0].source_name, JADE)
        self.assertEqual(plan[0].target_area, "in_hand")
        self.assertEqual(plan[1].source_name, SPARKLE)
        self.assertEqual(plan[1].target_area, "on_field")
        after, moves = self.finish(state, stage, 5)
        self.assertEqual(len(moves), 2)
        self.assertIn(SPARKLE, [formation._name(o) for o in after["on_field"]])
        self.assertNotIn(JADE, formation._field_names(after))
        self.assertEqual(len(formation._field_names(after)), 5)
        self.assertEqual(state, original)

    def test_future_backend_target_directly_replaces_jade(self):
        state, stage = self.board([TRIB])
        move = formation.plan_formation_move(self.config, stage, state, 5)
        self.assertEqual((move.source_name, move.target_name, move.target_area),
                         (TRIB, JADE, "off_field"))

    def test_already_misplaced_sparkle_moves_to_configured_front(self):
        state, stage = self.board(capacity=6, sparkle_fielded=True)
        move = formation.plan_formation_move(self.config, stage, state, 6)
        self.assertEqual((move.source_name, move.source_area, move.target_area),
                         (SPARKLE, "off_field", "on_field"))
        after, moves = self.finish(state, stage, 6)
        self.assertEqual(len(moves), 1)
        self.assertIn(JADE, formation._field_names(after))

    def test_no_ready_candidate_does_not_retire_jade(self):
        for hand in ([], [fixture.unknown(SPARKLE)], [fixture.known(SPARKLE, evidence="stale")]):
            with self.subTest(hand=hand):
                state, stage = self.board(hand)
                self.assertEqual(formation.plan_formation_sequence(self.config, stage, state, 5), ())

    def test_failed_replacement_destination_does_not_retire_jade(self):
        state, stage = self.board([SPARKLE])
        excluded = [("in_hand", 0, "on_field", i) for i in range(4)]
        self.assertEqual(formation.plan_formation_sequence(
            self.config, stage, state, 5, excluded_moves=excluded), ())

    def test_future_target_cannot_evict_current_stage_member(self):
        state = fixture.snapshot([MAIN, SUNDAY, "丹恒·饮月"], [MARCH, BLADE], [SPARKLE])
        stage = formation.select_formation_stage(self.config, state, 5)
        self.assertEqual(formation.plan_formation_sequence(self.config, stage, state, 5), ())

    def test_held_stage_target_wins_over_future_root_filler(self):
        state, stage = self.board([TRIB, "丹恒·饮月"])
        plan = formation.plan_formation_sequence(self.config, stage, state, 5)
        self.assertTrue(formation.validate_formation_sequence(self.config, stage, state, 5, plan))
        after = state
        for move in plan:
            after = fixture.apply_move(after, move)
        self.assertIn("丹恒·饮月", formation._field_names(after))
        self.assertNotIn(TRIB, formation._field_names(after))

    def test_established_trait_still_protects_temporary_unit(self):
        self.characters[JADE] = fixture.Character(JADE, positioning=2)
        self.data["formation"]["traits"][JADE] = ["临时保护"]
        self.data["formation"]["preserve_traits"]["临时保护"] = 1
        self.config = formation.validate_formation_config(self.data, self.characters.get)
        state, stage = self.board([SPARKLE])
        self.assertEqual(formation.plan_formation_sequence(self.config, stage, state, 5), ())

    def test_established_role_still_protects_temporary_unit(self):
        self.characters[JADE] = fixture.Character(JADE, positioning=2)
        self.data["formation"]["roles"]["interim_role"] = [{"name": JADE, "area": "off_field"}]
        self.data["formation"]["role_requirements"]["interim_role"] = {"candidates": [JADE]}
        self.config = formation.validate_formation_config(self.data, self.characters.get)
        state, stage = self.board([SPARKLE])
        self.assertEqual(formation.plan_formation_sequence(self.config, stage, state, 5), ())

    def test_stage_area_overrides_conflicting_root_and_default(self):
        state = fixture.snapshot([MAIN, SUNDAY], [MARCH, BLADE], [SPARKLE])
        stage = formation.FormationStage("stage_override", 0, (MAIN, SUNDAY), (MARCH, BLADE, SPARKLE))
        state["in_hand"][0].character.positioning = 1
        move = formation.plan_formation_move(self.config, stage, state, 5)
        self.assertEqual(move.target_area, "off_field")

    def test_character_configured_position_precedes_default_without_root_metadata(self):
        stage = formation.FormationStage("opening", 0, (MAIN,), ())
        config = formation.FormationConfig({}, {}, {}, (stage,))
        sparkle = fixture.known(SPARKLE)
        sparkle.character.positioning = 2
        sparkle.character.position = 1
        state = fixture.snapshot([MAIN], [], [sparkle])
        move = formation.plan_formation_move(config, stage, state, 2)
        self.assertEqual(move.target_area, "on_field")

    def test_assignment_candidates_do_not_become_future_fillers(self):
        stage = formation.FormationStage("waiting", 0, (MAIN,), (MARCH,))
        group = formation.AssignmentGroup("on_field", (formation.AssignmentCandidate(SPARKLE),), (SPARKLE,))
        config = formation.FormationConfig({}, {}, {}, (stage,),
            assignment_groups={"future_seat": group}, purchase_targets={SPARKLE: 2},
            root_positions={SPARKLE: ("on_field",)})
        state = fixture.snapshot([MAIN], [JADE], [SPARKLE])
        for capacity in (2, 3):
            with self.subTest(capacity=capacity):
                self.assertEqual(formation.plan_formation_sequence(config, stage, state, capacity), ())


if __name__ == "__main__":
    unittest.main()
