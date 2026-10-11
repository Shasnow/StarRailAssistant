"""Result animations and ready controls are replayed without controlling a game."""

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
spec = importlib.util.spec_from_file_location("_currency_wars_battle_vision", ROOT / "tasks/currency_wars/vision.py")
vision = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = vision
spec.loader.exec_module(vision)


def text(value, score=0.99, box=None):
    return [(box if box is not None else [[5, 5], [150, 5], [150, 50], [5, 50]], value, score)]


class ThreadStoppedError(Exception):
    pass


class FakeOperator:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []
        self.frame = Image.new("RGB", (1920, 1080), "blue")
        self.stop_event = threading.Event()

    def screenshot(self):
        self.calls.append(("screenshot", self.frame.size))
        return self.frame.copy()

    def ocr_engine(self, image, **kwargs):
        self.calls.append(("engine", (image.size, image.getpixel((0, 0)))))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class BattleVisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sra_battle_vision_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def make_vision(self, operator, **kwargs):
        return vision.CurrencyWarsVision(operator, self.root / "profile.json", self.root / "samples",
                                         max_samples=0, **kwargs)

    def test_success_animation_has_grounded_acceleration_point(self):
        result = self.make_vision(FakeOperator([text("挑战成功"), text("点击空白加速")])).read_battle_screen()
        self.assertEqual(result.state, "result_animation")
        self.assertEqual(result.outcome, "success")
        self.assertIsNone(result.continue_point)
        self.assertEqual(result.accelerate_point, ((672 + 77.5) / 1920, (832 + 27.5) / 1080))

    def test_ready_uses_actual_box_center_rather_than_a_fixed_click(self):
        box = [[300, 60], [450, 60], [450, 110], [300, 110]]
        result = self.make_vision(FakeOperator([text("挑战成功"), text("继续挑战", box=box)])).read_battle_screen()
        self.assertEqual(result.state, "result_ready")
        self.assertEqual(result.outcome, "success")
        self.assertEqual(result.continue_point, ((672 + 375) / 1920, (832 + 85) / 1080))
        self.assertIsNone(result.accelerate_point)

    def test_header_alone_proves_result_without_authorizing_a_continue_click(self):
        for action in (None, text("3"), text("继续挑战", 0.89)):
            result = self.make_vision(FakeOperator([text("挑战成功"), action])).read_battle_screen()
            self.assertEqual((result.state, result.continue_point, result.accelerate_point),
                             ("result_animation", None, None))

    def test_central_early_success_title_authenticates_reward_animation(self):
        # Early reward animations keep the title near the middle of the screen,
        # below the compact title position used by the final results layout.
        central_header = [[70, 275], [320, 275], [320, 330], [70, 330]]
        result = self.make_vision(FakeOperator([
            text("挑战成功", box=central_header), text("点击空白加速"),
        ])).read_battle_screen()
        self.assertEqual(result.state, "result_animation")
        self.assertIsNone(result.continue_point)
        self.assertIsNotNone(result.accelerate_point)

    def test_isolated_controls_without_a_result_title_remain_unknown(self):
        for header in (None, text("挑战进度"), text("挑战成功", 0.89), text("未挑战成功")):
            for action in ("继续挑战", "点击空白加速"):
                result = self.make_vision(FakeOperator([header, text(action)])).read_battle_screen()
                self.assertEqual((result.state, result.continue_point, result.accelerate_point),
                                 ("unknown", None, None))

    def test_exact_failure_title_can_confirm_a_ready_result(self):
        result = self.make_vision(FakeOperator([text("挑战失败"), text("继续挑战")])).read_battle_screen()
        self.assertEqual(result.state, "result_ready")
        self.assertEqual(result.outcome, "failure")
        result = self.make_vision(FakeOperator([text("挑战失败"), text("点击空白加速")])).read_battle_screen()
        self.assertEqual((result.state, result.accelerate_point), ("result_animation", None))
        self.assertEqual(result.outcome, "failure")

    def test_legacy_observation_constructor_keeps_unknown_outcome(self):
        result = vision.BattleScreenObservation("result_animation", None, None, "legacy", "")
        self.assertEqual(result.outcome, "unknown")

    def test_isolated_or_conflicting_result_words_have_no_outcome(self):
        for header in (None, text("挑战成功", 0.89), text("挑战成功") + text("挑战失败")):
            result = self.make_vision(FakeOperator([header, text("继续挑战")])).read_battle_screen()
            self.assertEqual((result.state, result.outcome), ("unknown", "unknown"))

    def test_action_ocr_error_keeps_confirmed_same_frame_outcome_without_clicks(self):
        for title, outcome in (("挑战成功", "success"), ("挑战失败", "failure")):
            result = self.make_vision(FakeOperator([text(title), RuntimeError("action OCR failed")])).read_battle_screen()
            self.assertEqual((result.state, result.outcome, result.continue_point, result.accelerate_point),
                             ("result_animation", outcome, None, None))

    def test_whitespace_and_inclusive_confidence_are_supported(self):
        result = self.make_vision(FakeOperator([text(" 挑战 成功\n", 0.9), text("继续 挑战", 0.9)])).read_battle_screen()
        self.assertEqual(result.state, "result_ready")

    def test_invalid_scores_cannot_authenticate_a_title(self):
        for score in (True, None, float("nan"), float("inf"), 1.01, "garbled"):
            result = self.make_vision(FakeOperator([text("挑战成功", score), text("继续挑战")])).read_battle_screen()
            self.assertEqual(result.state, "unknown")

    def test_invalid_control_boxes_never_produce_a_click_point(self):
        for box in ([], [[0, 0]], [[-1, 5], [100, 5], [100, 20], [-1, 20]],
                    [[0, 0], [577, 0], [577, 30], [0, 30]],
                    [[0, 0], [100, 0], [100, 141], [0, 141]],
                    [[0, 0], [100, 0], [100, float("nan")], [0, 20]],
                    [[0, 0]] * 4, [[True, 0], [100, 0], [100, 20], [0, 20]]):
            with self.subTest(box=box):
                result = self.make_vision(FakeOperator([text("挑战成功"), text("继续挑战", box=box)])).read_battle_screen()
                self.assertEqual((result.state, result.continue_point), ("result_animation", None))

    def test_invalid_header_box_or_conflicting_headers_remain_unknown(self):
        for header in (text("挑战成功", box=[]), text("挑战成功") + text("挑战失败")):
            result = self.make_vision(FakeOperator([header, text("继续挑战")])).read_battle_screen()
            self.assertEqual(result.state, "unknown")

    def test_conflicting_action_labels_do_not_authorize_either_control(self):
        result = self.make_vision(FakeOperator([text("挑战成功"),
                                               text("继续挑战") + text("点击空白加速")])).read_battle_screen()
        self.assertEqual((result.state, result.continue_point, result.accelerate_point),
                         ("result_animation", None, None))

    def test_both_rois_are_read_from_the_same_single_new_frame(self):
        operator = FakeOperator([text("挑战成功"), text("继续挑战")])
        task = self.make_vision(operator)
        task.read_battle_screen()
        self.assertEqual(operator.calls, [("screenshot", (1920, 1080)),
                                          ("engine", ((384, 410), (0, 0, 255))),
                                          ("engine", ((576, 140), (0, 0, 255)))])
        self.assertEqual(len(task.last_battle_attempts), 2)

    def test_stop_at_entry_or_during_action_ocr_propagates(self):
        def stop():
            raise ThreadStoppedError("stop")

        operator = FakeOperator([])
        with self.assertRaises(ThreadStoppedError):
            self.make_vision(operator, stop_check=stop).read_battle_screen()
        self.assertEqual(operator.calls, [])
        operator = FakeOperator([text("挑战成功"), ThreadStoppedError("stop action OCR")])
        with self.assertRaises(ThreadStoppedError):
            self.make_vision(operator).read_battle_screen()
        self.assertFalse((self.root / "samples").exists())

    def test_stop_event_after_header_propagates_before_action_ocr(self):
        operator = FakeOperator([])

        def engine(image, **kwargs):
            operator.calls.append(("engine", image.size))
            operator.stop_event.set()
            return text("挑战成功")

        operator.ocr_engine = engine
        with self.assertRaises(vision.VisionStoppedError):
            self.make_vision(operator).read_battle_screen()
        self.assertEqual(sum(call[0] == "engine" for call in operator.calls), 1)

    def test_unavailable_engine_or_ordinary_error_stays_unknown(self):
        operator = FakeOperator([])
        operator.ocr_engine = None
        self.assertEqual(self.make_vision(operator).read_battle_screen().state, "unknown")
        self.assertEqual(operator.calls, [])
        operator = FakeOperator([RuntimeError("offline OCR failure")])
        self.assertEqual(self.make_vision(operator).read_battle_screen().state, "unknown")
        self.assertLessEqual(sum(call[0] == "engine" for call in operator.calls), 2)

    def replay_real(self, name, expected_state, expected_action):
        source = REPLAY_ROOT / name
        if not source.exists():
            self.skipTest("historical result screenshot not present")
        deps = os.environ.get("SRA_POPULATION_OCR_DEPS")
        if not deps:
            self.skipTest("optional isolated RapidOCR dependencies not configured")
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
            operator = FakeOperator([])
            operator.frame, operator.ocr_engine = frame, engine
            task = self.make_vision(operator)
            result = task.read_battle_screen()
            self.assertEqual(result.state, expected_state, task.last_battle_attempts)
            self.assertIn("挑战成功", result.raw_text)
            self.assertIn(expected_action, result.raw_text)
            point = result.continue_point if expected_state == "result_ready" else result.accelerate_point
            self.assertIsNotNone(point)
            self.assertTrue(0.45 < point[0] < 0.55 and 0.8 < point[1] < 0.86)
            self.assertEqual(sum(call[0] == "screenshot" for call in operator.calls), 1)
        finally:
            sys.path.remove(deps)

    def test_real_success_animation_with_offline_rapidocr(self):
        self.replay_real("battle_result_animation.png", "result_animation", "点击空白加速")

    def test_real_success_ready_with_offline_rapidocr(self):
        self.replay_real("battle_result_ready.png", "result_ready", "继续挑战")


if __name__ == "__main__":
    unittest.main()
