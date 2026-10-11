"""Readiness before shopping reuses bounded board recovery without shop input."""

from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import test_currency_wars_flow as fixture


class ShoppingObservationTests(unittest.TestCase):
    character = fixture.CurrencyWarsFlowTests.character
    observe = fixture.CurrencyWarsFlowTests.observe
    empty_board = fixture.CurrencyWarsFlowTests.empty_board

    def setUp(self):
        fixture.CurrencyWarsFlowTests.setUp(self)
        self.empty_board()
        self.task.economy_config = SimpleNamespace()
        self.task._layout_valid = True
        self.task._bench_dirty = False
        self.task._dirty_slots.clear()
        self.physical = {area: list(slots) for area, slots in self.task._observations.items()}
        self.task._observe_slot = Mock(side_effect=lambda area, index, **kwargs: self.physical[area][index])
        self.task.get_in_hand_area = Mock(side_effect=self.read_bench)
        self.task.refresh_backend_character = Mock(side_effect=self.read_layout)
        self.task.refresh_character = Mock()
        self.task._resume_shopping_after = Mock(wraps=self.task._resume_shopping_after)

    def read_bench(self, force):
        for obs in self.physical["in_hand"]:
            self.task._set_observation("in_hand", obs)
        self.task._bench_dirty = False

    def read_layout(self, **kwargs):
        self.task._layout_valid = True

    def assert_no_shop_actions(self):
        self.assertEqual(self.operator.keys(), [])
        self.assertEqual(self.operator.drags(), [])
        self.assertTrue(all(call.args == (False,) for call in self.task._set_shop_open.call_args_list))

    def test_known_board_does_not_scan_or_consume_recovery(self):
        self.observe("off_field", 0, self.character("花火"), stars=2)
        self.task._economy_recovery_attempts = 1
        self.assertTrue(self.task._ensure_shopping_observations())
        self.assertEqual(self.task._economy_recovery_attempts, 1)
        self.task._resume_shopping_after.assert_not_called()
        self.task._observe_slot.assert_not_called()
        self.task.get_in_hand_area.assert_not_called()
        self.task.refresh_character.assert_not_called()
        self.task.refresh_backend_character.assert_not_called()
        self.task._set_shop_open.assert_not_called()

    def test_missing_first_main_does_not_block_known_empty_board(self):
        self.task.main_c = self.character("银狼LV.999").name
        self.task.main_c_first_fielded_confirmed = False
        self.assertTrue(self.task._ensure_shopping_observations())
        self.task._resume_shopping_after.assert_not_called()

    def test_legacy_economy_does_not_add_new_recovery(self):
        self.task.economy_config = None
        self.task._layout_valid = False
        self.task._bench_dirty = True
        self.assertTrue(self.task._ensure_shopping_observations())
        self.task._resume_shopping_after.assert_not_called()

    def test_layout_is_recovered_before_dirty_field_reads(self):
        self.task._layout_valid = False
        self.task._dirty_slots.add(("off_field", 0))
        events = []
        self.task.refresh_backend_character.side_effect = lambda **kwargs: (
            events.append("layout"), self.read_layout(**kwargs))
        self.task._observe_slot.side_effect = lambda area, index, **kwargs: (
            events.append("slot"), self.physical[area][index])[1]
        self.assertTrue(self.task._ensure_shopping_observations())
        self.assertEqual(events, ["layout", "slot"])
        self.task.refresh_backend_character.assert_called_once_with(equip=False, recover_layout=True)
        self.assert_no_shop_actions()

    def test_unknown_or_stale_field_identity_is_recovered_only_at_affected_slot(self):
        for state, evidence in ((self.logic.SlotState.UNKNOWN, "observation_error"),
                                (self.logic.SlotState.EMPTY, "stale")):
            with self.subTest(state=state, evidence=evidence):
                self.task._economy_recovery_attempts = 0
                self.task._observe_slot.reset_mock()
                self.task._observations["off_field"][2] = self.logic.SlotObservation(
                    2, state, occupied=None, evidence=evidence)
                self.assertTrue(self.task._ensure_shopping_observations())
                self.task._observe_slot.assert_called_once_with(
                    "off_field", 2, count_stars=True, use_backup_ocr=True)
                self.assertEqual(self.task._economy_recovery_attempts, 1)
                self.task.get_in_hand_area.assert_not_called()
                self.task.refresh_character.assert_not_called()

    def test_known_field_with_unknown_star_is_recovered_before_shopping(self):
        obs = self.observe("on_field", 0, self.character("火花"), stars=None)
        self.physical["on_field"][0] = replace(obs, stars=2)
        self.assertTrue(self.task._ensure_shopping_observations())
        self.task._observe_slot.assert_called_once_with(
            "on_field", 0, count_stars=True, use_backup_ocr=False)
        self.assertEqual(self.task._observations["on_field"][0].stars, 2)
        self.task.get_in_hand_area.assert_not_called()
        self.assert_no_shop_actions()

    def test_known_npc_without_stars_does_not_force_recovery(self):
        npc = SimpleNamespace(name="可靠NPC", is_npc=True)
        self.observe("on_field", 0, npc, stars=None)
        self.assertTrue(self.task._ensure_shopping_observations())
        self.task._resume_shopping_after.assert_not_called()

    def test_bench_dirty_unknown_identity_or_unknown_star_force_one_bench_read(self):
        for reason in ("dirty", "unknown", "star", "stale", "dirty_slot"):
            with self.subTest(reason=reason):
                self.task._economy_recovery_attempts = 0
                self.task.get_in_hand_area.reset_mock()
                if reason == "dirty":
                    self.task._bench_dirty = True
                elif reason == "unknown":
                    self.observe("in_hand", 0, state=self.logic.SlotState.UNKNOWN)
                elif reason == "star":
                    self.observe("in_hand", 0, self.character("花火"), stars=None)
                elif reason == "stale":
                    self.task._observations["in_hand"][0] = replace(
                        self.physical["in_hand"][0], evidence="stale")
                else:
                    self.task._dirty_slots.add(("in_hand", 0))
                self.assertTrue(self.task._ensure_shopping_observations())
                self.task.get_in_hand_area.assert_called_once_with(True)
                self.task._observe_slot.assert_not_called()
                self.assertFalse(self.task._bench_dirty)
                self.assertEqual(self.task._dirty_slots, set())

    def test_recovery_can_need_two_reads_but_does_not_refresh_known_slots(self):
        unknown = self.observe("on_field", 0, state=self.logic.SlotState.UNKNOWN)
        self.task._observe_slot.side_effect = [unknown, self.physical["on_field"][0]]
        self.assertTrue(self.task._ensure_shopping_observations())
        self.assertEqual(self.task._observe_slot.call_count, 2)
        self.assertEqual(self.task._economy_recovery_attempts, 2)
        self.task.refresh_character.assert_not_called()
        self.task.get_in_hand_area.assert_not_called()

    def test_exhausted_recovery_stops_without_replenishing_shop_or_preparation_budget(self):
        self.task._economy_recovery_attempts = 1
        self.task.preparation_budget["recoveries"] = 2
        self.task._preparation_shop_counts = {"refreshes": 6, "purchases": 2, "experiences": 3, "actions": 11}
        expected_counts = dict(self.task._preparation_shop_counts)
        self.task._preparation_deadline = 12345
        self.task._all_in_budget = 53
        unknown = self.observe("on_field", 0, state=self.logic.SlotState.UNKNOWN)
        self.task._observe_slot.side_effect = None
        self.task._observe_slot.return_value = unknown
        with self.assertRaisesRegex(RuntimeError, "购物证据恢复无进展"):
            self.task._ensure_shopping_observations()
        self.assertEqual(self.task._economy_recovery_attempts, 2)
        self.assertEqual(self.task._observe_slot.call_count, 1)
        self.assertEqual(self.task._preparation_shop_counts, expected_counts)
        self.assertEqual(self.task._preparation_deadline, 12345)
        self.assertEqual(self.task._all_in_budget, 53)
        self.assert_no_shop_actions()

    def test_layout_failure_is_bounded_without_reading_invalid_coordinates(self):
        self.task._layout_valid = False
        self.task.refresh_backend_character.side_effect = None
        with self.assertRaisesRegex(RuntimeError, "购物证据恢复无进展"):
            self.task._ensure_shopping_observations()
        self.assertEqual(self.task.refresh_backend_character.call_count, self.task.preparation_budget["recoveries"])
        self.task._observe_slot.assert_not_called()
        self.task.get_in_hand_area.assert_not_called()
        self.assert_no_shop_actions()

    def test_stop_is_respected_before_recovery_input(self):
        self.task._bench_dirty = True
        self.operator.stop_event.set()
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task._ensure_shopping_observations()
        self.task._resume_shopping_after.assert_not_called()
        self.task._set_shop_open.assert_not_called()


if __name__ == "__main__":
    unittest.main()
