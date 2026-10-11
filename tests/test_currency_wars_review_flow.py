"""Final audit regressions for event failure and role purchase precedence."""
from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from unittest.mock import Mock

from test_currency_wars_flow import FakeOperator, load_isolated_task


class CurrencyWarsReviewFlowTests(unittest.TestCase):
    def setUp(self):
        self.module, self.characters, self.logic, names = load_isolated_task()
        self.addCleanup(lambda: [sys.modules.pop(name, None) for name in names])
        self.operator = FakeOperator()
        self.task = self.module.CurrencyWars(self.operator, runtimes=1)
        self.task._vision.capture_sample = Mock(return_value=None)
        # These regressions start on an authenticated ordinary preparation/shop state.
        self.task._preparation_round = (2, 1)
        self.task._set_shop_open = Mock(return_value=True)

    def test_failed_fortune_teller_selection_stops_without_opening_shop(self):
        self.task.handle_fortune_teller = Mock(return_value=False)
        with self.assertRaises(RuntimeError):
            self.task._handle_fortune_teller_after_battle(None)
        self.task.handle_fortune_teller.assert_called_once()
        self.assertFalse(any(name == "click" for name, _, _ in self.operator.calls))

    def test_confirmed_fortune_teller_selection_can_continue(self):
        self.task.handle_fortune_teller = Mock(return_value=True)
        self.assertFalse(self.task._handle_fortune_teller_after_battle(None))
        self.task.handle_fortune_teller.assert_called_once()

    def test_higher_role_star_goal_overrides_lower_strategy_purchase_goal(self):
        character = self.characters.Characters.get_character("灵砂")
        self.task.strategy_characters = {character.name: 1}
        self.task._set_observation("on_field", self.logic.SlotObservation(
            0, self.logic.SlotState.KNOWN, character=character,
            occupied=True, stars=1, evidence="confirmed_character", revision=1))
        self.task.get_level = Mock(return_value=5)
        self.task.get_coins = Mock(return_value=50)
        self.task.min_level = self.task.mid_level = 5
        self.task.min_coins = 99
        self.task.shopping_budget.update(actions=1, refreshes=0)
        self.task._role_purchase_goals = Mock(return_value={character.name: 2})
        self.task._role_evaluations = Mock(return_value={})
        card = self.logic.ShopCard(0, character, self.task.store_area[0],
                                  raw_text=character.name, price=2, price_evidence="price_badge")
        self.task._scan_store = Mock(return_value=self.logic.ShopObservation(
            self.logic.ShopState.READY, (card,)))
        self.task._confirm_purchase = Mock(return_value=self.logic.ActionResult.CONFIRMED)
        result = self.task.shopping()
        self.assertEqual(result.confirmed_purchases, 1)
        self.task._confirm_purchase.assert_called_once()

    def test_role_upgrade_materials_can_merge_before_batch_returns_to_placement(self):
        character = self.characters.Characters.get_character("灵砂")
        empty = lambda i: self.logic.SlotObservation(i, self.logic.SlotState.EMPTY,
                                                    occupied=False, evidence="confirmed_empty")
        physical = {
            area: [empty(i) for i in range(len(slots))]
            for area, slots in self.task._observations.items()
        }
        physical["on_field"][0] = self.logic.SlotObservation(
            0, self.logic.SlotState.KNOWN, character=character, occupied=True,
            stars=1, evidence="confirmed_character", revision=1)
        for area, observations in physical.items():
            for observation in observations:
                self.task._set_observation(area, observation)
        stage = self.module.FormationStage("role upgrade", 0, (character.name,), ())
        self.task.formation_config = self.module.FormationConfig(
            {}, {}, {}, (stage,),
            roles={"survival": (self.module.RoleProvider(character.name, ("on_field",), 2),)},
            role_requirements={"survival": self.module.RoleRequirement(
                1, (character.name,), (), "block")})
        self.task.strategy_characters = {character.name: 2}
        self.task.get_level = Mock(return_value=5)
        self.task.get_coins = Mock(return_value=50)
        self.task.min_level = self.task.mid_level = 5
        self.task.min_coins = 99
        self.task.shopping_budget.update(actions=8, refreshes=0)
        card = self.logic.ShopCard(0, character, self.task.store_area[0],
                                  raw_text=character.name, price=2, price_evidence="price_badge")
        self.task._scan_store = Mock(return_value=self.logic.ShopObservation(
            self.logic.ShopState.READY, (card,)))

        def field_scan():
            for area in ("on_field", "off_field"):
                for observation in physical[area]:
                    self.task._set_observation(area, observation)
            self.task._dirty_slots.clear()

        def bench_scan(*args, **kwargs):
            for observation in physical["in_hand"]:
                self.task._set_observation("in_hand", observation)
            self.task._bench_dirty = False
            self.task._reconcile_purchase_pending()

        self.task._refresh_dirty_field = Mock(side_effect=field_scan)
        self.task.get_in_hand_area = Mock(side_effect=bench_scan)
        purchases = []

        def confirm(*args, **kwargs):
            purchases.append(card)
            if len(purchases) == 1:
                physical["in_hand"][0] = replace(physical["on_field"][0], slot_index=0)
            else:
                physical["on_field"][0] = replace(physical["on_field"][0], stars=2, revision=2)
                physical["in_hand"][0] = empty(0)
            return self.logic.ActionResult.CONFIRMED

        self.task._confirm_purchase = Mock(side_effect=confirm)
        result = self.task.shopping()
        self.assertEqual(result.confirmed_purchases, 2)
        self.assertEqual(self.task._role_evaluations()["survival"].state, "satisfied")


if __name__ == "__main__":
    unittest.main()
