"""Regression coverage for backend-only recovery and pending drag reconciliation."""
from dataclasses import replace
import unittest
from unittest.mock import Mock

import test_currency_wars_flow as fixture


class LayoutReviewTests(unittest.TestCase):
    setUp = fixture.CurrencyWarsFlowTests.setUp
    character = fixture.CurrencyWarsFlowTests.character
    observe = fixture.CurrencyWarsFlowTests.observe
    empty_board = fixture.CurrencyWarsFlowTests.empty_board

    def initialize_board(self):
        self.empty_board()
        self.observe("on_field", 0, self.character("灵砂"), stars=1)
        self.task.get_on_field_area = Mock(side_effect=AssertionError("unrelated frontline scan"))
        self.task.get_off_field_area = Mock()
        self.task.get_in_hand_area = Mock()
        self.task._vision.capture_layout_failure = Mock()
        self.task._vision.capture_sample = Mock()
        self.task._confirmed_layout_positions = tuple(self.task.off_field_area)
        self.task._field_observed_at = 123.0
        self.task._bench_dirty = False
        self.task._placement_pending = False
        self.task._dirty_slots.clear()

    def install_pending(self, source_area="in_hand"):
        source = self.observe(source_area, 0, self.character("黑塔"), stars=1)
        target = self.observe("off_field", 0)
        pending = {"source": (source_area, 0), "target": ("off_field", 0),
            "source_before": source, "target_before": target,
            "layout": self.task._layout_revision,
            "positions": (getattr(self.task, source_area + "_area")[0], self.task.off_field_area[0])}
        self.task._pending_move = pending
        self.task._placement_pending = True
        return pending

    def layout_result(self, valid=True, *, changed=False):
        return self.module.LayoutObservation(valid=valid, positions=tuple(self.task.off_field_area),
            reason="test_confirmed" if valid else "test_missing_anchor", changed=changed)

    def test_normal_backend_recovery_preserves_frontline_and_full_scan_timestamp(self):
        self.initialize_board()
        front = tuple(self.task._observations["on_field"])
        self.task._layout_valid = False
        order = []
        self.task._set_shop_open = Mock(side_effect=lambda opened: order.append("page") or True)
        self.operator.move_to = Mock(side_effect=lambda *args: order.append("cursor"))
        self.task._vision.read_backend_layout = Mock(
            side_effect=lambda *args, **kwargs: order.append("layout") or self.layout_result())

        self.assertTrue(self.task.refresh_backend_character())
        self.assertEqual(order, ["page", "cursor", "layout", "layout"])
        self.assertEqual(tuple(self.task._observations["on_field"]), front)
        self.assertEqual(self.task._field_observed_at, 123.0)
        self.task.get_on_field_area.assert_not_called()
        self.task.get_in_hand_area.assert_not_called()
        self.task.get_off_field_area.assert_called_once_with(True, equip=False)

    def test_unknown_page_never_reads_backend_or_discards_old_anchors(self):
        self.initialize_board()
        old = tuple(self.task.off_field_area)
        front = tuple(self.task._observations["on_field"])
        self.task._layout_valid = False
        self.task._set_shop_open = Mock(return_value=False)
        self.task._vision.read_backend_layout = Mock()

        self.assertFalse(self.task.refresh_backend_character(recover_layout=True))
        self.assertEqual(tuple(self.task.off_field_area), old)
        self.assertEqual(self.task._confirmed_layout_positions, old)
        self.assertEqual(tuple(self.task._observations["on_field"]), front)
        self.assertTrue(all(o.state == self.logic.SlotState.UNKNOWN
            for o in self.task._observations["off_field"]))
        self.task._vision.read_backend_layout.assert_not_called()
        self.task.get_off_field_area.assert_not_called()

    def test_pending_backend_drag_never_reads_unconfirmed_coordinates(self):
        self.initialize_board()
        pending = self.install_pending()
        self.task._layout_valid = False
        self.task._observe_slot = Mock()

        self.assertFalse(self.task._resolve_pending_move())
        self.assertIs(self.task._pending_move, pending)
        self.task._observe_slot.assert_not_called()
        self.assertEqual(self.operator.drags(), [])
        self.assertEqual(self.task._assess_preparation().reason, "backend_layout_not_confirmed")

    def test_pending_drag_recovers_layout_before_confirming_original_action(self):
        self.initialize_board()
        pending = self.install_pending()
        self.task._layout_valid = False
        source_after = replace(pending["target_before"], slot_index=0)
        target_after = replace(pending["source_before"], slot_index=0)
        order = []
        attempts = []
        def read_layout(*args, recover=False):
            order.append("layout")
            attempts.append(recover)
            return self.layout_result(valid=recover)
        self.task._vision.read_backend_layout = Mock(side_effect=read_layout)
        def observe(area, index, **kwargs):
            self.assertTrue(self.task._layout_valid)
            order.append("endpoint")
            return source_after if area == "in_hand" else target_after
        self.task._observe_slot = Mock(side_effect=observe)
        self.task._refresh_dirty_field = Mock()
        self.task.update_max_team_size = Mock()
        self.task.place_character = Mock()
        self.task._assess_preparation = Mock(return_value=self.module.PreparationResult(
            self.module.Readiness.READY, "test_ready"))

        result = self.task.prepare_for_battle()
        self.assertEqual(result.state, self.module.Readiness.READY)
        self.assertEqual(attempts, [False, True])
        self.assertEqual(order, ["layout", "layout", "endpoint", "endpoint"])
        self.assertIsNone(self.task._pending_move)
        self.assertFalse(self.task._placement_pending)
        self.task.get_on_field_area.assert_not_called()
        self.assertEqual(self.operator.drags(), [])

    def test_pending_drag_cannot_mask_terminal_layout_failure(self):
        self.initialize_board()
        pending = self.install_pending()
        self.task._layout_valid = False
        self.task._vision.read_backend_layout = Mock(return_value=self.layout_result(False))
        self.task._observe_slot = Mock()

        result = self.task.prepare_for_battle()
        self.assertEqual(result.state, self.module.Readiness.BLOCKED)
        self.assertEqual(result.blocked_reason, "backend_layout_not_confirmed")
        self.assertEqual(self.task._vision.read_backend_layout.call_count, 2)
        self.assertEqual([c.kwargs["recover"] for c in
            self.task._vision.read_backend_layout.call_args_list], [False, True])
        self.task._vision.capture_layout_failure.assert_called_with(
            "backend_layout_not_confirmed", terminal=True)
        self.assertIs(self.task._pending_move, pending)
        self.task._observe_slot.assert_not_called()
        self.assertEqual(self.operator.drags(), [])

    def test_second_unstable_frame_keeps_backend_unknown(self):
        self.initialize_board()
        self.task._layout_valid = False
        old = tuple(self.task.off_field_area)
        self.task._vision.read_backend_layout = Mock(side_effect=[
            self.layout_result(), self.layout_result(False)])

        self.assertFalse(self.task.refresh_backend_character())
        self.assertEqual(tuple(self.task.off_field_area), old)
        self.assertTrue(all(o.state == self.logic.SlotState.UNKNOWN
            for o in self.task._observations["off_field"]))
        self.task.get_off_field_area.assert_not_called()
        self.task._vision.capture_layout_failure.assert_called_once_with("layout_not_stable")

    def test_changed_backend_failure_defers_other_drag_endpoint_reads(self):
        self.initialize_board()
        pending = self.install_pending(source_area="on_field")
        self.task._layout_revision += 1
        self.task._vision.read_backend_layout = Mock(return_value=self.layout_result(False))
        self.task._observe_slot = Mock()

        self.assertFalse(self.task._resolve_pending_move())
        self.assertFalse(self.task._layout_valid)
        self.assertIs(self.task._pending_move, pending)
        self.task._observe_slot.assert_not_called()
        self.task.get_on_field_area.assert_not_called()
        self.task.get_in_hand_area.assert_not_called()
        self.assertEqual(self.operator.drags(), [])

    def test_changed_backend_reconciles_only_affected_frontline_endpoint(self):
        self.initialize_board()
        pending = self.install_pending(source_area="on_field")
        self.observe("on_field", 1, self.character("佩拉"), stars=1)
        unrelated = self.task._observations["on_field"][1]
        self.task._layout_revision += 1
        self.task._vision.read_backend_layout = Mock(return_value=self.layout_result())
        self.task._observe_slot = Mock(return_value=replace(pending["target_before"], slot_index=0))

        self.assertTrue(self.task._resolve_pending_move())
        self.task._observe_slot.assert_called_once_with("on_field", 0, count_stars=True)
        self.assertIs(self.task._observations["on_field"][1], unrelated)
        self.task.get_on_field_area.assert_not_called()
        self.task.get_in_hand_area.assert_not_called()
        self.assertIsNone(self.task._pending_move)
        self.assertEqual(self.operator.drags(), [])


if __name__ == "__main__":
    unittest.main()
