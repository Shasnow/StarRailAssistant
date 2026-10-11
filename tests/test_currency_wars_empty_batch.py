"""Batch vacancy evidence uses shared frames, with independent per-slot results."""

import json
import threading
import unittest

from PIL import Image

import test_currency_wars_vision as fixture


class EmptyBatchTests(unittest.TestCase):
    setUp = fixture.VisionTests.setUp
    make_vision = fixture.VisionTests.make_vision

    def write_nine_slots(self):
        self.positions = tuple((0.1 + index * 0.1, 0.5) for index in range(9))
        box = (-0.025, -0.1, 0.025, 0.1)
        entries = []
        for index, position in enumerate(self.positions):
            for label, frame in (("empty", self.empty_frame), ("occupied", self.occupied_frame)):
                fixture.vision.crop_slot_template(frame, position, box).save(self.root / f"{label}{index}.png")
            entries.append(fixture.vision.make_template_entry("in_hand", index, position, box,
                f"empty{index}.png", f"occupied{index}.png", self.root))
        self.profile_path.write_text(json.dumps({"version": 1, "window_size": [200, 100],
                                                "slots": entries}), encoding="utf-8")

    def mixed_frame(self, occupied):
        frame = self.empty_frame.copy()
        for index in occupied:
            x = round(self.positions[index][0] * frame.width)
            frame.paste("white", (x - 5, 40, x + 5, 60))
        return frame

    def test_nine_slots_need_two_frames_instead_of_eighteen(self):
        self.write_nine_slots()
        frame = self.mixed_frame({1, 7})
        operator = fixture.FakeOperator(frames=[frame, frame])
        reader = self.make_vision(operator)

        batch = reader.read_empty_slots("in_hand", self.positions)

        self.assertEqual(batch, {index: index not in (1, 7) for index in range(9)})
        self.assertEqual([name for name, _ in operator.calls], ["screenshot", "sleep", "screenshot"])
        individual_operator = fixture.FakeOperator(frames=[frame] * 18)
        individual = self.make_vision(individual_operator)
        self.assertEqual(batch, {index: individual.slot_is_empty("in_hand", index, position)
                                 for index, position in enumerate(self.positions)})
        self.assertEqual(sum(name == "screenshot" for name, _ in individual_operator.calls), 18)

    def test_conflict_in_one_slot_does_not_discard_other_slots(self):
        self.write_nine_slots()
        operator = fixture.FakeOperator(frames=[self.mixed_frame({1}), self.mixed_frame({1, 3})])
        reader = self.make_vision(operator)

        result = reader.read_empty_slots("in_hand", self.positions)

        self.assertIsNone(result[3])
        self.assertIs(result[1], False)
        self.assertTrue(all(result[index] is True for index in (0, 2, 4, 5, 6, 7, 8)))
        self.assertEqual(reader.last_empty_slot_reasons[3], "conflicting_slot_frames")

    def test_missing_profile_never_invents_empty_slots(self):
        reader = self.make_vision()
        self.assertEqual(reader.read_empty_slots("in_hand", [(0.1, 0.5)] * 9), dict.fromkeys(range(9)))
        self.assertEqual(reader.operator.calls, [])

    def test_only_calibrated_positions_are_accepted(self):
        self.write_nine_slots()
        operator = fixture.FakeOperator(frames=[self.empty_frame] * 2)
        reader = self.make_vision(operator)
        positions = dict(enumerate(self.positions))
        positions[4] = (0.55, 0.5)
        positions[9] = (0.95, 0.5)

        result = reader.read_empty_slots("in_hand", positions)

        self.assertIsNone(result[4])
        self.assertIsNone(result[9])
        self.assertIs(result[3], True)

    def test_window_mismatch_and_frame_failure_remain_unknown(self):
        self.write_nine_slots()
        for frames in ([Image.new("RGB", (100, 100))] * 2,
                       [self.empty_frame, RuntimeError("capture failed")]):
            with self.subTest(frames=repr(frames)):
                reader = self.make_vision(fixture.FakeOperator(frames=frames))
                self.assertEqual(reader.read_empty_slots("in_hand", self.positions), dict.fromkeys(range(9)))

    def test_stop_between_frames_never_takes_another_frame(self):
        self.write_nine_slots()
        operator = fixture.FakeOperator(frames=[self.empty_frame] * 2)
        operator.stop_event = threading.Event()

        def stop_after_wait(seconds):
            operator.calls.append(("sleep", seconds))
            operator.stop_event.set()

        operator.sleep = stop_after_wait
        reader = self.make_vision(operator)
        with self.assertRaises(fixture.vision.VisionStoppedError):
            reader.read_empty_slots("in_hand", self.positions)
        self.assertEqual([name for name, _ in operator.calls], ["screenshot", "sleep"])


if __name__ == "__main__":
    unittest.main()
