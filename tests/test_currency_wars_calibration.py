"""Regression checks against user-supplied real images; no game connection.

The first batch is now held out from the later all-slots training pair.
These checks do not claim unseen-character or live-action validation.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from PIL import Image

from tests.currency_wars_replays import REPLAY_ROOT, require_frames

ROOT = Path(__file__).resolve().parents[1]
BATCH = REPLAY_ROOT / "bench_shop_holdouts"
CALIBRATION = ROOT / "tasks/currency_wars/calibration"
spec = importlib.util.spec_from_file_location("_cw_real_calibration_tests", ROOT / "tasks/currency_wars/vision.py")
vision = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = vision
spec.loader.exec_module(vision)

class ReplayOperator:
    def __init__(self, *frames):
        self.frames = list(frames)
        self.calls = 0
    def screenshot(self):
        image = self.frames[min(self.calls, len(self.frames) - 1)]
        self.calls += 1
        return image.copy()
    def sleep(self, seconds):
        pass

class RealCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_frames(*(BATCH / (name + "_client.png") for name in (
            "01_bench_right_occupied", "02_bench_right_empty", "03_shop_occupied", "04_shop_left_empty")))
        cls.frames = []
        for name in ("01_bench_right_occupied", "02_bench_right_empty",
                     "03_shop_occupied", "04_shop_left_empty"):
            with Image.open(BATCH / (name + "_client.png")) as im:
                cls.frames.append(im.convert("RGB").copy())
        cls.raw_profile = json.loads((CALIBRATION / "profile.json").read_text(encoding="utf-8"))
        cls.profile = vision.validate_profile(cls.raw_profile, CALIBRATION)

    def classify(self, area, index, frames, position=None):
        operator = ReplayOperator(*frames)
        detector = vision.CurrencyWarsVision(
            operator, CALIBRATION / "profile.json", BATCH / "unused-diagnostics", max_samples=0)
        position = position or ({"in_hand": (.749, .844), "store": (.25, .18)}[area])
        return detector.slot_is_empty(area, index, position)

    def test_held_out_bench_occupied_frame_is_not_empty(self):
        self.assertIsNot(self.classify("in_hand", 8, [self.frames[0]]), True)

    def test_held_out_bench_empty_frame_is_empty(self):
        self.assertIs(self.classify("in_hand", 8, [self.frames[1]]), True)

    def test_held_out_bench_empty_images_agree_across_two_frames(self):
        self.assertIs(self.classify("in_hand", 8, self.frames[2:4]), True)

    def test_changing_bench_occupancy_is_unknown(self):
        self.assertIsNone(self.classify("in_hand", 8, [self.frames[1], self.frames[0]]))

    def test_held_out_shop_occupied_frame_is_not_empty(self):
        self.assertIsNot(self.classify("store", 0, [self.frames[2]]), True)

    def test_held_out_shop_empty_frame_is_empty(self):
        self.assertIs(self.classify("store", 0, [self.frames[3]]), True)

    def test_closed_shop_is_not_mistaken_for_empty_shop_slot(self):
        for frame in self.frames[:2]:
            with self.subTest(frame=self.frames.index(frame)):
                self.assertIsNone(self.classify("store", 0, [frame]))

    def test_calibrated_field_and_unreviewed_backend_coordinates_are_distinguished(self):
        self.assertIs(self.classify("on_field", 0, [self.frames[1]], (.386, .365)), True)
        self.assertIsNone(self.classify("off_field", 0, [self.frames[1]], (.3056, .620)))

    def test_wrong_slot_position_and_uncalibrated_size_are_unknown(self):
        self.assertIsNone(self.classify("in_hand", 8, [self.frames[1]], (.70, .844)))
        with Image.open(BATCH / "02_bench_right_empty_original.png") as full_window:
            self.assertIsNone(self.classify("in_hand", 8, [full_window]))
        self.assertIsNone(self.classify("in_hand", 8, [self.frames[1].resize((1280, 720))]))

    def test_other_visible_portraits_are_never_classified_as_empty(self):
        hand_positions = ((.229,.844),(.297,.844),(.358,.844))
        shop_positions = ((.4,.18),(.55,.18),(.68,.18),(.8,.18))
        for area, frame, positions in (("in_hand", self.frames[0], hand_positions),
                                       ("store", self.frames[2], shop_positions)):
            slot = self.profile.slots[(area, 8 if area == "in_hand" else 0)]
            for position in positions:
                with self.subTest(area=area,position=position):
                    crop = vision.crop_slot_template(frame, position, slot.relative_box)
                    self.assertIsNot(vision.CurrencyWarsVision._classify(crop, slot), True)

    def test_original_inputs_and_unscaled_client_crops_match_manifest(self):
        manifest = json.loads((BATCH / "input_manifest.json").read_text(encoding="utf-8"))
        for entry in manifest["records"]:
            for key in ("original", "client"):
                content = (BATCH / entry[key]).read_bytes()
                self.assertEqual(hashlib.sha256(content).hexdigest(), entry[key + "_sha256"])
            with Image.open(BATCH / entry["original"]) as original, Image.open(BATCH / entry["client"]) as client:
                cropped = original.crop(tuple(entry["client_box"])).convert("RGB")
                self.assertEqual(cropped.size, client.size)
                self.assertEqual(cropped.tobytes(), client.convert("RGB").tobytes())




class ShippedCalibrationTests(unittest.TestCase):
    def test_all_bench_shop_slots_validate_with_integral_template_hashes(self):
        raw = json.loads((CALIBRATION / "profile.json").read_text(encoding="utf-8"))
        profile = vision.validate_profile(raw, CALIBRATION)
        expected = {("in_hand", i) for i in range(9)} | {("store", i) for i in range(5)}
        self.assertEqual(set(profile.slots), expected)
        self.assertEqual(raw["window_size"], [1920, 1080])
        self.assertTrue(all(slot.get("require_empty_structure") is True for slot in raw["slots"]))
        checked = set()
        for slot in raw["slots"]:
            for state in ("empty", "occupied"):
                for sample in slot[state]:
                    path = CALIBRATION / sample["path"]
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), sample["sha256"])
                    checked.add(sample["path"])
        self.assertEqual(len(checked), 28)

    def test_locked_bench_templates_match_declared_slots_and_hashes(self):
        raw = json.loads((CALIBRATION / "locked_bench.json").read_text(encoding="utf-8"))
        self.assertEqual([slot["index"] for slot in raw["slots"]], list(range(3, 9)))
        self.assertEqual(raw["window_size"], [1920, 1080])
        for slot in raw["slots"]:
            sample = slot["template"]
            path = CALIBRATION / sample["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), sample["sha256"])

if __name__ == "__main__":
    unittest.main()
