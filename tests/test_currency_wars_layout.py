"""Geometry fixtures never serve as EMPTY/occupied calibration."""

import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("_currency_wars_layout_tests", ROOT / "tasks/currency_wars/layout.py")
layout = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = layout
spec.loader.exec_module(layout)

# Production rectangle detector replay of the existing 0/3 diagnostic frame.
# These coordinates establish geometry only, not the contents of any slot.
REAL_RECTS = ((534, 599, 141, 141), (678, 599, 136, 141), (823, 599, 130, 141),
              (967, 599, 130, 141), (1106, 599, 136, 141), (1245, 599, 141, 141))


def boxes(rects=REAL_RECTS):
    return [SimpleNamespace(left=x, top=y, width=w, height=h) for x, y, w, h in rects]


class BackendLayoutTests(unittest.TestCase):
    def test_real_rectangles_are_sorted_and_report_new_layout(self):
        result = layout.validate_backend_layout(list(reversed(boxes())), (1920, 1080))
        self.assertTrue(result.valid, result.reason)
        self.assertTrue(result.changed)
        self.assertEqual(result.boxes, REAL_RECTS)
        self.assertAlmostEqual(result.positions[0][0], 604.5 / 1920)
        self.assertAlmostEqual(result.positions[0][1], 669.5 / 1080)

    def test_unchanged_layout_and_small_jitter_do_not_invalidate(self):
        first = layout.validate_backend_layout(boxes(), (1920, 1080))
        jitter = boxes(tuple((x + 1, y + 1, w, h) for x, y, w, h in REAL_RECTS))
        result = layout.validate_backend_layout(jitter, (1920, 1080), previous_positions=first.positions)
        self.assertTrue(result.valid)
        self.assertFalse(result.changed)

    def test_real_position_change_is_reported(self):
        first = layout.validate_backend_layout(boxes(), (1920, 1080))
        result = layout.validate_backend_layout(boxes(tuple((x + 8, y, w, h) for x, y, w, h in REAL_RECTS)),
                                                (1920, 1080), previous_positions=first.positions)
        self.assertTrue(result.valid)
        self.assertTrue(result.changed)

    def test_full_centered_five_slot_row_can_replace_six_geometry(self):
        first = layout.validate_backend_layout(boxes(), (1920, 1080))
        five = boxes(tuple((center - 70, 600, 140, 140) for center in (676, 818, 960, 1102, 1244)))
        result = layout.validate_backend_layout(five, (1920, 1080), previous_positions=first.positions)
        self.assertTrue(result.valid)
        self.assertTrue(result.changed)
        self.assertEqual(len(result.positions), 5)

    def test_missing_six_slot_edge_cannot_look_like_a_complete_five(self):
        for rects in (REAL_RECTS[1:], REAL_RECTS[:-1]):
            result = layout.validate_backend_layout(boxes(rects), (1920, 1080))
            self.assertFalse(result.valid)
            self.assertEqual(result.reason, "row_boundary_incomplete")
            self.assertEqual(result.positions, ())

    def test_missing_interior_slot_rejects_double_gap(self):
        result = layout.validate_backend_layout(boxes(REAL_RECTS[:2] + REAL_RECTS[3:]), (1920, 1080))
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "non_contiguous_slots")

    def test_duplicate_rectangles_and_excessive_overlap_are_rejected(self):
        for rects in (REAL_RECTS[:2] + (REAL_RECTS[1],) + REAL_RECTS[3:],
                      ((610, 600, 140, 140), (722, 600, 140, 140), (834, 600, 140, 140),
                       (946, 600, 140, 140), (1058, 600, 140, 140), (1170, 600, 140, 140))):
            result = layout.validate_backend_layout(boxes(rects), (1920, 1080))
            self.assertFalse(result.valid)
            self.assertIn(result.reason, ("duplicate_rectangles", "overlapping_rectangles"))

    def test_count_and_explicit_expected_count_are_checked(self):
        for count in (0, 1, 4, 7):
            self.assertFalse(layout.validate_backend_layout(boxes()[:count] if count < 7 else boxes() + boxes()[:1],
                                                           (1920, 1080)).valid)
        self.assertEqual(layout.validate_backend_layout(boxes(), (1920, 1080), expected_count=5).reason,
                         "unexpected_slot_count")
        self.assertEqual(layout.validate_backend_layout(boxes(), (1920, 1080), expected_count=True).reason,
                         "invalid_expected_count")

    def test_rectangle_dimensions_roi_and_row_alignment_are_checked(self):
        for changed, expected in ((SimpleNamespace(left=534, top=599, width=119, height=141), "invalid_rectangle_size"),
                                  (SimpleNamespace(left=180, top=599, width=141, height=141), "rectangle_outside_roi"),
                                  (SimpleNamespace(left=534, top=625, width=141, height=141), "rectangle_outside_roi"),
                                  (SimpleNamespace(left=534, top=610, width=141, height=141), "row_not_aligned")):
            current = boxes()
            current[0] = changed
            self.assertEqual(layout.validate_backend_layout(current, (1920, 1080)).reason, expected)

    def test_window_and_malformed_coordinates_are_rejected(self):
        for size in ((0, 1080), (1920, True), (1920, float("nan")), (1920, 1200), None):
            self.assertFalse(layout.validate_backend_layout(boxes(), size).valid)
        for bad in (None, SimpleNamespace(left=float("nan"), top=599, width=141, height=141),
                    SimpleNamespace(left=True, top=599, width=141, height=141)):
            current = boxes()
            current[0] = bad
            self.assertEqual(layout.validate_backend_layout(current, (1920, 1080)).reason, "invalid_rectangle")

    def test_supported_geometry_scales_with_window(self):
        half = boxes(tuple((x / 2, y / 2, w / 2, h / 2) for x, y, w, h in REAL_RECTS))
        scaled = layout.validate_backend_layout(half, (960, 540))
        original = layout.validate_backend_layout(boxes(), (1920, 1080))
        self.assertEqual(scaled.positions, original.positions)

    def test_invalid_historical_positions_do_not_certify_change(self):
        for previous in (None, ((0.2,),), ((float("nan"), 0.62),), ((True, 0.62),)):
            self.assertEqual(layout.validate_backend_layout(boxes(), (1920, 1080),
                                                           previous_positions=previous).reason, "invalid_previous_positions")


if __name__ == "__main__":
    unittest.main()
