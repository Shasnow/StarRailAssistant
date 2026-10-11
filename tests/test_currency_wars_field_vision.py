"""Reviewed real field replays plus explicitly synthetic rejection controls.

Synthetic edits below test false positives; none are calibration assets.
Published templates are checksum-audited; private full-frame replays are optional.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from PIL import Image, ImageStat

from tests.currency_wars_replays import REPLAY_ROOT, open_rgb

ROOT = Path(__file__).resolve().parents[1]
CALIBRATION = ROOT / "tasks/currency_wars/calibration"
DIAG = REPLAY_ROOT / "field"
RUN_A = DIAG / "a"
RUN_B = DIAG / "b"
_spec = importlib.util.spec_from_file_location("_currency_wars_field_vision", ROOT / "tasks/currency_wars/vision.py")
vision = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = vision
_spec.loader.exec_module(vision)

EMPTY_FRAME = DIAG / "empty.png"
OCCUPIED_FRAME = DIAG / "occupied.png"
FAILURE_FRAME = DIAG / "preparation_blocked.png"

ALL_EMPTY = [DIAG / f"empty_{index:02d}.png" for index in range(1, 9)]
MIXED = [DIAG / f"mixed_{index:02d}.png" for index in range(1, 11)]


def read_frame(path):
    return open_rgb(path)


class ReplayOperator:
    def __init__(self, frames):
        self.frames = list(frames)
        self.last = self.frames[0]
        self.captures = 0
        self.stop_event = threading.Event()
        self.stop_after_sleep = False

    def screenshot(self):
        self.captures += 1
        if self.frames:
            self.last = self.frames.pop(0)
        return self.last.copy()

    def sleep(self, seconds):
        if self.stop_after_sleep:
            self.stop_event.set()


class FieldVisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = json.loads((CALIBRATION / "field_profile.json").read_text(encoding="utf8"))
        cls.profile = vision.validate_field_profile(cls.raw, CALIBRATION)

    def detector(self, *frames, profile_path=None):
        operator = ReplayOperator(frames)
        task = vision.CurrencyWarsVision(operator, profile_path or CALIBRATION / "profile.json",
                                         REPLAY_ROOT / "unused-field-samples", max_samples=0)
        return task

    def test_every_shipped_field_template_matches_its_manifest_checksum(self):
        checked = set()
        for slot in self.raw["slots"]:
            for label in ("empty", "occupied"):
                for sample in slot[label]:
                    if sample["path"] in checked:
                        continue
                    checked.add(sample["path"])
                    path = CALIBRATION / sample["path"]
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), sample["sha256"])
                    actual = read_frame(path)
                    self.assertGreater(actual.width, 0)
                    self.assertGreater(actual.height, 0)
        self.assertEqual(len(checked), 36)

    def test_held_out_failure_frame_confirms_all_seven_empty_slots(self):
        detector = self.detector(read_frame(FAILURE_FRAME))
        for key,slot in self.profile.slots.items():
            with self.subTest(slot=key):
                answer = detector.slot_is_empty(*key, slot.position)
                if key in (("on_field",0),("on_field",1),("off_field",0)):
                    self.assertIsNot(answer, True)
                else:
                    self.assertIs(answer, True)
                    self.assertEqual(detector.last_slot_reason, "two_empty_frames")

    def test_all_reviewed_real_frames_have_no_occupied_false_empty_or_empty_misses(self):
        # 18 frames / 180 slot observations; 13 frames are not training inputs.
        for path in ALL_EMPTY + MIXED:
            detector = self.detector(read_frame(path))
            for key,slot in self.profile.slots.items():
                with self.subTest(frame=path.name, slot=key):
                    answer = detector.slot_is_empty(*key, slot.position)
                    occupied = path in MIXED and key in (("on_field",0),("on_field",1),("off_field",0))
                    if occupied:
                        self.assertIsNot(answer, True)
                    else:
                        self.assertIs(answer, True)

    def test_fixed_anchor_tolerates_contour_jitter_but_rejects_wrong_layout_positions(self):
        frame = read_frame(FAILURE_FRAME)
        for index in range(1,6):
            slot = self.profile.slots[("off_field",index)]
            jitter = (slot.position[0]+.001, slot.position[1]-.001)
            self.assertIs(self.detector(frame).slot_is_empty("off_field",index,jitter), True)
            wrong = (slot.position[0]+.0021, slot.position[1])
            detector = self.detector(frame)
            self.assertIsNone(detector.slot_is_empty("off_field",index,wrong))
            self.assertEqual(detector.last_slot_reason, "uncalibrated_slot")
            self.assertEqual(detector.operator.captures, 0)

    def test_five_slot_backend_remains_explicitly_uncalibrated(self):
        detector = self.detector(Image.new("RGB", (1920, 1080)))
        for index,x in enumerate((.352,.426,.5,.574,.648)):
            self.assertIsNone(detector.slot_is_empty("off_field",index,(x,.62)))
            self.assertEqual(detector.last_slot_reason,"uncalibrated_slot")
        self.assertEqual(detector.operator.captures,0)

    def test_one_empty_frame_cannot_override_conflicting_occupied_frame(self):
        detector = self.detector(read_frame(EMPTY_FRAME),read_frame(OCCUPIED_FRAME))
        slot = self.profile.slots[("on_field",0)]
        self.assertIsNone(detector.slot_is_empty("on_field",0,slot.position))
        self.assertEqual(detector.last_slot_reason,"conflicting_slot_frames")
        self.assertEqual(detector.operator.captures,2)

    def test_changed_window_size_is_unknown_before_classification(self):
        detector = self.detector(Image.new("RGB", (1920, 1080)).resize((1280,720)))
        slot = self.profile.slots[("on_field",0)]
        self.assertIsNone(detector.slot_is_empty("on_field",0,slot.position))
        self.assertEqual(detector.last_slot_reason,"window_profile_mismatch")

    def test_flat_similar_blue_is_rejected_despite_small_rgb_distance(self):
        for slot in self.profile.slots.values():
            template = slot.empty_images[1]
            color = tuple(round(v) for v in ImageStat.Stat(template).mean)
            flat = Image.new("RGB",template.size,color)
            self.assertLess(vision.image_distance(flat,template),slot.max_mae)
            self.assertIsNone(vision.CurrencyWarsVision._classify(flat,slot))

    def test_partial_glyph_occlusion_and_unrelated_blue_scenery_are_not_empty(self):
        scenery = Image.new("RGB", (52, 106), (35, 65, 110))
        for slot in self.profile.slots.values():
            self.assertIsNot(vision.CurrencyWarsVision._classify(scenery,slot),True)
            # Synthetic negative: remove the emblem's lower half, retaining
            # the upper real pixels. This is not a deployed training image.
            template = slot.empty_images[1].copy()
            color = tuple(round(v) for v in ImageStat.Stat(template).mean)
            template.paste(color,(0,template.height//2,template.width,template.height))
            self.assertIsNone(vision.CurrencyWarsVision._classify(template,slot))

    def test_other_pages_and_open_shop_frames_never_authenticate_closed_field_slots(self):
        paths = [DIAG/"battle_entry_timeout.png",
                 DIAG/"battle_entry_timeout.png",
                 RUN_B/"unknown_battle_screen.png",
                 REPLAY_ROOT / "bench_shop_training/empty_client.png",
                 REPLAY_ROOT / "bench_shop_holdouts/03_shop_occupied_client.png"]
        for path in paths:
            detector = self.detector(read_frame(path))
            for key,slot in self.profile.slots.items():
                with self.subTest(frame=path.name,slot=key):
                    self.assertIsNot(detector.slot_is_empty(*key,slot.position),True)

    def test_missing_field_profile_is_explicit_and_reason_does_not_leak(self):
        with tempfile.TemporaryDirectory() as directory:
            detector = self.detector(Image.new("RGB", (1920, 1080)),profile_path=Path(directory)/"profile.json")
            self.assertIsNone(detector.slot_is_empty("on_field",0,(.386,.365)))
            self.assertEqual(detector.last_slot_reason,"field_profile_missing")
            self.assertIsNone(detector.slot_is_empty("in_hand",0,(.229,.844)))
            self.assertEqual(detector.last_slot_reason,"empty_profile_missing")

    def test_stop_between_frames_preserves_cancellation_and_avoids_second_capture(self):
        detector = self.detector(Image.new("RGB", (1920, 1080)))
        detector.operator.stop_after_sleep = True
        slot = self.profile.slots[("on_field",0)]
        # Classification has independent template tests; this case exercises
        # cancellation after an accepted first frame, without private pixels.
        with patch.object(detector, "_classify", return_value=True), self.assertRaises(vision.VisionStoppedError):
            detector.slot_is_empty("on_field",0,slot.position)
        self.assertEqual(detector.operator.captures,1)


if __name__ == "__main__":
    unittest.main()
