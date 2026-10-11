"""Read-only regressions for calibration cache recovery and cancellation."""

import importlib.util
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
CALIBRATION = ROOT / "tasks/currency_wars/calibration"
spec = importlib.util.spec_from_file_location(
    "_currency_wars_profile_recovery_vision", ROOT / "tasks/currency_wars/vision.py")
vision = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = vision
spec.loader.exec_module(vision)


class ThreadStoppedError(Exception):
    pass


class ProfileRecoveryTests(unittest.TestCase):
    def detector(self, **kwargs):
        # Production samples are only read. None of these tests captures images
        # or writes diagnostics or calibration files.
        return vision.CurrencyWarsVision(
            SimpleNamespace(), CALIBRATION / "profile.json", CALIBRATION,
            max_samples=0, **kwargs)

    def cases(self):
        return (
            ("main", "_load_profile", "profile.json", "validate_profile"),
            ("field", "_load_field_profile", "field_profile.json", "validate_field_profile"),
        )

    def fail_stat(self, profile_path, error):
        original = Path.stat

        def stat(path, *args, **kwargs):
            if path == profile_path:
                raise error
            return original(path, *args, **kwargs)

        return patch.object(Path, "stat", stat)

    def assert_unavailable(self, detector, kind, missing=False):
        if kind == "main":
            self.assertEqual(detector.profile_status,
                             "not_configured" if missing else "invalid_profile")
        else:
            self.assertEqual(detector.last_slot_reason,
                             "field_profile_missing" if missing else "field_profile_invalid")

    def test_loaded_profile_recovers_after_temporary_stat_failure_at_same_stamp(self):
        for kind, method, filename, validator in self.cases():
            for error_type in (PermissionError, FileNotFoundError):
                with self.subTest(profile=kind, error=error_type.__name__):
                    detector = self.detector()
                    load = getattr(detector, method)
                    path = CALIBRATION / filename
                    original_stat = path.stat()
                    with patch.object(vision, validator, wraps=getattr(vision, validator)) as validate:
                        first = load()
                        self.assertIsNotNone(first)
                        with self.fail_stat(path, error_type("temporary profile access failure")):
                            self.assertIsNone(load())
                            self.assert_unavailable(detector, kind, error_type is FileNotFoundError)
                        self.assertEqual((path.stat().st_mtime_ns, path.stat().st_size),
                                         (original_stat.st_mtime_ns, original_stat.st_size))
                        recovered = load()
                        self.assertIsNotNone(recovered)
                        self.assertEqual(set(recovered.slots), set(first.slots))
                        self.assertIs(load(), recovered)
                        self.assertEqual(validate.call_count, 2)
                        if kind == "main":
                            self.assertEqual(detector.profile_status, "validated_local_profile")

    def test_initially_missing_profile_loads_when_it_becomes_available(self):
        for kind, method, filename, _ in self.cases():
            with self.subTest(profile=kind):
                detector = self.detector()
                load = getattr(detector, method)
                with self.fail_stat(CALIBRATION / filename, FileNotFoundError("not yet available")):
                    self.assertIsNone(load())
                    self.assert_unavailable(detector, kind, missing=True)
                self.assertIsNotNone(load())

    def test_failed_reload_does_not_return_stale_profile_and_can_recover(self):
        original_stat, original_read = Path.stat, Path.read_text
        for kind, method, filename, _ in self.cases():
            for failure in ("unreadable", "invalid_json"):
                with self.subTest(profile=kind, failure=failure):
                    detector = self.detector()
                    load = getattr(detector, method)
                    first = load()
                    self.assertIsNotNone(first)
                    path = CALIBRATION / filename
                    stamp = path.stat()

                    def updated_stat(candidate, *args, **kwargs):
                        if candidate == path:
                            return SimpleNamespace(st_mtime_ns=stamp.st_mtime_ns + 1,
                                                   st_size=stamp.st_size)
                        return original_stat(candidate, *args, **kwargs)

                    def failed_read(candidate, *args, **kwargs):
                        if candidate == path:
                            if failure == "unreadable":
                                raise PermissionError("temporary read failure")
                            return "{incomplete JSON"
                        return original_read(candidate, *args, **kwargs)

                    with patch.object(Path, "stat", updated_stat), patch.object(Path, "read_text", failed_read):
                        self.assertIsNone(load())
                        self.assert_unavailable(detector, kind)
                    recovered = load()
                    self.assertIsNotNone(recovered)
                    self.assertEqual(set(recovered.slots), set(first.slots))

    def test_unchanged_valid_profile_reuses_cache(self):
        for kind, method, _, validator in self.cases():
            with self.subTest(profile=kind):
                detector = self.detector()
                load = getattr(detector, method)
                with patch.object(vision, validator, wraps=getattr(vision, validator)) as validate:
                    first = load()
                    self.assertIsNotNone(first)
                    self.assertIs(load(), first)
                    self.assertIs(load(), first)
                    validate.assert_called_once()

    def test_stop_event_is_checked_before_reading_profile(self):
        for kind, method, _, _ in self.cases():
            with self.subTest(profile=kind):
                detector = self.detector()
                detector.operator.stop_event = threading.Event()
                detector.operator.stop_event.set()
                with patch.object(Path, "stat") as stat:
                    with self.assertRaises(vision.VisionStoppedError):
                        getattr(detector, method)()
                    stat.assert_not_called()

    def test_stop_errors_during_profile_access_propagate(self):
        for kind, method, filename, _ in self.cases():
            for error_type in (InterruptedError, ThreadStoppedError):
                with self.subTest(profile=kind, error=error_type.__name__):
                    detector = self.detector()
                    error = error_type("stopped during access")
                    with self.fail_stat(CALIBRATION / filename, error):
                        with self.assertRaises(error_type) as raised:
                            getattr(detector, method)()
                    self.assertIs(raised.exception, error)

    def test_stop_requested_during_recoverable_failure_propagates(self):
        for kind, method, filename, _ in self.cases():
            with self.subTest(profile=kind):
                event = threading.Event()
                detector = self.detector()
                detector.operator.stop_event = event
                original = Path.stat

                def stopped_stat(path, *args, **kwargs):
                    if path == CALIBRATION / filename:
                        event.set()
                        raise PermissionError("access failed while stopping")
                    return original(path, *args, **kwargs)

                with patch.object(Path, "stat", stopped_stat):
                    with self.assertRaises(vision.VisionStoppedError):
                        getattr(detector, method)()


if __name__ == "__main__":
    unittest.main()
