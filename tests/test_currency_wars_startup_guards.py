"""Startup regressions with a stateful UI; no game, clipboard or real waits."""

import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from test_currency_wars_flow import FakeBox, FakeOperator, load_isolated_task


class StartupGuardTests(unittest.TestCase):
    def setUp(self):
        self.module, _, _, names = load_isolated_task()
        self.addCleanup(lambda: [sys.modules.pop(name, None) for name in names])
        self.operator = FakeOperator()
        self.task = self.module.CurrencyWars(self.operator, runtimes=2)
        self.task.is_running = True
        self.task._vision.capture_sample = Mock()
        self.elapsed = 0
        self.module.time = SimpleNamespace(monotonic=lambda: self.elapsed, time_ns=lambda: 1234)
        self.operator.sleep = self.sleep
        self.task.ENTRY_TRANSITION_TIMEOUT = 1
        self.task.DIFFICULTY_SELECTION_TIMEOUT = 5
        self.task.DIFFICULTY_MAX_CLICKS = 4

    def sleep(self, seconds):
        self.operator.record("sleep", seconds)
        self.elapsed += seconds

    def box(self, template):
        return FakeBox(source=template)

    def configure_difficulty(self, ranks, *, ready=True, stuck=False):
        self.rank = ranks
        self.difficulty_clicks = 0
        self.observations = 0

        def locate(templates, **kwargs):
            self.observations += 1
            if self.rank > 0:
                return 0, self.box(self.module.CWIMG.DOWN_ARROW)
            if ready:
                return 1, self.box(self.module.CWIMG.START_GAME)
            return -1, None

        def click(box, **kwargs):
            self.difficulty_clicks += 1
            if not stuck:
                self.rank -= 1
            self.sleep(kwargs.get("after_sleep", 0))
            return True

        self.operator.locate_any = Mock(side_effect=locate)
        self.operator.click_box = Mock(side_effect=click)

    def test_lowest_stops_only_after_two_reads_of_start_without_arrow(self):
        self.configure_difficulty(2)
        self.assertTrue(self.task._select_difficulty())
        self.assertEqual(self.difficulty_clicks, 2)
        self.assertEqual(self.observations, 4)

    def test_already_lowest_sends_no_click(self):
        self.configure_difficulty(0)
        self.assertTrue(self.task._select_difficulty())
        self.operator.click_box.assert_not_called()
        self.assertEqual(self.observations, 2)

    def test_stuck_arrow_has_a_click_limit(self):
        self.configure_difficulty(2, stuck=True)
        self.assertFalse(self.task._select_difficulty())
        self.assertEqual(self.difficulty_clicks, self.task.DIFFICULTY_MAX_CLICKS)

    def test_missing_page_times_out_instead_of_being_treated_as_lowest(self):
        self.configure_difficulty(0, ready=False)
        self.assertFalse(self.task._select_difficulty())
        self.operator.click_box.assert_not_called()
        self.assertGreaterEqual(self.elapsed, self.task.DIFFICULTY_SELECTION_TIMEOUT)

    def test_arrow_returning_between_ready_frames_is_not_accepted(self):
        cw = self.module.CWIMG
        self.operator.locate_any = Mock(side_effect=[
            (1, self.box(cw.START_GAME)), (0, self.box(cw.DOWN_ARROW)),
            (1, self.box(cw.START_GAME)), (1, self.box(cw.START_GAME)),
        ])
        self.assertTrue(self.task._select_difficulty())
        self.assertEqual(len([c for c in self.operator.calls if c[0] == "click_box"]), 1)
        self.assertEqual(self.operator.locate_any.call_count, 4)

    def test_slow_observation_cannot_send_input_after_deadline(self):
        def slow_read(*args, **kwargs):
            self.elapsed = self.task.DIFFICULTY_SELECTION_TIMEOUT
            return 0, self.box(self.module.CWIMG.DOWN_ARROW)
        self.operator.locate_any = Mock(side_effect=slow_read)
        self.operator.click_box = Mock()
        self.assertFalse(self.task._select_difficulty())
        self.operator.click_box.assert_not_called()

    def test_failed_difficulty_does_not_start_a_new_game(self):
        self.configure_difficulty(1, stuck=True)
        self.operator.click_img = Mock(return_value=True)
        self.task._handle_boss_info_flow = Mock()
        # Entering the selection screen is separate from lowering a rank.
        click_rank = self.operator.click_box.side_effect
        self.operator.click_box.side_effect = lambda box, **kwargs: (
            True if box.source == "enter" else click_rank(box, **kwargs))
        self.assertFalse(self.task._enter_new_game(self.box("enter")))
        self.operator.click_img.assert_not_called()
        self.task._handle_boss_info_flow.assert_not_called()

    def test_failed_rank_click_stops_and_cancellation_propagates(self):
        self.configure_difficulty(1)
        self.operator.click_box.side_effect = None
        self.operator.click_box.return_value = False
        self.assertFalse(self.task._select_difficulty())
        self.operator.stop_event.set()
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task._select_difficulty()
        self.assertEqual(self.operator.click_box.call_count, 1)

    def test_highest_and_current_keep_optional_button_behavior(self):
        self.task.difficulty = self.module.Difficulty.HIGHEST
        self.assertTrue(self.task._select_difficulty())
        self.assertEqual([c[1][0] for c in self.operator.calls if c[0] == "click_img"],
                         [self.module.CWIMG.RETURN_HIGHEST_RANK])
        self.operator.calls.clear()
        self.task.difficulty = self.module.Difficulty.CURRENT
        self.assertTrue(self.task._select_difficulty())
        self.assertEqual(self.operator.calls, [])

    def configure_guide(self, *, needs_hot=False, apply_changes=True, exit_depth=2):
        self.task.strategy_code = "test-guide-code"
        self.stage = "prepare"
        self.events = []
        self.missing = set()
        self.failed_clicks = set()
        self.escapes = 0
        cw = self.module.CWIMG
        applied = self.task.STRATEGY_APPLIED_IMAGE

        def visible(template):
            if template in self.missing:
                return False
            return template in {
                "prepare": {cw.STRATEGY, cw.PREPARATION_STAGE},
                "landing": {cw.HOT_STRATEGIES},
                "list": {cw.ENTER_STRATEGY_CODE},
                "dialog": {self.module.IMG.ENSURE2},
                "detail": {cw.APPLY_STRATEGY},
                "applied": {applied},
                "closing": set(),
            }[self.stage]

        def locate(template, **kwargs):
            return self.box(template) if visible(template) else None

        def locate_any(templates, **kwargs):
            for index, template in enumerate(templates):
                if visible(template):
                    return index, self.box(template)
            return -1, None

        def click(box, **kwargs):
            self.events.append(("click", box.source))
            if box.source in self.failed_clicks or not visible(box.source):
                return False
            transitions = {cw.STRATEGY: "landing" if needs_hot else "list",
                           cw.HOT_STRATEGIES: "list", cw.ENTER_STRATEGY_CODE: "dialog",
                           self.module.IMG.ENSURE2: "detail",
                           cw.APPLY_STRATEGY: "applied" if apply_changes else "detail"}
            self.stage = transitions[box.source]
            self.sleep(kwargs.get("after_sleep", 0))
            return True

        def escape(key, **kwargs):
            self.assertEqual(key, "esc")
            self.assertEqual(kwargs.get("presses", 1), 1)
            self.escapes += 1
            self.events.append(("key", key))
            self.stage = "prepare" if self.escapes >= exit_depth else "closing"
            return True

        self.operator.locate = Mock(side_effect=locate)
        self.operator.locate_any = Mock(side_effect=locate_any)
        self.operator.wait_img = Mock(side_effect=locate)
        self.operator.click_box = Mock(side_effect=click)
        self.operator.press_key = Mock(side_effect=escape)
        self.operator.copy = Mock()
        self.operator.paste = Mock()

    def test_guide_applies_without_optional_hot_button_and_exits_only_needed_layers(self):
        self.configure_guide(exit_depth=1)
        self.assertTrue(self.task.handle_game_entered())
        self.assertEqual(self.stage, "prepare")
        self.assertEqual(self.escapes, 1)
        self.operator.copy.assert_called_once_with("test-guide-code")
        self.operator.paste.assert_called_once()
        self.assertNotIn(("click", self.module.CWIMG.HOT_STRATEGIES), self.events)
        self.task._vision.capture_sample.assert_not_called()

    def test_guide_can_navigate_through_hot_tab(self):
        self.configure_guide(needs_hot=True, exit_depth=3)
        self.assertTrue(self.task.handle_game_entered())
        self.assertIn(("click", self.module.CWIMG.HOT_STRATEGIES), self.events)
        self.assertEqual(self.escapes, 3)

    def test_missing_each_required_screen_stops_without_escape(self):
        for template in (self.module.CWIMG.STRATEGY, self.module.CWIMG.ENTER_STRATEGY_CODE,
                         self.module.IMG.ENSURE2, self.module.CWIMG.APPLY_STRATEGY):
            with self.subTest(template=template):
                self.configure_guide()
                self.missing.add(template)
                self.assertFalse(self.task.handle_game_entered())
                self.assertTrue(self.task._startup_failed)
                self.assertEqual(self.escapes, 0)
                if template != self.module.CWIMG.APPLY_STRATEGY:
                    self.operator.paste.assert_not_called()

    def test_failed_each_required_click_stops_without_escape(self):
        for template in (self.module.CWIMG.STRATEGY, self.module.CWIMG.ENTER_STRATEGY_CODE,
                         self.module.IMG.ENSURE2, self.module.CWIMG.APPLY_STRATEGY):
            with self.subTest(template=template):
                self.configure_guide()
                self.failed_clicks.add(template)
                self.assertFalse(self.task.handle_game_entered())
                self.assertEqual(self.escapes, 0)

    def test_sent_apply_click_without_confirmation_is_not_success(self):
        self.configure_guide(apply_changes=False)
        self.assertFalse(self.task.handle_game_entered())
        self.assertEqual(self.escapes, 0)
        self.assertEqual(self.task._vision.capture_sample.call_args.args[0],
                         "strategy_apply_unconfirmed")

    def test_one_frame_applied_evidence_is_not_enough(self):
        self.configure_guide()
        original = self.operator.locate_any.side_effect
        seen = []
        def flicker(templates, **kwargs):
            if self.task.STRATEGY_APPLIED_IMAGE in templates:
                seen.append(True)
                return original(templates, **kwargs) if len(seen) == 1 else (-1, None)
            return original(templates, **kwargs)
        self.operator.locate_any.side_effect = flicker
        self.assertFalse(self.task.handle_game_entered())
        self.assertEqual(self.escapes, 0)

    def test_stuck_guide_exit_has_three_input_limit_and_reports_failure(self):
        self.configure_guide(exit_depth=99)
        self.assertFalse(self.task.handle_game_entered())
        self.assertEqual(self.escapes, 3)
        self.assertEqual(self.task._vision.capture_sample.call_args.args[0],
                         "strategy_return_unconfirmed")

    def test_failed_escape_stops_without_retry(self):
        self.configure_guide()
        self.operator.press_key.side_effect = None
        self.operator.press_key.return_value = False
        self.assertFalse(self.task.handle_game_entered())
        self.operator.press_key.assert_called_once_with("esc")

    def test_clipboard_error_fails_startup_but_user_stop_propagates(self):
        self.configure_guide()
        self.operator.copy.side_effect = RuntimeError("clipboard unavailable")
        self.assertFalse(self.task.handle_game_entered())
        self.operator.paste.assert_not_called()
        self.assertEqual(self.escapes, 0)
        self.configure_guide()
        self.operator.paste.side_effect = self.module.ThreadStoppedError("stopped")
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task.handle_game_entered()
        self.assertEqual(self.escapes, 0)

    def test_resume_and_no_code_skip_import(self):
        self.configure_guide()
        self.task.is_continue = True
        self.assertTrue(self.task.handle_game_entered())
        self.task.is_continue = False
        self.task.strategy_code = ""
        self.assertTrue(self.task.handle_game_entered())
        self.operator.wait_img.assert_not_called()
        self.operator.copy.assert_not_called()

    def test_failed_import_stops_run_without_initialization_ending_or_second_attempt(self):
        self.configure_guide(apply_changes=False)
        self.task._report_runtime_identity = Mock()
        self.task.page_locate = Mock(return_value=self.module.CurrencyWarsPage.START)
        self.task._handle_page_enter = Mock(return_value=True)
        self.task._begin_session = Mock()
        self.task._initialize_game = Mock()
        self.task.game_loop = Mock()
        self.task.handle_ending = Mock()
        self.assertFalse(self.task.run())
        self.task._handle_page_enter.assert_called_once()
        self.task._initialize_game.assert_not_called()
        self.task.game_loop.assert_not_called()
        self.task.handle_ending.assert_not_called()


if __name__ == "__main__":
    unittest.main()
