"""Replay reviewed seven-slot support layouts; synthetic edits are rejection controls."""

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

from PIL import Image

import test_currency_wars_flow as fixture


from tests.currency_wars_replays import REPLAY_ROOT, require_frames

ROOT = Path(__file__).resolve().parents[1]
CALIBRATION = ROOT / "tasks/currency_wars/calibration"
SESSION = REPLAY_ROOT / "locked_backend_support"
FRAMES = (
    SESSION / "preparation_blocked_a.png",
    SESSION / "preparation_blocked_b.png",
)
ORDINARY = ((462, 599, 144, 141), (606, 599, 139, 141), (751, 599, 133, 141),
            (895, 599, 130, 141), (1036, 599, 133, 141), (1175, 599, 139, 141))
SUPPORT = (1316, 601, 139, 133)


def boxes(rectangles=ORDINARY):
    return [fixture.FakeBox(*values) for values in rectangles]


class LockedBackendSupportTests(unittest.TestCase):
    setUp = fixture.CurrencyWarsFlowTests.setUp
    character = fixture.CurrencyWarsFlowTests.character
    observe = fixture.CurrencyWarsFlowTests.observe
    empty_board = fixture.CurrencyWarsFlowTests.empty_board

    def real_frame(self, index=0):
        if not FRAMES[index].exists():
            self.skipTest("Reviewed user snapshot unavailable in this checkout")
        with Image.open(FRAMES[index]) as frame:
            return frame.convert("RGB").copy()

    def require_opencv(self):
        try:
            import cv2
        except ImportError:
            self.skipTest("Optional OpenCV dependency unavailable")
        if not hasattr(cv2, "Canny"):
            self.skipTest("Optional OpenCV dependency unavailable")

    def vision(self):
        self.task._vision.profile_path = CALIBRATION / "profile.json"
        return self.task._vision

    def test_seven_actual_borders_pass_geometry_and_missing_edges_still_fail(self):
        seven = boxes(ORDINARY + (SUPPORT,))
        complete = self.module.validate_backend_layout(seven, (1920, 1080))
        self.assertTrue(complete.valid, complete.reason)
        self.assertEqual(len(complete.positions), 7)
        # Geometry never grants protected occupancy by itself.
        self.assertEqual(complete.protected_slots, ())
        for partial in (seven[:-1], seven[1:]):
            self.assertEqual(self.module.validate_backend_layout(partial, (1920, 1080)).reason,
                             "row_boundary_incomplete")

    def test_six_left_shifted_boxes_only_propose_a_real_border_search(self):
        probes = self.module.backend_rectangle_candidates.__globals__["backend_probe_positions"](
            boxes(), (1920, 1080))
        self.assertEqual(len(probes), 7)
        self.assertFalse(self.module.validate_backend_layout(boxes(), (1920, 1080)).valid)
        self.assertFalse(self.module.revalidate_backend_layout(
            boxes(), (1920, 1080), previous_positions=probes).valid)

    def test_shipped_locked_support_templates_have_valid_checksums(self):
        raw = json.loads((CALIBRATION / "field_profile_locked_support.json").read_text(encoding="utf8"))
        support = json.loads((CALIBRATION / "backend_locked_support.json").read_text(encoding="utf8"))
        records = [entry for slot in raw["slots"] if slot["area"] == "off_field" for entry in slot["empty"]]
        records += support["templates"]
        self.assertEqual(len(records), 8)
        for entry in records:
            asset = CALIBRATION / entry["path"]
            self.assertEqual(hashlib.sha256(asset.read_bytes()).hexdigest(), entry["sha256"])
            with Image.open(asset) as image:
                self.assertGreater(image.width, 0)
                self.assertGreater(image.height, 0)

    def test_both_real_stop_frames_have_actual_seven_slot_borders(self):
        self.require_opencv()
        for index in (0, 1):
            with self.subTest(frame=index):
                frame = self.real_frame(index)
                actual = self.module.backend_rectangle_candidates(frame)
                result = self.module.validate_backend_layout(actual, frame.size)
                self.assertTrue(result.valid, result.reason)
                self.assertEqual(len(result.positions), 7)
                self.assertTrue(self.vision()._authenticated_backend_support(frame, result.positions))

    def test_normal_detector_omission_recovers_complete_protected_row_on_two_frames(self):
        self.require_opencv()
        frame = self.real_frame()
        self.operator.rectangle_detect = Mock(return_value=boxes())
        self.operator.screenshot = Mock(side_effect=lambda: frame.copy())
        result = self.vision().read_backend_layout(())
        self.assertTrue(result.valid, result.reason)
        self.assertEqual(result.protected_slots, (6,))
        self.assertEqual(self.operator.screenshot.call_count, 2)

    def test_existing_six_slot_anchors_do_not_hide_new_authenticated_support(self):
        self.require_opencv()
        frame = self.real_frame(1)
        self.operator.screenshot = Mock(side_effect=lambda: frame.copy())
        result = self.vision().read_backend_layout(tuple(self.task.off_field_area), recover=True)
        self.assertTrue(result.valid, result.reason)
        self.assertEqual(len(result.positions), 7)
        self.assertEqual(result.protected_slots, (6,))
        self.assertEqual(self.operator.screenshot.call_count, 2)

    def test_center_five_subset_cannot_hide_live_support_without_previous_anchors(self):
        frame = self.real_frame(1)
        middle = boxes(ORDINARY[1:])
        self.operator.rectangle_detect = Mock(return_value=middle)
        self.operator.screenshot = Mock(side_effect=lambda: frame.copy())
        reader = self.vision()
        api = list(reader.layout_api)
        api[1] = Mock(return_value=middle)  # Both exterior borders are unavailable.
        reader.layout_api = tuple(api)
        result = reader.read_backend_layout(())
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "backend_support_row_incomplete")

    def test_known_seven_slot_layout_cannot_downgrade_to_center_five_subset(self):
        middle = boxes(ORDINARY[1:])
        previous = self.module.validate_backend_layout(boxes(ORDINARY + (SUPPORT,)), (1920, 1080)).positions
        self.operator.rectangle_detect = Mock(return_value=middle)
        self.operator.screenshot = Mock(return_value=Image.new("RGB", (1920, 1080)))
        reader = self.vision()
        api = list(reader.layout_api)
        api[1] = Mock(return_value=middle)
        reader.layout_api = tuple(api)
        self.assertFalse(reader.read_backend_layout(previous).valid)
        self.assertFalse(reader.read_backend_layout(previous, recover=True).valid)

    def test_genuine_centered_five_slot_layout_without_support_remains_supported(self):
        middle = boxes(ORDINARY[1:])
        self.operator.rectangle_detect = Mock(return_value=middle)
        self.operator.screenshot = Mock(return_value=Image.new("RGB", (1920, 1080)))
        reader = self.vision()
        api = list(reader.layout_api)
        api[1] = Mock(return_value=middle)
        reader.layout_api = tuple(api)
        result = reader.read_backend_layout(())
        self.assertTrue(result.valid, result.reason)
        self.assertEqual(len(result.positions), 5)
        self.assertEqual(result.protected_slots, ())

    def test_support_requires_both_portrait_and_lock_evidence(self):
        frame = self.real_frame()
        positions = self.module.validate_backend_layout(boxes(ORDINARY + (SUPPORT,)), frame.size).positions
        for crop in ((1338, 622, 1427, 720), (1413, 610, 1429, 636)):
            with self.subTest(crop=crop):
                negative = frame.copy()
                negative.paste((0, 0, 0), crop)
                self.assertFalse(self.vision()._authenticated_backend_support(negative, positions))

    def test_half_pixel_contour_jitter_keeps_calibrated_crop_dimensions(self):
        frame = self.real_frame()
        positions = self.module.validate_backend_layout(boxes(ORDINARY + (SUPPORT,)), frame.size).positions
        for dx, dy in ((0.5, 0), (-0.5, 0), (0, 0.5), (0, -0.5), (0.5, 0.5)):
            with self.subTest(dx=dx, dy=dy):
                shifted = positions[:-1] + ((positions[-1][0] + dx / frame.width,
                                             positions[-1][1] + dy / frame.height),)
                self.assertTrue(self.vision()._authenticated_backend_support(frame, shifted))

    def test_support_must_still_be_authenticated_on_second_frame(self):
        self.require_opencv()
        first = self.real_frame()
        second = first.copy()
        second.paste((0, 0, 0), (1413, 610, 1429, 636))
        self.operator.rectangle_detect = Mock(return_value=boxes())
        self.operator.screenshot = Mock(side_effect=[first, second])
        result = self.vision().read_backend_layout(())
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "layout_not_stable")

    def test_erased_support_cannot_be_authenticated_from_six_empty_boxes(self):
        self.require_opencv()
        frame = self.real_frame()
        frame.paste((0, 0, 0), (1315, 599, 1461, 741))
        # Erasing with a black rectangle creates its own four visible edges.
        # Geometry cannot establish whether those edges enclose a support card;
        # require the production reader to reject its absent portrait and lock.
        self.operator.rectangle_detect = Mock(return_value=boxes())
        self.operator.screenshot = Mock(side_effect=lambda: frame.copy())
        result = self.vision().read_backend_layout(())
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "backend_support_not_authenticated")
        self.assertEqual(result.protected_slots, ())

    def test_replayed_seven_slot_layout_records_npc_without_clicking_its_panel(self):
        self.require_opencv()
        self.empty_board()
        frame = self.real_frame()
        self.operator.screenshot = Mock(side_effect=lambda: frame.copy())
        self.operator.rectangle_detect = Mock(return_value=boxes())
        self.vision()
        self.task._set_shop_open = Mock(return_value=True)
        self.task.get_off_field_area = Mock()
        self.assertTrue(self.task.refresh_backend_character(recover_layout=True))
        self.assertEqual(len(self.task.off_field_area), 7)
        self.operator.calls.clear()
        npc = self.task._observe_slot("off_field", 6, count_stars=True)
        self.assertEqual(npc.state, self.logic.SlotState.KNOWN)
        self.assertTrue(npc.occupied)
        self.assertTrue(npc.character.is_locked)
        self.assertTrue(npc.character.is_npc)
        self.assertIsNone(npc.stars)
        self.assertEqual(self.operator.calls, [])
        self.task._set_observation("off_field", npc)
        self.assertEqual(self.task.on_field_character.count(None), 4)
        self.assertEqual(self.task.current_team_size, 1)

    def test_shifted_empty_glyphs_are_calibrated_and_occupied_slot_is_not_empty(self):
        reader = self.vision()
        raw = json.loads((CALIBRATION / "field_profile_locked_support.json").read_text(encoding="utf8"))
        positions = {slot["index"]: slot["position"] for slot in raw["slots"] if slot["area"] == "off_field"}
        for frame_index in (0, 1):
            frame = self.real_frame(frame_index)
            self.operator.screenshot = Mock(side_effect=lambda: frame.copy())
            answers = reader.read_empty_slots("off_field", positions)
            self.assertTrue(all(answers[index] is True for index in range(1, 6)))
            if frame_index == 0:
                self.assertIs(answers[0], True)
            else:
                self.assertIsNot(answers[0], True)

    def test_layout_variant_never_accepts_unreviewed_slot_coordinates(self):
        frame = self.real_frame()
        self.operator.screenshot = Mock(side_effect=lambda: frame.copy())
        self.assertIsNone(self.vision().slot_is_empty("off_field", 0, (0.24, 0.62)))
        self.assertIsNone(self.vision().slot_is_empty("off_field", 6, (0.7216, 0.618)))

    def test_original_frontline_calibration_covers_both_reviewed_support_frames(self):
        reader = self.vision()
        raw = json.loads((CALIBRATION / "field_profile.json").read_text(encoding="utf8"))
        positions = {slot["index"]: slot["position"] for slot in raw["slots"] if slot["area"] == "on_field"}
        for frame_index in (0, 1):
            frame = self.real_frame(frame_index)
            self.operator.screenshot = Mock(side_effect=lambda: frame.copy())
            answers = reader.read_empty_slots("on_field", positions)
            self.assertTrue(all(answers[index] is True for index in range(1, 4)))
            if frame_index == 0:
                self.assertIs(answers[0], True)
            else:
                self.assertIsNot(answers[0], True)


if __name__ == "__main__":
    unittest.main()
