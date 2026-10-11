"""Purchase cache reuse against independently mutated physical board state."""

from dataclasses import replace
import unittest
from unittest.mock import Mock

import test_currency_wars_page_purchase as fixture


class ScanCacheTests(unittest.TestCase):
    setUp = fixture.PagePurchaseTests.setUp
    configure = fixture.PagePurchaseTests.configure
    configure_page = fixture.PagePurchaseTests.configure_page
    character = fixture.PagePurchaseTests.character
    observe = fixture.PagePurchaseTests.observe
    empty_board = fixture.PagePurchaseTests.empty_board
    shop = fixture.PagePurchaseTests.shop
    card = fixture.PagePurchaseTests.card
    add_physical_copy = fixture.PagePurchaseTests.add_physical_copy
    install_game = fixture.PagePurchaseTests.install_game

    def prepare_purchase(self, *, bench_names=("景元", "翡翠", "符玄"), bought="花火"):
        self.configure_page()
        for index, name in enumerate(bench_names):
            self.observe("in_hand", index, self.character(name), stars=2)
        self.install_game([[]])
        self.task._shopping_active = True
        self.before = {area: tuple(slots) for area, slots in self.task._observations.items()}
        self.task._purchase_scan_baseline = (self.task._layout_revision, self.before)
        self.task._vision.read_empty_slots = Mock(side_effect=lambda area, positions:
            {index: slot.state == self.logic.SlotState.EMPTY
             for index, slot in enumerate(self.physical[area])})
        self.add_physical_copy(self.character(bought))
        self.task._bench_dirty = True
        self.task._purchase_pending_names.add(bought)
        self.task._invalidate_character_evidence(bought, "page_purchase_or_merge", level_changed=False)
        return {bought}

    def reads(self, area="in_hand"):
        return [event[2] for event in self.events if event[:2] == ("read", area)]

    def assert_scopes_cleared(self):
        self.assertIsNone(self.task._purchase_scan_baseline)
        self.assertIsNone(self.task._bench_scan_overrides)

    def test_one_new_copy_reads_one_identity_instead_of_nine(self):
        names = self.prepare_purchase()

        self.assertTrue(self.task._recheck_purchased_characters(names))

        self.assertEqual(self.reads(), [3])
        self.assertEqual(self.reads("on_field") + self.reads("off_field"), [])
        for index in range(3):
            self.assertIs(self.task._observations["in_hand"][index], self.before["in_hand"][index])
        self.assertEqual(self.task._observations["in_hand"][3].character.name, "花火")
        self.task._vision.read_empty_slots.assert_called_once()
        self.assert_scopes_cleared()

    def test_ordinary_forced_scan_skips_empty_slots_but_reads_occupied_identities(self):
        self.prepare_purchase()
        self.task._purchase_scan_baseline = None

        self.task.get_in_hand_area(True)

        self.assertEqual(self.reads(), [0, 1, 2, 3])
        self.assertIsNone(self.task._bench_scan_overrides)

    def test_nonforced_complete_known_cache_does_not_add_screenshot_work(self):
        self.prepare_purchase()
        for index in range(9):
            self.observe("in_hand", index, self.character("景元"), stars=1)

        self.task.get_in_hand_area()

        self.assertEqual(self.reads(), [])
        self.task._vision.read_empty_slots.assert_not_called()

    def test_broken_batch_detector_falls_back_to_identity_reads(self):
        names = self.prepare_purchase()
        self.task._vision.read_empty_slots.side_effect = RuntimeError("capture unavailable")

        self.assertTrue(self.task._recheck_purchased_characters(names))

        self.assertEqual(self.reads(), list(range(3, 9)))
        self.assert_scopes_cleared()

    def test_unavailable_empty_detector_only_reuses_confirmed_unrelated_names(self):
        names = self.prepare_purchase()
        self.task._vision.read_empty_slots.return_value = dict.fromkeys(range(9))
        self.task._vision.read_empty_slots.side_effect = None

        self.assertTrue(self.task._recheck_purchased_characters(names))

        self.assertEqual(self.reads(), list(range(3, 9)))
        self.assert_scopes_cleared()

    def test_dirty_unrelated_character_is_read_even_when_old_identity_looks_complete(self):
        names = self.prepare_purchase()
        self.task._dirty_slots.add(("in_hand", 1))

        self.assertTrue(self.task._recheck_purchased_characters(names))

        self.assertEqual(self.reads(), [1, 3])

    def test_missing_old_stars_or_identity_cannot_be_reused(self):
        names = self.prepare_purchase()
        self.task._observations["in_hand"][0] = replace(self.before["in_hand"][0], stars=None)
        self.task._observations["in_hand"][1] = replace(self.before["in_hand"][1],
            state=self.logic.SlotState.UNKNOWN)
        self.task._purchase_scan_baseline = (self.task._layout_revision,
            {area: tuple(slots) for area, slots in self.task._observations.items()})

        self.assertTrue(self.task._recheck_purchased_characters(names))

        self.assertEqual(self.reads(), [0, 1, 3])

    def test_changed_unrelated_observation_invalidates_the_purchase_baseline(self):
        names = self.prepare_purchase()
        self.task._observations["in_hand"][1] = replace(self.before["in_hand"][1], revision=99)

        self.assertTrue(self.task._recheck_purchased_characters(names))

        self.assertEqual(self.reads(), list(range(9)))
        self.assertEqual(len(self.reads("on_field")), len(self.task.on_field_area))

    def test_layout_move_and_event_changes_force_complete_reads(self):
        for change in ("layout", "move", "event", "runtime_event"):
            with self.subTest(change=change):
                names = self.prepare_purchase()
                if change == "layout":
                    self.task._layout_revision += 1
                elif change == "move":
                    self.task._pending_move = {"source": 1}
                elif change == "event":
                    self.task._form_change_pending["花火"] = 2
                else:
                    self.task._runtime_node_pending = "event"
                self.assertTrue(self.task._recheck_purchased_characters(names))
                self.assertEqual(self.reads(), list(range(9)))
                self.assert_scopes_cleared()
                self.task._pending_move = None
                self.task._form_change_pending.clear()
                self.task._runtime_node_pending = None

    def test_unrelated_slot_disappearing_forces_full_read_without_reuse(self):
        names = self.prepare_purchase()
        self.physical["in_hand"][0] = self.logic.SlotObservation(0, self.logic.SlotState.EMPTY,
                                                              occupied=False, evidence="physical removal")

        self.assertTrue(self.task._recheck_purchased_characters(names))

        self.assertEqual(self.reads(), list(range(9)))
        self.assertEqual(self.task._observations["in_hand"][0].state, self.logic.SlotState.EMPTY)

    def test_new_unrelated_identity_triggers_full_second_pass(self):
        names = self.prepare_purchase()
        self.add_physical_copy(self.character("三月七"))

        self.assertTrue(self.task._recheck_purchased_characters(names))

        self.assertEqual(self.reads(), [3, 4] + list(range(9)))
        self.assertEqual(self.task.get_in_hand_area.call_count, 2)
        self.assert_scopes_cleared()

    def test_merged_field_name_and_consumed_bench_copies_are_refreshed(self):
        self.configure_page()
        flower = self.character("花火")
        self.observe("off_field", 0, flower, stars=1)
        self.observe("in_hand", 0, flower, stars=1)
        self.observe("in_hand", 1, self.character("景元"), stars=2)
        self.install_game([[]])
        self.task._shopping_active = True
        self.task._purchase_scan_baseline = (self.task._layout_revision,
            {area: tuple(slots) for area, slots in self.task._observations.items()})
        self.task._vision.read_empty_slots = Mock(side_effect=lambda area, positions:
            {index: slot.state == self.logic.SlotState.EMPTY
             for index, slot in enumerate(self.physical[area])})
        self.add_physical_copy(flower)
        self.task._bench_dirty = True
        self.task._invalidate_character_evidence(flower.name, "page_purchase_or_merge", level_changed=False)

        self.assertTrue(self.task._recheck_purchased_characters({flower.name}))

        self.assertEqual(self.reads(), [])
        self.assertEqual(self.reads("off_field"), [0])
        self.assertEqual(self.task._observations["off_field"][0].stars, 2)
        self.assertEqual(self.task._held_purchase_copies(flower.name), 3)
        self.assert_scopes_cleared()

    def test_incomplete_stars_retry_full_read_and_preserve_pending_if_unresolved(self):
        names = self.prepare_purchase()
        read_slot = self.task._observe_slot.side_effect

        def missing_stars(area, index, *args, **kwargs):
            obs = read_slot(area, index, *args, **kwargs)
            return replace(obs, stars=None) if obs.character is not None and obs.character.name in names else obs

        self.task._observe_slot.side_effect = missing_stars

        self.assertFalse(self.task._recheck_purchased_characters(names))

        self.assertEqual(self.reads(), [3] + list(range(9)))
        self.assertTrue(names <= self.task._purchase_pending_names)
        self.assert_scopes_cleared()

    def prepare_settlement(self, *, second_copy_exists):
        self.prepare_purchase()
        name = "花火"
        if second_copy_exists:
            self.add_physical_copy(self.character(name))
            physical_empty = self.task._vision.read_empty_slots.side_effect

            def hide_second_landing(area, positions):
                # Simulate an initially incorrect vacancy read without changing
                # physical holdings. Complete fallback must read the real slot.
                empty = physical_empty(area, positions)
                empty[4] = True
                return empty

            self.task._vision.read_empty_slots.side_effect = hide_second_landing
        cycle = {"baseline": self.task._purchase_scan_baseline,
                 "receipts": {name: 2}, "before": {name: 0},
                 "transformed": set(), "roles": {}}
        progress = {"purchases": 0, "result": self.logic.ActionResult.CONFIRMED,
                    "reason": "", "closed": False, "coins": None}
        self.task.sell_character = Mock(return_value=self.logic.SellResult(self.logic.ActionResult.CONFIRMED))
        return cycle, progress

    def test_settlement_recovers_incomplete_copy_count_with_one_full_scan(self):
        cycle, progress = self.prepare_settlement(second_copy_exists=True)

        self.task._settle_demand_purchases(cycle, progress)

        self.assertEqual(progress["result"], self.logic.ActionResult.CONFIRMED)
        self.assertEqual(progress["purchases"], 2)
        self.assertEqual(self.task._held_purchase_copies("花火"), 2)
        self.assertEqual(self.task._recheck_purchased_characters.call_count, 2)
        self.assertEqual(self.reads(), [3] + list(range(9)))
        self.assertEqual(len(self.reads("on_field")), len(self.task.on_field_area))
        self.assertEqual(len(self.reads("off_field")), len(self.task.off_field_area))
        # Targeted recheck and its one full fallback both authenticate locked slots.
        self.assertEqual(self.task._vision.read_empty_slots.call_count, 2)
        self.task.place_character.assert_called_once()
        self.task.sell_character.assert_called_once()
        self.assertEqual(cycle, {})
        self.assert_scopes_cleared()

    def test_settlement_still_short_after_one_full_scan_does_not_place_or_sell(self):
        cycle, progress = self.prepare_settlement(second_copy_exists=False)

        self.task._settle_demand_purchases(cycle, progress)

        self.assertEqual(progress["result"], self.logic.ActionResult.INDETERMINATE)
        self.assertEqual(progress["reason"], "purchase_recheck_unknown")
        self.assertEqual(progress["purchases"], 0)
        self.assertEqual(self.task._recheck_purchased_characters.call_count, 2)
        self.assertEqual(self.reads(), [3] + list(range(9)))
        self.assertEqual(len(self.reads("on_field")), len(self.task.on_field_area))
        self.assertEqual(len(self.reads("off_field")), len(self.task.off_field_area))
        self.task.place_character.assert_not_called()
        self.task.sell_character.assert_not_called()
        self.assertEqual(cycle["receipts"], {"花火": 2})
        self.assertIn("花火", self.task._purchase_pending_names)
        self.assert_scopes_cleared()

    def test_stop_during_empty_detection_drops_cache_without_cleanup_inputs(self):
        names = self.prepare_purchase()

        def stop(area, positions):
            self.operator.stop_event.set()
            return dict.fromkeys(range(9), True)

        self.task._vision.read_empty_slots.side_effect = stop
        count = len(self.operator.calls)
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task._recheck_purchased_characters(names)
        self.assertEqual(len(self.operator.calls), count)
        self.assertEqual(self.reads(), [])
        self.assert_scopes_cleared()


if __name__ == "__main__":
    unittest.main()
