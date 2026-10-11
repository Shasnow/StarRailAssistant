"""Startup outcome regressions against production run/start_game methods.

The tests isolate game I/O and never click, capture a real window, or sleep.
A failed start must stop the run; deliberate reroll hooks remain non-errors.
"""
from __future__ import annotations

import sys
import unittest
from unittest.mock import Mock

from test_currency_wars_flow import FakeBox, FakeOperator, load_isolated_task


class CurrencyWarsStartupTests(unittest.TestCase):
    def setUp(self):
        self.module, _, _, module_names = load_isolated_task()
        self.addCleanup(lambda: [sys.modules.pop(name, None) for name in module_names])
        self.operator = FakeOperator()
        self.task = self.module.CurrencyWars(self.operator, runtimes=3)
        self.task._report_runtime_identity = Mock()
        self.task.game_loop = Mock(return_value=True)
        self.task.handle_ending = Mock()
        self.task._vision.capture_sample = Mock()
        self.task.start_game = Mock(wraps=self.task.start_game)

    def prepare_successful_start(self):
        # PREPARATION is a supported entry point that skips new-game UI clicks.
        self.task.page_locate = Mock(return_value=self.module.CurrencyWarsPage.PREPARATION)
        self.task.handle_game_entered = Mock(return_value=True)
        self.task._initialize_game = Mock(return_value=True)
        self.task.handle_game_initialized = Mock(return_value=True)

    def assert_failed_start_stops_run(self, sample_reason):
        self.assertFalse(self.task.run())
        self.assertEqual(self.task.start_game.call_count, 1)
        self.assertFalse(self.task.is_running)
        self.task.game_loop.assert_not_called()
        self.task.handle_ending.assert_not_called()
        capture = self.task._vision.capture_sample
        capture.assert_called_once()
        self.assertEqual(capture.call_args.args[0], sample_reason)
        self.assertTrue(capture.call_args.args[1].get("evidence"))

    def test_unrecognized_page_stops_without_ending_or_next_attempt(self):
        # FakeOperator returns no page: both production page_locate and start_game run.
        self.assert_failed_start_stops_run("startup_page_not_found")
        self.assertEqual(sum(name == "wait_any_img" for name, _, _ in self.operator.calls), 1)

    def test_start_button_missing_stops_without_ending_or_next_attempt(self):
        # Page was initially visible, then the entry button cannot be found.
        self.operator.wait_any_img = Mock(side_effect=[(1, FakeBox()), (-1, None)])
        self.assert_failed_start_stops_run("startup_entry_failed")
        self.assertEqual(self.operator.wait_any_img.call_count, 2)
        self.assertFalse(any(name in ("click", "click_box")
                             for name, _, _ in self.operator.calls))

    def test_initialization_failure_stops_without_game_or_ending(self):
        self.prepare_successful_start()
        self.task._initialize_game.return_value = False
        self.assert_failed_start_stops_run("startup_initialization_failed")
        self.task._initialize_game.assert_called_once()
        self.task.handle_game_initialized.assert_not_called()

    def test_successful_start_runs_game_and_normal_ending(self):
        self.prepare_successful_start()
        self.task.runtimes = 1
        self.assertTrue(self.task.run())
        self.task.start_game.assert_called_once()
        self.task.game_loop.assert_called_once()
        self.task.handle_ending.assert_called_once()
        self.task._vision.capture_sample.assert_not_called()

    def test_entered_hook_can_deliberately_stop_reroll_without_failure(self):
        self.prepare_successful_start()

        def deliberate_stop():
            self.task.is_running = False
            return False

        self.task.handle_game_entered.side_effect = deliberate_stop
        self.assertTrue(self.task.run())
        self.task.start_game.assert_called_once()
        self.task._initialize_game.assert_not_called()
        self.task.game_loop.assert_not_called()
        self.task.handle_ending.assert_called_once()
        self.task._vision.capture_sample.assert_not_called()

    def test_entered_hook_can_skip_one_reroll_then_start_next(self):
        self.prepare_successful_start()
        self.task.runtimes = 2
        self.task.handle_game_entered.side_effect = [False, True]
        self.assertTrue(self.task.run())
        self.assertEqual(self.task.start_game.call_count, 2)
        self.task._initialize_game.assert_called_once()
        self.task.game_loop.assert_called_once()
        self.task.handle_ending.assert_called_once()
        self.task._vision.capture_sample.assert_not_called()

    def test_initialized_hook_can_deliberately_stop_without_failure(self):
        self.prepare_successful_start()

        def deliberate_stop():
            self.task.is_running = False
            return False

        self.task.handle_game_initialized.side_effect = deliberate_stop
        self.assertTrue(self.task.run())
        self.task.start_game.assert_called_once()
        self.task._initialize_game.assert_called_once()
        self.task.game_loop.assert_not_called()
        self.task.handle_ending.assert_called_once()
        self.task._vision.capture_sample.assert_not_called()

    def test_initialized_hook_can_skip_one_round_then_start_next(self):
        self.prepare_successful_start()
        self.task.runtimes = 2
        self.task.handle_game_initialized.side_effect = [False, True]
        self.assertTrue(self.task.run())
        self.assertEqual(self.task.start_game.call_count, 2)
        self.assertEqual(self.task._initialize_game.call_count, 2)
        self.task.game_loop.assert_called_once()
        self.task.handle_ending.assert_called_once()
        self.task._vision.capture_sample.assert_not_called()

    def test_new_run_can_recover_after_previous_start_failure(self):
        self.assertFalse(self.task.run())
        self.task.game_loop.assert_not_called()
        self.task.handle_ending.assert_not_called()
        self.prepare_successful_start()
        self.task.runtimes = 1
        self.assertTrue(self.task.run())
        self.assertEqual(self.task.start_game.call_count, 2)
        self.task.game_loop.assert_called_once()
        self.task.handle_ending.assert_called_once()
        self.task._vision.capture_sample.assert_called_once()

    def test_stop_exception_during_page_detection_propagates(self):
        self.task.page_locate = Mock(side_effect=self.module.ThreadStoppedError("stopped"))
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task.run()
        self.task.start_game.assert_called_once()
        self.task.game_loop.assert_not_called()
        self.task.handle_ending.assert_not_called()
        self.task._vision.capture_sample.assert_not_called()

    def test_stop_exception_during_entered_hook_propagates(self):
        self.prepare_successful_start()
        self.task.handle_game_entered.side_effect = self.module.ThreadStoppedError("stopped")
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task.run()
        self.task.start_game.assert_called_once()
        self.task._initialize_game.assert_not_called()
        self.task.game_loop.assert_not_called()
        self.task.handle_ending.assert_not_called()
        self.task._vision.capture_sample.assert_not_called()


    def test_page_locate_recognizes_boss_preview_without_pressing_escape(self):
        self.operator.wait_any_img = Mock(return_value=(4, FakeBox()))
        self.assertEqual(self.task.page_locate(), self.module.CurrencyWarsPage.BOSS_PREVIEW)
        templates = self.operator.wait_any_img.call_args.args[0]
        self.assertEqual(templates[4], self.module.CWIMG.BOSS_PREVIEW)
        self.assertEqual(self.operator.keys(), [])

    def test_page_locate_uses_battle_button_when_open_shop_hides_preparation_title(self):
        def open_shop_page(images, **kwargs):
            if self.module.CWIMG.BATTLE in images:
                return images.index(self.module.CWIMG.BATTLE), FakeBox(source="BATTLE")
            return -1, None

        self.operator.wait_any_img = Mock(side_effect=open_shop_page)
        self.assertEqual(self.task.page_locate(), self.module.CurrencyWarsPage.PREPARATION)
        self.assertEqual(self.operator.keys(), [])
        self.assertFalse(any(name in ("click", "click_box", "click_img")
                             for name, _, _ in self.operator.calls))

    def test_boss_preview_resets_stale_state_then_resumes_in_order(self):
        events = []
        character = self.module.Characters.get_character("灵砂")
        character.is_placed, character.stars = True, 3
        self.task.on_field_character[0] = character
        self.task.in_hand_character[0] = character
        self.task.is_continue = True
        self.task.main_c_first_fielded_confirmed = True
        self.task._purchase_pending_names.add(character.name)
        reset = self.task.reset_character

        def reset_and_record():
            events.append("reset")
            reset()

        self.task.reset_character = Mock(side_effect=reset_and_record)
        self.task._handle_boss_info_flow = Mock(side_effect=lambda: events.append("boss") or True)
        self.task._handle_invest_environment_flow = Mock(
            side_effect=lambda: events.append("environment") or True)
        self.task._enter_from_start_page = Mock()
        self.assertTrue(self.task._handle_page_enter(self.module.CurrencyWarsPage.BOSS_PREVIEW))
        self.assertEqual(events, ["reset", "boss", "environment"])
        self.task._enter_from_start_page.assert_not_called()
        self.assertFalse(self.task.is_continue)
        self.assertFalse(self.task.main_c_first_fielded_confirmed)
        self.assertFalse(self.task._purchase_pending_names)
        self.assertFalse(character.is_placed)
        self.assertEqual(character.stars, 0)
        for area in ("on_field", "off_field", "in_hand"):
            self.assertTrue(all(value is None for value in getattr(self.task, area + "_character")))

    def test_boss_preview_continues_real_boss_hook_and_normal_initialization(self):
        self.task.runtimes = 1
        self.operator.wait_any_img = Mock(return_value=(4, FakeBox()))
        next_step = FakeBox(source=self.module.CWIMG.NEXT_STEP)
        self.operator.wait_img = Mock(return_value=next_step)
        self.task.handle_boss_info = Mock()
        self.task._handle_invest_environment_flow = Mock(return_value=True)
        self.task.handle_game_entered = Mock(return_value=True)
        self.task.handle_game_initialized = Mock(return_value=True)
        self.task._initialize_game = Mock(wraps=self.task._initialize_game)
        self.task._enter_from_start_page = Mock()
        self.task.refresh_character = Mock(side_effect=AssertionError("must initialize a new game"))
        self.assertTrue(self.task.run())
        self.operator.wait_img.assert_called_once_with(self.module.CWIMG.NEXT_STEP, timeout=30)
        self.task.handle_boss_info.assert_called_once()
        self.assertTrue(any(name == "click_box" and args[0] is next_step
                            for name, args, _ in self.operator.calls))
        self.task._handle_invest_environment_flow.assert_called_once()
        self.task._initialize_game.assert_called_once()
        self.task.handle_game_initialized.assert_called_once()
        self.task.game_loop.assert_called_once()
        self.task.handle_ending.assert_called_once()
        self.task._enter_from_start_page.assert_not_called()
        self.task._vision.capture_sample.assert_not_called()
        for area in ("on_field", "off_field"):
            self.assertTrue(all(obs.state == self.module.SlotState.EMPTY
                                for obs in self.task._observations[area]))

    def test_boss_preview_failure_does_not_attempt_environment_or_initialize(self):
        self.operator.wait_any_img = Mock(return_value=(4, FakeBox()))
        self.task._handle_boss_info_flow = Mock(return_value=False)
        self.task._handle_invest_environment_flow = Mock()
        self.task._initialize_game = Mock()
        self.task._enter_from_start_page = Mock()
        self.assert_failed_start_stops_run("startup_entry_failed")
        self.task._handle_boss_info_flow.assert_called_once()
        self.task._handle_invest_environment_flow.assert_not_called()
        self.task._initialize_game.assert_not_called()
        self.task._enter_from_start_page.assert_not_called()

    def test_boss_preview_environment_failure_stops_before_initialize(self):
        self.operator.wait_any_img = Mock(return_value=(4, FakeBox()))
        self.task._handle_boss_info_flow = Mock(return_value=True)
        self.task._handle_invest_environment_flow = Mock(return_value=False)
        self.task._initialize_game = Mock()
        self.task._enter_from_start_page = Mock()
        self.assert_failed_start_stops_run("startup_entry_failed")
        self.task._handle_boss_info_flow.assert_called_once()
        self.task._handle_invest_environment_flow.assert_called_once()
        self.task._initialize_game.assert_not_called()
        self.task._enter_from_start_page.assert_not_called()

if __name__ == "__main__":
    unittest.main()
