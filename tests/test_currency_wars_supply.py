"""Supply-box regressions using production waits and synthetic image sequences.

All screenshots, OCR, mouse input, time and sleeps are isolated from the game.
"""
from __future__ import annotations

import sys
from itertools import cycle
import unittest
from unittest.mock import Mock, patch

from PIL import Image, ImageDraw

from test_currency_wars_flow import FakeBox, FakeOperator, load_isolated_task


class CurrencyWarsSupplyTests(unittest.TestCase):
    def setUp(self):
        self.module, _, _, names = load_isolated_task()
        self.addCleanup(lambda: [sys.modules.pop(name, None) for name in names])
        self.operator = FakeOperator()
        self.operator.mouse_down = Mock(return_value=True)
        self.operator.mouse_up = Mock(return_value=True)
        self.task = self.module.CurrencyWars(self.operator, runtimes=3)
        self.task._vision.capture_sample = Mock(return_value=None)
        self.task._release_pointer_unconditionally = Mock(return_value=True)
        self.task._get_character_in_area = Mock()
        self.choice = Image.new("RGB", (100, 60), (10, 10, 10))
        self.moving = Image.new("RGB", (100, 60), (110, 110, 110))
        self.ready = Image.new("RGB", (100, 60), (230, 230, 230))
        self.prompt = "请选择1件装备"
        self.elapsed = 0.0
        original_sleep = self.operator.sleep

        def advance_sleep(seconds):
            self.elapsed += seconds
            original_sleep(seconds)

        self.operator.sleep = advance_sleep
        clock = patch.object(self.module.time, "monotonic", side_effect=lambda: self.elapsed)
        clock.start()
        self.addCleanup(clock.stop)

    def route_targets(self, targets, preparation=True):
        queue = iter(targets)

        def locate(image, *args, **kwargs):
            if image == self.module.CWIMG.OPEN:
                return next(queue)
            if image == self.module.CWIMG.PREPARATION_STAGE and preparation:
                return FakeBox()
            return None

        self.operator.locate = Mock(side_effect=locate)

    def capture_reason(self):
        self.task._vision.capture_sample.assert_called_once()
        return self.task._vision.capture_sample.call_args.args[0]

    def test_no_supply_items_scans_bench_without_reward_clicks(self):
        self.task.get_in_hand_area(True)
        self.task._get_character_in_area.assert_called_once()
        self.operator.mouse_down.assert_not_called()
        self.assertFalse(any(name in ("click", "click_box") for name, _, _ in self.operator.calls))

    def test_slow_animation_has_no_choice_click_until_stable_duration_passes(self):
        self.route_targets([FakeBox(left=430, top=945), None])
        self.task._read_supply_frame = Mock(side_effect=[
            None, None, None, (self.moving, self.prompt),
        ] + [(self.choice, self.prompt)] * 5 + [(self.ready, "")] * 2)
        click = self.operator.click_point

        def click_after_stability(*args, **kwargs):
            self.assertEqual(self.task._read_supply_frame.call_count, 9)
            self.assertGreaterEqual(self.elapsed, 4.9)
            return click(*args, **kwargs)

        self.operator.click_point = Mock(side_effect=click_after_stability)
        self.task.get_in_hand_area(True)
        self.operator.mouse_down.assert_called_once()
        self.operator.mouse_up.assert_called_once()
        self.operator.click_point.assert_called_once()
        self.task._get_character_in_area.assert_called_once()
        self.task._vision.capture_sample.assert_not_called()

    def test_choice_title_change_requires_new_stability_pair(self):
        second_prompt = "请选择1名角色"
        self.task._read_supply_frame = Mock(side_effect=[
            (self.choice, self.prompt),
        ] + [(self.choice, second_prompt)] * 5)
        frame, prompt = self.task._wait_supply_choice()
        self.assertIs(frame, self.choice)
        self.assertEqual(prompt, second_prompt)
        self.assertEqual(self.task._read_supply_frame.call_count, 6)
        self.assertFalse(any(name in ("click", "click_box") for name, _, _ in self.operator.calls))

    def test_missing_choice_never_reclicks_same_box_or_scans_bench(self):
        self.operator.locate = Mock(return_value=FakeBox(left=560, top=945))
        self.task._read_supply_frame = Mock(return_value=None)
        with self.assertRaisesRegex(RuntimeError, "supply_choice_timeout"):
            self.task.get_in_hand_area(True)
        self.operator.mouse_down.assert_called_once()
        self.operator.mouse_up.assert_called_once()
        self.assertGreaterEqual(self.elapsed, 30)
        self.assertLessEqual(self.elapsed, 30.5)
        self.assertFalse(any(name in ("click", "click_box") for name, _, _ in self.operator.calls))
        self.task._get_character_in_area.assert_not_called()
        self.assertEqual(self.capture_reason(), "supply_choice_timeout")

    def test_choice_click_is_not_repeated_when_reward_does_not_close(self):
        self.route_targets([FakeBox()])
        self.task._read_supply_frame = Mock(return_value=(self.choice, self.prompt))
        with self.assertRaisesRegex(RuntimeError, "supply_result_timeout"):
            self.task.get_in_hand_area(True)
        self.operator.mouse_down.assert_called_once()
        self.assertEqual(sum(name == "click" for name, _, _ in self.operator.calls), 1)
        self.task._get_character_in_area.assert_not_called()
        self.assertEqual(self.capture_reason(), "supply_result_timeout")

    def test_result_confirmation_is_clicked_only_once_until_popup_closes(self):
        self.route_targets([])
        confirm = FakeBox(source="CONFIRM_SELECTION")
        self.operator.locate_any = Mock(return_value=(0, confirm))
        self.task._read_supply_frame = Mock(side_effect=[
            (self.choice, self.prompt), (self.choice, self.prompt),
            (self.choice, self.prompt), (self.ready, ""), (self.ready, ""),
        ])
        self.task._wait_supply_result(self.choice)
        self.operator.locate_any.assert_called_once()
        confirmations = [args[0] for name, args, _ in self.operator.calls if name == "click_box"]
        self.assertEqual(confirmations, [confirm])
        self.assertEqual(self.task._read_supply_frame.call_count, 5)
        self.task._vision.capture_sample.assert_not_called()

    def test_result_needs_changed_image_and_consecutive_unobstructed_ready_frames(self):
        self.route_targets([])
        self.task._read_supply_frame = Mock(side_effect=[
            (self.choice, ""), None, (self.ready, ""),
            (self.ready, self.prompt), (self.ready, ""), (self.ready, ""),
        ])
        self.task._wait_supply_result(self.choice)
        self.assertEqual(self.task._read_supply_frame.call_count, 6)
        self.task._vision.capture_sample.assert_not_called()

    def test_result_ocr_failure_is_not_popup_closed_evidence(self):
        self.route_targets([])
        self.task._read_supply_frame = Mock(return_value=None)
        with self.assertRaisesRegex(RuntimeError, "supply_result_timeout"):
            self.task._wait_supply_result(self.choice)
        self.assertGreaterEqual(self.elapsed, 30)
        self.assertLessEqual(self.elapsed, 30.5)
        self.assertEqual(self.capture_reason(), "supply_result_timeout")

    def test_two_boxes_are_processed_sequentially_before_bench_scan(self):
        first, second = FakeBox(left=430, top=945), FakeBox(left=555, top=945)
        self.route_targets([first, second, None])
        one_box = [(self.choice, self.prompt)] * 5 + [(self.ready, "")] * 2
        self.task._read_supply_frame = Mock(side_effect=one_box + one_box)
        opened = []

        def down(*point):
            opened.append(point)
            self.assertEqual(self.task._read_supply_frame.call_count, 7 * (len(opened) - 1))
            return True

        self.operator.mouse_down.side_effect = down
        self.task.get_in_hand_area(True)
        self.assertEqual(opened, [first.center, second.center])
        self.assertEqual(sum(name == "click" for name, _, _ in self.operator.calls), 2)
        self.task._get_character_in_area.assert_called_once()

    def test_item_limit_with_remaining_box_stops_before_bench_scan(self):
        self.route_targets([FakeBox(left=100 * i, top=945) for i in range(10)])
        self.task._wait_supply_choice = Mock(return_value=(self.choice, self.prompt))
        self.task._wait_supply_result = Mock()
        with self.assertRaisesRegex(RuntimeError, "supply_item_limit"):
            self.task.get_in_hand_area(True)
        self.assertEqual(self.operator.mouse_down.call_count, 9)
        self.assertEqual(self.task._wait_supply_result.call_count, 9)
        self.task._get_character_in_area.assert_not_called()
        self.assertEqual(self.capture_reason(), "supply_item_limit")

    def test_stop_during_held_button_releases_mouse_and_propagates(self):
        def stop_while_down(*args):
            self.operator.stop_event.set()
            return True

        self.operator.mouse_down.side_effect = stop_while_down
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task._press_supply_open(FakeBox())
        self.operator.mouse_up.assert_not_called()
        self.task._release_pointer_unconditionally.assert_called_once()

    def test_failed_mouse_release_uses_emergency_release(self):
        self.operator.mouse_up.return_value = False
        self.assertFalse(self.task._press_supply_open(FakeBox()))
        self.task._release_pointer_unconditionally.assert_called_once()

    def test_failed_selection_click_does_not_try_confirmation_or_scan(self):
        self.route_targets([FakeBox()])
        self.task._wait_supply_choice = Mock(return_value=(self.choice, self.prompt))
        self.task._wait_supply_result = Mock()
        self.operator.click_point = Mock(return_value=False)
        with self.assertRaisesRegex(RuntimeError, "supply_choice_click_failed"):
            self.task.get_in_hand_area(True)
        self.task._wait_supply_result.assert_not_called()
        self.task._get_character_in_area.assert_not_called()

    def test_failed_confirmation_click_does_not_retry(self):
        self.task._read_supply_frame = Mock(return_value=(self.choice, self.prompt))
        self.operator.locate_any = Mock(return_value=(0, FakeBox()))
        self.operator.click_box = Mock(return_value=False)
        with self.assertRaisesRegex(RuntimeError, "supply_confirmation_click_failed"):
            self.task._wait_supply_result(self.choice)
        self.operator.click_box.assert_called_once()
        self.assertEqual(self.capture_reason(), "supply_confirmation_click_failed")

    def test_supply_failure_propagates_through_game_loop_and_stops_run(self):
        self.task._report_runtime_identity = Mock()
        self.task.start_game = Mock(return_value=True)
        self.task.harvest_crystals = Mock()
        self.task.place_character = Mock()
        self.task.battle = Mock()
        self.task.handle_ending = Mock()
        self.route_targets([FakeBox()])
        self.task._read_supply_frame = Mock(return_value=None)
        self.assertFalse(self.task.run())
        self.task.start_game.assert_called_once()
        self.task._get_character_in_area.assert_not_called()
        self.task.place_character.assert_not_called()
        self.task.battle.assert_not_called()
        self.task.handle_ending.assert_not_called()
        reasons = [call.args[0] for call in self.task._vision.capture_sample.call_args_list]
        self.assertEqual(reasons[0], "supply_choice_timeout")
        self.assertIn("runtime_recovery", reasons)

    def test_read_frame_requires_selection_instruction_and_reward_kind(self):
        self.operator.screenshot = Mock(return_value=self.ready)
        for text, expected in (
            ("请选择1件装备", True), ("挑选一名专家", True),
            ("选择角色", True), ("请选择武器", True),
            ("简易武装箱请选择1个", True),
            ("简易武装箱", False), ("请选择1个", False),
            ("装备说明", False), ("选择投资环境", False), ("", False),
        ):
            with self.subTest(text=text):
                self.task._vision._engine_ocr = Mock(return_value=[(None, text)])
                frame, prompt = self.task._read_supply_frame()
                self.assertIsNotNone(frame)
                self.assertEqual(bool(prompt), expected)

    def test_weapon_box_title_and_instruction_still_require_stable_choice_region(self):
        self.operator.screenshot = Mock(side_effect=[self.moving] + [self.choice] * 5)
        self.task._vision._engine_ocr = Mock(return_value=[
            (None, "简易武装箱"), (None, "请选择1个"),
            (None, "幸运星"), (None, "生命之花"),
            (None, "轮滑鞋"), (None, "以太钻头"),
        ])
        frame, prompt = self.task._wait_supply_choice()
        self.assertIn("简易武装箱请选择1个", prompt)
        self.assertEqual(self.operator.screenshot.call_count, 6)
        self.assertGreaterEqual(self.elapsed, 3.7)
        self.assertFalse(any(name in ("click", "click_box") for name, _, _ in self.operator.calls))
        self.task._vision.capture_sample.assert_not_called()

    def test_read_frame_distinguishes_ocr_failure_from_no_selection_prompt(self):
        self.operator.screenshot = Mock(return_value=self.ready)
        self.task._vision._engine_ocr = Mock(return_value=None)
        self.assertIsNone(self.task._read_supply_frame())
        self.task._vision._engine_ocr.return_value = []
        self.assertEqual(self.task._read_supply_frame()[1], "")


    def test_small_animation_at_choice_point_is_not_hidden_by_whole_frame_average(self):
        still = Image.new("RGB", (1000, 600), (10, 10, 10))
        animated = still.copy()
        # Window (0.8, 0.25) maps to about (857, 200) in this 0.08..0.92/0.05..0.65 crop.
        ImageDraw.Draw(animated).rectangle((837, 180, 877, 220), fill=(250, 250, 250))
        self.assertLess(self.module.image_distance(still, animated), 0.02)
        self.task._read_supply_frame = Mock(side_effect=cycle([
            (still, self.prompt), (animated, self.prompt),
        ]))
        with self.assertRaisesRegex(RuntimeError, "supply_choice_timeout"):
            self.task._wait_supply_choice()
        self.assertGreaterEqual(self.elapsed, 30)
        self.assertLessEqual(self.elapsed, 30.5)
        self.assertFalse(any(name in ("click", "click_box") for name, _, _ in self.operator.calls))
        self.assertEqual(self.capture_reason(), "supply_choice_timeout")

    def test_supply_choice_can_appear_after_twelve_seconds_and_still_be_selected(self):
        self.route_targets([FakeBox(left=430, top=945), None])
        selected_at = []
        click_point = self.operator.click_point

        def select_after_stability(*args, **kwargs):
            self.assertGreaterEqual(self.elapsed, 13.2)
            selected_at.append(self.elapsed)
            return click_point(*args, **kwargs)

        def delayed_choice():
            if selected_at:
                return self.ready, ""
            return (self.choice, self.prompt) if self.elapsed >= 12 else None

        self.operator.click_point = Mock(side_effect=select_after_stability)
        self.task._read_supply_frame = Mock(side_effect=delayed_choice)
        self.task.get_in_hand_area(True)
        self.operator.mouse_down.assert_called_once()
        self.operator.click_point.assert_called_once()
        self.task._get_character_in_area.assert_called_once()
        self.assertLess(selected_at[0], 15)
        self.task._vision.capture_sample.assert_not_called()

    def test_supply_result_can_return_after_twelve_seconds_with_one_confirmation(self):
        self.route_targets([FakeBox(left=430, top=945), None])
        selected_at = []
        confirm = FakeBox(source="CONFIRM_SELECTION")
        self.operator.locate_any = Mock(return_value=(0, confirm))
        click_point = self.operator.click_point

        def select_once(*args, **kwargs):
            selected_at.append(self.elapsed)
            return click_point(*args, **kwargs)

        def delayed_result():
            if selected_at and self.elapsed - selected_at[0] >= 12:
                return self.ready, ""
            return self.choice, self.prompt

        self.operator.click_point = Mock(side_effect=select_once)
        self.task._read_supply_frame = Mock(side_effect=delayed_result)
        self.task.get_in_hand_area(True)
        self.assertGreaterEqual(self.elapsed - selected_at[0], 12)
        self.assertLessEqual(self.elapsed - selected_at[0], 13)
        self.operator.click_point.assert_called_once()
        self.operator.locate_any.assert_called_once()
        self.assertEqual([args[0] for name, args, _ in self.operator.calls if name == "click_box"], [confirm])
        self.task._get_character_in_area.assert_called_once()
        self.task._vision.capture_sample.assert_not_called()

    def test_same_source_after_apparent_result_success_is_never_opened_twice(self):
        self.route_targets([FakeBox(left=550, top=945), FakeBox(left=560, top=945)])
        self.task._wait_supply_choice = Mock(return_value=(self.choice, self.prompt))
        self.task._wait_supply_result = Mock()
        with self.assertRaisesRegex(RuntimeError, "supply_source_unchanged"):
            self.task.get_in_hand_area(True)
        self.operator.mouse_down.assert_called_once()
        self.operator.mouse_up.assert_called_once()
        self.task._wait_supply_result.assert_called_once()
        self.assertEqual(sum(name == "click" for name, _, _ in self.operator.calls), 1)
        self.task._get_character_in_area.assert_not_called()
        self.assertEqual(self.capture_reason(), "supply_source_unchanged")


if __name__ == "__main__":
    unittest.main()
