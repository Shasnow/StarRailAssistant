"""Battle settlement may advance to a node before a continue button is seen."""
from __future__ import annotations

import unittest
from unittest.mock import Mock

import test_currency_wars_battle_result as reward_tests
from test_currency_wars_flow import FakeBox


class CurrencyWarsPostBattleStageTests(unittest.TestCase):
    # Reuse the isolated task, fake clock, and input fixture without inheriting
    # its test cases or operating a real game window.
    screen = reward_tests.CurrencyWarsBattleResultTests.screen
    assert_no_recovery = reward_tests.CurrencyWarsBattleResultTests.assert_no_recovery
    CONTINUE_POINT = reward_tests.CurrencyWarsBattleResultTests.CONTINUE_POINT
    ACCELERATE_POINT = reward_tests.CurrencyWarsBattleResultTests.ACCELERATE_POINT

    def setUp(self):
        reward_tests.CurrencyWarsBattleResultTests.setUp(self)
        self.prepared = False
        self.phase = lambda: "preparation" if self.prepared else (
            "reward" if self.elapsed < 5 else "node")
        self.operator.locate_any.side_effect = self.locate_stage
        self.operator.locate.side_effect = self.locate_control
        self.task._vision.read_battle_screen.side_effect = lambda: self.screen(
            "result_animation" if self.phase() == "reward" else "unknown")

    def locate_stage(self, images, **kwargs):
        target = None
        if self.phase() == "node":
            target = self.module.CWIMG.ENCOUNTER_NODE
        elif self.phase() == "preparation":
            target = self.module.CWIMG.PREPARATION_STAGE
        if target in images:
            return images.index(target), FakeBox(source=target)
        return -1, None

    def locate_control(self, image, **kwargs):
        if image == self.module.CWIMG.ENCOUNTER_NODE and self.phase() == "node":
            return FakeBox(source=image)
        return None

    def input_clicks(self):
        return [args for name, args, _ in self.operator.calls if name == "click"]

    def test_reward_advances_to_encounter_without_continue_then_selects_node_once(self):
        self.assertTrue(self.task.battle())
        self.assertGreaterEqual(self.elapsed, 5.5)
        self.assertEqual(self.input_clicks(), [])
        self.assert_no_recovery()
        self.task._vision.capture_sample.assert_not_called()

        def stage_wait(images, **kwargs):
            return self.locate_stage(images)

        click = self.operator.click_point

        def select_node(*args, **kwargs):
            if args[:2] == (0.56, 0.84):
                self.prepared = True
            return click(*args, **kwargs)

        self.operator.wait_any_img.side_effect = stage_wait
        self.operator.click_point = Mock(side_effect=select_node)
        self.task.handle_stage_transitioned = Mock(return_value=True)
        self.assertTrue(self.task.stage_transition())
        self.assertEqual([args[:2] for args in self.input_clicks()],
                         [(0.35, 0.50), (0.56, 0.84)])
        self.task.handle_stage_transitioned.assert_called_once()
        self.assert_no_recovery()

    def test_encounter_without_q_or_visible_reward_is_positive_entry_completion(self):
        self.phase = lambda: "node"
        self.assertTrue(self.task.battle())
        self.assertGreaterEqual(self.elapsed, 0.5)
        self.assertEqual(self.input_clicks(), [])
        self.assertNotIn("v", self.operator.keys())
        self.assert_no_recovery()
        self.task._vision.capture_sample.assert_not_called()

    def test_preparation_after_confirmed_reward_skips_missing_continue(self):
        self.phase = lambda: "reward" if self.elapsed < 5 else "preparation"
        self.assertTrue(self.task.battle())
        self.assertGreaterEqual(self.elapsed, 5.5)
        self.assertEqual(self.input_clicks(), [])
        self.assert_no_recovery()
        self.task._vision.capture_sample.assert_not_called()

    def test_preparation_alone_does_not_prove_settlement_during_combat(self):
        self.phase = lambda: "preparation"
        self.clock_step = 60
        self.assertEqual(self.task._wait_battle_result(in_combat=True), (None, None, False))
        self.assertGreaterEqual(self.elapsed, 600)
        self.assertEqual(self.input_clicks(), [])
        self.task._vision.capture_sample.assert_not_called()

    def test_single_node_frame_does_not_unlock_next_stage(self):
        self.phase = lambda: "node" if self.elapsed == 0 else "unknown"
        self.clock_step = 60
        with self.assertRaisesRegex(RuntimeError, "entry_timeout"):
            self.task.battle()
        self.assertGreaterEqual(self.elapsed, 600)
        self.assertEqual(self.input_clicks(), [])
        self.assert_no_recovery()

    def test_stop_between_node_observations_prevents_handoff(self):
        self.phase = lambda: "node"
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

    def test_encounter_that_does_not_close_has_bounded_failure_without_reclicks(self):
        self.phase = lambda: "node"
        with self.assertRaisesRegex(RuntimeError, "遭遇节点确认后仍未退场"):
            self.task.handle_encounter_node(None)
        self.assertGreaterEqual(self.elapsed, 30)
        self.assertEqual([args[:2] for args in self.input_clicks()],
                         [(0.35, 0.50), (0.56, 0.84)])
        self.task._vision.capture_sample.assert_called_once()
        self.assertEqual(self.task._vision.capture_sample.call_args.args[0],
                         "encounter_selection_timeout")

    def test_stop_during_encounter_departure_wait_propagates(self):
        self.phase = lambda: "node"
        advance = self.operator.sleep

        def stop_after_selection(seconds):
            advance(seconds)
            self.operator.stop_event.set()

        self.operator.sleep = stop_after_selection
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task.handle_encounter_node(None)
        self.assertEqual(len(self.input_clicks()), 2)
        self.task._vision.capture_sample.assert_not_called()

    def test_missing_node_title_alone_does_not_confirm_departure(self):
        self.phase = lambda: "unknown"
        with self.assertRaisesRegex(RuntimeError, "遭遇节点确认后仍未退场"):
            self.task.handle_encounter_node(None)
        self.assertGreaterEqual(self.elapsed, 30)
        self.assertEqual(len(self.input_clicks()), 2)

    def test_reappearing_encounter_is_not_selected_twice_in_one_transition(self):
        self.task._wait_stage_ready = Mock(side_effect=[2, 2])
        self.task.handle_encounter_node = Mock(return_value=False)
        with self.assertRaisesRegex(RuntimeError, "遭遇节点确认后重复出现"):
            self.task.stage_transition()
        self.task.handle_encounter_node.assert_called_once_with(None)
        self.assertEqual(self.input_clicks(), [])


if __name__ == "__main__":
    unittest.main()
