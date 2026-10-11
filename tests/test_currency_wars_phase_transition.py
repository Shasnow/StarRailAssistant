"""Delayed stage and event transitions with fake clocks and game input."""
from __future__ import annotations

import sys
import unittest
from unittest.mock import Mock, patch

from test_currency_wars_flow import FakeBox, FakeOperator, load_isolated_task


class CurrencyWarsPhaseTransitionTests(unittest.TestCase):
    def setUp(self):
        self.module, _, _, names = load_isolated_task()
        self.addCleanup(lambda: [sys.modules.pop(name, None) for name in names])
        self.operator = FakeOperator()
        self.task = self.module.CurrencyWars(self.operator, runtimes=1)
        self.task._vision.capture_sample = Mock()
        self.task.handle_stage_transitioned = Mock(return_value=True)
        self.elapsed = 0.0
        self.current_stage = None
        self.operator.locate_any = Mock(side_effect=self.recheck_current_stage)
        original_sleep = self.operator.sleep

        def advance_sleep(seconds):
            self.elapsed += seconds
            original_sleep(seconds)

        self.operator.sleep = advance_sleep
        clock = patch.object(self.module.time, "monotonic", side_effect=lambda: self.elapsed)
        clock.start()
        self.addCleanup(clock.stop)

    def recheck_current_stage(self, images, **kwargs):
        if self.current_stage in images:
            return images.index(self.current_stage), FakeBox(source=self.current_stage)
        return -1, None

    def fold_after_45_seconds(self, images, *, timeout, **kwargs):
        self.operator.sleep(min(max(0, 45 - self.elapsed), timeout))
        if self.elapsed >= 45:
            self.current_stage = self.module.CWIMG.FOLD
            return images.index(self.module.CWIMG.FOLD), FakeBox(source="FOLD")
        return -1, None

    def test_initial_stage_target_after_45_seconds_is_stabilized_then_continued(self):
        self.operator.wait_any_img = Mock(side_effect=self.fold_after_45_seconds)
        self.assertTrue(self.task.stage_transition())
        self.assertGreaterEqual(self.elapsed, 48)
        self.assertLessEqual(self.elapsed, 48.1)
        self.task.handle_stage_transitioned.assert_called_once()
        self.assertFalse(any(name in ("click", "click_box", "click_img")
                             for name, _, _ in self.operator.calls))

    def test_following_stage_target_can_arrive_45_seconds_after_event(self):
        event_done_at = []
        first = True

        def stage_sequence(images, *, timeout, **kwargs):
            nonlocal first
            if first:
                first = False
                self.current_stage = self.module.CWIMG.FORTUNE_TELLER
                return images.index(self.module.CWIMG.FORTUNE_TELLER), FakeBox(source="FORTUNE_TELLER")
            delay = event_done_at[0] + 45 - self.elapsed
            self.operator.sleep(min(max(0, delay), timeout))
            if self.elapsed >= event_done_at[0] + 45:
                self.current_stage = self.module.CWIMG.FOLD
                return images.index(self.module.CWIMG.FOLD), FakeBox(source="FOLD")
            return -1, None

        self.operator.wait_any_img = Mock(side_effect=stage_sequence)
        self.task._handle_fortune_teller_after_battle = Mock(
            side_effect=lambda previous: event_done_at.append(self.elapsed) or False)
        self.assertTrue(self.task.stage_transition())
        self.task._handle_fortune_teller_after_battle.assert_called_once_with(None)
        self.task.handle_stage_transitioned.assert_called_once()
        self.assertGreaterEqual(self.elapsed - event_done_at[0], 48)
        self.assertEqual(self.operator.wait_any_img.call_count, 2)

    def test_stop_after_stage_wait_prevents_stabilization_and_handler(self):
        def stop_at_stage_arrival(images, **kwargs):
            self.operator.sleep(12)
            self.operator.stop_event.set()
            return images.index(self.module.CWIMG.FOLD), FakeBox(source="FOLD")

        self.operator.wait_any_img = Mock(side_effect=stop_at_stage_arrival)
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task.stage_transition()
        self.task.handle_stage_transitioned.assert_not_called()
        self.assertEqual(self.elapsed, 12)
        self.task._vision.capture_sample.assert_not_called()

    def test_stop_during_stage_stabilization_prevents_handler(self):
        self.current_stage = self.module.CWIMG.FOLD
        self.operator.wait_any_img = Mock(return_value=(3, FakeBox(source="FOLD")))
        advance_sleep = self.operator.sleep

        def stop_while_settling(seconds):
            advance_sleep(seconds)
            if self.elapsed >= 0.4:
                self.operator.stop_event.set()

        self.operator.sleep = stop_while_settling
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task.stage_transition()
        self.task.handle_stage_transitioned.assert_not_called()
        self.assertLess(self.elapsed, 3)
        self.task._vision.capture_sample.assert_not_called()

    def test_stage_changed_during_stabilization_never_calls_the_old_handler(self):
        first = True

        def stage_sequence(images, **kwargs):
            nonlocal first
            target = self.module.CWIMG.REPLENISH_STAGE if first else self.module.CWIMG.FOLD
            first = False
            return images.index(target), FakeBox(source=target)

        def actual_stage_after_pause(images, **kwargs):
            target = self.module.CWIMG.FOLD if self.elapsed >= 3 else self.module.CWIMG.REPLENISH_STAGE
            return images.index(target), FakeBox(source=target)

        self.operator.wait_any_img = Mock(side_effect=stage_sequence)
        self.operator.locate_any = Mock(side_effect=actual_stage_after_pause)
        self.task.handle_replenish_stage = Mock(return_value=False)
        self.assertTrue(self.task.stage_transition())
        self.task.handle_replenish_stage.assert_not_called()
        self.task.handle_stage_transitioned.assert_called_once()
        self.assertGreaterEqual(self.elapsed, 6)
        self.assertEqual(self.operator.wait_any_img.call_count, 2)
        self.assertFalse(any(name in ("click", "click_box", "click_img")
                             for name, _, _ in self.operator.calls))

    def test_unknown_stage_rechecks_use_one_total_deadline(self):
        self.operator.wait_any_img = Mock(return_value=(3, FakeBox(source="FOLD")))
        self.operator.locate_any = Mock(return_value=(-1, None))
        with self.assertRaisesRegex(RuntimeError, "关卡状态检测超时"):
            self.task.stage_transition()
        self.assertGreaterEqual(self.elapsed, 60)
        self.assertLessEqual(self.elapsed, 60.1)
        self.task.handle_stage_transitioned.assert_not_called()
        self.assertFalse(any(name in ("click", "click_box", "click_img")
                             for name, _, _ in self.operator.calls))

    def test_selection_event_can_disappear_after_ten_seconds_without_reclicking(self):
        option = FakeBox(source="银狼LV.999")
        self.operator.ocr_boxes = Mock(return_value=[option])

        def confirm_once(image, **kwargs):
            self.operator.record("click_img", image, **kwargs)
            return image == self.module.CWIMG.CONFIRM_SELECTION

        def event_screen(image, **kwargs):
            if image == self.module.CWIMG.CONFIRM_SELECTION and self.elapsed < 10:
                return FakeBox(source="CONFIRM_SELECTION")
            if image == self.module.CWIMG.PREPARATION_STAGE and self.elapsed >= 10:
                return FakeBox(source="PREPARATION_STAGE")
            return None

        self.operator.click_img = Mock(side_effect=confirm_once)
        self.operator.locate = Mock(side_effect=event_screen)
        self.task.detect_special_event = Mock(
            side_effect=lambda: "头号玩家" if self.elapsed < 10 else "")
        self.assertTrue(self.task._handle_selection_event(
            (0.22, 0.34, 0.85, 0.4), "银狼", "头号玩家"))
        self.assertGreaterEqual(self.elapsed, 10)
        self.assertLess(self.elapsed, 15)
        self.assertEqual([args[0] for name, args, _ in self.operator.calls if name == "click_box"], [option])
        self.operator.click_img.assert_called_once()
        self.task._vision.capture_sample.assert_not_called()


if __name__ == "__main__":
    unittest.main()
