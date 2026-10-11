"""Backend geometry must not certify occupancy or reuse stale slot indices.

Only the isolated flow loader is shared; this module does not inherit existing
TestCase classes or write production calibration/runtime data.
"""

from dataclasses import replace
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("_currency_wars_layout_flow_fixture",
                                            ROOT / "tests/test_currency_wars_flow.py")
fixture = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = fixture
spec.loader.exec_module(fixture)

# Measured six-slot rectangles; only geometry is replayed here. Any EMPTY states
# in the fake board are explicit test observations, never calibration templates.
SIX_RECTS = ((534, 599, 141, 141), (678, 599, 136, 141), (823, 599, 130, 141),
             (967, 599, 130, 141), (1106, 599, 136, 141), (1245, 599, 141, 141))
FIVE_RECTS = tuple((center - 70, 600, 140, 140) for center in (676, 818, 960, 1102, 1244))


def boxes(rects=SIX_RECTS):
    return [fixture.FakeBox(left=x, top=y, width=w, height=h) for x, y, w, h in rects]


class BackendLayoutIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.module, self.characters, self.logic, self.module_names = fixture.load_isolated_task()
        self.addCleanup(lambda: [sys.modules.pop(name, None) for name in self.module_names])
        self.operator = fixture.FakeOperator()
        self.task = self.module.CurrencyWars(self.operator, runtimes=1)
        self.task.is_running = True
        self.task._vision.capture_sample = Mock(return_value=None)
        # These cases exercise geometry after page authentication. The fake
        # operator has no preparation screenshot, so provide that prerequisite.
        self.task._set_shop_open = Mock(return_value=True)
        self.task.get_on_field_area = Mock()
        self.task.get_off_field_area = Mock()
        self.task._layout_valid = True
        for area in ("on_field", "off_field", "in_hand"):
            for index in range(len(self.task._observations[area])):
                self.observe(area, index)

    def character(self, name):
        return self.characters.Characters.get_character(name)

    def observation(self, index, character=None, *, state=None, evidence="explicit test observation"):
        state = state or (self.logic.SlotState.KNOWN if character is not None else self.logic.SlotState.EMPTY)
        return self.logic.SlotObservation(index, state, character=character,
            occupied=True if state == self.logic.SlotState.KNOWN else
                     False if state == self.logic.SlotState.EMPTY else None,
            evidence=evidence, revision=1, stars=1 if character else None)

    def observe(self, area, index, character=None, **kwargs):
        result = self.observation(index, character, **kwargs)
        self.task._set_observation(area, result)
        return result

    def reject_nonempty_layout(self):
        self.observe("on_field", 0, self.character("黑塔"))
        self.observe("off_field", 0, self.character("吉尔伽美什"))
        self.operator.rectangle_detect = Mock(return_value=boxes(SIX_RECTS[:1]))
        self.task.refresh_character(equip=False)

    def test_bad_nonempty_rectangles_preserve_coordinates_and_invalidate_backend_identity(self):
        before = tuple(self.task.off_field_area)
        revision = self.task._layout_revision
        self.reject_nonempty_layout()
        self.assertEqual(tuple(self.task.off_field_area), before)
        self.assertEqual(self.task._layout_revision, revision)
        self.assertFalse(self.task._layout_valid)
        self.assertTrue(all(o.state == self.logic.SlotState.UNKNOWN
                            for o in self.task._observations["off_field"]))
        self.task.get_off_field_area.assert_not_called()
        self.task._vision.capture_sample.assert_called_once()

    def test_bad_layout_rejects_backend_swap_without_dragging(self):
        self.reject_nonempty_layout()
        self.observe("in_hand", 0, self.character("符玄"))
        # Even separately reintroduced identity cannot bypass layout validity.
        self.observe("off_field", 0, self.character("吉尔伽美什"))
        self.operator.drag_to = Mock(return_value=True)
        self.assertFalse(self.task.swap_character_between_areas("in_hand", 0, "off_field", 0))
        self.assertEqual(self.task._last_move_result.reason, "backend_layout_not_confirmed")
        self.operator.drag_to.assert_not_called()
        self.assertIsNone(self.task._pending_move)

    def test_dirty_and_direct_backend_scans_cannot_promote_old_coordinates_when_layout_is_bad(self):
        self.reject_nonempty_layout()
        self.task._dirty_slots.add(("off_field", 0))
        self.operator.calls.clear()
        # If an old coordinate is read, this confident text would promote it.
        row = [([[0, 0], [100, 0], [100, 30], [0, 30]], "吉尔伽美什", 0.999)]
        self.operator.ocr_results = [row] * 12
        self.task._refresh_dirty_field()
        self.assertEqual(self.task._observations["off_field"][0].state, self.logic.SlotState.UNKNOWN)
        self.module.CurrencyWars.get_off_field_area(self.task, True, equip=False)
        self.assertTrue(all(o.state == self.logic.SlotState.UNKNOWN
                            for o in self.task._observations["off_field"]))
        self.assertFalse(any(name == "ocr" for name, _, _ in self.operator.calls))

    def test_bad_layout_blocks_normal_battle_before_clicking(self):
        self.reject_nonempty_layout()
        assessment = self.task._assess_preparation()
        self.assertEqual((assessment.state, assessment.reason),
                         (self.module.Readiness.BLOCKED, "backend_layout_not_confirmed"))
        button = fixture.FakeBox(source="BATTLE")
        self.operator.wait_any_img = Mock(return_value=(0, button))
        self.operator.click_box = Mock(return_value=True)
        self.task.prepare_for_battle = Mock(return_value=assessment)
        with self.assertRaises(RuntimeError):
            self.task.battle()
        self.operator.click_box.assert_not_called()

    def resolve_front_bench_pending(self, changed):
        source = self.observe("in_hand", 0, self.character("黑塔"))
        target = self.observe("on_field", 0, self.character("藿藿"))
        self.observe("off_field", 4, state=self.logic.SlotState.UNKNOWN)
        self.observe("in_hand", 8, state=self.logic.SlotState.UNKNOWN)
        self.task._pending_move = {"source": ("in_hand", 0), "target": ("on_field", 0),
            "source_before": source, "target_before": target, "layout": self.task._layout_revision,
            "positions": (self.task.in_hand_area[0], self.task.on_field_area[0])}
        self.task._placement_pending = True
        self.task._layout_revision += 1
        ends = {( "in_hand", 0): replace(target if changed else source, slot_index=0),
                ("on_field", 0): replace(source if changed else target, slot_index=0)}
        self.task._observe_slot = Mock(side_effect=lambda area, index, **kwargs: ends[(area, index)])
        self.task.refresh_character = Mock(side_effect=AssertionError("unrelated full scan"))
        self.task.get_in_hand_area = Mock(side_effect=AssertionError("unrelated bench scan"))
        self.assertTrue(self.task._resolve_pending_move())
        self.assertIsNone(self.task._pending_move)
        self.assertFalse(self.task._placement_pending)
        self.assertEqual(self.task._observe_slot.call_count, 2)
        self.task.refresh_character.assert_not_called()
        self.task.get_in_hand_area.assert_not_called()
        self.assertEqual(self.task._observations["off_field"][4].state, self.logic.SlotState.UNKNOWN)
        self.assertEqual(self.task._observations["in_hand"][8].state, self.logic.SlotState.UNKNOWN)
        return source, target

    def test_backend_revision_does_not_block_changed_front_bench_pending_with_unrelated_unknowns(self):
        source, target = self.resolve_front_bench_pending(True)
        self.assertEqual(self.task._last_move_result.status, self.module.MoveStatus.CONFIRMED_CHANGED)
        self.assertIs(self.task.in_hand_character[0], target.character)
        self.assertIs(self.task.on_field_character[0], source.character)

    def test_backend_revision_does_not_block_unchanged_front_bench_pending_with_unrelated_unknowns(self):
        self.resolve_front_bench_pending(False)
        self.assertEqual(self.task._last_move_result.status, self.module.MoveStatus.CONFIRMED_UNCHANGED)
        self.assertEqual(sum(self.task._move_failures.values()), 1)

    def test_stable_layout_change_requires_two_frames_and_fresh_observations_before_identity(self):
        for rects in (SIX_RECTS, FIVE_RECTS):
            with self.subTest(slot_count=len(rects)):
                self.task.off_field_area = list(self.task._default_off_field_area)
                self.task.off_field_character[:] = [None] * len(self.task.off_field_area)
                self.task._observations["off_field"] = [self.observation(i)
                    for i in range(len(self.task.off_field_area))]
                old = self.character("吉尔伽美什")
                new = self.character("符玄")
                self.observe("off_field", 0, old)
                self.task._dirty_slots.add(("off_field", 0))
                self.task._equipment_checked[old.name] = ("off_field", 0, 1)
                before_revision = self.task._layout_revision
                self.operator.rectangle_detect = Mock(side_effect=[boxes(rects), boxes(rects)])

                def reobserve(*args, **kwargs):
                    self.assertEqual(self.operator.rectangle_detect.call_count, 2)
                    self.assertTrue(all(o.state == self.logic.SlotState.UNKNOWN and o.evidence == "layout_changed"
                                        for o in self.task._observations["off_field"]))
                    self.assertEqual(self.task.off_field_character, [None] * len(rects))
                    self.assertNotIn(old.name, self.task._equipment_checked)
                    for index in range(len(rects)):
                        char = new if index == 0 else old if index == len(rects) - 1 else None
                        self.observe("off_field", index, char)

                self.task.get_off_field_area = Mock(side_effect=reobserve)
                self.task.refresh_character(equip=False)
                self.assertEqual(self.task._layout_revision, before_revision + 1)
                self.assertEqual(len(self.task.off_field_area), len(rects))
                self.assertIs(self.task.off_field_character[0], new)
                self.assertIs(self.task.off_field_character[-1], old)
                self.assertTrue(self.task._layout_valid)
                self.task.get_off_field_area.assert_called_once()

    def test_unstable_second_frame_cannot_commit_candidate_layout_or_rescan_old_indices(self):
        before = tuple(self.task.off_field_area)
        revision = self.task._layout_revision
        self.observe("off_field", 0, self.character("吉尔伽美什"))
        self.operator.rectangle_detect = Mock(side_effect=[boxes(), boxes(SIX_RECTS[:-1])])
        self.task.refresh_character(equip=False)
        self.assertEqual(self.operator.rectangle_detect.call_count, 2)
        self.assertEqual(tuple(self.task.off_field_area), before)
        self.assertEqual(self.task._layout_revision, revision)
        self.assertFalse(self.task._layout_valid)
        self.assertTrue(all(o.state == self.logic.SlotState.UNKNOWN for o in self.task._observations["off_field"]))
        self.task.get_off_field_area.assert_not_called()

    def test_stop_during_second_layout_frame_propagates_without_committing_layout(self):
        before = tuple(self.task.off_field_area)
        revision = self.task._layout_revision
        self.operator.rectangle_detect = Mock(side_effect=[boxes(), self.module.ThreadStoppedError("stopped")])
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task.refresh_character(equip=False)
        self.assertEqual(tuple(self.task.off_field_area), before)
        self.assertEqual(self.task._layout_revision, revision)
        self.task.get_off_field_area.assert_not_called()


if __name__ == "__main__":
    unittest.main()
