"""Offline regressions for the actual 2026-10-09 shop and layout failure paths."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import test_currency_wars_flow as fixture
import test_currency_wars_shop_state as shop_fixture
from test_currency_wars_shop_overlay import synthetic_dialog, title_results


class ShopFieldVisibilityTests(unittest.TestCase):
    def setUp(self):
        shop_fixture.CurrencyWarsShopStateTests.setUp(self)
        self.character = self.characters.Characters.SilverWolfLV999
        self.point = self.task.on_field_area[2]
        self.selected = None
        self.probability_open = False
        physical_click = self.operator.click_point

        def click(x, y, *args, **kwargs):
            # A blank click does not reliably fold the store in the real UI.
            if (x, y) == (0.5, 0.5):
                self.operator.record("click", x, y, *args, **kwargs)
                return True
            if (x, y) == self.point:
                self.probability_open = self.operator.shop_open
                self.selected = "probability" if self.probability_open else "character"
            return physical_click(x, y, *args, **kwargs)

        self.operator.click_point = Mock(side_effect=click)
        self.operator.ocr = Mock(side_effect=lambda **kwargs:
            [([[0, 0], [100, 0], [100, 35], [0, 35]], self.character.name, 0.99)]
            if self.selected == "character" else [])
        self.operator.locate_all = Mock(return_value=[fixture.FakeBox(left=20)])
        self.task._set_observation("on_field", self.logic.SlotObservation(
            2, self.logic.SlotState.KNOWN, self.character, True, "name_match", 1, 1))
        self.task._dirty_slots.clear()
        self.task._invalidate_character_evidence(self.character.name, "observed_price:3->4")

    def test_price_change_recheck_folds_shop_before_frontline_click(self):
        self.task._refresh_dirty_field()
        self.assertEqual(self.operator.transition_actions, [False])
        self.assertFalse(self.probability_open)
        self.assertEqual(self.task._observations["on_field"][2].stars, 1)
        calls = self.operator.calls
        fold_at = next(i for i, (name, _, _) in enumerate(calls) if name == "click_box")
        card_at = next(i for i, (name, args, _) in enumerate(calls)
                       if name == "click" and args == self.point)
        self.assertLess(fold_at, card_at)

    def test_failed_fold_never_clicks_probability_bar(self):
        self.operator.block_close = True
        with self.assertRaisesRegex(RuntimeError, "field_scan_shop_not_closed"):
            self.task._refresh_dirty_field()
        self.assertIsNone(self.selected)
        self.assertFalse(self.probability_open)
        self.assertIn(("on_field", 2), self.task._dirty_slots)

    def test_no_dirty_field_does_not_toggle_shop(self):
        self.task._dirty_slots = {("in_hand", 0)}
        self.task._refresh_dirty_field()
        self.assertEqual(self.operator.transition_actions, [])
        self.assertTrue(self.operator.shop_open)


class ProbabilityRecoveryTests(unittest.TestCase):
    def setUp(self):
        shop_fixture.CurrencyWarsShopStateTests.setUp(self)
        self.modal_open = True
        self.block_close = False
        self.close_point = (0.78, 0.247)
        self.close_clicks = 0
        physical_visible = self.operator._visible
        physical_click = self.operator.click_point
        self.operator._visible = lambda name: not self.modal_open and physical_visible(name)
        self.task._read_shop_probability_overlay = Mock(
            side_effect=lambda frame=None: self.close_point if self.modal_open else None)

        def click(x, y, *args, **kwargs):
            if (x, y) == self.close_point:
                self.operator.record("click", x, y, *args, **kwargs)
                self.close_clicks += 1
                if not self.block_close:
                    self.modal_open = False
                return True
            return physical_click(x, y, *args, **kwargs)
        self.operator.click_point = Mock(side_effect=click)

    def test_close_overlay_then_authenticate_and_fold_store(self):
        self.assertTrue(self.task._set_shop_open(False))
        self.assertEqual(self.close_clicks, 1)
        self.assertFalse(self.modal_open)
        self.assertFalse(self.operator.shop_open)
        self.assertEqual(self.operator.transition_actions, [False])

    def test_close_overlay_keeps_requested_expanded_store(self):
        self.assertTrue(self.task._set_shop_open(True))
        self.assertEqual(self.close_clicks, 1)
        self.assertEqual(self.operator.transition_actions, [])
        self.assertTrue(self.operator.shop_open)

    def test_accepted_close_input_does_not_confirm_underlying_page(self):
        self.block_close = True
        self.assertFalse(self.task._set_shop_open(False))
        self.assertEqual(self.close_clicks, 1)
        self.assertEqual(self.operator.transition_actions, [])

    def test_single_frame_overlay_is_not_clicked(self):
        frames = iter([self.close_point] + [None] * 100)
        self.task._read_shop_probability_overlay = Mock(side_effect=lambda frame=None: next(frames))
        self.assertFalse(self.task._set_shop_open(False))
        self.assertEqual(self.close_clicks, 0)

    def test_stop_between_overlay_frames_prevents_close(self):
        self.operator.stop_on_sleep = True
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task._set_shop_open(False)
        self.assertEqual(self.close_clicks, 0)

    def test_runtime_recovery_closes_overlay_before_page_navigation(self):
        self.task._probe_runtime_page = Mock(side_effect=lambda:
            ("shop_probability", self.close_point) if self.modal_open else ("preparation", None))
        self.assertTrue(self.task._recover_runtime_flow(RuntimeError("shop_not_closed")))
        self.assertEqual(self.close_clicks, 1)
        self.assertFalse(self.operator.shop_open)


class ShoppingLayoutRecoveryTests(unittest.TestCase):
    character = fixture.CurrencyWarsFlowTests.character
    observe = fixture.CurrencyWarsFlowTests.observe
    empty_board = fixture.CurrencyWarsFlowTests.empty_board

    def setUp(self):
        fixture.CurrencyWarsFlowTests.setUp(self)
        self.empty_board()
        self.task.economy_config = object()
        self.task._layout_valid = False
        self.task._bench_dirty = False
        self.task._refresh_dirty_field = Mock()
        self.result = SimpleNamespace(reason="purchase_targets_unknown")

    def test_missing_layout_is_recovered_before_individual_slot_reads(self):
        order = []
        def recover(**kwargs):
            self.assertEqual(kwargs, {"equip": False, "recover_layout": True})
            order.append("layout")
            self.task._layout_valid = True
        self.task.refresh_backend_character = Mock(side_effect=recover)
        self.task._refresh_dirty_field.side_effect = lambda: order.append("slots")
        self.assertTrue(self.task._resume_shopping_after(self.result))
        self.assertEqual(order, ["layout", "slots"])
        self.assertEqual(self.task._economy_recovery_attempts, 1)

    def test_failed_layout_does_not_waste_budget_on_unreadable_slots(self):
        self.task.refresh_backend_character = Mock(return_value=False)
        self.task.preparation_budget["recoveries"] = 2
        self.assertTrue(self.task._resume_shopping_after(self.result))
        self.assertTrue(self.task._resume_shopping_after(self.result))
        with self.assertRaisesRegex(RuntimeError, "purchase_targets_unknown"):
            self.task._resume_shopping_after(self.result)
        self.assertEqual(self.task.refresh_backend_character.call_count, 2)
        self.task._refresh_dirty_field.assert_not_called()

    def test_confirmed_layout_is_not_rebuilt_for_unrelated_evidence(self):
        self.task._layout_valid = True
        self.task.refresh_backend_character = Mock()
        self.assertTrue(self.task._resume_shopping_after(self.result))
        self.task.refresh_backend_character.assert_not_called()
        self.task._refresh_dirty_field.assert_called_once()


class ProbabilityOCRAdapterTests(unittest.TestCase):
    def setUp(self):
        fixture.CurrencyWarsFlowTests.setUp(self)
        self.frame = synthetic_dialog()
        self.operator.screenshot = Mock(return_value=self.frame)

    def test_title_engine_receives_crop_from_the_same_client_frame(self):
        rows = title_results()
        def recognize(crop, **kwargs):
            self.assertEqual(crop.size, (500, 62))
            self.assertEqual(crop.tobytes(), self.frame.crop((374, 238, 874, 300)).tobytes())
            self.assertEqual(kwargs, {"use_det": True, "use_cls": False, "use_rec": True})
            return SimpleNamespace(txts=[rows[0][1]], boxes=[rows[0][0]], scores=[rows[0][2]])
        self.operator.ocr_engine = Mock(side_effect=recognize)
        point = self.task._read_shop_probability_overlay()
        self.assertIsNotNone(point)
        self.assertAlmostEqual(point[0], 1497 / 1920, places=3)
        self.operator.screenshot.assert_called_once()
        self.operator.ocr_engine.assert_called_once()
        self.assertEqual(self.operator.calls, [])

    def test_mismatched_window_frame_never_runs_title_ocr(self):
        self.operator.window_context.width = 1280
        self.operator.ocr_engine = Mock()
        self.assertIsNone(self.task._read_shop_probability_overlay())
        self.operator.ocr_engine.assert_not_called()

    def test_stop_during_ocr_is_not_swallowed_as_no_overlay(self):
        def recognize(*args, **kwargs):
            self.operator.stop_event.set()
            return (title_results(), 0.01)
        self.operator.ocr_engine = Mock(side_effect=recognize)
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task._read_shop_probability_overlay()


if __name__ == "__main__":
    unittest.main()
