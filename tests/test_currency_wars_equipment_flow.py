"""Replay configured equipment batches through the production task class."""

import unittest
from unittest.mock import Mock

import test_currency_wars_flow as fixture


class EquipmentFlowTests(unittest.TestCase):
    character = fixture.CurrencyWarsFlowTests.character
    observe = fixture.CurrencyWarsFlowTests.observe
    empty_board = fixture.CurrencyWarsFlowTests.empty_board

    def setUp(self):
        fixture.CurrencyWarsFlowTests.setUp(self)
        self.empty_board()
        # Give the normal traversal a non-priority frontline unit first.
        self.observe("on_field", 0, self.character("缇宝"), stars=2)
        self.observe("on_field", 2, self.character("银狼LV.999"), stars=1)
        self.observe("off_field", 0, self.character("佩拉"), stars=1)
        self.task.strategy_characters = {"缇宝": 2, "银狼LV.999": 2, "佩拉": 2}
        self.task.equipment_config = self.module.parse_equipment_config({
            "priority_characters": ["银狼LV.999"],
            "others_from_round": "3-4", "interval_battles": 2,
        }, self.task._lookup_known_character)
        self.task.equipment_interval_battles = 2
        self.task._equipment_battles_since_check = 2
        self.task._preparation_round = (3, 4)
        self.task._read_preparation_round = Mock(side_effect=lambda: self.task._preparation_round)
        self.task._observe_slot = Mock(side_effect=lambda area, index, **kwargs:
                                      self.task._observations[area][index])
        self.task._equip_observation = Mock()

    def equipped_names(self):
        return [call.args[2].character.name for call in self.task._equip_observation.call_args_list]

    def test_deployed_priority_is_checked_before_frontline_and_backend_others(self):
        self.assertTrue(self.task._process_equipment())
        self.assertEqual(self.equipped_names(), ["银狼LV.999", "缇宝", "佩拉"])
        self.assertTrue(self.task._equipment_others_checked)

    def test_before_round_unlock_only_priority_receives_equipment_checks(self):
        self.task._preparation_round = (3, 3)
        self.assertTrue(self.task._process_equipment())
        self.assertEqual(self.equipped_names(), ["银狼LV.999"])
        self.assertFalse(self.task._equipment_others_checked)

    def test_unknown_round_does_not_unlock_other_equipment_checks(self):
        self.task._preparation_round = None
        self.assertTrue(self.task._process_equipment())
        self.assertEqual(self.equipped_names(), ["银狼LV.999"])
        self.assertFalse(self.task._equipment_others_checked)

    def test_round_unlock_runs_once_without_waiting_for_two_battles(self):
        self.task._preparation_round = (3, 3)
        self.task._equipment_battles_since_check = 1
        self.assertFalse(self.task._equipment_due())
        self.assertFalse(self.task._process_equipment())
        self.task._equip_observation.assert_not_called()
        self.task._preparation_round = (3, 4)
        self.assertTrue(self.task._equipment_due())
        self.assertTrue(self.task._process_equipment())
        self.assertEqual(self.equipped_names(), ["银狼LV.999", "缇宝", "佩拉"])
        self.assertEqual(self.task._equipment_battles_since_check, 0)
        self.assertTrue(self.task._equipment_others_checked)
        self.assertFalse(self.task._equipment_due())
        self.assertFalse(self.task._process_equipment())
        self.assertEqual(len(self.equipped_names()), 3)

    def test_priority_on_bench_is_not_treated_as_deployed(self):
        self.observe("on_field", 2)
        self.observe("in_hand", 0, self.character("银狼LV.999"), stars=1)
        self.assertTrue(self.task._process_equipment())
        self.assertEqual(self.equipped_names(), ["缇宝", "佩拉"])

    def test_new_game_reset_clears_unlock_but_keeps_the_strategy_policy(self):
        self.assertTrue(self.task._process_equipment())
        config = self.task.equipment_config
        self.task.reset_character()
        self.assertIs(self.task.equipment_config, config)
        self.assertFalse(self.task._equipment_others_checked)
        self.assertIsNone(self.task._preparation_round)
        self.assertEqual(self.task._equipment_battles_since_check, 0)
        self.assertFalse(self.task._equipment_due())
        self.task._preparation_round = (3, 4)
        self.assertTrue(self.task._equipment_due())

    def test_unknown_priority_after_dirty_read_defers_others_and_preserves_unlock(self):
        self.task._dirty_slots.add(("on_field", 2))
        unknown = self.logic.SlotObservation(2, self.logic.SlotState.UNKNOWN,
                                            evidence="priority_name_unreadable")
        self.task._observe_slot = Mock(return_value=unknown)
        self.assertTrue(self.task._process_equipment())
        self.task._observe_slot.assert_called_once_with("on_field", 2, count_stars=True, use_backup_ocr=False)
        self.assertEqual(self.task.on_field_character[2].name, "银狼LV.999")
        self.assertEqual(self.task._observations["on_field"][2].state, self.logic.SlotState.UNKNOWN)
        self.task._equip_observation.assert_not_called()
        self.assertFalse(self.task._equipment_others_checked)
        self.assertTrue(self.task._equipment_due())

    def test_confirmed_priority_retry_can_complete_previously_deferred_unlock(self):
        self.task._dirty_slots.add(("on_field", 2))
        confirmed = self.task._observations["on_field"][2]
        unknown = self.logic.SlotObservation(2, self.logic.SlotState.UNKNOWN,
                                            evidence="priority_name_unreadable")
        self.task._observe_slot = Mock(side_effect=[unknown, confirmed])
        self.assertTrue(self.task._process_equipment())
        self.assertFalse(self.task._equipment_others_checked)
        self.assertTrue(self.task._process_equipment())
        self.assertEqual(self.equipped_names(), ["银狼LV.999", "缇宝", "佩拉"])
        self.assertTrue(self.task._equipment_others_checked)
        self.assertFalse(self.task._equipment_due())


if __name__ == "__main__":
    unittest.main()
