"""Strategy population excludes confirmed support NPCs; board capacity stays raw."""

from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import test_currency_wars_flow as flow_fixture
import test_currency_wars_page_purchase as page_fixture


class StrategyPopulationTests(unittest.TestCase):
    setUp = flow_fixture.CurrencyWarsFlowTests.setUp
    character = flow_fixture.CurrencyWarsFlowTests.character
    observe = flow_fixture.CurrencyWarsFlowTests.observe
    empty_board = flow_fixture.CurrencyWarsFlowTests.empty_board
    shop = flow_fixture.CurrencyWarsFlowTests.shop
    card = page_fixture.PagePurchaseTests.card
    add_physical_copy = page_fixture.PagePurchaseTests.add_physical_copy
    install_game = page_fixture.PagePurchaseTests.install_game

    def configure_stages(self, capacity=5):
        self.empty_board()
        self.task._begin_preparation()
        self.task.max_team_size = capacity
        self.task._placement_pending = self.task._bench_dirty = False
        self.task.strategy_characters = {"佩拉": 1}
        self.task.formation_config = self.module.FormationConfig({}, {}, {}, (
            self.module.FormationStage("opening", 0, ("佩拉",), ()),
            self.module.FormationStage("four", 4, ("佩拉",), ()),
            self.module.FormationStage("five", 5, ("佩拉",), ("三月七",)),
            self.module.FormationStage("six", 6, ("佩拉",), ("三月七", "花火")),
        ))
        self.observe("on_field", 0, self.character("佩拉"), stars=1)
        self.task._population_current = 1

    def add_npc(self, area="off_field", index=5):
        # Two distinct NPC slots can share the same UI name. Count physical
        # slots rather than deduplicating them as normal strategy identities.
        npc = self.characters.Character(
            "锁定支援单位", 0, self.characters.Positioning.OnOffField,
            is_locked=True, is_npc=True)
        observation = self.observe(area, index, npc)
        self.task._population_current += 1
        return observation

    def effective_capacity(self, capacity=None):
        return self.module.strategy_population_capacity(
            self.task._observations,
            self.task.max_team_size if capacity is None else capacity)

    def test_one_npc_selects_four_at_raw_five_and_five_at_raw_six(self):
        for capacity, expected in ((5, "four"), (6, "five")):
            with self.subTest(raw_capacity=capacity):
                self.configure_stages(capacity)
                self.add_npc()

                self.assertEqual(self.effective_capacity(), capacity - 1)
                self.assertEqual(self.task._formation_stage().name, expected)
                self.assertEqual(self.task.max_team_size, capacity)

    def test_two_npcs_with_same_name_deduct_two_physical_slots(self):
        for capacity, expected in ((6, "four"), (7, "five")):
            with self.subTest(raw_capacity=capacity):
                self.configure_stages(capacity)
                first = self.add_npc(index=4)
                second = self.add_npc(index=5)

                self.assertEqual(first.character.name, second.character.name)
                self.assertEqual(self.module.confirmed_field_npc_count(self.task._observations), 2)
                self.assertEqual(self.effective_capacity(), capacity - 2)
                self.assertEqual(self.task._formation_stage().name, expected)
                self.assertEqual(self.task.max_team_size, capacity)

    def test_no_npc_keeps_existing_capacity_and_stage(self):
        for capacity, expected in ((4, "four"), (5, "five"), (6, "six")):
            with self.subTest(raw_capacity=capacity):
                self.configure_stages(capacity)

                self.assertEqual(self.effective_capacity(), capacity)
                self.assertEqual(self.task._formation_stage().name, expected)

    def test_npc_in_frontline_also_reduces_strategy_capacity(self):
        self.configure_stages(5)
        self.add_npc("on_field", 1)

        self.assertEqual(self.effective_capacity(), 4)
        self.assertEqual(self.task._formation_stage().name, "four")

    def test_npc_on_bench_does_not_reduce_available_strategy_population(self):
        self.configure_stages(5)
        self.add_npc("in_hand", 0)
        self.task._population_current -= 1

        self.assertEqual(self.effective_capacity(), 5)
        self.assertEqual(self.task._formation_stage().name, "five")

    def test_unknown_npc_and_historical_character_cannot_supply_a_deduction(self):
        self.configure_stages(5)
        observed = self.add_npc()
        self.task._observations["off_field"][5] = replace(
            observed, state=self.logic.SlotState.UNKNOWN, occupied=None)

        self.assertIs(self.task.off_field_character[5], observed.character)
        self.assertEqual(self.effective_capacity(), 5)
        self.assertEqual(self.task._formation_stage().name, "five")

    def test_locked_ordinary_character_is_not_a_support_npc(self):
        self.configure_stages(5)
        ordinary = self.character("黑塔")
        ordinary.is_locked = True
        self.observe("off_field", 5, ordinary, stars=1)
        self.task._population_current += 1

        self.assertFalse(ordinary.is_npc)
        self.assertEqual(self.effective_capacity(), 5)
        self.assertEqual(self.task._formation_stage().name, "five")

    def test_unidentified_locked_slot_is_not_a_support_npc(self):
        self.configure_stages(5)
        self.task._observations["off_field"][5] = self.logic.SlotObservation(
            5, self.logic.SlotState.LOCKED, occupied=True, evidence="unidentified locked card")

        self.assertEqual(self.effective_capacity(), 5)

    def test_npc_marker_is_independent_of_character_lock_and_unknown_occupancy_flag(self):
        self.configure_stages(5)
        observation = self.add_npc()
        observation.character.is_locked = False
        self.task._observations["off_field"][5] = replace(observation, occupied=None)

        self.assertEqual(self.module.confirmed_field_npc_count(self.task._observations), 1)
        self.assertEqual(self.effective_capacity(), 4)

    def test_stale_or_unreliable_npc_observations_do_not_reduce_capacity(self):
        for evidence in ("pending_drag", "stale", "observation_error", "event_invalidated",
                         "layout_changed", "strategy_changed"):
            with self.subTest(evidence=evidence):
                self.configure_stages(5)
                observation = self.add_npc()
                self.task._observations["off_field"][5] = replace(
                    observation, evidence=evidence)

                self.assertEqual(self.effective_capacity(), 5)
        self.configure_stages(5)
        observation = self.add_npc()
        self.task._observations["off_field"][5] = SimpleNamespace(
            **vars(observation), stale=True)
        self.assertEqual(self.effective_capacity(), 5)

    def test_explicit_vacancy_or_invalid_name_cannot_deduct_an_npc(self):
        self.configure_stages(5)
        observation = self.add_npc()
        self.task._observations["off_field"][5] = replace(observation, occupied=False)
        self.assertEqual(self.effective_capacity(), 5)
        for name in ("", "   ", "123", None):
            with self.subTest(name=name):
                self.task._observations["off_field"][5] = replace(
                    observation, character=SimpleNamespace(name=name, is_npc=True))
                self.assertEqual(self.effective_capacity(), 5)

    def test_invalid_raw_capacity_remains_unknown_and_nonnegative_capacity_clamps(self):
        self.configure_stages(5)
        self.add_npc(index=4)
        self.add_npc(index=5)
        for capacity in (None, True, False, -1, 5.0, "5"):
            with self.subTest(raw_capacity=capacity):
                self.assertIsNone(self.module.strategy_population_capacity(
                    self.task._observations, capacity))
        self.assertEqual(self.effective_capacity(1), 0)
        self.assertEqual(self.effective_capacity(0), 0)

    def test_task_and_direct_formation_resolver_share_one_npc_deduction(self):
        self.configure_stages(5)
        self.add_npc()

        direct = self.module.select_formation_stage(
            self.task.formation_config, self.task._observations, self.task.max_team_size)
        resolved = self.module.resolve_effective_targets(
            self.task.formation_config, self.task._observations, self.task.max_team_size)

        self.assertEqual((direct.name, resolved.stage.name,
                          self.task._formation_stage().name), ("four", "four", "four"))
        self.assertEqual(self.task.max_team_size, 5)

    def test_position_rule_threshold_uses_strategy_population(self):
        self.configure_stages(5)
        self.add_npc()
        self.observe("off_field", 0, self.character("花火"), stars=1)
        stages = tuple(self.module.FormationStage(name, minimum, ("佩拉",), ("花火",))
                       for name, minimum in (("opening", 0), ("four", 4), ("five", 5)))
        self.task.formation_config = self.module.FormationConfig(
            {}, {}, {}, stages, position_rules=(
                self.module.PositionRule("花火", "on_field", min_capacity=5),))

        early = self.task._effective_formation()
        self.assertEqual(early.stage.name, "four")
        self.assertIn("花火", early.stage.off_field)
        self.assertNotIn("花火", early.stage.on_field)

        self.task.max_team_size = 6
        later = self.task._effective_formation()
        self.assertEqual(later.stage.name, "five")
        self.assertIn("花火", later.stage.on_field)
        self.assertNotIn("花火", later.stage.off_field)

    def test_previous_later_stage_cannot_bypass_new_confirmed_npc_deduction(self):
        self.configure_stages(5)
        self.assertEqual(self.task._effective_formation().stage.name, "five")
        self.add_npc()
        self.observe("in_hand", 0, state=self.logic.SlotState.UNKNOWN)

        self.assertEqual(self.task._effective_formation().stage.name, "four")

    def test_shared_stage_controls_role_procurement_and_battle_readiness(self):
        self.configure_stages(5)
        self.add_npc()
        requirement = self.module.RoleRequirement(1, ("符玄",), (), "block")
        stages = (
            self.module.FormationStage("opening", 0, ("佩拉",), ()),
            self.module.FormationStage("four", 4, ("佩拉",), ()),
            self.module.FormationStage("five", 5, ("佩拉",), (),
                                       role_requirements={"survival": requirement}),
        )
        self.task.formation_config = self.module.FormationConfig(
            {}, {}, {}, stages,
            roles={"survival": (self.module.RoleProvider("符玄", ("off_field",)),)},
            purchase_targets={"佩拉": 1})

        self.assertEqual(self.task._formation_stage().name, "four")
        self.assertEqual(self.task._role_evaluations(), {})
        self.assertEqual(self.task._role_purchase_goals(), {})
        self.assertNotIn("符玄", self.task._purchase_goals())
        self.assertNotEqual(self.task._assess_preparation().state, self.module.Readiness.BLOCKED)

        self.task.max_team_size = 6
        self.assertEqual(self.task._formation_stage().name, "five")
        self.assertEqual(self.task._role_purchase_goals(), {"符玄": 1})
        self.assertEqual(self.task._purchase_goals()["符玄"], 1)
        blocked = self.task._assess_preparation()
        self.assertEqual((blocked.state, blocked.reason),
                         (self.module.Readiness.BLOCKED, "role_not_ready"))

    def test_upgrade_gate_from_level_still_uses_actual_level(self):
        self.configure_stages(7)
        self.add_npc(index=4)
        self.add_npc(index=5)
        self.task.formation_config = replace(
            self.task.formation_config,
            upgrade_gate=self.module.UpgradeGate(6, fielded={"三月七": 3}))

        self.assertEqual(self.effective_capacity(), 5)
        self.assertTrue(self.task._can_upgrade(5))
        self.assertFalse(self.task._can_upgrade(6))
        self.assertEqual(self.task._economy_upgrade_gate(6, {"三月七": 3})[:3],
                         (False, True, False))

    def test_stage_field_and_star_requirements_still_apply_after_npc_deduction(self):
        self.configure_stages(6)
        self.add_npc()
        stages = (
            self.module.FormationStage("opening", 0, ("佩拉",), ()),
            self.module.FormationStage("four", 4, ("佩拉",), ()),
            self.module.FormationStage("five", 5, ("佩拉",), (),
                                       requires_fielded=("三月七",),
                                       requires_stars={"三月七": 2}),
        )
        self.task.formation_config = self.module.FormationConfig({}, {}, {}, stages)

        self.assertEqual(self.task._formation_stage().name, "four")
        self.observe("off_field", 0, self.character("三月七"), stars=1)
        self.assertEqual(self.task._formation_stage().name, "four")
        self.observe("off_field", 0, self.character("三月七"), stars=2)
        self.assertEqual(self.task._formation_stage().name, "five")

    def test_actual_deployment_uses_raw_capacity_and_preserves_npc(self):
        self.configure_stages(5)
        npc = self.add_npc().character
        names = ("佩拉", "灵砂", "黑塔", "三月七")
        self.task.strategy_characters = {name: 1 for name in names}
        self.task.formation_config = self.module.FormationConfig({}, {}, {}, (
            self.module.FormationStage("opening", 0, ("佩拉",), ()),
            self.module.FormationStage("four", 4, names, ()),
            self.module.FormationStage("five", 5, names, ("花火",)),
        ), purchase_targets=self.task.strategy_characters)
        for index, name in enumerate(names[:3]):
            self.observe("on_field", index, self.character(name), stars=1)
        self.observe("in_hand", 0, self.character("三月七"), stars=1)
        self.task._population_current = 4
        self.money = 40
        self.install_game([[]])
        self.task.place_character = self.module.CurrencyWars.place_character.__get__(self.task)

        def drag(source_x, source_y, target_x, target_y, **kwargs):
            self.assertEqual((source_x, source_y), self.task.in_hand_area[0])
            self.assertEqual((target_x, target_y), self.task.on_field_area[3])
            source, target = self.physical["in_hand"][0], self.physical["on_field"][3]
            self.physical["in_hand"][0] = replace(target, slot_index=0)
            self.physical["on_field"][3] = replace(source, slot_index=3)
            return True

        self.task._safe_drag_to = Mock(side_effect=drag)

        self.assertTrue(self.task.place_character())

        self.assertEqual(self.task._formation_stage().name, "four")
        self.assertEqual(self.task.max_team_size, 5)
        self.assertEqual(sum(obs.state == self.logic.SlotState.KNOWN
                             for area in ("on_field", "off_field")
                             for obs in self.task._observations[area]), 5)
        self.assertEqual(self.task.on_field_character[3].name, "三月七")
        self.assertIs(self.task.off_field_character[5], npc)
        self.task._safe_drag_to.assert_called_once()

    def test_previously_confirmed_npc_becoming_unknown_keeps_strategy_population(self):
        self.configure_stages(5)
        observation = self.add_npc()
        before = self.task._effective_formation()
        self.assertEqual((before.npc_count, before.strategy_capacity, before.stage.name),
                         (1, 4, "four"))
        self.task._observations["off_field"][5] = replace(
            observation, state=self.logic.SlotState.UNKNOWN, occupied=None,
            character=None, evidence="temporarily_unreadable")

        after = self.task._effective_formation()

        self.assertEqual(self.module.confirmed_field_npc_count(self.task._observations), 0)
        self.assertEqual((after.npc_count, after.strategy_capacity, after.stage.name),
                         (1, 4, "four"))
        self.assertEqual(self.task.max_team_size, 5)

    def test_previously_confirmed_npc_becoming_stale_keeps_strategy_population(self):
        for evidence in ("stale", "layout_changed", "observation_error", "pending_drag"):
            with self.subTest(evidence=evidence):
                self.configure_stages(5)
                observation = self.add_npc()
                self.task._effective_formation()
                self.task._observations["off_field"][5] = replace(
                    observation, evidence=evidence)

                after = self.task._effective_formation()

                self.assertEqual((after.npc_count, after.strategy_capacity, after.stage.name),
                                 (1, 4, "four"))

    def test_reliably_confirmed_npc_disappearance_releases_population_for_later_stage(self):
        self.configure_stages(5)
        self.add_npc()
        self.assertEqual(self.task._effective_formation().stage.name, "four")
        self.observe("off_field", 5)
        self.task._population_current -= 1

        after = self.task._effective_formation()

        self.assertEqual((after.npc_count, after.strategy_capacity, after.stage.name),
                         (0, 5, "five"))
        self.assertEqual(self.task.max_team_size, 5)

    def test_unknown_bench_does_not_prevent_reliable_field_from_releasing_npc(self):
        self.configure_stages(5)
        self.add_npc()
        self.task._effective_formation()
        self.observe("off_field", 5)
        self.task._population_current -= 1
        self.observe("in_hand", 0, state=self.logic.SlotState.UNKNOWN)

        after = self.task._effective_formation()

        self.assertEqual((after.npc_count, after.strategy_capacity, after.stage.name),
                         (0, 5, "five"))

    def test_npc_history_is_not_released_until_entire_field_is_reliable(self):
        self.configure_stages(5)
        self.add_npc()
        self.task._effective_formation()
        self.observe("off_field", 5)
        self.observe("on_field", 1, state=self.logic.SlotState.UNKNOWN)

        uncertain = self.task._effective_formation()
        self.assertEqual((uncertain.npc_count, uncertain.strategy_capacity, uncertain.stage.name),
                         (1, 4, "four"))

        self.observe("on_field", 1)
        complete = self.task._effective_formation()
        self.assertEqual((complete.npc_count, complete.strategy_capacity, complete.stage.name),
                         (0, 5, "five"))

    def test_two_npc_history_keeps_hidden_slot_and_releases_only_confirmed_disappearance(self):
        self.configure_stages(6)
        first = self.add_npc(index=4)
        self.add_npc(index=5)
        self.task._effective_formation()
        self.task._observations["off_field"][4] = replace(
            first, state=self.logic.SlotState.UNKNOWN, occupied=None)

        uncertain = self.task._effective_formation()
        self.assertEqual(self.module.confirmed_field_npc_count(self.task._observations), 1)
        self.assertEqual((uncertain.npc_count, uncertain.strategy_capacity, uncertain.stage.name),
                         (2, 4, "four"))

        self.observe("off_field", 4)
        complete = self.task._effective_formation()
        self.assertEqual((complete.npc_count, complete.strategy_capacity, complete.stage.name),
                         (1, 5, "five"))

    def test_unknown_npc_without_confirmed_history_is_not_authenticated(self):
        self.configure_stages(5)
        observation = self.add_npc()
        self.task._observations["off_field"][5] = replace(
            observation, state=self.logic.SlotState.UNKNOWN, occupied=None)
        self.assertIsNone(self.task._effective_targets)

        resolved = self.task._effective_formation()

        self.assertEqual((resolved.npc_count, resolved.strategy_capacity, resolved.stage.name),
                         (0, 5, "five"))

    def test_reserved_npc_count_is_a_lower_bound_and_deducted_only_once(self):
        self.configure_stages(6)
        self.add_npc(index=4)

        self.assertEqual(self.module.strategy_population_capacity(
            self.task._observations, 6, reserved_npc_count=2), 4)
        self.assertEqual(self.module.strategy_population_capacity(
            self.task._observations, 6, reserved_npc_count=1), 5)

        self.add_npc(index=5)
        self.assertEqual(self.module.strategy_population_capacity(
            self.task._observations, 6, reserved_npc_count=1), 4)


if __name__ == "__main__":
    unittest.main()
