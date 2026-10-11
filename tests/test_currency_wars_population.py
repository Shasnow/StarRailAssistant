"""Offline population evidence tests; no game control or field-state mutation."""

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PIL import Image


from tests.currency_wars_replays import REPLAY_ROOT, OCR_ROOT

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("_currency_wars_population_vision", ROOT / "tasks/currency_wars/vision.py")
vision = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = vision
spec.loader.exec_module(vision)
REAL_FRAME = REPLAY_ROOT / "population_zero.png"
REAL_FIVE_SIX = (REPLAY_ROOT / "population_five_six.png")


def text(value, score=0.99):
    return [([[0, 0], [150, 0], [150, 80], [0, 80]], value, score)]


class ThreadStoppedError(Exception):
    pass


class FakeOperator:
    def __init__(self, results=(), frames=()):
        self.results = list(results)
        self.frames = list(frames)
        self.last_frame = Image.new("RGB", (1920, 1080), "black")
        self.calls = []

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

    def ocr(self, **kwargs):
        self.calls.append(("ocr", kwargs))
        result = self.results.pop(0) if self.results else None
        if isinstance(result, Exception):
            raise result
        return result

    def sleep(self, seconds):
        self.calls.append(("sleep", seconds))


class PopulationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sra_population_offline_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def make_vision(self, operator, **kwargs):
        return vision.CurrencyWarsVision(operator, self.root / "missing_profile.json", self.root / "samples", **kwargs)

    def test_complete_counter_requires_at_least_point_nine_confidence(self):
        for value in ("0/3", "3/3", "2 / 10", "０／３"):
            with self.subTest(value=value):
                result = vision.parse_population(text(value, 0.9))
                self.assertIsNotNone(result.current)
                self.assertEqual(result.reason, "complete_population")
        for score in (0.89999, -1, 1.01, float("nan"), float("inf"), "bad", None, True):
            with self.subTest(score=score):
                result = vision.parse_population(text("0/3", score))
                self.assertEqual((result.current, result.capacity), (None, None))

    def test_missing_partial_and_garbled_text_never_infers_zero(self):
        for value in ("3", "0", "/3", "0/", "O/3", "0|3", "0/3垃圾", "等级3", "-1/3", "1.0/3", "人口 0/3"):
            with self.subTest(value=value):
                result = vision.parse_population(text(value))
                self.assertEqual((result.current, result.capacity), (None, None))
        for results in (None, [], "0/3", [(None, "0/3")], [(None, 0, 0.99)], [None]):
            with self.subTest(results=results):
                self.assertIsNone(vision.parse_population(results).current)

    def test_out_of_range_and_conflicting_counters_are_unknown(self):
        for value in ("0/0", "4/3", "0/11", "11/11", "99/99"):
            self.assertEqual(vision.parse_population(text(value)).reason, "invalid_population_range")
        result = vision.parse_population(text("0/3") + text("1/3"))
        self.assertEqual(result.reason, "ambiguous_population")
        self.assertIsNone(result.current)
        # A low-confidence conflicting reading cannot authenticate an empty field.
        self.assertIsNone(vision.parse_population(text("0/3") + text("1/3", 0.5)).current)

    def test_two_color_frames_confirm_zero_without_changing_any_slots(self):
        operator = FakeOperator([text("0/3"), text("0/3")])
        task = self.make_vision(operator)
        result = task.read_population()
        self.assertEqual((result.current, result.capacity, result.evidence), (0, 3, "two_population_frames"))
        self.assertEqual(result.reason, "consistent_population")
        self.assertEqual(len(task.last_population_attempts), 2)
        self.assertIsNone(task._profile)
        self.assertEqual(task.profile_status, "not_loaded")
        self.assertFalse((self.root / "samples").exists())
        calls = [arguments for method, arguments in operator.calls if method == "ocr"]
        self.assertEqual(len(calls), 2)
        # Preserve weak conflicting tokens for the parser instead of filtering
        # them before two-frame confidence validation.
        self.assertTrue(all(not call["grayscale"] and call["confidence"] == 0.0 for call in calls))
        self.assertEqual(sum(method == "sleep" for method, _ in operator.calls), 1)

    def test_positive_population_is_returned_without_guessing_occupied_slots(self):
        task = self.make_vision(FakeOperator([text("2/3"), text("2/3")]))
        result = task.read_population()
        self.assertEqual((result.current, result.capacity), (2, 3))
        self.assertIsNone(task._profile)

    def test_both_readings_must_be_complete_confident_and_identical(self):
        for pair in ((text("0/3"), text("3")), (text("0/3"), text("0/3", 0.85)),
                     (text("0/3"), text("1/3")), (None, text("0/3")),
                     (text("0/3"), text("0/4")), (RuntimeError("ocr failed"), text("0/3"))):
            with self.subTest(pair=pair):
                operator = FakeOperator(pair)
                task = self.make_vision(operator, max_samples=0)
                result = task.read_population()
                self.assertEqual((result.current, result.capacity), (None, None))
                self.assertEqual(len(task.last_population_attempts), 2)
                self.assertEqual(sum(method == "ocr" for method, _ in operator.calls), 2)

    def test_unknown_diagnostics_are_bounded_and_keep_population_attempts(self):
        import json
        operator = FakeOperator([None, None, None, None])
        task = self.make_vision(operator)
        task.read_population()
        task.read_population()
        images = list((self.root / "samples").glob("*.png"))
        self.assertEqual(len(images), 1)
        payload = json.loads(images[0].with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(len(payload["ocr_attempts"]), 2)

    def test_stop_at_entry_or_during_second_ocr_propagates(self):
        def stop():
            raise ThreadStoppedError("stop")

        operator = FakeOperator()
        with self.assertRaises(ThreadStoppedError):
            self.make_vision(operator, stop_check=stop).read_population()
        self.assertEqual(operator.calls, [])
        operator = FakeOperator([text("0/3"), ThreadStoppedError("stop second frame")])
        with self.assertRaises(ThreadStoppedError):
            self.make_vision(operator).read_population()
        self.assertFalse((self.root / "samples").exists())

    def test_stop_event_during_inter_frame_pause_propagates(self):
        import threading
        operator = FakeOperator([text("0/3"), text("0/3")])
        operator.stop_event = threading.Event()
        operator.sleep = lambda _seconds: operator.stop_event.set()
        with self.assertRaises(vision.VisionStoppedError):
            self.make_vision(operator).read_population()
        self.assertEqual(sum(method == "ocr" for method, _ in operator.calls), 1)

    def test_engine_uses_two_new_frames_with_identical_two_times_preprocessing(self):
        frames = [Image.new("RGB", (1920, 1080), color) for color in ("red", "blue")]
        operator = FakeOperator(frames=frames)
        engine_inputs = []

        def engine(image, **kwargs):
            engine_inputs.append((image.size, image.mode, image.getpixel((0, 0)), kwargs))
            return SimpleNamespace(boxes=[[[0, 0], [150, 0], [150, 80], [0, 80]]], txts=["0/3"], scores=[0.9])

        operator.ocr_engine = engine
        # Host confidence must not silently raise the population's own threshold.
        operator.ocr_confidence = 0.999
        result = self.make_vision(operator).read_population()
        self.assertEqual((result.current, result.capacity), (0, 3))
        self.assertEqual([item[:3] for item in engine_inputs],
                         [((308, 162), "RGB", (255, 0, 0)), ((308, 162), "RGB", (0, 0, 255))])
        self.assertEqual(sum(method == "screenshot" for method, _ in operator.calls), 2)

    def test_window_resize_between_frames_rejects_even_agreeing_counters(self):
        operator = FakeOperator(frames=[Image.new("RGB", size) for size in ((1920, 1080), (1280, 720))])
        operator.ocr_engine = lambda image, **kwargs: text("0/3")
        task = self.make_vision(operator, max_samples=0)
        result = task.read_population()
        self.assertIsNone(result.current)
        self.assertEqual(result.reason, "population_window_changed")
        self.assertEqual(len(task.last_population_attempts), 2)

    def test_new_page_without_counter_cannot_reuse_first_frame(self):
        operator = FakeOperator(frames=[Image.new("RGB", (1920, 1080), color) for color in ("red", "black")])
        inputs = []

        def engine(image, **kwargs):
            inputs.append(image.getpixel((0, 0)))
            return text("5/6") if inputs[-1] == (255, 0, 0) else None

        operator.ocr_engine = engine
        result = self.make_vision(operator, max_samples=0).read_population()
        self.assertIsNone(result.current)
        self.assertEqual(inputs, [(255, 0, 0), (0, 0, 0)])
        self.assertEqual(result.reason, "population_not_confirmed")

    def test_old_rapidocr_tuple_output_is_still_confidence_checked(self):
        operator = FakeOperator()
        operator.ocr_engine = lambda image, **kwargs: (text("0/3", 0.85), [0.01, 0.02])
        result = self.make_vision(operator, max_samples=0).read_population()
        self.assertIsNone(result.current)

    @unittest.skipUnless(REAL_FRAME.exists(), "reviewed historical game screenshot not present")
    def test_real_zero_population_crop_replays_recorded_ocr_outputs(self):
        with Image.open(REAL_FRAME) as image:
            frame = image.convert("RGB")
        operator = FakeOperator(frames=[frame, frame])
        scores = iter((0.97685, 0.97685))
        inputs = []

        def engine(image, **kwargs):
            inputs.append(image.copy())
            return SimpleNamespace(boxes=[[[0, 0], [image.width - 1, 0],
                                           [image.width - 1, image.height - 1], [0, image.height - 1]]],
                                   txts=["0/3"], scores=[next(scores)])

        operator.ocr_engine = engine
        result = self.make_vision(operator).read_population()
        self.assertEqual((result.current, result.capacity), (0, 3))
        roi = vision.POPULATION_ROI
        expected = frame.crop(tuple(round(value * (frame.width if index % 2 == 0 else frame.height))
                                    for index, value in enumerate(roi)))
        expected = expected.resize((308, 162), Image.Resampling.LANCZOS)
        self.assertEqual(inputs[0].tobytes(), expected.tobytes())
        self.assertEqual(inputs[1].tobytes(), expected.tobytes())

    @unittest.skipUnless(REAL_FIVE_SIX.exists(), "reviewed historical 5/6 screenshot not present")
    def test_real_five_six_replays_scale_sensitive_offline_ocr_scores(self):
        # Recorded from the local PP-OCRv6 models: raw .89378 falls below the
        # gate; 2x .91588 passes. This fixture verifies preprocessing, not OCR.
        with Image.open(REAL_FIVE_SIX) as image:
            frame = image.convert("RGB")
        operator = FakeOperator(frames=[frame, frame.copy()])
        calls = []

        def engine(image, **kwargs):
            calls.append(image.size)
            return text("5/6", 0.91588 if image.size == (308, 162) else 0.89378)

        operator.ocr_engine = engine
        task = self.make_vision(operator)
        result = task.read_population()
        self.assertEqual((result.current, result.capacity), (5, 6))
        self.assertEqual(calls, [(308, 162), (308, 162)])
        self.assertEqual([a["method"] for a in task.last_population_attempts], ["population_2x"] * 2)

    @unittest.skipUnless(REAL_FRAME.exists() and REAL_FIVE_SIX.exists() and os.environ.get("SRA_POPULATION_OCR_DEPS"),
                         "optional isolated RapidOCR dependencies not configured")
    def test_real_zero_and_five_six_population_with_offline_rapidocr(self):
        # Opt in with an isolated pip --target directory; never install/alter
        # the application runtime or contact an OCR service during this test.
        deps = Path(os.environ["SRA_POPULATION_OCR_DEPS"])
        sys.path.insert(0, str(deps))
        try:
            from rapidocr import RapidOCR
            models = OCR_ROOT / "models"
            engine = RapidOCR(config_path=OCR_ROOT / "config.yaml", params={
                "Global.log_level": "error", "Det.model_path": str(models / "PP-OCRv6_det_small.onnx"),
                "Rec.model_path": str(models / "PP-OCRv6_rec_small.onnx"),
                "Cls.model_path": str(models / "ch_ppocr_mobile_v2.0_cls_mobile.onnx"),
                "EngineConfig.onnxruntime.intra_op_num_threads": 2,
                "EngineConfig.onnxruntime.inter_op_num_threads": 2,
            })
            for path, population in ((REAL_FRAME, (0, 3)), (REAL_FIVE_SIX, (5, 6))):
                with self.subTest(path=path.name):
                    with Image.open(path) as image:
                        frame = image.convert("RGB")
                    operator = FakeOperator(frames=[frame, frame.copy()])
                    operator.ocr_engine = engine
                    task = self.make_vision(operator)
                    result = task.read_population()
                    self.assertEqual((result.current, result.capacity), population, task.last_population_attempts)
                    expected_text = "/".join(map(str, population))
                    self.assertEqual([attempt["text"] for attempt in task.last_population_attempts], [expected_text] * 2)
                    if population == (5, 6):
                        roi = vision.POPULATION_ROI
                        raw = frame.crop(tuple(round(v * (frame.width if i % 2 == 0 else frame.height))
                                               for i, v in enumerate(roi)))
                        self.assertIsNone(vision.parse_population(task._engine_ocr(
                            raw, minimum_confidence=vision.POPULATION_MIN_CONFIDENCE)).current)
        finally:
            sys.path.remove(str(deps))


if __name__ == "__main__":
    unittest.main()
