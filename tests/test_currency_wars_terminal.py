"""Terminal pages use observed controls and preserve wins across UI failures."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PIL import Image

from test_currency_wars_flow import FakeBox, FakeOperator, load_isolated_task
from test_currency_wars_battle_vision import vision, FakeOperator as VisionOperator, text
from test_currency_wars_health import FakeOperator as HealthOperator

from tests.currency_wars_replays import REPLAY_ROOT, OCR_ROOT

ROOT = Path(__file__).resolve().parents[1]
REAL_FINAL = REPLAY_ROOT / "final_summary.png"
REAL_SETTLE = REPLAY_ROOT / "final_settle.png"


class TerminalVisionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def make(self, rows):
        operator = VisionOperator(rows)
        task = vision.CurrencyWarsVision(operator, self.root / "profile.json", self.root / "samples", max_samples=0)
        task._terminal_template_point = Mock(side_effect=lambda frame, name: (.5, .83) if name == "next_step.png" else None)
        return task, operator

    def test_final_title_labels_and_strong_template_accept_truncated_action(self):
        for title, outcome in (("挑战成功", "success"), ("挑战失败", "failure")):
            task, operator = self.make([text(title), text("下一"), text("对局评价") + text("当前职级")])
            answer = task.read_battle_screen()
            self.assertEqual((answer.state, answer.outcome, answer.terminal_point), ("final_summary", outcome, (.5, .83)))
            self.assertIsNone(answer.continue_point)
            self.assertIsNone(answer.accelerate_point)
            self.assertEqual(sum(c[0] == "screenshot" for c in operator.calls), 1)

    def test_next_step_without_final_identity_does_not_authorize_click(self):
        for identity in (None, text("对局评价"), text("当前职级"), text("SS")):
            task, _ = self.make([text("挑战成功"), text("下一步"), identity])
            answer = task.read_battle_screen()
            self.assertEqual(answer.state, "result_animation")
            self.assertIsNone(answer.terminal_point)
        task, _ = self.make([text("首领详情"), text("下一步")])
        self.assertEqual(task.read_battle_screen().state, "unknown")

    def test_exact_later_page_label_requires_its_own_template(self):
        for label, template, state in (("下一页", "next_page.png", "final_next_page"),
                                        ("返回货币战争", "back_currency_wars.png", "final_return")):
            task, _ = self.make([None, text(label)])
            task._terminal_template_point = Mock(return_value=None)
            self.assertEqual(task.read_battle_screen().state, "unknown")
            task, _ = self.make([None, text(label)])
            task._terminal_template_point = Mock(side_effect=lambda frame, name: (.5, .83) if name == template else None)
            self.assertEqual(task.read_battle_screen().state, state)

    def test_challenge_ended_and_settle_control_authenticate_first_terminal_page(self):
        task, operator = self.make([text("挑战结束"), text("前往结算")])
        task._terminal_template_point = Mock(
            side_effect=lambda frame, name: (.5, .83) if name == "settle.png" else None)
        answer = task.read_battle_screen()
        self.assertEqual((answer.state, answer.outcome, answer.terminal_point),
                         ("final_settle", "unknown", (.5, .83)))
        self.assertIsNone(answer.continue_point)
        self.assertEqual(sum(c[0] == "screenshot" for c in operator.calls), 1)
        self.assertEqual(sum(c[0] == "engine" for c in operator.calls), 2)

    def test_settle_requires_same_frame_title_exact_action_and_template(self):
        cases = ((None, text("前往结算"), True),
                 (text("首领详情"), text("前往结算"), True),
                 (text("挑战结束", 0.89), text("前往结算"), True),
                 (text("挑战结束"), text("前往结算", 0.89), True),
                 (text("挑战结束"), text("前往结"), True),
                 (text("挑战结束"), text("前往结算", box=[]), True),
                 (text("挑战结束") + text("挑战成功"), text("前往结算"), True),
                 (text("挑战结束"), text("前往结算"), False))
        for header, action, matched in cases:
            with self.subTest(header=header, action=action, matched=matched):
                task, _ = self.make([header, action])
                task._terminal_template_point = Mock(side_effect=lambda frame, name:
                    (.5, .83) if matched and name == "settle.png" else None)
                answer = task.read_battle_screen()
                self.assertNotIn(answer.state, vision.TERMINAL_STATES)
                self.assertIsNone(answer.terminal_point)

    def test_summary_with_neutral_ended_title_preserves_unknown_outcome(self):
        task, _ = self.make([text("挑战结束"), text("下一步"),
                             text("对局评价") + text("当前职级")])
        answer = task.read_battle_screen()
        self.assertEqual((answer.state, answer.outcome), ("final_summary", "unknown"))

    @unittest.skipUnless(REAL_SETTLE.exists(), "October 9 settlement frame is unavailable")
    def test_real_settle_frame_matches_existing_template_at_actual_button(self):
        # OCR rows are an independent transcription of this reviewed frame;
        # the image/template match itself runs against the real screenshot.
        try:
            import cv2  # noqa: F401
        except ImportError:
            self.skipTest("OpenCV required for real template replay")
        for size in ((1920, 1080), (1280, 720), (2560, 1440)):
            with self.subTest(size=size):
                operator = VisionOperator([text("挑战结束"), text("前往结算")])
                with Image.open(REAL_SETTLE) as source:
                    operator.frame = source.convert("RGB").resize(size)
                task = vision.CurrencyWarsVision(operator, self.root / "profile.json",
                                                self.root / "samples", max_samples=0)
                answer = task.read_battle_screen()
                self.assertEqual((answer.state, answer.outcome), ("final_settle", "unknown"),
                                 task.last_battle_attempts)
                self.assertAlmostEqual(answer.terminal_point[0], 959.5 / 1920, delta=.003)
                self.assertAlmostEqual(answer.terminal_point[1], 896 / 1080, delta=.003)

    @unittest.skipUnless(REAL_FINAL.exists() and os.environ.get("SRA_POPULATION_OCR_DEPS"), "offline RapidOCR and real final screenshot required")
    def test_real_final_screen_and_independent_final_health_frames(self):
        deps = os.environ["SRA_POPULATION_OCR_DEPS"]
        sys.path.insert(0, deps)
        self.addCleanup(lambda: sys.path.remove(deps))
        from rapidocr import RapidOCR
        models = OCR_ROOT / "models"
        engine = RapidOCR(config_path=OCR_ROOT / "config.yaml", params={
            "Global.log_level": "error", "Det.model_path": str(models / "PP-OCRv6_det_small.onnx"),
            "Rec.model_path": str(models / "PP-OCRv6_rec_small.onnx"),
            "Cls.model_path": str(models / "ch_ppocr_mobile_v2.0_cls_mobile.onnx")})
        operator = HealthOperator([])
        with Image.open(REAL_FINAL) as source:
            operator.frame = source.convert("RGB")
        operator.ocr_engine = engine
        operator.sleep = Mock()
        task = vision.CurrencyWarsVision(operator, self.root / "profile.json", self.root / "samples", max_samples=0)
        answer = task.read_battle_screen()
        self.assertEqual((answer.state, answer.outcome), ("final_summary", "success"), task.last_battle_attempts)
        self.assertAlmostEqual(answer.terminal_point[0], .5, delta=.01)
        self.assertAlmostEqual(answer.terminal_point[1], 897.5 / 1080, delta=.01)
        # Two fresh captures even when replaying the same stable source frame.
        operator.calls.clear()
        health = task.read_squad_health(vision.FINAL_HEALTH_ROI)
        self.assertEqual(health.current, 93, task.last_health_attempts)
        self.assertEqual(sum(c[0] == "screenshot" for c in operator.calls), 2)
        self.assertNotEqual(vision.FINAL_HEALTH_ROI, vision.RESULT_HEALTH_ROI)


class TerminalFlowTests(unittest.TestCase):
    def setUp(self):
        self.module, _, _, names = load_isolated_task()
        self.addCleanup(lambda: [sys.modules.pop(name, None) for name in names])
        self.operator = FakeOperator()
        self.task = self.module.CurrencyWars(self.operator, runtimes=1)
        self.task.is_running = True
        self.task._begin_session()
        self.elapsed = 0.0
        self.phase = 0
        self.outcome = "success"
        self.delayed_until = 0
        self.states = ("final_summary", "final_next_page", "final_return", "unknown")
        self.task._vision.capture_sample = Mock(return_value=None)
        self.task._vision.read_squad_health = Mock(return_value=SimpleNamespace(current=93))
        self.task._vision.read_battle_screen = Mock(side_effect=self.screen)
        self.operator.locate = Mock(side_effect=lambda name, **kw: FakeBox(source=name)
                                    if name == self.module.CWIMG.START_CURRENCY_WARS and self.phase == 3 else None)
        self.operator.sleep = Mock(side_effect=self.advance)
        self.operator.click_point = Mock(side_effect=self.click)
        clock = patch.object(self.module.time, "monotonic", side_effect=lambda: self.elapsed)
        clock.start()
        self.addCleanup(clock.stop)

    def advance(self, seconds):
        self.elapsed += seconds

    def screen(self):
        state = "unknown" if self.elapsed < self.delayed_until else self.states[self.phase]
        return self.module.BattleScreenObservation(state, None, None, "same_frame_test", "",
            self.outcome if state == "final_summary" else "unknown", (.5, .83) if state != "unknown" else None)

    def click(self, *args, **kwargs):
        self.phase += 1
        return True

    def include_settle_page(self):
        self.states = ("final_settle", "final_summary", "final_next_page", "final_return", "unknown")
        self.operator.locate.side_effect = lambda name, **kw: (
            FakeBox(source=name) if name == self.module.CWIMG.START_CURRENCY_WARS
            and self.phase == len(self.states) - 1 else None)

    def test_settle_to_menu_navigates_four_controls_and_counts_battle_once(self):
        self.include_settle_page()
        self.task._pending_battle_id = "35a2caed-84d2-42a6-8776-fdf2a6a656ef"
        self.task._battle_entry_confirmed = True
        self.assertTrue(self.task._record_checkpoint(pending_battle_id=self.task._pending_battle_id))
        self.assertTrue(self.task.handle_game_over(None))
        checkpoint = self.task._session_store.checkpoint
        self.assertTrue(checkpoint.finalized)
        self.assertEqual(checkpoint.confirmed_battle_count, 1)
        self.assertEqual(checkpoint.terminal_outcome, "won")
        self.assertEqual(checkpoint.terminal_navigation_step, "complete")
        self.assertEqual(self.operator.click_point.call_count, 4)
        self.assertEqual([call.kwargs["tag"] for call in self.operator.click_point.call_args_list],
                         ["终局：" + state for state in self.states[:-1]])

    def test_settle_page_can_resume_directly_after_stopping(self):
        self.include_settle_page()
        self.task._recovery_page = "terminal"
        self.assertTrue(self.task._recover_live_page())
        self.assertEqual(self.operator.click_point.call_count, 4)
        self.assertTrue(self.task._session_store.checkpoint.finalized)

    def test_settle_is_terminal_at_startup_probe_and_stage_transition(self):
        self.include_settle_page()
        self.assertEqual(self.task.page_locate(), self.module.CurrencyWarsPage.RECOVERY)
        self.assertEqual(self.task._recovery_page, "terminal")
        self.assertEqual(self.task._probe_runtime_page()[0], "terminal")
        self.assertTrue(self.task.stage_transition())
        self.assertEqual(self.operator.click_point.call_count, 4)

    def test_settle_overrides_ordinary_reward_wait_without_guessing_win(self):
        self.include_settle_page()
        self.task._last_battle_outcome = "success"  # Previous fight is not this run's outcome.
        self.operator.locate.side_effect = lambda name, **kw: (
            FakeBox() if name == self.module.CWIMG.SETTLE else None)
        self.assertEqual(self.task._wait_battle_result(), (None, None, True))
        checkpoint = self.task._session_store.checkpoint
        self.assertEqual(checkpoint.terminal_navigation_step, "final_settle")
        self.assertEqual(checkpoint.terminal_outcome, "unknown")
        self.assertFalse(checkpoint.finalized)
        self.operator.click_point.assert_not_called()

    def test_settle_click_without_page_change_is_bounded_and_unfinalized(self):
        self.include_settle_page()
        self.operator.click_point.side_effect = lambda *a, **kw: True
        with self.assertRaisesRegex(RuntimeError, "result_terminal_page_not_changed"):
            self.task.handle_game_over(None)
        self.assertEqual(self.operator.click_point.call_count, 2)
        checkpoint = self.task._session_store.checkpoint
        self.assertEqual(checkpoint.terminal_outcome, "unknown")
        self.assertFalse(checkpoint.finalized)

    def test_neutral_summary_finishes_without_inventing_victory(self):
        self.include_settle_page()
        self.outcome = "unknown"
        self.task._last_battle_outcome = "success"
        self.assertTrue(self.task.handle_game_over(None))
        checkpoint = self.task._session_store.checkpoint
        self.assertEqual(checkpoint.terminal_outcome, "unknown")
        self.assertEqual(checkpoint.last_outcome, "returned_to_main_menu")
        self.assertTrue(checkpoint.finalized)

    def test_stop_while_confirming_settle_sends_no_click_and_keeps_run_pending(self):
        self.include_settle_page()
        def stop(seconds):
            self.advance(seconds)
            self.operator.stop_event.set()
        self.operator.sleep.side_effect = stop
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task.handle_game_over(None)
        self.operator.click_point.assert_not_called()
        self.assertFalse(self.task._session_store.checkpoint.finalized)

    def test_terminal_failure_sample_keeps_latest_recognition_attempts(self):
        attempts = [{"method": "result_header", "text": "挑战结束"},
                    {"method": "result_action", "text": "前往结算"}]
        self.task._vision.last_battle_attempts = attempts
        with self.assertRaisesRegex(RuntimeError, "result_timeout"):
            self.task._fail_battle("result_timeout")
        self.assertEqual(self.task._vision.capture_sample.call_args.args[1]["ocr_attempts"], attempts)

    def test_success_navigates_each_page_and_only_finalizes_at_confirmed_menu(self):
        self.assertTrue(self.task.handle_game_over(None))
        checkpoint = self.task._session_store.checkpoint
        self.assertEqual((checkpoint.terminal_outcome, checkpoint.last_outcome, checkpoint.execution_status),
                         ("won", "game_won", "completed"))
        self.assertTrue(checkpoint.finalized)
        self.assertEqual(checkpoint.pending_actions, ())
        self.assertEqual(self.operator.click_point.call_count, 3)
        self.assertEqual(self.task._last_health_read.current, 93)
        self.task._vision.read_squad_health.assert_called_once_with(self.module.FINAL_HEALTH_ROI)

    def test_failure_and_unknown_health_still_finish(self):
        self.outcome = "failure"
        self.task._vision.read_squad_health.return_value = SimpleNamespace(current=None)
        self.assertTrue(self.task.handle_game_over(None))
        self.assertEqual(self.task._session_store.checkpoint.last_outcome, "game_lost")

    def test_each_later_page_can_resume_without_replaying_previous_clicks(self):
        for phase in (1, 2):
            with self.subTest(phase=phase):
                self.phase = phase
                self.task._session_store.begin("a" * 64)
                self.task._session_store.record(terminal_outcome="won", terminal_evidence="previous_summary")
                self.operator.click_point.reset_mock()
                self.task._recovery_page = "terminal"
                self.assertTrue(self.task._recover_live_page())
                checkpoint = self.task._session_store.checkpoint
                self.assertEqual((checkpoint.phase, checkpoint.last_outcome), ("finished", "game_won"))
                self.assertEqual(self.operator.click_point.call_count, 3 - phase)

    def test_slow_next_page_does_not_repeat_previous_action(self):
        def click(*args, **kwargs):
            self.phase += 1
            self.delayed_until = self.elapsed + 7
            return True
        self.operator.click_point.side_effect = click
        self.assertTrue(self.task.handle_game_over(None))
        self.assertEqual(self.operator.click_point.call_count, 3)

    def test_failed_clicks_are_bounded_and_win_remains_pending(self):
        self.operator.click_point.side_effect = lambda *a, **kw: False
        with self.assertRaisesRegex(RuntimeError, "result_terminal_page_not_changed"):
            self.task.handle_game_over(None)
        self.task._record_execution_stop("error")
        checkpoint = self.task._session_store.checkpoint
        self.assertEqual((checkpoint.terminal_outcome, checkpoint.last_outcome, checkpoint.execution_status),
                         ("won", "game_won", "error"))
        self.assertFalse(checkpoint.finalized)
        self.assertTrue(checkpoint.pending_actions)
        self.assertEqual(self.operator.click_point.call_count, 2)

    def test_accepted_click_with_no_page_change_is_also_bounded(self):
        self.operator.click_point.side_effect = lambda *a, **kw: True
        with self.assertRaisesRegex(RuntimeError, "result_terminal_page_not_changed"):
            self.task.handle_game_over(None)
        self.assertEqual(self.operator.click_point.call_count, 2)
        self.assertFalse(self.task._session_store.checkpoint.finalized)

    def test_unknown_page_after_success_times_out_with_win_and_pending_step(self):
        def click(*args, **kwargs):
            self.phase = 3
            return True
        self.operator.click_point.side_effect = click
        self.operator.locate.side_effect = lambda *a, **kw: None
        self.task.REWARD_TRANSITION_TIMEOUT = 4
        with self.assertRaisesRegex(RuntimeError, "result_terminal_navigation_timeout"):
            self.task.handle_game_over(None)
        checkpoint = self.task._session_store.checkpoint
        self.assertEqual(checkpoint.last_outcome, "game_won")
        self.assertFalse(checkpoint.finalized)
        self.assertTrue(checkpoint.pending_actions)
        self.assertEqual(self.operator.click_point.call_count, 1)

    def test_one_main_menu_frame_does_not_finalize(self):
        self.phase = 3
        sightings = iter((FakeBox(), None))
        self.operator.locate.side_effect = lambda *a, **kw: next(sightings, None)
        self.task.REWARD_TRANSITION_TIMEOUT = 2
        with self.assertRaisesRegex(RuntimeError, "result_terminal_navigation_timeout"):
            self.task.handle_game_over(None)
        self.assertFalse(self.task._session_store.checkpoint.finalized)
        self.operator.click_point.assert_not_called()

    def test_run_error_keeps_confirmed_win_separate_from_execution_failure(self):
        self.task._record_terminal_screen(self.screen())
        self.task._report_runtime_identity = Mock()
        self.task.start_game = Mock(return_value=True)
        self.task.game_loop = Mock(side_effect=RuntimeError("return failed"))
        self.assertFalse(self.task.run())
        checkpoint = self.task._session_store.checkpoint
        self.assertEqual((checkpoint.last_outcome, checkpoint.terminal_outcome, checkpoint.execution_status),
                         ("game_won", "won", "error"))
        self.assertFalse(checkpoint.finalized)

    def test_run_user_stop_keeps_confirmed_win_and_pending_navigation(self):
        self.task._record_terminal_screen(self.screen())
        self.task._report_runtime_identity = Mock()
        self.task.start_game = Mock(return_value=True)
        self.task.game_loop = Mock(side_effect=self.module.ThreadStoppedError("stop"))
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task.run()
        checkpoint = self.task._session_store.checkpoint
        self.assertEqual((checkpoint.last_outcome, checkpoint.execution_status), ("game_won", "stopped"))
        self.assertTrue(checkpoint.pending_actions)

    def test_terminal_summary_overrides_settlement_animation_branch(self):
        self.operator.locate.side_effect = lambda name, **kw: FakeBox() if name == self.module.CWIMG.SETTLE else None
        self.assertEqual(self.task._wait_battle_result(), (None, None, True))
        self.operator.click_point.assert_not_called()
        self.assertEqual(self.task._session_store.checkpoint.terminal_outcome, "won")

    def test_stop_between_stable_observations_sends_no_input(self):
        def stop(seconds):
            self.advance(seconds)
            self.operator.stop_event.set()
        self.operator.sleep.side_effect = stop
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task.handle_game_over(None)
        self.operator.click_point.assert_not_called()
        self.assertFalse(self.task._session_store.checkpoint.finalized)

    def test_user_advancing_page_during_confirmation_does_not_use_stale_point(self):
        initial = self.screen()
        self.phase = 1
        self.assertIsNone(self.task._stable_terminal_screen(initial))
        self.operator.click_point.assert_not_called()
        self.assertTrue(self.task.handle_game_over(None))
        self.assertEqual(self.operator.click_point.call_count, 2)

    def test_missing_main_menu_does_not_send_escape(self):
        with self.assertRaisesRegex(RuntimeError, "result_main_menu_missing"):
            self.task.handle_ending()
        self.assertNotIn("esc", self.operator.keys())

    def test_known_main_menu_allows_ending(self):
        self.operator.wait_img = Mock(return_value=FakeBox())
        self.assertTrue(self.task.handle_ending())
        self.assertEqual(self.operator.keys(), ["esc"])


if __name__ == "__main__":
    unittest.main()
