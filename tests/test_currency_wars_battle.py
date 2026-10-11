"""Battle entry regressions using production flow with isolated game I/O.

Confirmed frontline observations and positive battle/result images are required
before the flow can wait for a fight or click the result continuation.
"""
from __future__ import annotations

import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from test_currency_wars_flow import FakeBox, FakeOperator, load_isolated_task


class CurrencyWarsBattleTests(unittest.TestCase):
    def setUp(self):
        self.module, self.characters, self.logic, names = load_isolated_task()
        self.addCleanup(lambda: [sys.modules.pop(name, None) for name in names])
        self.operator = FakeOperator()
        self.task = self.module.CurrencyWars(self.operator, runtimes=3)
        self.task.is_running = True
        self.task._vision.capture_sample = Mock()
        self.task._vision.read_battle_screen = Mock(return_value=SimpleNamespace(
            state="unknown", continue_point=None, accelerate_point=None,
            evidence="no_battle_screen_evidence", raw_text=""))
        self.task.refresh_character = Mock()
        self.task.place_character = Mock()
        self.task.abort_and_return = Mock()
        self.module.logger = Mock()
        self.elapsed = 0.0
        original_sleep = self.operator.sleep

        def advance_sleep(seconds):
            self.elapsed += seconds
            original_sleep(seconds)

        self.operator.sleep = advance_sleep
        clock = patch.object(self.module.time, "monotonic", side_effect=lambda: self.elapsed)
        clock.start()
        self.addCleanup(clock.stop)
        self.button = FakeBox(source="BATTLE")
        self.current_button = FakeBox(left=120, top=150, source="CURRENT_BATTLE")
        self.result = FakeBox(source="CONTINUE")
        self.operator.wait_any_img = Mock(side_effect=self.wait_any)
        self.operator.wait_img = Mock(return_value=self.current_button)
        self.operator.locate_any = Mock(side_effect=self.preparation_without_entry)
        self.operator.locate = Mock(return_value=None)

    def preparation_without_entry(self, images, **kwargs):
        if self.module.CWIMG.PREPARATION_STAGE in images and self.module.CWIMG.BATTLE in images:
            return images.index(self.module.CWIMG.PREPARATION_STAGE), FakeBox(source="PREPARATION_STAGE")
        return -1, None

    def wait_any(self, images, **kwargs):
        if images == [self.module.CWIMG.BATTLE, self.module.CWIMG.SKIP]:
            return 0, self.button
        if images == [self.module.CWIMG.SETTLE, self.module.CWIMG.CONTINUE]:
            return 1, self.result
        self.fail(f"Unexpected image wait: {images}")

    def observe(self, area="on_field", *, character=None, state=None, evidence="name_match"):
        character = character or self.characters.Characters.get_character("灵砂")
        state = state or self.logic.SlotState.KNOWN
        observation = self.logic.SlotObservation(
            0, state, character=character, occupied=True,
            evidence=evidence, revision=1, stars=1,
        )
        self.task._observations[area][0] = observation
        getattr(self.task, area + "_character")[0] = character
        return character

    def enter_via(self, index=0):
        # SETTLE is an animation; a later CONTINUE is still required.
        first = [self.module.IMG.Q, self.module.CWIMG.SETTLE, self.module.CWIMG.CONTINUE][index]
        targets = iter([first])

        def locate_any(images, **kwargs):
            if self.module.CWIMG.PREPARATION_STAGE in images:
                return self.preparation_without_entry(images, **kwargs)
            target = next(targets, self.module.CWIMG.CONTINUE)
            if target not in images:
                return -1, None
            return images.index(target), FakeBox(source=target)

        self.operator.locate_any.side_effect = locate_any
        self.operator.locate.side_effect = lambda image, **kwargs: (
            self.result if image == self.module.CWIMG.CONTINUE else None)

    def click_boxes(self):
        return [args[0] for name, args, _ in self.operator.calls
                if name == "click_box" and getattr(args[0], "source", "") != "CONTINUE"]

    def continuation_clicks(self):
        return [call for call in self.operator.calls
                if call[0] == "click" or (
                    call[0] == "click_box" and getattr(call[1][0], "source", "") == "CONTINUE")]

    def assert_no_result_or_retreat_actions(self):
        self.assertEqual(self.continuation_clicks(), [])
        self.assertFalse(any(name == "click_img" and args[0] == self.module.CWIMG.RETREAT
                             for name, args, _ in self.operator.calls))
        self.assertNotIn("esc", self.operator.keys())
        self.task.abort_and_return.assert_not_called()

    def assert_no_long_wait_or_battle_log(self):
        self.assertFalse(any(call.kwargs.get("timeout", 0) >= 600
                             for call in self.operator.wait_any_img.call_args_list))
        messages = [str(call.args[0]) for call in self.module.logger.info.call_args_list]
        self.assertFalse(any("等待挑战结束" in message for message in messages))

    def assert_sample(self, reason):
        # Population verification can independently sample an UNKNOWN reading.
        # The battle failure itself must still produce exactly one diagnosis.
        calls = [call for call in self.task._vision.capture_sample.call_args_list
                 if call.args[0].startswith("battle_")]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].args[0], "battle_" + reason)
        self.assertTrue(calls[0].args[1].get("evidence"))

    def test_unknown_frontline_stops_before_battle_button_or_result_click(self):
        with self.assertRaisesRegex(RuntimeError, "no_confirmed_frontline"):
            self.task.battle()
        self.task.refresh_character.assert_called_once_with(equip=False)
        self.task.place_character.assert_called_once_with()
        self.assertEqual(self.click_boxes(), [])
        self.operator.wait_img.assert_not_called()
        self.assert_no_long_wait_or_battle_log()
        self.assert_no_result_or_retreat_actions()
        self.assert_sample("no_confirmed_frontline")

    def test_stale_cache_bench_backline_npc_locked_and_pending_drag_do_not_unlock(self):
        for source in ("stale_cache", "in_hand", "off_field", "npc", "locked", "pending_drag"):
            with self.subTest(source=source):
                self.operator.calls.clear()
                self.task._vision.capture_sample.reset_mock()
                self.task.refresh_character.reset_mock()
                self.task.place_character.reset_mock()
                self.task.reset_character()
                character = self.characters.Characters.get_character("灵砂")
                character.is_npc = False
                character.is_locked = False
                if source == "stale_cache":
                    self.task.on_field_character[0] = character
                    character.is_placed = True
                elif source in ("in_hand", "off_field"):
                    self.observe(source, character=character)
                else:
                    self.observe(character=character,
                                 evidence="pending_drag" if source == "pending_drag" else "name_match")
                    character.is_npc = source == "npc"
                    character.is_locked = source == "locked"
                with self.assertRaisesRegex(RuntimeError, "no_confirmed_frontline"):
                    self.task.battle()
                self.assertEqual(self.click_boxes(), [])
                self.task.refresh_character.assert_called_once_with(equip=False)
                self.task.place_character.assert_called_once_with()
                self.assert_no_long_wait_or_battle_log()
                self.assert_no_result_or_retreat_actions()
                self.assert_sample("no_confirmed_frontline")

    def test_empty_frontline_is_repaired_once_before_relocating_and_clicking_battle(self):
        self.task._observations["on_field"][0] = self.logic.SlotObservation(
            0, self.logic.SlotState.EMPTY, occupied=False, evidence="empty")
        self.task.place_character.side_effect = lambda: self.observe()
        self.enter_via(2)
        self.assertTrue(self.task.battle())
        self.task.refresh_character.assert_called_once_with(equip=False)
        self.task.place_character.assert_called_once_with()
        self.assertEqual(self.click_boxes(), [self.current_button])
        self.operator.wait_img.assert_called_once_with(self.module.CWIMG.BATTLE, timeout=15)
        self.assertFalse(any(call.args[0].startswith("battle_")
                             for call in self.task._vision.capture_sample.call_args_list))

    def test_confirmed_frontline_needs_no_repair_and_relocates_before_click(self):
        self.observe()
        self.enter_via(0)
        self.assertTrue(self.task.battle())
        self.task.refresh_character.assert_not_called()
        self.task.place_character.assert_not_called()
        self.assertEqual(self.click_boxes(), [self.current_button])
        self.assertEqual(self.operator.keys(), [])
        messages = [str(call.args[0]) for call in self.module.logger.info.call_args_list]
        self.assertTrue(any("已确认进入战斗" in message for message in messages))
        self.task._vision.capture_sample.assert_not_called()

    def test_clicked_button_without_entry_evidence_has_short_timeout_and_no_continuation(self):
        self.observe()
        with self.assertRaisesRegex(RuntimeError, "entry_timeout"):
            self.task.battle()
        self.assertEqual(self.click_boxes(), [self.current_button])
        self.assertGreaterEqual(self.elapsed, 48)
        self.assertLessEqual(self.elapsed, 48.5)
        self.assertGreater(self.operator.locate_any.call_count, 1)
        self.assert_no_long_wait_or_battle_log()
        self.assert_no_result_or_retreat_actions()
        self.assert_sample("entry_timeout")

    def test_thirty_seconds_of_preparation_can_still_transition_into_battle(self):
        self.observe()

        def delayed_combat(images, **kwargs):
            if self.module.CWIMG.PREPARATION_STAGE in images:
                return self.preparation_without_entry(images, **kwargs)
            if self.elapsed >= 32 and self.module.IMG.Q in images:
                return images.index(self.module.IMG.Q), FakeBox(source="Q")
            return -1, None

        self.operator.locate_any.side_effect = delayed_combat
        self.operator.locate.side_effect = lambda image, **kwargs: (
            self.result if image == self.module.CWIMG.CONTINUE else None)
        self.assertTrue(self.task.battle())
        self.assertGreaterEqual(self.elapsed, 32)
        self.assertNotIn("v", self.operator.keys())
        self.assertEqual(len(self.continuation_clicks()), 1)
        self.task._vision.capture_sample.assert_not_called()

    def test_single_preparation_frame_after_grace_does_not_stop_transition(self):
        self.observe()
        preparation_seen = []

        def transient_preparation(images, **kwargs):
            if self.module.CWIMG.PREPARATION_STAGE in images:
                if 45 <= self.elapsed < 45.5:
                    preparation_seen.append(self.elapsed)
                    return self.preparation_without_entry(images, **kwargs)
                return -1, None
            if self.elapsed >= 50 and self.module.IMG.Q in images:
                return images.index(self.module.IMG.Q), FakeBox(source="Q")
            return -1, None

        self.operator.locate_any.side_effect = transient_preparation
        self.operator.locate.side_effect = lambda image, **kwargs: (
            self.result if image == self.module.CWIMG.CONTINUE else None)
        self.assertTrue(self.task.battle())
        self.assertEqual(preparation_seen, [45])
        self.assertGreaterEqual(self.elapsed, 50)
        self.assertEqual(len(self.continuation_clicks()), 1)
        self.task._vision.capture_sample.assert_not_called()

    def test_late_entry_does_not_disable_manually_enabled_auto_battle(self):
        self.observe()
        auto = {"enabled": False, "manual_enabled": False}

        def press(key):
            if key == "v":
                auto["enabled"] = not auto["enabled"]

        def late_entry(images, **kwargs):
            # Reproduce the observed timing: manual enable around 52 seconds,
            # followed by delayed Q recognition around 69 seconds after entry.
            if self.elapsed >= 52 and not auto["manual_enabled"]:
                auto.update(enabled=True, manual_enabled=True)
            if self.elapsed >= 69 and self.module.IMG.Q in images:
                return images.index(self.module.IMG.Q), FakeBox(source="Q")
            return -1, None

        self.operator.on_press = press
        self.operator.locate_any.side_effect = late_entry
        self.operator.locate.side_effect = lambda image, **kwargs: (
            self.result if image == self.module.CWIMG.CONTINUE else None)

        self.assertTrue(self.task.battle())
        self.assertGreaterEqual(self.elapsed, 69)
        self.assertTrue(auto["manual_enabled"])
        self.assertTrue(auto["enabled"])
        self.assertEqual(self.operator.keys(), [])
        self.assertEqual(len(self.continuation_clicks()), 1)
        self.task._vision.capture_sample.assert_not_called()

    def test_unknown_frame_resets_the_preparation_confirmation_duration(self):
        self.observe()

        def interrupted_preparation(images, **kwargs):
            if self.module.CWIMG.PREPARATION_STAGE in images:
                if 45 <= self.elapsed < 47 or 48 <= self.elapsed < 50.5:
                    return self.preparation_without_entry(images, **kwargs)
                return -1, None
            if self.elapsed >= 50.5 and self.module.IMG.Q in images:
                return images.index(self.module.IMG.Q), FakeBox(source="Q")
            return -1, None

        self.operator.locate_any.side_effect = interrupted_preparation
        self.operator.locate.side_effect = lambda image, **kwargs: (
            self.result if image == self.module.CWIMG.CONTINUE else None)
        self.assertTrue(self.task.battle())
        self.assertGreaterEqual(self.elapsed, 50.5)
        self.assertEqual(len(self.continuation_clicks()), 1)
        self.task._vision.capture_sample.assert_not_called()

    def test_confirmation_popup_is_clicked_once_but_is_not_battle_evidence(self):
        self.observe()
        confirmation = FakeBox(source="ENSURE")
        self.operator.locate.side_effect = lambda image, **kwargs: (
            confirmation if image == self.module.IMG.ENSURE else None)
        with self.assertRaisesRegex(RuntimeError, "entry_timeout"):
            self.task.battle()
        self.assertEqual(self.click_boxes(), [self.current_button, confirmation])
        self.assert_no_long_wait_or_battle_log()
        self.assert_no_result_or_retreat_actions()
        self.assert_sample("entry_timeout")

    def test_delayed_q_after_confirmation_allows_battle_wait_and_continuation(self):
        self.observe()
        confirmation = FakeBox(source="ENSURE")
        self.operator.locate.side_effect = lambda image, **kwargs: (
            confirmation if image == self.module.IMG.ENSURE else
            self.result if image == self.module.CWIMG.CONTINUE else None)
        observations = iter([None, None, self.module.IMG.Q])

        def delayed_entry(images, **kwargs):
            if self.module.CWIMG.PREPARATION_STAGE in images:
                return self.preparation_without_entry(images, **kwargs)
            target = next(observations, self.module.CWIMG.CONTINUE)
            if target is None or target not in images:
                return -1, None
            return images.index(target), FakeBox(source=target)

        self.operator.locate_any.side_effect = delayed_entry
        self.assertTrue(self.task.battle())
        self.assertEqual(self.click_boxes(), [self.current_button, confirmation])
        self.assertEqual(self.operator.keys(), [])
        messages = [str(call.args[0]) for call in self.module.logger.info.call_args_list]
        self.assertTrue(any("已确认进入战斗" in message for message in messages))
        self.assertEqual(len(self.continuation_clicks()), 1)

    def test_direct_result_evidence_skips_combat_wait(self):
        for index in (1, 2):
            with self.subTest(entry_index=index):
                self.operator.calls.clear()
                self.operator.wait_any_img.reset_mock()
                self.module.logger.reset_mock()
                self.observe()
                self.enter_via(index)
                self.assertTrue(self.task.battle())
                self.assertEqual(self.operator.keys(), [])
                self.assertEqual(len(self.continuation_clicks()), 1)
                self.assert_no_long_wait_or_battle_log()
                self.task._vision.capture_sample.assert_not_called()

    def test_skip_requires_result_evidence_but_not_frontline(self):
        self.operator.wait_any_img.side_effect = None
        self.operator.wait_any_img.return_value = 1, self.button
        self.operator.locate_any.side_effect = None
        self.operator.locate_any.return_value = 1, self.result
        self.operator.locate.side_effect = lambda image, **kwargs: (
            self.result if image == self.module.CWIMG.CONTINUE else None)
        self.assertTrue(self.task.battle())
        self.task.refresh_character.assert_not_called()
        self.task.place_character.assert_not_called()
        self.operator.wait_img.assert_not_called()
        self.assertEqual(self.click_boxes(), [self.button])
        self.operator.locate_any.assert_called_with(
            [self.module.CWIMG.SETTLE, self.module.CWIMG.CONTINUE], trace=False)
        self.assert_no_long_wait_or_battle_log()
        self.assertEqual(len(self.continuation_clicks()), 1)

    def test_skip_without_result_does_not_click_continuation_or_start_combat_wait(self):
        self.operator.wait_any_img.side_effect = None
        self.operator.wait_any_img.return_value = 1, self.button
        with self.assertRaisesRegex(RuntimeError, "entry_timeout"):
            self.task.battle()
        self.task.refresh_character.assert_not_called()
        self.task.place_character.assert_not_called()
        self.assertEqual(self.click_boxes(), [self.button])
        self.assert_no_long_wait_or_battle_log()
        self.assert_no_result_or_retreat_actions()
        self.assert_sample("entry_timeout")

    def test_entry_index_without_matched_box_does_not_prove_combat_started(self):
        self.observe()

        def false_q_with_preparation(images, **kwargs):
            if self.module.CWIMG.PREPARATION_STAGE in images:
                return self.preparation_without_entry(images, **kwargs)
            return 0, None

        self.operator.locate_any.side_effect = false_q_with_preparation
        with self.assertRaisesRegex(RuntimeError, "entry_timeout"):
            self.task.battle()
        self.assert_no_long_wait_or_battle_log()
        self.assert_no_result_or_retreat_actions()
        self.assert_sample("entry_timeout")

    def test_stop_during_short_entry_wait_propagates_without_result_or_recovery_clicks(self):
        self.observe()
        advance_sleep = self.operator.sleep

        def stop_during_sleep(seconds):
            advance_sleep(seconds)
            self.operator.stop_event.set()

        self.operator.sleep = stop_during_sleep
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task.battle()
        self.assert_no_long_wait_or_battle_log()
        self.assert_no_result_or_retreat_actions()
        self.task._vision.capture_sample.assert_not_called()

    def test_battle_entry_failure_stops_run_without_next_attempt_or_ending(self):
        self.task._report_runtime_identity = Mock()
        self.task.start_game = Mock(return_value=True)
        self.task._read_preparation_round = Mock(return_value=(1, 1))
        self.task.harvest_crystals = Mock()
        self.task.get_in_hand_area = Mock()
        self.task._refresh_dirty_field = Mock()
        self.task.handle_characters_updated = Mock()
        self.task.update_max_team_size = Mock()
        self.task.sell_character = Mock(return_value=self.logic.SellResult(
            self.logic.ActionResult.CONFIRMED))
        self.task.stage_transition = Mock()
        self.task.shopping = Mock()
        self.task.handle_ending = Mock()
        self.assertFalse(self.task.run())
        self.task.start_game.assert_called_once()
        # Preparation retries are bounded and never send the battle input.
        self.assertLessEqual(self.task.place_character.call_count,
                             2 + self.task.preparation_budget["recoveries"])
        self.task.stage_transition.assert_not_called()
        self.task.shopping.assert_not_called()
        self.task.handle_ending.assert_not_called()
        self.assertEqual(self.click_boxes(), [])
        self.assert_no_long_wait_or_battle_log()
        self.assert_no_result_or_retreat_actions()
        self.assert_sample("preparation_preparation_no_progress")
        self.assertEqual(self.task._last_preparation_result.blocked_reason, "no_confirmed_frontline")
        self.assertEqual(self.task._last_preparation_result.recoveries, 1)


if __name__ == "__main__":
    unittest.main()
