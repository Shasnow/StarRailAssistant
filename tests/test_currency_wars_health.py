"""Conservative health parsing and explicit-ROI offline replay only."""

import importlib.util
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from PIL import Image

from tests.currency_wars_replays import REPLAY_ROOT, OCR_ROOT

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("_currency_wars_health_tests", ROOT / "tasks/currency_wars/vision.py")
vision = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = vision
spec.loader.exec_module(vision)


def text(value, score=0.99, box=None):
    return [(box or [[5, 5], [145, 5], [145, 35], [5, 35]], value, score)]


def health(value="82", label_score=0.99, value_score=0.99):
    return text("小队生命值", label_score) + text(value, value_score,
                                               [[148, 6], [220, 6], [220, 34], [148, 34]])


class ThreadStoppedError(Exception):
    pass


class FakeOperator:
    def __init__(self, results=()):
        self.results = list(results)
        self.calls = []
        self.stop_event = threading.Event()
        self.frame = Image.new("RGB", (1920, 1080), "blue")

    def screenshot(self, **kwargs):
        self.calls.append(("screenshot", kwargs))
        frame = self.frame.copy()
        if kwargs:
            frame = frame.crop((round(kwargs["from_x"] * frame.width), round(kwargs["from_y"] * frame.height),
                                round(kwargs["to_x"] * frame.width), round(kwargs["to_y"] * frame.height)))
        return frame

    def ocr_engine(self, image, **kwargs):
        self.calls.append(("engine", image.size))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def ocr(self, **kwargs):
        self.calls.append(("ocr", kwargs))
        return self.results.pop(0)

    def sleep(self, seconds):
        self.calls.append(("sleep", seconds))


class SquadHealthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sra_health_offline_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def task(self, operator, **kwargs):
        return vision.CurrencyWarsVision(operator, self.root / "profile.json", self.root / "samples",
                                         max_samples=0, **kwargs)

    def test_exact_label_and_value_accept_zero_and_one_hundred_without_assuming_maximum(self):
        for value in ("0", "82", "100"):
            answer = vision.parse_squad_health(health(value), image_size=(326, 76))
            self.assertEqual((answer.current, answer.maximum), (int(value), None))
            self.assertEqual(answer.reason, "labelled_health")

    def test_complete_health_fraction_and_whitespace_are_supported(self):
        answer = vision.parse_squad_health(text(" 小队 生命值：８２／１００ ", 0.9), image_size=(326, 76))
        self.assertEqual((answer.current, answer.maximum), (82, 100))
        self.assertEqual(vision.parse_squad_health(health("0/100")).current, 0)

    def test_bare_numbers_other_hp_levels_and_partial_labels_cannot_authenticate(self):
        for value in ("82", "生命值82", "角色生命值82", "最大生命值82", "小队生命82", "Lv.6", "6/40",
                      "小队生命值82垃圾", "小队生命值82.0", "小队生命值-1"):
            self.assertIsNone(vision.parse_squad_health(text(value)).current, value)
        self.assertIsNone(vision.parse_squad_health(text("生命值") + health()[1:]).current)

    def test_low_confidence_label_or_number_cannot_confirm_health(self):
        for rows in (health(label_score=0.899), health(value_score=0.899), text("小队生命值82", 0.899)):
            answer = vision.parse_squad_health(rows)
            self.assertIsNone(answer.current)
            self.assertEqual(answer.reason, "low_health_confidence")

    def test_conflicting_nearby_values_are_unknown_even_if_one_has_low_confidence(self):
        rows = health() + text("72", 0.4, [[150, 6], [220, 6], [220, 34], [150, 34]])
        self.assertEqual(vision.parse_squad_health(rows).reason, "ambiguous_health")

    def test_values_must_be_on_the_label_row_and_adjacent_to_it(self):
        for box in ([[148, 60], [220, 60], [220, 90], [148, 90]],
                    [[280, 6], [320, 6], [320, 34], [280, 34]],
                    [[5, 6], [45, 6], [45, 34], [5, 34]]):
            self.assertIsNone(vision.parse_squad_health(text("小队生命值") + text("82", box=box)).current)

    def test_recorded_two_times_ocr_boundary_overlap_preserves_actual_eighty_two(self):
        rows = text("小队生命值", 0.99878, [[134, 36], [431, 36], [431, 118], [134, 118]])
        rows += text("82", 1.0, [[418, 42], [502, 43], [501, 110], [417, 110]])
        self.assertEqual(vision.parse_squad_health(rows, image_size=(652, 152)).current, 82)

    def test_out_of_range_and_invalid_boxes_scores_remain_unknown(self):
        for value in ("101", "999", "82/80", "0/0", "82/101"):
            self.assertEqual(vision.parse_squad_health(health(value)).reason, "invalid_health_range")
        for score in (True, None, float("nan"), float("inf"), 1.01):
            self.assertIsNone(vision.parse_squad_health(health(value_score=score)).current)
        for box in ([], [[0, 0]], [[-1, 1], [100, 1], [100, 20], [-1, 20]],
                    [[5, 5], [400, 5], [400, 35], [5, 35]], [[0, 0]] * 4):
            rows = [(box, "小队生命值82", 0.99)]
            self.assertIsNone(vision.parse_squad_health(rows, image_size=(326, 76)).current)

    def test_unconfigured_or_invalid_roi_never_captures_or_guesses(self):
        operator = FakeOperator()
        task = self.task(operator)
        self.assertEqual(task.read_squad_health().reason, "health_roi_not_configured")
        for roi in ((0.3, 0.4, 0.2, 0.5), (True, 0.4, 0.8, 0.5), (0, 0, float("nan"), 1), ()):
            self.assertEqual(task.read_squad_health(roi).reason, "invalid_health_roi")
        self.assertEqual(operator.calls, [])

    def test_two_independent_frames_are_required_and_constructor_roi_is_opt_in(self):
        operator = FakeOperator([health(), health()])
        result = self.task(operator, health_roi=vision.RESULT_HEALTH_ROI).read_squad_health()
        self.assertEqual((result.current, result.maximum, result.evidence), (82, None, "two_health_frames"))
        self.assertEqual([call[1] for call in operator.calls if call[0] == "engine"], [(326, 76), (652, 152)])
        self.assertEqual(sum(call[0] == "screenshot" for call in operator.calls), 2)

    def test_missing_or_disagreeing_second_frame_does_not_use_first_value(self):
        for second in (None, health("81"), RuntimeError("OCR failed")):
            task = self.task(FakeOperator([health(), second]))
            result = task.read_squad_health(vision.RESULT_HEALTH_ROI)
            self.assertIsNone(result.current)
            self.assertEqual(len(task.last_health_attempts), 2)

    def test_legacy_ocr_wrapper_remains_bounded_to_two_calls(self):
        operator = FakeOperator([health(), health()])
        operator.ocr_engine = None
        result = self.task(operator).read_squad_health(vision.RESULT_HEALTH_ROI)
        self.assertEqual(result.current, 82)
        self.assertEqual(sum(call[0] == "ocr" for call in operator.calls), 2)

    def test_cancellation_before_and_during_ocr_propagates(self):
        operator = FakeOperator([health()])
        operator.stop_event.set()
        with self.assertRaises(vision.VisionStoppedError):
            self.task(operator).read_squad_health(vision.RESULT_HEALTH_ROI)
        self.assertEqual(operator.calls, [])
        operator = FakeOperator([health(), ThreadStoppedError("stopped")])
        with self.assertRaises(ThreadStoppedError):
            self.task(operator).read_squad_health(vision.RESULT_HEALTH_ROI)

    def test_real_result_health_with_existing_offline_rapidocr(self):
        deps = os.environ.get("SRA_POPULATION_OCR_DEPS")
        source = REPLAY_ROOT / "battle_result_ready.png"
        if not deps or not source.exists():
            self.skipTest("optional offline OCR dependencies and historical result screenshot required")
        sys.path.insert(0, deps)
        try:
            from rapidocr import RapidOCR
            models = OCR_ROOT / "models"
            engine = RapidOCR(config_path=OCR_ROOT / "config.yaml", params={
                "Global.log_level": "error", "Det.model_path": str(models / "PP-OCRv6_det_small.onnx"),
                "Rec.model_path": str(models / "PP-OCRv6_rec_small.onnx"),
                "Cls.model_path": str(models / "ch_ppocr_mobile_v2.0_cls_mobile.onnx"),
            })
            with Image.open(source) as opened:
                frame = opened.convert("RGB")
            if frame.size == (1924, 1127):
                frame = frame.crop((2, 45, 1922, 1125))
            operator = FakeOperator()
            operator.frame, operator.ocr_engine = frame, engine
            task = self.task(operator)
            result = task.read_squad_health(vision.RESULT_HEALTH_ROI)
            self.assertEqual((result.current, result.maximum), (82, None), task.last_health_attempts)
            self.assertIn("小队生命值", result.raw_text)
            self.assertEqual(len(task.last_health_attempts), 2)
        finally:
            sys.path.remove(deps)


if __name__ == "__main__":
    unittest.main()
