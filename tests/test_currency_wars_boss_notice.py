"""Strong-enemy notices are positive post-battle evidence, then close once.

All gameplay observations, input and time are fake. The optional final case
replays the real 20:12 timeout screenshot without opening a game window.
"""
from __future__ import annotations

from pathlib import Path
from tests.currency_wars_replays import REPLAY_ROOT, require_frames
import unittest
from unittest.mock import Mock

import test_currency_wars_post_battle_stage as stage_tests
from test_currency_wars_flow import FakeBox


class CurrencyWarsBossNoticeTests(unittest.TestCase):
    screen = stage_tests.CurrencyWarsPostBattleStageTests.screen
    assert_no_recovery = stage_tests.CurrencyWarsPostBattleStageTests.assert_no_recovery
    CONTINUE_POINT = stage_tests.CurrencyWarsPostBattleStageTests.CONTINUE_POINT
    ACCELERATE_POINT = stage_tests.CurrencyWarsPostBattleStageTests.ACCELERATE_POINT
    input_clicks = stage_tests.CurrencyWarsPostBattleStageTests.input_clicks
    CLOSE_POINT = (0.5, 0.70)

    def setUp(self):
        stage_tests.CurrencyWarsPostBattleStageTests.setUp(self)
        self.dismissed = False
        self.phase = lambda: "preparation" if self.dismissed else (
            "reward" if self.elapsed < 5 else "boss_notice")
        self.operator.locate_any.side_effect = self.locate_stage
        self.operator.locate.side_effect = self.locate_control
        self.task._vision.read_battle_screen.side_effect = lambda: self.screen(
            "result_animation" if self.phase() == "reward" else "unknown")

    def locate_stage(self, images, **kwargs):
        if self.phase() == "boss_notice" and self.module.CWIMG.CLICK_BLANK in images:
            target = self.module.CWIMG.CLICK_BLANK
            return images.index(target), FakeBox(source=target)
        return stage_tests.CurrencyWarsPostBattleStageTests.locate_stage(self, images, **kwargs)

    def locate_control(self, image, **kwargs):
        if image == self.module.CWIMG.CLICK_BLANK and self.phase() == "boss_notice":
            return FakeBox(source=image)
        return stage_tests.CurrencyWarsPostBattleStageTests.locate_control(self, image, **kwargs)

    def dismiss_on_click(self):
        click = self.operator.click_point

        def close_notice(*args, **kwargs):
            if args[:2] == self.CLOSE_POINT:
                self.dismissed = True
            return click(*args, **kwargs)

        self.operator.click_point = Mock(side_effect=close_notice)

    def assert_departure_failure(self):
        self.task._vision.capture_sample.assert_called_once()
        self.assertEqual(self.task._vision.capture_sample.call_args.args[0],
                         "boss_notice_departure_timeout")
        self.assertEqual([args[:2] for args in self.input_clicks()], [self.CLOSE_POINT])
        self.assert_no_recovery()

    def test_visible_notice_over_preparation_takes_priority(self):
        visible = {self.module.CWIMG.CLICK_BLANK, self.module.CWIMG.PREPARATION_STAGE}

        def first_visible(images, **kwargs):
            target = next((image for image in images if image in visible), None)
            return (images.index(target), FakeBox(source=target)) if target else (-1, None)

        self.operator.locate_any.side_effect = first_visible
        self.assertEqual(self.task._post_battle_stage(allow_preparation=True),
                         self.module.CWIMG.CLICK_BLANK)
        self.assertEqual(self.input_clicks(), [])

    def test_reward_advances_to_notice_without_continue(self):
        self.assertTrue(self.task.battle())
        self.assertGreaterEqual(self.elapsed, 5.5)
        self.assertLess(self.elapsed, self.task.REWARD_TRANSITION_TIMEOUT)
        self.assertEqual(self.input_clicks(), [])
        self.assertNotIn("v", self.operator.keys())
        self.assert_no_recovery()
        self.task._vision.capture_sample.assert_not_called()

    def test_notice_without_q_or_reward_is_positive_entry_completion(self):
        self.phase = lambda: "boss_notice"
        self.assertTrue(self.task.battle())
        self.assertGreaterEqual(self.elapsed, 0.5)
        self.assertEqual(self.input_clicks(), [])
        self.assertEqual(self.operator.keys(), [])
        self.assert_no_recovery()
        self.task._vision.capture_sample.assert_not_called()

    def test_notice_during_combat_is_positive_settlement_evidence(self):
        self.phase = lambda: "boss_notice"
        self.assertEqual(self.task._wait_battle_result(in_combat=True), (None, None, True))
        self.assertGreaterEqual(self.elapsed, 0.5)
        self.assertEqual(self.input_clicks(), [])
        self.task._vision.capture_sample.assert_not_called()

    def test_handoff_closes_notice_once_then_confirms_preparation(self):
        self.assertTrue(self.task.battle())
        self.assertEqual(self.input_clicks(), [])
        self.dismiss_on_click()
        self.operator.wait_any_img.side_effect = self.locate_stage
        self.task.handle_stage_transitioned = Mock(return_value=True)
        self.assertTrue(self.task.stage_transition())
        self.assertTrue(self.dismissed)
        self.assertEqual([args[:2] for args in self.input_clicks()], [self.CLOSE_POINT])
        self.task.handle_stage_transitioned.assert_called_once()
        self.task._vision.capture_sample.assert_not_called()
        self.assert_no_recovery()

    def test_restart_locates_notice_and_recovers_to_preparation_without_battle(self):
        self.phase = lambda: "preparation" if self.dismissed else "boss_notice"
        self.operator.wait_any_img.side_effect = self.locate_stage
        self.assertEqual(self.task.page_locate(), self.module.CurrencyWarsPage.RECOVERY)
        self.assertEqual(self.task._recovery_page, "node")
        self.assertEqual(self.input_clicks(), [])
        self.dismiss_on_click()
        self.task.handle_stage_transitioned = Mock(return_value=True)
        self.assertTrue(self.task._recover_live_page())
        self.assertEqual([args[:2] for args in self.input_clicks()], [self.CLOSE_POINT])
        self.assertFalse(any(name == "click_box" for name, _, _ in self.operator.calls))
        self.assertEqual(self.operator.keys(), [])
        self.task._vision.capture_sample.assert_not_called()

    def test_single_notice_frame_does_not_confirm_entry(self):
        self.phase = lambda: "boss_notice" if self.elapsed == 0 else "unknown"
        self.clock_step = 60
        with self.assertRaisesRegex(RuntimeError, "entry_timeout"):
            self.task.battle()
        self.assertGreaterEqual(self.elapsed, self.task.BATTLE_TIMEOUT)
        self.assertEqual(self.input_clicks(), [])
        self.assert_no_recovery()

    def test_single_notice_frame_after_reward_does_not_confirm_settlement(self):
        self.phase = lambda: ("reward" if self.elapsed < 5 else
                              "boss_notice" if self.elapsed == 5 else "unknown")
        with self.assertRaisesRegex(RuntimeError, "result_timeout"):
            self.task.battle()
        self.assertEqual(self.input_clicks(), [])
        self.assert_no_recovery()
        self.task._vision.capture_sample.assert_called_once()
        self.assertEqual(self.task._vision.capture_sample.call_args.args[0],
                         "battle_result_timeout")

    def test_stop_between_notice_observations_prevents_handoff(self):
        self.phase = lambda: "boss_notice"
        advance = self.operator.sleep

        def stop_after_first_probe(seconds):
            advance(seconds)
            self.operator.stop_event.set()

        self.operator.sleep = stop_after_first_probe
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task.battle()
        self.assertEqual(self.input_clicks(), [])
        self.assert_no_recovery()
        self.task._vision.capture_sample.assert_not_called()

    def test_notice_that_never_closes_has_bounded_failure_without_reclicks(self):
        self.phase = lambda: "boss_notice"
        with self.assertRaisesRegex(RuntimeError, "强敌提示确认后仍未退场"):
            self.task.handle_click_blank(None)
        self.assertGreaterEqual(self.elapsed, self.task.ENTRY_TRANSITION_TIMEOUT)
        self.assertLessEqual(self.elapsed, self.task.ENTRY_TRANSITION_TIMEOUT + 0.5)
        self.assert_departure_failure()

    def test_unknown_after_close_is_not_positive_departure(self):
        self.phase = lambda: "unknown" if self.dismissed else "boss_notice"
        self.dismiss_on_click()
        with self.assertRaisesRegex(RuntimeError, "强敌提示确认后仍未退场"):
            self.task.handle_click_blank(None)
        self.assertGreaterEqual(self.elapsed, self.task.ENTRY_TRANSITION_TIMEOUT)
        self.assert_departure_failure()

    def test_one_preparation_frame_then_notice_reappears_does_not_confirm_departure(self):
        self.phase = lambda: ("preparation" if self.dismissed and self.elapsed == 0
                              else "boss_notice")
        self.dismiss_on_click()
        with self.assertRaisesRegex(RuntimeError, "强敌提示确认后仍未退场"):
            self.task.handle_click_blank(None)
        self.assertGreaterEqual(self.elapsed, self.task.ENTRY_TRANSITION_TIMEOUT)
        self.assert_departure_failure()

    def test_preparation_departure_requires_two_consecutive_frames(self):
        self.phase = lambda: "preparation" if self.dismissed else "boss_notice"
        self.dismiss_on_click()
        self.assertFalse(self.task.handle_click_blank(None))
        self.assertGreaterEqual(self.elapsed, 0.5)
        self.assertEqual([args[:2] for args in self.input_clicks()], [self.CLOSE_POINT])
        self.task._vision.capture_sample.assert_not_called()

    def test_stop_during_notice_departure_wait_propagates_without_reclick(self):
        self.phase = lambda: "boss_notice"
        advance = self.operator.sleep

        def stop_after_close(seconds):
            advance(seconds)
            self.operator.stop_event.set()

        self.operator.sleep = stop_after_close
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task.handle_click_blank(None)
        self.assertEqual([args[:2] for args in self.input_clicks()], [self.CLOSE_POINT])
        self.task._vision.capture_sample.assert_not_called()
        self.assert_no_recovery()

    def test_already_stopped_never_closes_notice(self):
        self.phase = lambda: "boss_notice"
        self.operator.stop_event.set()
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task.handle_click_blank(None)
        self.assertEqual(self.input_clicks(), [])
        self.task._vision.capture_sample.assert_not_called()

    def test_failed_close_click_stops_without_further_input(self):
        self.phase = lambda: "boss_notice"

        def failed_click(*args, **kwargs):
            self.operator.record("click", *args, **kwargs)
            return False

        self.operator.click_point = Mock(side_effect=failed_click)
        with self.assertRaisesRegex(RuntimeError, "强敌提示关闭失败"):
            self.task.handle_click_blank(None)
        self.assertEqual([name for name, _, _ in self.operator.calls], ["click"])
        self.assertEqual(self.elapsed, 0)
        self.task._vision.capture_sample.assert_not_called()
        self.assert_no_recovery()

    def test_stale_notice_title_is_reobserved_without_clicking(self):
        self.phase = lambda: "unknown"
        self.assertFalse(self.task.handle_click_blank(None))
        self.operator.locate.assert_called_once_with(self.module.CWIMG.CLICK_BLANK, trace=False)
        self.assertEqual(self.input_clicks(), [])
        self.task._vision.capture_sample.assert_not_called()


class CurrencyWarsBossNoticeScreenshotTests(unittest.TestCase):
    def test_real_2012_timeout_screenshot_matches_notice_template_above_point_nine(self):
        try:
            import cv2
            import numpy as np
        except ImportError as error:
            self.skipTest("Optional offline screenshot verification needs OpenCV: " + str(error))
        root = Path(__file__).resolve().parents[1]
        template_path = root / "resources/img/currency_wars/click_blank.png"
        screenshot_path = REPLAY_ROOT / "boss_notice.png"
        if not template_path.is_file() or not screenshot_path.is_file():
            self.skipTest("Real timeout screenshot is a local diagnostic artifact")
        # imdecode with fromfile supports the Chinese path on Windows.
        template = cv2.imdecode(np.fromfile(template_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        screenshot = cv2.imdecode(np.fromfile(screenshot_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        self.assertIsNotNone(template)
        self.assertIsNotNone(screenshot)
        scores = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        maximum = float(cv2.minMaxLoc(scores)[1])
        self.assertGreater(maximum, 0.9, "Real strong-enemy notice template score: " + str(maximum))


if __name__ == "__main__":
    unittest.main()
