"""Strict geometry recovery and bounded final diagnostics, using real borders."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from PIL import Image
import test_currency_wars_flow as fixture

from tests.currency_wars_replays import REPLAY_ROOT, require_frames

ROOT = Path(__file__).resolve().parents[1]
RECTS = ((534,599,141,141),(678,599,136,141),(823,599,130,141),
         (967,599,130,141),(1106,599,136,141),(1245,599,141,141))


def boxes(rects=RECTS):
    return [fixture.FakeBox(x,y,w,h) for x,y,w,h in rects]


class LayoutRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.module, self.characters, self.logic, self.names = fixture.load_isolated_task()
        self.addCleanup(lambda: [sys.modules.pop(name, None) for name in self.names])
        self.operator = fixture.FakeOperator()
        self.task = self.module.CurrencyWars(self.operator,1)
        self.task.is_running = True
        self.task._set_shop_open = Mock(return_value=True)
        self.old = self.module.validate_backend_layout(boxes(), (1920,1080)).positions
        self.task.off_field_area = list(self.old)
        self.task._confirmed_layout_positions = self.old
        self.task.get_on_field_area = Mock()
        self.task.get_off_field_area = Mock()
        self.task._vision.capture_layout_failure = Mock()

    def test_nested_actual_contours_can_revalidate_complete_row(self):
        result = self.module.revalidate_backend_layout(boxes()+boxes(), (1920,1080), previous_positions=self.old)
        self.assertTrue(result.valid)
        self.assertEqual(result.positions, self.old)

    def test_old_coordinates_cannot_fill_missing_anchor(self):
        result = self.module.revalidate_backend_layout(boxes()[1:], (1920,1080), previous_positions=self.old)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "recovery_missing_anchor")

    def test_ambiguous_fresh_anchor_is_rejected(self):
        competing = boxes() + [fixture.FakeBox(542,599,141,141)]
        result = self.module.revalidate_backend_layout(competing,(1920,1080),previous_positions=self.old)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "recovery_ambiguous_anchor")

    def test_first_bad_candidate_preserves_anchors_and_suspends_identity(self):
        self.operator.rectangle_detect = Mock(return_value=boxes()[:1])
        self.task.refresh_character(equip=False)
        self.assertFalse(self.task._layout_valid)
        self.assertEqual(tuple(self.task.off_field_area), self.old)
        self.assertEqual(self.task._confirmed_layout_positions, self.old)
        self.assertTrue(all(o.state==self.logic.SlotState.UNKNOWN and o.evidence=="layout_unconfirmed"
                            for o in self.task._observations["off_field"]))
        self.task.get_off_field_area.assert_not_called()

    def test_normal_recovery_requires_two_stable_real_frames(self):
        self.task._layout_valid = False
        self.operator.rectangle_detect = Mock(side_effect=[boxes(), boxes()[:1]])
        self.task.refresh_character(equip=False)
        self.assertFalse(self.task._layout_valid)
        self.assertEqual(self.operator.rectangle_detect.call_count,2)
        self.task.get_off_field_area.assert_not_called()

    def test_alternative_recovery_uses_actual_candidates_twice(self):
        self.task._layout_valid = False
        self.task._set_shop_open = Mock(return_value=True)
        self.operator.screenshot = Mock(return_value=Image.new("RGB",(1920,1080)))
        candidates = Mock(return_value=boxes())
        api = list(self.task._vision.layout_api); api[1] = candidates
        self.task._vision.layout_api = tuple(api)
        self.task.refresh_character(equip=False,recover_layout=True)
        self.assertTrue(self.task._layout_valid)
        self.assertEqual(candidates.call_count,2)
        self.task.get_off_field_area.assert_called_once()
        self.assertTrue(any(name=="move" for name,_,_ in self.operator.calls))

    def read_recovery_sequence(self, frames):
        self.operator.screenshot = Mock(return_value=Image.new("RGB", (1920, 1080)))
        candidates = Mock(side_effect=frames)
        api = list(self.task._vision.layout_api)
        api[1] = candidates
        self.task._vision.layout_api = tuple(api)
        result = self.task._vision.read_backend_layout(self.old, recover=True)
        return result, candidates

    def test_intermittent_miss_recovers_only_after_two_consecutive_complete_frames(self):
        result, candidates = self.read_recovery_sequence(
            [boxes(), boxes()[1:], boxes(), boxes()])
        self.assertTrue(result.valid, result.reason)
        self.assertEqual(result.positions, self.old)
        self.assertEqual(candidates.call_count, 4)
        self.assertEqual(self.task._vision.last_layout_diagnostics["layout_recovery_frames"], 4)
        self.assertEqual(self.operator.calls, [("sleep", (0.2,), {})] * 3)

    def test_separated_complete_frames_cannot_confirm_layout(self):
        result, candidates = self.read_recovery_sequence(
            [boxes(), boxes()[1:], boxes(), boxes()[1:]])
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "layout_not_stable")
        self.assertEqual(candidates.call_count, 4)
        self.assertEqual(self.task._vision.last_layout_diagnostics["layout_second_evidence"],
                         "recovery_missing_anchor")

    def test_persistent_missing_border_stops_at_four_frames(self):
        result, candidates = self.read_recovery_sequence([boxes()[1:]] * 4)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "recovery_missing_anchor")
        self.assertEqual(candidates.call_count, 4)

    def test_single_complete_final_frame_does_not_confirm_layout(self):
        result, candidates = self.read_recovery_sequence([boxes()[1:]] * 3 + [boxes()])
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "layout_not_stable")
        self.assertEqual(candidates.call_count, 4)

    def test_recovery_keeps_original_anchors_when_candidates_move(self):
        shifted = lambda offset: boxes(tuple((x + offset, y, w, h) for x, y, w, h in RECTS))
        result, candidates = self.read_recovery_sequence(
            [boxes(), shifted(5), shifted(10), shifted(15)])
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "layout_not_stable")
        self.assertEqual(candidates.call_count, 4)
        self.assertTrue(all(call.kwargs["previous_positions"] == self.old
                            for call in candidates.call_args_list))

    def test_stop_during_recovery_wait_does_not_take_another_frame(self):
        self.operator.sleep = Mock(side_effect=lambda seconds: self.operator.stop_event.set())
        with self.assertRaises(self.module.ThreadStoppedError):
            self.read_recovery_sequence([boxes()[1:]])
        self.assertEqual(self.operator.screenshot.call_count, 1)

    def test_recovered_anchor_shift_revises_coordinates_actually_used_by_actions(self):
        self.task._layout_valid=False
        # The current candidate matches recent anchors, but those anchors differ
        # from the coordinates retained by the action layer.
        self.task.off_field_area=[(x-0.005,y) for x,y in self.old]
        self.task._set_shop_open=Mock(return_value=True)
        self.operator.screenshot=Mock(return_value=Image.new("RGB",(1920,1080)))
        api=list(self.task._vision.layout_api); api[1]=Mock(return_value=boxes())
        self.task._vision.layout_api=tuple(api)
        revision=self.task._layout_revision
        self.task.refresh_character(equip=False,recover_layout=True)
        self.assertEqual(tuple(self.task.off_field_area),self.old)
        self.assertEqual(self.task._layout_revision,revision+1)

    def test_repeated_failure_gets_one_meaningful_alternative_before_stop(self):
        self.task._layout_valid = False
        self.task._bench_dirty = False
        self.task._placement_pending = False
        self.task._refresh_dirty_field = Mock()
        self.task.update_max_team_size = Mock()
        self.task.place_character = Mock()
        self.task._population_conflict = Mock(return_value=None)
        self.task.refresh_backend_character = Mock()
        self.task.get_in_hand_area = Mock()
        self.task._vision.capture_sample = Mock()
        blocked = self.module.PreparationResult(self.module.Readiness.BLOCKED,"backend_layout_not_confirmed")
        self.task._assess_preparation = Mock(return_value=blocked)
        result = self.task.prepare_for_battle()
        self.assertEqual(result.reason,"preparation_no_progress")
        self.assertEqual(self.task.refresh_backend_character.call_count,2)
        self.assertEqual([c.kwargs["recover_layout"] for c in self.task.refresh_backend_character.call_args_list],[False,True])
        self.task._vision.capture_layout_failure.assert_called_with("backend_layout_not_confirmed",terminal=True)

    def test_diagnostics_keep_sorted_centers_and_gap_reason_evidence(self):
        d=self.module.layout_diagnostics(boxes(RECTS[:2]+RECTS[3:]),(1920,1080),previous_positions=self.old)
        self.assertEqual(d["layout_candidate_count"],5)
        self.assertEqual(len(d["layout_gaps"]),4)
        self.assertGreater(max(d["layout_gaps"]),250)

    def test_fresh_partial_row_probes_never_certify_missing_slot(self):
        partial = boxes(RECTS[:1] + RECTS[2:])
        probes = self.module.backend_probe_positions(partial,(1920,1080))
        self.assertEqual(len(probes),6)
        self.assertFalse(self.module.validate_backend_layout(partial,(1920,1080)).valid)
        self.assertFalse(self.module.revalidate_backend_layout(partial,(1920,1080),previous_positions=probes).valid)

    def test_bad_partial_row_does_not_generate_probes(self):
        self.assertEqual(self.module.backend_probe_positions(boxes()[:1],(1920,1080)),())
        shifted = boxes(tuple((x+100,y,w,h) for x,y,w,h in RECTS))
        self.assertEqual(self.module.backend_probe_positions(shifted,(1920,1080)),())

    def test_restart_without_old_layout_can_recover_real_stop_borders(self):
        try:
            import cv2
        except ImportError:
            self.skipTest("Optional OpenCV dependency unavailable")
        paths=list((REPLAY_ROOT / "layout_recovery").rglob(
            "preparation_blocked.png"))
        if not paths:
            self.skipTest("Historical user snapshot not available in this checkout")
        self.task._confirmed_layout_positions = ()
        self.task._layout_valid = False
        self.task._set_shop_open = Mock(return_value=True)
        with Image.open(paths[0]) as im:
            self.operator.screenshot = Mock(side_effect=lambda: im.copy())
            self.task.refresh_character(equip=False,recover_layout=True)
        self.assertTrue(self.task._layout_valid)
        self.assertEqual(len(self.task._confirmed_layout_positions),6)
        self.assertEqual(self.operator.screenshot.call_count,2)
        self.task.get_off_field_area.assert_called_once()

    def test_real_stop_snapshot_recovery_preserves_original_geometry_gate(self):
        try:
            import cv2
        except ImportError:
            self.skipTest("Optional OpenCV dependency unavailable")
        candidates=list((REPLAY_ROOT / "layout_recovery").rglob(
            "preparation_blocked.png"))
        if not candidates:
            self.skipTest("Historical user snapshot not available in this checkout")
        with Image.open(candidates[0]) as im:
            actual=self.module.backend_rectangle_candidates(im,previous_positions=self.old)
            result=self.module.revalidate_backend_layout(actual,im.size,previous_positions=self.old)
        self.assertTrue(result.valid,result.reason)
        self.assertEqual(len(result.positions),6)
        self.assertFalse(result.changed)
        # Acceptance certifies borders only: no card identity or EMPTY inference.
        self.assertEqual(self.task._observations["off_field"][0].state,self.logic.SlotState.UNKNOWN)

    def test_latest_failure_snapshots_have_real_six_slot_borders(self):
        try:
            import cv2
        except ImportError:
            self.skipTest("Optional OpenCV dependency unavailable")
        snapshot_dir = (REPLAY_ROOT / "layout_recovery")
        names = (
            "invalid_backend_layout_row_boundary_incomplete",
            "invalid_backend_layout_layout_not_stable",
            "last_backend_layout",
        )
        if not all((snapshot_dir / (name + ".png")).exists() for name in names):
            self.skipTest("User failure snapshots not available in this checkout")
        for name in names:
            with self.subTest(snapshot=name):
                metadata = json.loads((snapshot_dir / (name + ".json")).read_text(encoding="utf-8"))
                old = metadata["previous_layout_positions"]
                with Image.open(snapshot_dir / (name + ".png")) as frame:
                    self.operator.screenshot = Mock(side_effect=lambda: frame.copy())
                    result = self.task._vision.read_backend_layout(old, recover=True)
                self.assertTrue(result.valid, result.reason)
                self.assertEqual(len(result.positions), 6)
                self.assertEqual(self.operator.screenshot.call_count, 2)


class LayoutDiagnosticRetentionTests(unittest.TestCase):
    def test_fixed_latest_and_terminal_pairs_survive_history_quota(self):
        module,_,_,names=fixture.load_isolated_task()
        self.addCleanup(lambda: [sys.modules.pop(name,None) for name in names])
        with tempfile.TemporaryDirectory() as temp:
            op=fixture.FakeOperator()
            op.screenshot=Mock(return_value=Image.new("RGB",(1920,1080)))
            v=module.CurrencyWarsVision(op,Path(temp)/"profile.json",Path(temp)/"samples",max_samples=1)
            v.begin_sample_scope("game","run",critical_reserve=0)
            v.last_layout_diagnostics=module.layout_diagnostics(boxes(),(1920,1080))
            first=v.capture_layout_failure("incomplete_slot_count")
            latest=v.capture_layout_failure("non_contiguous_slots")
            self.assertEqual(first,latest)
            self.assertEqual(json.loads(latest.with_suffix(".json").read_text())['reason'],"non_contiguous_slots")
            terminal=v.capture_layout_failure("backend_layout_not_confirmed",terminal=True)
            v.capture_layout_failure("incomplete_slot_count")
            payload=json.loads(terminal.with_suffix(".json").read_text())
            self.assertEqual(payload['reason'],"backend_layout_not_confirmed")
            self.assertEqual(payload['layout_candidate_count'],6)
            self.assertTrue(payload['terminal'])
            self.assertEqual(len(list(v.sample_dir.glob('*.png'))),3)


if __name__ == "__main__":
    unittest.main()
