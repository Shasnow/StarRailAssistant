"""Offline visual mechanics tests; synthetic fixtures are NOT game calibration."""

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PIL import Image


def load_module(name, relative):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[1] / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


vision = load_module("_currency_wars_vision_unit", "tasks/currency_wars/vision.py")
logic = load_module("_currency_wars_vision_logic_unit", "tasks/currency_wars/logic.py")


def text(value):
    return [([[0, 0], [100, 0], [100, 20], [0, 20]], value, 0.99)]


class ThreadStoppedError(Exception):
    pass


class FakeOperator:
    def __init__(self, ocr_results=(), frames=()):
        self.ocr_results = list(ocr_results)
        self.frames = list(frames)
        self.calls = []
        self.last_frame = Image.new("RGB", (200, 100), "black")
        self.ocr_confidence = 0.7

    def ocr(self, **kwargs):
        self.calls.append(("ocr", kwargs))
        result = self.ocr_results.pop(0) if self.ocr_results else None
        if isinstance(result, Exception):
            raise result
        return result

    def screenshot(self, **kwargs):
        self.calls.append(("screenshot", kwargs))
        if self.frames:
            self.last_frame = self.frames.pop(0)
        if isinstance(self.last_frame, Exception):
            raise self.last_frame
        image = self.last_frame.copy()
        if kwargs:
            image = image.crop((round(kwargs["from_x"] * image.width), round(kwargs["from_y"] * image.height),
                                round(kwargs["to_x"] * image.width), round(kwargs["to_y"] * image.height)))
        return image

    def sleep(self, seconds):
        self.calls.append(("sleep", seconds))


class VisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sra_vision_offline_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.profile_path = self.root / "profile.json"
        self.sample_dir = self.root / "samples"
        self.position = (0.5, 0.5)
        self.relative_box = (-0.1, -0.1, 0.1, 0.1)
        self.empty_frame = Image.new("RGB", (200, 100), "black")
        self.occupied_frame = Image.new("RGB", (200, 100), "white")

    def write_profile(self, area="in_hand"):
        # Mechanically labelled synthetic controls only; never copied to production.
        vision.crop_slot_template(self.empty_frame, self.position, self.relative_box).save(self.root / "empty.png")
        vision.crop_slot_template(self.occupied_frame, self.position, self.relative_box).save(self.root / "occupied.png")
        entry = vision.make_template_entry(area, 0, self.position, self.relative_box,
                                           "empty.png", "occupied.png", self.root)
        data = {"version": 1, "window_size": [200, 100], "slots": [entry]}
        self.profile_path.write_text(json.dumps(data), encoding="utf-8")
        return data

    def make_vision(self, operator=None, **kwargs):
        return vision.CurrencyWarsVision(operator or FakeOperator(), self.profile_path, self.sample_dir, **kwargs)

    def write_structured_profile(self, version=2):
        # Deliberately faint, sparse detail: ordinary MAE alone accepts its
        # uniform background, just as it did for the real empty-slot outline.
        self.empty_frame = Image.new("RGB", (200, 100), (30, 31, 43))
        for y in range(43, 58):
            for x in (92, 108):
                self.empty_frame.putpixel((x, y), (42, 43, 55))
        for x in range(93, 108):
            for y in (42, 58):
                self.empty_frame.putpixel((x, y), (42, 43, 55))
        data = self.write_profile()
        data["version"] = version
        data["slots"][0]["require_empty_structure"] = True
        self.profile_path.write_text(json.dumps(data), encoding="utf-8")
        return data

    def test_original_level_success_returns_parser_observation(self):
        operator = FakeOperator([text("Lv.7")])
        result = self.make_vision(operator).read_level(logic.parse_shop_level)
        self.assertIsInstance(result, logic.LevelObservation)
        self.assertEqual((result.level, result.evidence), (7, "original_gray"))
        self.assertEqual(len(operator.calls), 1)
        self.assertTrue(operator.calls[0][1]["grayscale"])

    def test_failed_original_uses_expanded_color_region(self):
        operator = FakeOperator([None, text("等级 6")])
        result = self.make_vision(operator).read_level(logic.parse_shop_level)
        self.assertEqual((result.level, result.evidence), (6, "expanded_color"))
        self.assertFalse(operator.calls[1][1]["grayscale"])
        self.assertEqual(operator.calls[1][1]["from_y"], vision.EXPANDED_LEVEL_ROI[1])

    def test_second_failure_uses_two_times_preprocessing_and_engine(self):
        operator = FakeOperator([None, None])
        engine_sizes = []

        def engine(image, **kwargs):
            engine_sizes.append(image.size)
            return SimpleNamespace(boxes=[[[0, 0], [80, 0], [80, 20], [0, 20]]], txts=["Lv.8"], scores=[0.99])

        operator.ocr_engine = engine
        result = self.make_vision(operator).read_level(logic.parse_shop_level)
        self.assertEqual((result.level, result.evidence), (8, "expanded_2x"))
        roi = vision.EXPANDED_LEVEL_ROI
        expected = ((round(roi[2] * 200) - round(roi[0] * 200)) * 2,
                    (round(roi[3] * 100) - round(roi[1] * 100)) * 2)
        self.assertEqual(engine_sizes, [expected])

    def test_all_failures_are_bounded_and_bare_population_never_substitutes(self):
        operator = FakeOperator([text("3"), text("人口 7/9")])
        task = self.make_vision(operator)
        result = task.read_level(logic.parse_shop_level)
        self.assertIsNone(result.level)
        self.assertEqual(result.reason, "all_level_attempts_failed")
        self.assertEqual(sum(call[0] == "ocr" for call in operator.calls), 2)
        self.assertEqual(len(task.last_level_attempts), 3)
        self.assertEqual(len(list(self.sample_dir.glob("*.png"))), 1)

    def test_ocr_stop_exception_is_never_converted_to_unknown(self):
        operator = FakeOperator([ThreadStoppedError("stop")])
        with self.assertRaises(ThreadStoppedError):
            self.make_vision(operator).read_level(logic.parse_shop_level)
        self.assertFalse(self.sample_dir.exists())

    def test_host_stop_callback_runs_before_visual_operations(self):
        operator = FakeOperator()

        def stop():
            raise ThreadStoppedError("stop callback")

        task = self.make_vision(operator, stop_check=stop)
        with self.assertRaises(ThreadStoppedError):
            task.slot_is_empty("in_hand", 0, self.position)
        self.assertEqual(operator.calls, [])

    def test_missing_profile_never_infers_empty_from_blank_image(self):
        task = self.make_vision()
        self.assertIsNone(task.slot_is_empty("in_hand", 0, self.position))
        self.assertEqual(task.profile_status, "not_configured")
        self.assertEqual(len(list(self.sample_dir.glob("*.png"))), 1)
        self.assertIsNone(task.slot_is_empty("in_hand", 0, self.position))
        self.assertEqual(len(list(self.sample_dir.glob("*.png"))), 1)

    def test_missing_screenshot_returns_unknown_without_writing_placeholder(self):
        task = self.make_vision(SimpleNamespace(ocr=lambda **kwargs: None))
        self.assertIsNone(task.slot_is_empty("in_hand", 0, self.position))
        self.assertFalse(self.sample_dir.exists())

    def test_two_empty_frames_are_required(self):
        self.write_profile()
        operator = FakeOperator(frames=[self.empty_frame, self.empty_frame])
        self.assertIs(self.make_vision(operator).slot_is_empty("in_hand", 0, self.position), True)
        self.assertEqual(sum(call[0] == "screenshot" for call in operator.calls), 2)
        self.assertEqual(sum(call[0] == "sleep" for call in operator.calls), 1)

    def test_two_negative_frames_confirm_occupied(self):
        self.write_profile()
        operator = FakeOperator(frames=[self.occupied_frame, self.occupied_frame])
        self.assertIs(self.make_vision(operator).slot_is_empty("in_hand", 0, self.position), False)

    def test_structure_rejects_uniform_background_that_passes_legacy_mae(self):
        data = self.write_structured_profile()
        slot = vision.validate_profile(data, self.root).slots[("in_hand", 0)]
        uniform = Image.new("RGB", slot.empty_images[0].size, (30, 31, 43))
        self.assertLess(vision.image_distance(uniform, slot.empty_images[0]), slot.max_mae)
        legacy_data = copy.deepcopy(data)
        legacy_data["version"] = 1
        legacy_data["slots"][0].pop("require_empty_structure")
        legacy = vision.validate_profile(legacy_data, self.root).slots[("in_hand", 0)]
        self.assertIs(vision.CurrencyWarsVision._classify(uniform, legacy), True)
        self.assertIsNone(vision.CurrencyWarsVision._classify(uniform, slot))
        for color in ((0, 0, 0), (34, 35, 47), (127, 127, 127), (255, 255, 255)):
            with self.subTest(color=color):
                patch = Image.new("RGB", uniform.size, color)
                self.assertIsNot(vision.CurrencyWarsVision._classify(patch, slot), True)

    def test_structure_accepts_outline_brightness_shift_and_small_cursor_occlusion(self):
        self.write_structured_profile()
        shifted = self.empty_frame.point(lambda value: min(255, value + 2))
        occluded = self.empty_frame.copy()
        for x in (92, 93):
            for y in (47, 48):
                occluded.putpixel((x, y), (255, 255, 255))
        for frame in (self.empty_frame, shifted, occluded):
            operator = FakeOperator(frames=[frame, frame])
            self.assertIs(self.make_vision(operator, max_samples=0).slot_is_empty("in_hand", 0, self.position), True)

    def test_structure_at_wrong_coordinates_is_not_empty(self):
        data = self.write_structured_profile()
        slot = vision.validate_profile(data, self.root).slots[("in_hand", 0)]
        reference = slot.empty_images[0]
        shifted = Image.new("RGB", reference.size, (30, 31, 43))
        shifted.paste(reference, (7, 0))
        self.assertLess(vision.image_distance(shifted, reference), slot.max_mae)
        self.assertIsNone(vision.CurrencyWarsVision._classify(shifted, slot))

    def test_structure_check_also_applies_to_second_frame(self):
        self.write_structured_profile()
        uniform = Image.new("RGB", self.empty_frame.size, (30, 31, 43))
        task = self.make_vision(FakeOperator(frames=[self.empty_frame, uniform]), max_samples=0)
        self.assertIsNone(task.slot_is_empty("in_hand", 0, self.position))

    def test_structure_enabled_profile_rejects_flat_empty_template(self):
        data = self.write_profile()
        data["slots"][0]["require_empty_structure"] = True
        with self.assertRaisesRegex(ValueError, "structure"):
            vision.validate_profile(data, self.root)

    def test_version_two_requires_explicit_structure_on_every_slot(self):
        data = self.write_structured_profile()
        self.assertTrue(vision.validate_profile(data, self.root).slots[("in_hand", 0)].require_empty_structure)
        data["version"] = 1
        self.assertTrue(vision.validate_profile(data, self.root).slots[("in_hand", 0)].require_empty_structure)
        data["version"] = 2
        for value in (False, None, "true", 1):
            broken = copy.deepcopy(data)
            broken["slots"][0]["require_empty_structure"] = value
            with self.assertRaisesRegex(ValueError, "version 2"):
                vision.validate_profile(broken, self.root)
        data["slots"][0].pop("require_empty_structure")
        with self.assertRaisesRegex(ValueError, "version 2"):
            vision.validate_profile(data, self.root)

    def test_template_helper_can_opt_in_to_structure_check(self):
        self.write_structured_profile()
        entry = vision.make_template_entry("in_hand", 0, self.position, self.relative_box,
                                           "empty.png", "occupied.png", self.root,
                                           require_empty_structure=True)
        self.assertIs(entry["require_empty_structure"], True)
        entry["require_empty_structure"] = "true"
        with self.assertRaisesRegex(ValueError, "boolean"):
            vision.validate_profile({"version": 1, "window_size": [200, 100], "slots": [entry]}, self.root)

    def test_store_empty_uses_its_own_explicitly_labelled_profile(self):
        self.write_profile("store")
        task = self.make_vision(FakeOperator(frames=[self.empty_frame, self.empty_frame]))
        self.assertIs(task.slot_is_empty("store", 0, self.position), True)
        self.assertIsNone(task.slot_is_empty("in_hand", 0, self.position))

    def test_conflicting_frames_and_ambiguous_patch_remain_unknown(self):
        self.write_profile()
        task = self.make_vision(FakeOperator(frames=[self.empty_frame, self.occupied_frame]))
        self.assertIsNone(task.slot_is_empty("in_hand", 0, self.position))
        gray = Image.new("RGB", (200, 100), (127, 127, 127))
        self.assertIsNone(self.make_vision(FakeOperator(frames=[gray])).slot_is_empty("in_hand", 0, self.position))

    def test_aspect_scale_and_position_mismatch_do_not_match(self):
        self.write_profile()
        for size in ((200, 150), (400, 200)):
            task = self.make_vision(FakeOperator(frames=[Image.new("RGB", size)]), max_samples=0)
            self.assertIsNone(task.slot_is_empty("in_hand", 0, self.position))
        task = self.make_vision(max_samples=0)
        self.assertIsNone(task.slot_is_empty("in_hand", 0, (0.6, 0.5)))

    def test_stop_during_second_frame_propagates(self):
        self.write_profile()
        operator = FakeOperator(frames=[self.empty_frame, ThreadStoppedError("frame stopped")])
        with self.assertRaises(ThreadStoppedError):
            self.make_vision(operator).slot_is_empty("in_hand", 0, self.position)

    def test_missing_negative_or_wrong_labels_are_rejected(self):
        data = self.write_profile()
        for mutate in (lambda d: d["slots"][0].pop("occupied"),
                       lambda d: d["slots"][0]["empty"][0].update(label="occupied")):
            broken = copy.deepcopy(data)
            mutate(broken)
            with self.assertRaises(ValueError):
                vision.validate_profile(broken, self.root)

    def test_checksum_and_template_dimensions_are_verified(self):
        data = self.write_profile()
        Image.new("RGB", (40, 20), (5, 5, 5)).save(self.root / "empty.png")
        with self.assertRaisesRegex(ValueError, "checksum"):
            vision.validate_profile(data, self.root)
        data = self.write_profile()
        data["window_size"] = [400, 200]
        with self.assertRaisesRegex(ValueError, "dimensions"):
            vision.validate_profile(data, self.root)

    def test_equal_positive_and_negative_controls_are_rejected(self):
        self.write_profile()
        with self.assertRaisesRegex(ValueError, "separated"):
            vision.make_template_entry("in_hand", 0, self.position, self.relative_box,
                                       "empty.png", "empty.png", self.root)

    def test_profile_paths_cannot_escape_calibration_directory(self):
        data = self.write_profile()
        data["slots"][0]["empty"][0]["path"] = "../empty.png"
        with self.assertRaisesRegex(ValueError, "inside"):
            vision.validate_profile(data, self.root)

    def test_samples_are_reason_limited_globally_capped_and_metadata_filtered(self):
        task = self.make_vision(max_samples=2)
        first = task.capture_sample("unknown_level", {"area": "store", "account": "do-not-save",
                                                     "ocr_attempts": [{"method": "gray", "secret": "no"}]})
        self.assertIsNotNone(first)
        self.assertIsNone(task.capture_sample("unknown_level", {}))
        self.assertIsNotNone(task.capture_sample("ambiguous_slot", {}))
        self.assertIsNone(task.capture_sample("third", {}))
        payload = json.loads(first.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertNotIn("account", payload)
        self.assertNotIn("secret", payload["ocr_attempts"][0])
        self.assertEqual(payload["calibration_status"], "unlabelled_requires_review")
        new_task = self.make_vision(max_samples=2)
        self.assertIsNone(new_task.capture_sample("after_restart", {}))
        self.assertEqual(len(list(self.sample_dir.glob("*.png"))), 2)

    def test_file_error_is_bounded_and_does_not_bypass_cancellation(self):
        bad_samples = self.root / "not_a_directory"
        bad_samples.write_text("file", encoding="utf-8")
        task = vision.CurrencyWarsVision(FakeOperator(), self.profile_path, bad_samples)
        self.assertIsNone(task.capture_sample("failure", {}))
        self.assertIsNone(task.capture_sample("failure", {}))


if __name__ == "__main__":
    unittest.main()
