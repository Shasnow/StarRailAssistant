"""Live population evidence and starting-hand deployment regressions."""
from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import Mock

from test_currency_wars_flow import FakeBox, FakeOperator, ROOT, load_isolated_task


class CurrencyWarsFieldStartTests(unittest.TestCase):
    def setUp(self):
        self.module, self.characters, self.logic, names = load_isolated_task()
        self.addCleanup(lambda: [sys.modules.pop(name, None) for name in names])
        self.operator = FakeOperator()
        self.task = self.module.CurrencyWars(self.operator, runtimes=1)
        self.task._vision.capture_sample = Mock()
        self.operator.locate_any = Mock(return_value=(0, FakeBox()))
        self.set_population(0, 3)

    def set_population(self, current, capacity):
        self.task._vision.read_population = Mock(return_value=types.SimpleNamespace(
            current=current, capacity=capacity, evidence="stable_population", reason="test"))

    def field_states(self):
        return [obs.state for area in ("on_field", "off_field")
                for obs in self.task._observations[area]]

    def test_live_zero_population_recovers_unknown_continued_game_slots(self):
        old = self.characters.Characters.get_character("黑塔")
        self.task.on_field_character[0] = old
        old.is_placed = True
        self.task.update_max_team_size()
        self.assertEqual(self.task.max_team_size, 3)
        self.assertTrue(all(state == self.logic.SlotState.EMPTY for state in self.field_states()))
        self.assertTrue(all(obs.evidence == "zero_population"
                            for area in ("on_field", "off_field")
                            for obs in self.task._observations[area]))
        self.assertIsNone(self.task.on_field_character[0])
        self.assertFalse(old.is_placed)

    def test_zero_population_without_preparation_evidence_keeps_unknown_slots(self):
        self.operator.locate_any.return_value = -1, None
        self.task.update_max_team_size()
        self.assertTrue(all(state == self.logic.SlotState.UNKNOWN for state in self.field_states()))

    def test_population_image_index_without_box_keeps_unknown_slots(self):
        self.operator.locate_any.return_value = 0, None
        self.task.update_max_team_size()
        self.assertTrue(all(state == self.logic.SlotState.UNKNOWN for state in self.field_states()))

    def test_occupied_population_does_not_guess_individual_empty_slots(self):
        self.set_population(1, 4)
        self.task.update_max_team_size()
        self.assertEqual(self.task.max_team_size, 4)
        self.assertTrue(all(state == self.logic.SlotState.UNKNOWN for state in self.field_states()))

    def test_capacity_only_fallback_cannot_unlock_empty_field(self):
        self.set_population(None, None)
        self.operator.ocr_results = [([], "3", 0.999)]
        self.task.update_max_team_size()
        self.assertEqual(self.task.max_team_size, 3)
        self.assertTrue(all(state == self.logic.SlotState.UNKNOWN for state in self.field_states()))

    def test_empty_baseline_is_retained_until_slot_is_targeted(self):
        self.task.update_max_team_size()
        self.operator.ocr_results = [([], "1", 0.999)]
        self.task._vision.slot_is_empty = Mock(return_value=None)
        before = self.task._observe_slot("on_field", 0)
        self.assertEqual(before.state, self.logic.SlotState.EMPTY)
        self.assertEqual(before.evidence, "zero_population")
        self.task._set_observation("on_field", self.logic.SlotObservation(
            0, self.logic.SlotState.UNKNOWN, evidence="pending_drag"))
        after = self.task._observe_slot("on_field", 0)
        self.assertEqual(after.state, self.logic.SlotState.UNKNOWN)

    def test_conflicting_name_invalidates_empty_baseline(self):
        self.task.update_max_team_size()
        self.operator.ocr_results = [([], "未识别角色", 0.999)]
        self.task._vision.slot_is_empty = Mock(return_value=None)
        self.assertEqual(self.task._observe_slot("on_field", 0).state,
                         self.logic.SlotState.UNKNOWN)

    def test_reported_starting_hand_deploys_and_is_confirmed_before_battle(self):
        self.task.load_strategy(str(ROOT / "tasks/currency_wars/strategies/"
                                    "silver_wolf_lv999_aha_time_stop.json"))
        occupants = {area: [None] * len(getattr(self.task, area + "_area"))
                     for area in self.task._observations}
        for i, name in zip((2, 3, 4, 5), ("三月七", "黑塔", "真理医生", "阿格莱雅")):
            occupants["in_hand"][i] = self.characters.Characters.get_character(name)

        def observe(area, index, **kwargs):
            char = occupants[area][index]
            return self.logic.SlotObservation(
                index, self.logic.SlotState.KNOWN if char else self.logic.SlotState.EMPTY,
                character=char, occupied=bool(char), evidence="name_match" if char else "empty_detector",
                stars=1 if char else None)

        for i in range(9):
            self.task._set_observation("in_hand", observe("in_hand", i))
        positions = {point: (area, i) for area in occupants
                     for i, point in enumerate(getattr(self.task, area + "_area"))}

        def drag(x, y, tx, ty, **kwargs):
            self.operator.record("drag", x, y, tx, ty)
            source_area, si = positions[x, y]
            target_area, ti = positions[tx, ty]
            occupants[source_area][si], occupants[target_area][ti] = (
                occupants[target_area][ti], occupants[source_area][si])
            return True

        self.operator.drag_to = drag
        self.task._observe_slot = Mock(side_effect=observe)
        self.task.handle_special_event = Mock()
        self.task.update_max_team_size()
        self.assertTrue(self.task.place_character())
        self.assertEqual(len(self.operator.drags()), 3)
        self.assertEqual(self.task.current_team_size, 3)
        self.assertEqual({c.name for c in self.task._confirmed_frontline()}, {"黑塔", "真理医生"})
        self.assertEqual([c.name for c in self.task.off_field_character if c], ["三月七"])
        self.assertTrue(self.task._ensure_battle_roster())
        self.assertFalse(self.task._placement_pending)


if __name__ == "__main__":
    unittest.main()
