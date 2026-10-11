"""Bounded scoped diagnostics, with no game control or historical deletion."""

import importlib.util
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("_currency_wars_diagnostic_tests", ROOT / "tasks/currency_wars/vision.py")
vision = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = vision
spec.loader.exec_module(vision)


class FakeOperator:
    def __init__(self):
        self.calls = 0
        self.stop_event = threading.Event()

    def screenshot(self):
        self.calls += 1
        return Image.new("RGB", (200, 100), "black")


class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sra_scoped_diagnostics_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.operator = FakeOperator()

    def task(self, max_samples=4):
        return vision.CurrencyWarsVision(self.operator, self.root / "profile.json", self.root / "samples",
                                         max_samples=max_samples)

    def test_legacy_flat_directory_keeps_existing_total_cap(self):
        task = self.task(2)
        self.assertEqual(task.capture_sample("one").parent, self.root / "samples")
        self.assertIsNone(task.capture_sample("one"))
        self.assertEqual(task.last_sample_reason, "reason_quota_exhausted")
        self.assertIsNotNone(task.capture_sample("two"))
        reopened = self.task(2)
        self.assertIsNone(reopened.capture_sample("three"))
        self.assertEqual(reopened.last_sample_reason, "directory_quota_exhausted")
        self.assertEqual(self.operator.calls, 2)

    def test_old_flat_samples_do_not_exhaust_a_new_run(self):
        historical = self.root / "samples"
        historical.mkdir()
        for number in range(12):
            Image.new("RGB", (10, 10)).save(historical / f"old-{number}.png")
        task = self.task()
        directory = task.begin_sample_scope("game-1", "run-1", critical_reserve=1)
        self.assertIsNotNone(task.capture_sample("unknown_slot"))
        self.assertEqual(len(list(historical.glob("*.png"))), 12)
        self.assertEqual(len(list(directory.glob("*.png"))), 1)

    def test_routine_diagnostics_leave_room_for_two_critical_images(self):
        task = self.task()
        directory = task.begin_sample_scope("game", "run", critical_reserve=2)
        self.assertIsNotNone(task.capture_sample("routine-1"))
        self.assertIsNotNone(task.capture_sample("routine-2"))
        self.assertIsNone(task.capture_sample("routine-3"))
        self.assertEqual(task.last_sample_reason, "critical_reserve_protected")
        first = task.capture_sample("placement_failed")
        self.assertIsNotNone(first)
        self.assertIsNotNone(task.capture_sample("custom_critical", critical=True))
        self.assertIsNone(task.capture_sample("another_critical", critical=True))
        self.assertEqual(task.last_sample_reason, "run_quota_exhausted")
        self.assertEqual(len(list(directory.glob("*.png"))), 4)
        self.assertTrue(json.loads(first.with_suffix(".json").read_text(encoding="utf-8"))["critical"])

    def test_reason_specific_quota_is_bounded_and_same_scope_does_not_reset(self):
        task = self.task()
        task.begin_sample_scope("game", "run", critical_reserve=0, reason_quotas={"failed_move": 2})
        self.assertIsNotNone(task.capture_sample("failed_move"))
        task.begin_sample_scope("game", "run", critical_reserve=0, reason_quotas={"failed_move": 4})
        self.assertIsNotNone(task.capture_sample("failed_move"))
        self.assertIsNone(task.capture_sample("failed_move"))
        self.assertEqual(task.last_sample_reason, "reason_quota_exhausted")

    def test_saved_reason_quota_survives_reader_recreation(self):
        first = self.task()
        first.begin_sample_scope("game", "run", critical_reserve=0)
        self.assertIsNotNone(first.capture_sample("failed_move"))
        reopened = self.task()
        reopened.begin_sample_scope("game", "run", critical_reserve=0)
        self.assertIsNone(reopened.capture_sample("failed_move"))
        self.assertEqual(reopened.last_sample_reason, "saved_reason_quota_exhausted")

    def test_saved_routine_count_cannot_consume_critical_reserve_after_restart(self):
        first = self.task()
        first.begin_sample_scope("game", "run", critical_reserve=2)
        first.capture_sample("routine-1")
        first.capture_sample("routine-2")
        reopened = self.task()
        reopened.begin_sample_scope("game", "run", critical_reserve=2)
        self.assertIsNone(reopened.capture_sample("routine-3"))
        self.assertEqual(reopened.last_sample_reason, "saved_critical_reserve_protected")
        self.assertIsNotNone(reopened.capture_sample("placement_unknown"))

    def test_new_run_has_fresh_quota_and_preserves_previous_run(self):
        task = self.task(1)
        old = task.begin_sample_scope("game", "one", critical_reserve=0)
        task.capture_sample("problem")
        new = task.begin_sample_scope("game", "two", critical_reserve=0)
        self.assertIsNotNone(task.capture_sample("problem"))
        self.assertNotEqual(old, new)
        self.assertEqual(len(list(old.glob("*.png"))), 1)

    def test_scope_identifiers_cannot_escape_or_collide_when_sanitized(self):
        task = self.task()
        first = task.begin_sample_scope("../game", "..\\run", critical_reserve=0)
        first.resolve().relative_to((self.root / "samples").resolve())
        second = task.begin_sample_scope("game", "run", critical_reserve=0)
        self.assertNotEqual(first, second)
        for kwargs in ({"critical_reserve": True}, {"reason_quota": -1}, {"reason_quotas": {"x": 33}}):
            with self.assertRaises(ValueError):
                task.begin_sample_scope("game", "run", **kwargs)

    def test_none_returns_explain_disabled_missing_screenshot_and_invalid_input(self):
        task = self.task(0)
        self.assertIsNone(task.capture_sample("x"))
        self.assertEqual(task.last_sample_reason, "sampling_disabled")
        task = self.task()
        self.assertIsNone(task.capture_sample(""))
        self.assertEqual(task.last_sample_reason, "invalid_sample_request")
        self.operator.screenshot = lambda: None
        self.assertIsNone(task.capture_sample("missing"))
        self.assertEqual(task.last_sample_reason, "screenshot_unavailable")

    def test_io_failure_is_reason_limited(self):
        blocked = self.root / "samples"
        blocked.write_text("file", encoding="utf-8")
        task = self.task()
        self.assertIsNone(task.capture_sample("io_failed"))
        self.assertTrue(task.last_sample_reason.startswith("capture_error:"))
        self.assertIsNone(task.capture_sample("io_failed"))
        self.assertEqual(task.last_sample_reason, "reason_quota_exhausted")

    def test_metadata_filters_secrets_but_keeps_coordinates_and_health_attempts(self):
        task = self.task()
        task.begin_sample_scope("game", "run", critical_reserve=1)
        image = task.capture_sample("placement_failed", {
            "account": "secret", "source_position": [0.3, 0.8], "layout_version": 2,
            "ocr_attempts": [{"current": 82, "maximum": None, "secret": "no"}],
        })
        data = json.loads(image.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertNotIn("account", data)
        self.assertNotIn("secret", data["ocr_attempts"][0])
        self.assertEqual(data["source_position"], [0.3, 0.8])
        self.assertEqual(data["session_id"], "game")
        self.assertEqual(task.last_sample_reason, "captured")

    def test_stop_propagates_before_capture_or_scope_change(self):
        task = self.task()
        self.operator.stop_event.set()
        with self.assertRaises(vision.VisionStoppedError):
            task.capture_sample("failure")
        with self.assertRaises(vision.VisionStoppedError):
            task.begin_sample_scope("game", "run")
        self.assertEqual(self.operator.calls, 0)


if __name__ == "__main__":
    unittest.main()
