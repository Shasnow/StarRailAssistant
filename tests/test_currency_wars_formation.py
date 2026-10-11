"""Offline tests load only the pure formation planner, never the game runtime."""

import copy
import importlib.util
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "_currency_wars_formation_unit",
    Path(__file__).resolve().parents[1] / "tasks/currency_wars/formation.py")
formation = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = formation
SPEC.loader.exec_module(formation)

LV999, EXPERT, BLADE = "银狼LV.999", "银狼", "千冶·刃"
YAO, YING, TRIB = "爻光", "绯英", "缇宝"
SPARXIE, SPARKLE, MC, FU = "火花", "花火", "开拓者", "符玄"
FINAL_ON = [LV999, SPARXIE, EXPERT, TRIB]
FINAL_OFF = [YAO, YING, SPARKLE, MC, FU]


@dataclass
class Character:
    name: str
    is_npc: bool = False
    is_locked: bool = False
    positioning: int = 3


@dataclass
class Observation:
    slot_index: int
    state: str
    character: Character | None = None
    occupied: bool | None = None
    evidence: str = "name_match"
    stars: int | None = 1


def known(name, stars=1, evidence="name_match"):
    return Observation(0, "known", Character(name), True, evidence, stars)


def empty():
    return Observation(0, "empty", occupied=False, evidence="empty_template", stars=None)


def unknown(name=None):
    return Observation(0, "unknown", Character(name) if name else None, evidence="unrecognized")


def snapshot(on=(), off=(), hand=(), on_size=4, off_size=6, hand_size=9):
    result = {}
    for area, names, size in (("on_field", on, on_size), ("off_field", off, off_size),
                              ("in_hand", hand, hand_size)):
        result[area] = [known(n) if isinstance(n, str) else n for n in names]
        result[area] += [empty() for _ in range(size - len(names))]
        for i, obs in enumerate(result[area]):
            obs.slot_index = i
    return result


def apply_move(state, move):
    result = copy.deepcopy(state)
    source, target = result[move.source_area], result[move.target_area]
    source[move.source_index], target[move.target_index] = target[move.target_index], source[move.source_index]
    # Simulate a fresh confirmed snapshot after the actual action, not a pending drag.
    for area, slots in result.items():
        for i, obs in enumerate(slots):
            obs.slot_index = i
    return result


def strategy():
    return {
        "on_field": {name: 2 for name in FINAL_ON},
        "off_field": {name: 2 for name in FINAL_OFF + [BLADE]},
        "formation": {
            "traits": {
                LV999: ["欢愉", "星核猎手"], YAO: ["欢愉"], YING: ["欢愉"],
                SPARXIE: ["欢愉"], MC: ["欢愉"], BLADE: ["星核猎手"], EXPERT: ["星核猎手"],
            },
            "preserve_traits": {"欢愉": 3, "星核猎手": 2},
            "protect_until_fielded": {BLADE: EXPERT},
            "stages": [
                {"name": "early", "min_capacity": 0, "on_field": [LV999, YAO, YING, TRIB],
                 "off_field": [BLADE], "priority": [LV999, YAO, BLADE, YING, TRIB]},
                {"name": "final", "min_capacity": 9, "on_field": FINAL_ON,
                 "off_field": FINAL_OFF},
            ],
        },
    }


