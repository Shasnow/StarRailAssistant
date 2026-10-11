"""Reward-animation regressions with positive screen evidence and fake time.

The production battle flow must distinguish an ended fight from a result that
is ready to continue. No real screenshots, input or waits are performed here.
"""
from __future__ import annotations

import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from test_currency_wars_flow import FakeBox, FakeOperator, load_isolated_task


class CurrencyWarsBattleResultTests(unittest.TestCase):
    CONTINUE_POINT = (0.5, 0.829)
    ACCELERATE_POINT = (0.5, 0.65)

    def setUp(self):
        self.module, self.characters, self.logic, names = load_isolated_task()
        self.addCleanup(lambda: [sys.modules.pop(name, None) for name in names])
        self.operator = FakeOperator()
        self.task = self.module.CurrencyWars(self.operator, runtimes=1)
        self.task.is_running = True
        self.task._vision.capture_sample = Mock()
        self.task.refresh_character = Mock()
        self.task.place_character = Mock()
        self.task.abort_and_return = Mock()
        self.module.logger = Mock()
        self.elapsed = 0.0
        self.clock_step = None
        original_sleep = self.operator.sleep

        def advance_sleep(seconds):
            self.elapsed += self.clock_step if self.clock_step is not None else seconds
            original_sleep(seconds)

        self.operator.sleep = advance_sleep
        clock = patch.object(self.module.time, "monotonic", side_effect=lambda: self.elapsed)
        clock.start()
        self.addCleanup(clock.stop)
        self.battle_button = FakeBox(source="BATTLE")
        self.continue_button = FakeBox(source="CONTINUE")
        self.operator.wait_any_img = Mock(return_value=(0, self.battle_button))
        self.operator.wait_img = Mock(return_value=self.battle_button)
        self.operator.locate_any = Mock(return_value=(-1, None))
        self.operator.locate = Mock(return_value=None)
        self.task._vision.read_battle_screen = Mock(return_value=self.screen("unknown"))
        character = self.characters.Characters.get_character("灵砂")
        self.task._observations["on_field"][0] = self.logic.SlotObservation(
            0, self.logic.SlotState.KNOWN, character=character, occupied=True,
            evidence="name_match", revision=1, stars=1)
        self.task.on_field_character[0] = character

    def screen(self, state, *, accelerate=False, point=None):
        return SimpleNamespace(
            state=state,
            continue_point=(point if point is not None else self.CONTINUE_POINT)
            if state == "result_ready" else None,
            accelerate_point=self.ACCELERATE_POINT if accelerate else None,
            evidence="challenge_header" if state != "unknown" else "no_screen_evidence",
            raw_text="挑战成功 继续挑战" if state == "result_ready" else (
                "挑战成功 点击空白加速" if accelerate else
                "挑战成功" if state == "result_animation" else ""),
        )

    def point_clicks(self, point):
        return [call for call in self.operator.calls if call[0] == "click"
                and call[1][:2] == point]

    def assert_no_recovery(self):
        self.assertNotIn("esc", self.operator.keys())
        self.assertFalse(any(name == "click_img" and args[0] == self.module.CWIMG.RETREAT
                             for name, args, _ in self.operator.calls))
        self.task.abort_and_return.assert_not_called()

    def assert_failure_sample(self, reason):
        self.task._vision.capture_sample.assert_called_once()
        self.assertEqual(self.task._vision.capture_sample.call_args.args[0], "battle_" + reason)

    def test_success_animation_without_q_waits_for_real_continue_point(self):
        animation = self.screen("result_animation", accelerate=True)
        ready = self.screen("result_ready")
        self.task._vision.read_battle_screen.side_effect = (
            lambda: animation if self.elapsed < 26 else ready)
        click_point = self.operator.click_point

        def click_only_when_ready(*args, **kwargs):
            if args[:2] == self.CONTINUE_POINT:
                self.assertGreaterEqual(self.elapsed, 26)
            return click_point(*args, **kwargs)

        self.operator.click_point = Mock(side_effect=click_only_when_ready)
        self.assertTrue(self.task.battle())
        self.assertEqual(len(self.point_clicks(self.ACCELERATE_POINT)), 1)
        self.assertEqual(len(self.point_clicks(self.CONTINUE_POINT)), 1)
        self.assertNotIn("v", self.operator.keys())
        self.assert_no_recovery()
        self.task._vision.capture_sample.assert_not_called()

    def test_success_header_without_accelerate_prompt_waits_without_blank_click(self):
        animation = self.screen("result_animation")
        ready = self.screen("result_ready", point=(0.55, 0.84))
        self.task._vision.read_battle_screen.side_effect = (
            lambda: animation if self.elapsed < 3 else ready)
        self.assertTrue(self.task.battle())
        self.assertEqual(len(self.point_clicks((0.55, 0.84))), 1)
        self.assertEqual(sum(name == "click" for name, _, _ in self.operator.calls), 1)
        self.assert_no_recovery()

    def test_success_animation_without_continue_times_out_as_result_not_entry(self):
        self.task._vision.read_battle_screen.return_value = self.screen(
            "result_animation", accelerate=True)
        with self.assertRaisesRegex(RuntimeError, "result_timeout"):
            self.task.battle()
        self.assertGreaterEqual(self.elapsed, 120)
        self.assertLessEqual(self.elapsed, 120.5)
        self.assertEqual(len(self.point_clicks(self.ACCELERATE_POINT)), 1)
        self.assertEqual(self.point_clicks(self.CONTINUE_POINT), [])
        self.assertNotIn("v", self.operator.keys())
        self.assert_no_recovery()
        self.assert_failure_sample("result_timeout")

    def test_reward_animation_can_wait_105_seconds_for_continue(self):
        self.task._vision.read_battle_screen.side_effect = lambda: self.screen(
            "result_animation" if self.elapsed < 105 else "result_ready")
        click_point = self.operator.click_point

        def continue_only_after_ready(*args, **kwargs):
            if args[:2] == self.CONTINUE_POINT:
                self.assertGreaterEqual(self.elapsed, 105)
            return click_point(*args, **kwargs)

        self.operator.click_point = Mock(side_effect=continue_only_after_ready)
        self.assertTrue(self.task.battle())
        self.assertGreaterEqual(self.elapsed, 105)
        self.assertEqual(len(self.point_clicks(self.CONTINUE_POINT)), 1)
        self.assertEqual(self.point_clicks(self.ACCELERATE_POINT), [])
        self.assertNotIn("v", self.operator.keys())
        self.assert_no_recovery()
        self.task._vision.capture_sample.assert_not_called()

    def test_unknown_after_click_still_has_bounded_entry_failure_without_continuation(self):
        # A disappeared BATTLE template and empty OCR are not positive evidence.
        # Probe latency is represented by a larger fake clock step, avoiding
        # hundreds of no-op input records while exercising the 600s deadline.
        self.clock_step = 10.0
        with self.assertRaisesRegex(RuntimeError, "entry_timeout"):
            self.task.battle()
        self.assertGreaterEqual(self.elapsed, 600)
        self.assertLessEqual(self.elapsed, 610)
        self.assertFalse(any(name == "click" for name, _, _ in self.operator.calls))
        self.assertNotIn("v", self.operator.keys())
        self.assert_no_recovery()
        self.assert_failure_sample("entry_timeout")

    def test_unknown_long_battle_can_finish_without_q_or_false_entry_timeout(self):
        def after_long_battle():
            if self.elapsed < 80:
                return self.screen("unknown")
            return self.screen("result_animation", accelerate=True) if self.elapsed < 84 else self.screen("result_ready")

        self.task._vision.read_battle_screen.side_effect = after_long_battle
        click_point = self.operator.click_point

        def continue_only_after_ready(*args, **kwargs):
            if args[:2] == self.CONTINUE_POINT:
                self.assertGreaterEqual(self.elapsed, 84)
            return click_point(*args, **kwargs)

        self.operator.click_point = Mock(side_effect=continue_only_after_ready)
        self.assertTrue(self.task.battle())
        self.assertGreaterEqual(self.elapsed, 84)
        self.assertEqual(len(self.point_clicks(self.ACCELERATE_POINT)), 1)
        self.assertEqual(len(self.point_clicks(self.CONTINUE_POINT)), 1)
        self.assertNotIn("v", self.operator.keys())
        self.assert_no_recovery()
        self.task._vision.capture_sample.assert_not_called()

    def test_q_then_success_switches_to_result_deadline_without_retreat(self):
        first = True

        def q_once(images, **kwargs):
            nonlocal first
            if first and self.module.IMG.Q in images:
                first = False
                return images.index(self.module.IMG.Q), FakeBox(source="Q")
            return -1, None

        self.operator.locate_any.side_effect = q_once
        self.task._vision.read_battle_screen.side_effect = lambda: self.screen(
            "unknown" if self.elapsed < 5 else "result_animation")
        with self.assertRaisesRegex(RuntimeError, "result_timeout"):
            self.task.battle()
        self.assertNotIn("v", self.operator.keys())
        self.assertGreaterEqual(self.elapsed, 125)
        self.assertLessEqual(self.elapsed, 126)
        self.assertEqual(self.point_clicks(self.CONTINUE_POINT), [])
        self.assert_no_recovery()
        self.assert_failure_sample("result_timeout")

    def test_q_then_settle_template_with_unknown_ocr_has_result_timeout_without_retreat(self):
        first = True
        settled = FakeBox(source="SETTLE")

        def positive_q_then_settle(images, **kwargs):
            nonlocal first
            if first and self.module.IMG.Q in images:
                first = False
                return images.index(self.module.IMG.Q), FakeBox(source="Q")
            if self.module.CWIMG.SETTLE in images:
                return images.index(self.module.CWIMG.SETTLE), settled
            return -1, None

        self.operator.locate_any.side_effect = positive_q_then_settle
        self.operator.locate.side_effect = lambda image, **kwargs: (
            settled if image == self.module.CWIMG.SETTLE else None)
        with self.assertRaisesRegex(RuntimeError, "result_timeout"):
            self.task.battle()
        self.assertNotIn("v", self.operator.keys())
        self.assertGreaterEqual(self.elapsed, 120)
        self.assertLessEqual(self.elapsed, 120.5)
        self.assertFalse(any(name == "click" for name, _, _ in self.operator.calls))
        self.assert_no_recovery()
        self.assert_failure_sample("result_timeout")

    def test_stop_at_combat_result_deadline_prevents_timeout_recovery(self):
        first = True

        def q_once(images, **kwargs):
            nonlocal first
            if first and self.module.IMG.Q in images:
                first = False
                return images.index(self.module.IMG.Q), FakeBox(source="Q")
            return -1, None

        self.operator.locate_any.side_effect = q_once
        self.clock_step = 10.0
        advance_sleep = self.operator.sleep

        def stop_at_deadline(seconds):
            advance_sleep(seconds)
            if self.elapsed >= 600:
                self.operator.stop_event.set()

        self.operator.sleep = stop_at_deadline
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task.battle()
        self.assertNotIn("v", self.operator.keys())
        self.assert_no_recovery()
        self.assertFalse(any(name == "click" for name, _, _ in self.operator.calls))
        self.task._vision.capture_sample.assert_not_called()

    def test_direct_continue_uses_observed_coordinates_without_accelerate_or_q(self):
        point = (0.56, 0.81)
        self.task._vision.read_battle_screen.return_value = self.screen("result_ready", point=point)
        self.assertTrue(self.task.battle())
        self.assertEqual(len(self.point_clicks(point)), 1)
        self.assertEqual(sum(name == "click" for name, _, _ in self.operator.calls), 1)
        self.assertEqual(self.operator.keys(), [])
        self.assertLess(self.elapsed, 2)
        self.assert_no_recovery()

    def test_settle_template_is_animation_and_later_continue_template_is_clicked(self):
        def template_state(images, **kwargs):
            target = self.module.CWIMG.SETTLE if self.elapsed < 4 else self.module.CWIMG.CONTINUE
            box = FakeBox(source="SETTLE") if self.elapsed < 4 else self.continue_button
            return (images.index(target), box) if target in images else (-1, None)

        self.operator.locate_any.side_effect = template_state
        self.operator.locate.side_effect = lambda image, **kwargs: (
            self.continue_button if image == self.module.CWIMG.CONTINUE and self.elapsed >= 4 else None)
        click_box = self.operator.click_box

        def click_only_real_continue(box, **kwargs):
            if box is self.continue_button:
                self.assertGreaterEqual(self.elapsed, 4)
            self.assertNotEqual(box.source, "SETTLE")
            return click_box(box, **kwargs)

        self.operator.click_box = Mock(side_effect=click_only_real_continue)
        self.assertTrue(self.task.battle())
        self.assertEqual([args[0] for name, args, _ in self.operator.calls if name == "click_box"],
                         [self.battle_button, self.continue_button])
        self.assertFalse(any(name == "click" for name, _, _ in self.operator.calls))
        self.assertEqual(self.operator.keys(), [])

    def test_skip_success_animation_needs_actual_continue_without_frontline(self):
        self.task.reset_character()
        self.operator.wait_any_img.return_value = 1, self.battle_button
        self.task._vision.read_battle_screen.side_effect = lambda: self.screen(
            "result_animation" if self.elapsed < 3 else "result_ready", accelerate=self.elapsed < 3)
        self.assertTrue(self.task.battle())
        self.task.refresh_character.assert_not_called()
        self.task.place_character.assert_not_called()
        self.assertEqual(len(self.point_clicks(self.ACCELERATE_POINT)), 1)
        self.assertEqual(len(self.point_clicks(self.CONTINUE_POINT)), 1)
        self.assertEqual(self.operator.keys(), [])
        self.assert_no_recovery()

    def test_result_ready_without_continue_target_never_clicks(self):
        malformed = self.screen("result_ready")
        malformed.continue_point = None
        self.task._vision.read_battle_screen.return_value = malformed
        with self.assertRaisesRegex(RuntimeError, "result_timeout"):
            self.task._wait_battle_result()
        self.assertFalse(any(name == "click" for name, _, _ in self.operator.calls))
        self.assert_no_recovery()
        self.assert_failure_sample("result_timeout")

    def test_stop_during_reward_animation_propagates_without_continuing_or_recovery(self):
        self.task._vision.read_battle_screen.return_value = self.screen("result_animation")
        advance_sleep = self.operator.sleep

        def stop_during_sleep(seconds):
            advance_sleep(seconds)
            self.operator.stop_event.set()

        self.operator.sleep = stop_during_sleep
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task.battle()
        self.assertFalse(any(name == "click" for name, _, _ in self.operator.calls))
        self.assert_no_recovery()
        self.task._vision.capture_sample.assert_not_called()


if __name__ == "__main__":
    unittest.main()