class FormationTests(unittest.TestCase):
    def setUp(self):
        self.data = strategy()
        self.characters = {name: Character(name) for name in FINAL_ON + FINAL_OFF + [BLADE]}
        self.characters["交光"] = self.characters[YAO]
        self.lookup = self.characters.get
        self.config = formation.validate_formation_config(self.data, self.lookup)

    def test_failed_replacement_keeps_interim_unit_and_can_deploy_another_card(self):
        stage = formation.FormationStage("retry", 0, ("灵砂", "希儿"), (BLADE,),
                                        priority=(BLADE, "希儿", "灵砂"))
        config = formation.FormationConfig({}, {}, {}, (stage,))
        state = snapshot(["灵砂"], ["吉尔伽美什"], [BLADE, "希儿"], off_size=1)
        failed = {("in_hand", 0, "off_field", 0)}
        move = formation.plan_formation_move(config, stage, state, 3, excluded_moves=failed)
        self.assertEqual((move.source_area, move.source_index, move.target_area),
                         ("in_hand", 1, "on_field"))
        state = apply_move(state, move)
        self.assertIsNone(formation.plan_formation_move(
            config, stage, state, 3, excluded_moves=failed))
        self.assertEqual(state["off_field"][0].character.name, "吉尔伽美什")

    def test_unusable_replacement_does_not_retire_a_useful_interim_unit(self):
        stage = formation.FormationStage("retry", 0, ("灵砂", "希儿"), (BLADE,))
        config = formation.FormationConfig({}, {}, {}, (stage,))
        state = snapshot(["灵砂", "希儿"], ["吉尔伽美什"], [BLADE], off_size=1)
        state["in_hand"][0].character.positioning = 2
        # A failed deployment to this endpoint cannot justify retiring its
        # occupant merely to repeat the same action against an EMPTY identity.
        excluded = {("in_hand", 0, "off_field", 0)}
        self.assertIsNone(formation.plan_formation_move(
            config, stage, state, 4, excluded_moves=excluded))

    def test_legacy_strategy_keeps_feature_disabled(self):
        self.assertIsNone(formation.validate_formation_config({}, self.lookup))
        self.assertTrue(formation.stage_upgrade_allowed(None, {}, None).allowed)
        self.assertIsNone(formation.plan_formation_move(None, None, {}, 9))

    def test_canonical_aliases_and_duplicate_validation(self):
        self.data["formation"]["stages"][0]["on_field"][1] = "交光"
        parsed = formation.validate_formation_config(self.data, self.lookup)
        self.assertEqual(parsed.stages[0].on_field[1], YAO)
        self.data["formation"]["stages"][0]["off_field"].append(YAO)
        with self.assertRaises(ValueError):
            formation.validate_formation_config(self.data, self.lookup)

    def test_noise_hand_and_dynamic_fee_duplicates_never_inflate_traits(self):
        state = snapshot([known(LV999, 2), unknown(YAO), "1"],
                         [known(LV999, 1), BLADE], [YAO, YING])
        self.assertEqual(formation.confirmed_trait_counts(self.config, state),
                         {"欢愉": 1, "星核猎手": 2})
        state["off_field"][0].evidence = "event_invalidated"
        self.assertEqual(formation.confirmed_trait_counts(self.config, state)["星核猎手"], 2)

    def test_pending_drag_does_not_unlock_protected_transition(self):
        before = snapshot([LV999, YAO, YING, known(EXPERT, evidence="pending_drag")], [BLADE])
        after = copy.deepcopy(before)
        after["off_field"][0] = empty()
        decision = formation.formation_change_allowed(self.config, before, after)
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.reason.startswith("protect:"))

    def test_successor_must_be_confirmed_before_retirement_not_only_predicted_after(self):
        before = snapshot([LV999, YAO, YING], [BLADE], [EXPERT])
        after = snapshot([LV999, YAO, YING, EXPERT], [], [BLADE])
        self.assertFalse(formation.formation_change_allowed(self.config, before, after).allowed)
        before["on_field"][3] = known(EXPERT)
        self.assertTrue(formation.formation_change_allowed(self.config, before, after).allowed)

    def test_established_trait_thresholds_are_preserved_by_replacement(self):
        before = snapshot([LV999, YAO, YING, TRIB], [BLADE])
        after = copy.deepcopy(before)
        after["on_field"][1] = known(SPARKLE)
        decision = formation.formation_change_allowed(self.config, before, after)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "preserve:欢愉:3")
        after["on_field"][1] = known(SPARXIE)
        self.assertTrue(formation.formation_change_allowed(self.config, before, after).allowed)

    def test_missing_or_uncertain_capacity_cannot_select_final(self):
        state = snapshot([LV999, YAO, YING], [BLADE])
        self.assertEqual(formation.select_formation_stage(self.config, state, None).name, "early")
        self.assertEqual(formation.select_formation_stage(self.config, state, 7).name, "early")
        self.assertEqual(formation.select_formation_stage(self.config, state, 9).name, "final")

    def test_required_fielded_character_needs_positive_observation(self):
        self.data["formation"]["stages"][1]["requires_fielded"] = [EXPERT]
        config = formation.validate_formation_config(self.data, self.lookup)
        state = snapshot([unknown(EXPERT)], [], [EXPERT])
        self.assertEqual(formation.select_formation_stage(config, state, 9).name, "early")
        state["on_field"][0] = known(EXPERT)
        self.assertEqual(formation.select_formation_stage(config, state, 9).name, "final")

    def test_available_requirement_accepts_held_successor_without_fielding_deadlock(self):
        self.data["formation"]["stages"][1]["requires_available"] = [EXPERT]
        config = formation.validate_formation_config(self.data, self.lookup)
        state = snapshot([LV999, YAO, YING], [BLADE], [EXPERT])
        self.assertEqual(formation.select_formation_stage(config, state, 9).name, "final")
        state["in_hand"][0] = unknown(EXPERT)
        self.assertEqual(formation.select_formation_stage(config, state, 9).name, "early")
        state["in_hand"][0] = known(EXPERT, evidence="pending_drag")
        self.assertEqual(formation.select_formation_stage(config, state, 9).name, "early")
        state["in_hand"][0] = known(EXPERT)
        state["in_hand"][0].character.is_locked = True
        self.assertEqual(formation.select_formation_stage(config, state, 9).name, "early")

    def test_available_and_fielded_requirements_remain_independent(self):
        self.data["formation"]["stages"][1].update({
            "requires_available": [SPARXIE], "requires_fielded": [EXPERT]})
        config = formation.validate_formation_config(self.data, self.lookup)
        state = snapshot([LV999], [BLADE], [EXPERT, SPARXIE])
        self.assertEqual(formation.select_formation_stage(config, state, 9).name, "early")
        state["on_field"][1] = known(EXPERT)
        self.assertEqual(formation.select_formation_stage(config, state, 9).name, "final")

    def test_early_order_prioritizes_main_and_hunter_across_areas(self):
        state = snapshot(hand=[TRIB, YING, BLADE, YAO, LV999])
        deployed = []
        for _ in range(5):
            move = formation.plan_formation_move(self.config, self.config.stages[0], state, 5,
                                                 preferred_names=(LV999,))
            self.assertIsNotNone(move)
            deployed.append(state[move.source_area][move.source_index].character.name)
            state = apply_move(state, move)
        self.assertEqual(deployed, [LV999, YAO, BLADE, YING, TRIB])
        self.assertEqual(sum(o.state == "known" for o in state["on_field"]), 4)
        self.assertEqual(sum(o.state == "known" for o in state["off_field"]), 1)

    def test_unknown_endpoints_and_population_are_conservative(self):
        state = snapshot(on=[unknown()] * 4, off=[unknown()] * 6, hand=[LV999])
        self.assertIsNone(formation.plan_formation_move(self.config, self.config.stages[0], state, 9))
        state = snapshot([TRIB], [], [LV999])
        move = formation.plan_formation_move(self.config, self.config.stages[0], state, None)
        # A confirmed one-for-one replacement is safe even with unknown population.
        self.assertEqual((move.source_area, move.target_area, move.target_index), ("in_hand", "on_field", 0))

    def test_unknown_successor_cannot_cause_blade_removal(self):
        state = snapshot([LV999, YAO, YING, unknown(EXPERT)], [BLADE], [SPARKLE])
        move = formation.plan_formation_move(self.config, self.config.stages[1], state, 9)
        if move:
            after = apply_move(state, move)
            self.assertIn(BLADE, formation._field_names(after))

    def test_three_front_six_back_reaches_four_front_five_back(self):
        state = snapshot([LV999, SPARXIE, TRIB], [YAO, YING, SPARKLE, MC, FU, BLADE], [EXPERT])
        original = copy.deepcopy(state)
        trace = []
        for _ in range(20):
            move = formation.plan_formation_move(self.config, self.config.stages[1], state, 9)
            if move is None:
                break
            before_names = formation._field_names(state)
            after = apply_move(state, move)
            self.assertTrue(formation.formation_change_allowed(self.config, state, after).allowed)
            if BLADE not in formation._field_names(after):
                self.assertIn(EXPERT, before_names)
            counts = formation.confirmed_trait_counts(self.config, after)
            self.assertGreaterEqual(counts["欢愉"], 3)
            self.assertGreaterEqual(counts["星核猎手"], 2)
            trace.append(move)
            state = after
        self.assertEqual({o.character.name for o in state["on_field"] if o.state == "known"}, set(FINAL_ON))
        self.assertEqual({o.character.name for o in state["off_field"] if o.state == "known"}, set(FINAL_OFF))
        self.assertLess(len(trace), 20)
        self.assertEqual(original["in_hand"][0].character.name, EXPERT)

    def test_full_front_early_formation_relocates_without_breaking_traits(self):
        state = snapshot([LV999, YAO, YING, TRIB], [BLADE], [EXPERT, SPARXIE, SPARKLE, MC, FU])
        for _ in range(25):
            move = formation.plan_formation_move(self.config, self.config.stages[1], state, 9)
            if move is None:
                break
            after = apply_move(state, move)
            self.assertTrue(formation.formation_change_allowed(self.config, state, after).allowed)
            state = after
        self.assertEqual({o.character.name for o in state["on_field"] if o.state == "known"}, set(FINAL_ON))
        self.assertEqual({o.character.name for o in state["off_field"] if o.state == "known"}, set(FINAL_OFF))

    def test_optional_core_gate_uses_stars_traits_and_dynamic_price_separately(self):
        self.data["formation"]["upgrade_gate"] = {
            "from_level": 7, "fielded": {LV999: 2},
            "traits": {"欢愉": 3, "星核猎手": 2}, "prices": {LV999: 4}}
        config = formation.validate_formation_config(self.data, self.lookup)
        state = snapshot([known(LV999, 2), YAO, YING], [BLADE])
        self.assertFalse(formation.stage_upgrade_allowed(config, state, 7, {LV999: 3}).allowed)
        self.assertTrue(formation.stage_upgrade_allowed(config, state, 7, {LV999: 4}).allowed)
        state["on_field"][0] = known(LV999, 1)
        self.assertFalse(formation.stage_upgrade_allowed(config, state, 7, {LV999: 4}).allowed)
        self.assertTrue(formation.stage_upgrade_allowed(config, state, 6).allowed)
        self.assertFalse(formation.stage_upgrade_allowed(config, state, None).allowed)

    def test_disabled_core_gate_does_not_block_existing_strategies(self):
        self.assertTrue(formation.stage_upgrade_allowed(self.config, snapshot(), 7).allowed)

    def test_config_rejects_cycles_noise_and_invalid_numbers(self):
        for mutation in (
            lambda f: f["protect_until_fielded"].update({EXPERT: BLADE}),
            lambda f: f["stages"][0].update({"min_capacity": True}),
            lambda f: f["traits"].update({"1": ["欢愉"]}),
            lambda f: f["preserve_traits"].update({"未定义羁绊": 3}),
        ):
            data = strategy()
            mutation(data["formation"])
            with self.assertRaises(ValueError):
                formation.validate_formation_config(data, self.lookup)

    def test_planning_does_not_mutate_input_or_character_placement(self):
        state = snapshot([LV999, YAO, YING], [BLADE], [EXPERT])
        before = copy.deepcopy(state)
        formation.plan_formation_move(self.config, self.config.stages[1], state, 9)
        self.assertEqual(state, before)

    def test_interim_units_are_not_benched_without_a_ready_replacement(self):
        state = snapshot(["临时前台"], ["临时后台"])
        self.assertIsNone(formation.plan_formation_move(self.config, self.config.stages[0], state, 3))

    def test_locked_or_npc_occupants_are_never_moved(self):
        locked, npc = known("锁定角色"), known("NPC")
        locked.character.is_locked = True
        npc.character.is_npc = True
        state = snapshot([locked, npc, unknown(), unknown()], [unknown()] * 6, [LV999])
        self.assertIsNone(formation.plan_formation_move(self.config, self.config.stages[0], state, 3))

    def test_no_second_same_name_field_copy_is_deployed(self):
        state = snapshot([LV999], [], [LV999])
        self.assertIsNone(formation.plan_formation_move(self.config, self.config.stages[0], state, 3))


    def test_starter_hand_is_deployed_until_population_is_full(self):
        march, herta, ratio, aglaea = [known(n) for n in ("三月七", "黑塔", "真理医生", "阿格莱雅")]
        march.character.positioning = 2
        ratio.character.positioning = aglaea.character.positioning = 1
        state = snapshot(hand=[march, herta, ratio, aglaea])
        trace = []
        for _ in range(3):
            move = formation.plan_formation_move(self.config, self.config.stages[0], state, 3)
            self.assertIsNotNone(move)
            self.assertEqual(move.reason, "deploy_interim")
            self.assertEqual(state[move.target_area][move.target_index].state, "empty")
            trace.append((state[move.source_area][move.source_index].character.name, move.target_area))
            state = apply_move(state, move)
        self.assertEqual(trace, [("黑塔", "on_field"), ("三月七", "off_field"), ("真理医生", "on_field")])
        self.assertIsNone(formation.plan_formation_move(self.config, self.config.stages[0], state, 3))

    def test_strategy_character_is_prioritized_over_temporary_starter(self):
        state = snapshot(hand=["黑塔", LV999])
        move = formation.plan_formation_move(self.config, self.config.stages[0], state, 3,
                                             preferred_names=(LV999,))
        self.assertEqual(state[move.source_area][move.source_index].character.name, LV999)
        self.assertEqual(move.reason, "deploy")

    def test_excluded_failed_deployment_uses_another_confirmed_empty_destination(self):
        state = snapshot(hand=[LV999])
        first = formation.plan_formation_move(self.config, self.config.stages[0], state, 3)
        key = (first.source_area, first.source_index, first.target_area, first.target_index)
        alternative = formation.plan_formation_move(self.config, self.config.stages[0], state, 3,
                                                    excluded_moves={key})
        self.assertNotEqual((alternative.source_area, alternative.source_index,
                             alternative.target_area, alternative.target_index), key)

    def test_excluded_temporary_moves_do_not_fall_back_to_the_failed_endpoint(self):
        state = snapshot(hand=["黑塔"])
        excluded = {("in_hand", 0, "on_field", index) for index in range(4)}
        self.assertIsNone(formation.plan_formation_move(self.config, self.config.stages[0], state, 3,
                                                       excluded_moves=excluded))

    def test_strategy_character_replaces_a_temporary_unit_at_full_population(self):
        state = snapshot(["黑塔", "真理医生"], ["三月七"], [LV999])
        move = formation.plan_formation_move(self.config, self.config.stages[0], state, 3,
                                             preferred_names=(LV999,))
        self.assertEqual((move.source_area, move.target_area), ("in_hand", "on_field"))
        after = apply_move(state, move)
        self.assertIn(LV999, formation._field_names(after))
        self.assertEqual(sum(o.state == "known" for a in formation.FIELD_AREAS for o in after[a]), 3)

    def test_temporary_deployment_requires_known_capacity_and_empty_destination(self):
        state = snapshot(hand=["黑塔"])
        self.assertIsNone(formation.plan_formation_move(self.config, self.config.stages[0], state, None))
        state = snapshot([unknown()] * 4, [unknown()] * 6, ["黑塔"])
        self.assertIsNone(formation.plan_formation_move(self.config, self.config.stages[0], state, 3))
        state = snapshot([empty(), unknown(), unknown(), unknown()], [unknown()] * 6, ["黑塔"])
        self.assertIsNone(formation.plan_formation_move(self.config, self.config.stages[0], state, 3))

    def test_temporary_deployment_never_moves_unreliable_locked_or_npc_hands(self):
        locked, npc = known("锁定角色"), known("NPC")
        locked.character.is_locked = True
        npc.character.is_npc = True
        state = snapshot(hand=[locked, npc, unknown("黑塔"), known("真理医生", evidence="pending_drag")])
        self.assertIsNone(formation.plan_formation_move(self.config, self.config.stages[0], state, 3))

    def test_off_field_only_temporary_hand_cannot_fill_population_before_a_front_unit(self):
        march = known("三月七")
        march.character.positioning = 2
        state = snapshot(hand=[march])
        self.assertIsNone(formation.plan_formation_move(self.config, self.config.stages[0], state, 3))
        state = snapshot(["黑塔"], [], [march])
        move = formation.plan_formation_move(self.config, self.config.stages[0], state, 3)
        self.assertEqual(move.target_area, "off_field")

    def test_same_name_temporary_copy_is_not_deployed_twice(self):
        state = snapshot(["黑塔"], [], ["黑塔"])
        self.assertIsNone(formation.plan_formation_move(self.config, self.config.stages[0], state, 3))

    def test_temporary_deployment_keeps_protected_occupants_and_trait_thresholds(self):
        state = snapshot([LV999, YAO, YING], [BLADE], ["黑塔"])
        move = formation.plan_formation_move(self.config, self.config.stages[0], state, 5)
        self.assertEqual(move.reason, "deploy_interim")
        after = apply_move(state, move)
        self.assertIn(BLADE, formation._field_names(after))
        self.assertEqual(formation.confirmed_trait_counts(self.config, state),
                         formation.confirmed_trait_counts(self.config, after))

    def test_temporary_planning_does_not_mutate_observations(self):
        state = snapshot(hand=["黑塔"])
        before = copy.deepcopy(state)
        formation.plan_formation_move(self.config, self.config.stages[0], state, 3)
        self.assertEqual(state, before)

if __name__ == "__main__":
    unittest.main()
