"""Shop/board visibility regressions using independent physical UI state.

The UI changes only when an input succeeds and its animation completes. Merely
requesting a shop state does not alter what subsequent observations can see.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "_currency_wars_shop_state_fixture", ROOT / "tests/test_currency_wars_flow.py")
fixture = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = fixture
_spec.loader.exec_module(fixture)


class ShopUI(fixture.FakeOperator):
    def __init__(self):
        super().__init__()
        self.shop_open = True
        self.preparation = True
        self.preparation_marker = "BATTLE"
        self.seconds = 1.0
        self.transition_delay = 0.0
        self.pending_transition = None
        self.block_open = False
        self.block_close = False
        self.fail_collect = False
        self.collection_states = []
        self.transition_actions = []
        self.stop_on_sleep = False
        self.purchase_target = None
        self.purchased = False
        self.coins = 50

    def monotonic(self):
        return self.seconds

    def _complete_transition(self):
        if self.pending_transition and self.seconds >= self.pending_transition[0]:
            self.shop_open = self.pending_transition[1]
            self.pending_transition = None

    def _visible(self, name):
        self._complete_transition()
        if not self.preparation:
            return False
        return (name == "FOLD" and self.shop_open or
                name == self.preparation_marker and not self.shop_open)

    def locate(self, name, *args, **kwargs):
        self.record("locate", name, *args, **kwargs)
        return fixture.FakeBox(source=name) if self._visible(name) else None

    def locate_any(self, names, *args, **kwargs):
        self.record("locate_any", names, *args, **kwargs)
        for index, name in enumerate(names):
            if self._visible(name):
                return index, fixture.FakeBox(source=name)
        return -1, None

    def sleep(self, seconds):
        self.record("sleep", seconds)
        self.seconds += seconds
        self._complete_transition()
        if self.stop_on_sleep:
            self.stop_event.set()

    def _transition(self, opened):
        self.transition_actions.append(opened)
        blocked = self.block_open if opened else self.block_close
        if not blocked:
            self.pending_transition = (self.seconds + self.transition_delay, opened)
            self._complete_transition()
        return True  # Accepted input alone does not prove a UI transition.

    def click_box(self, box, *args, **kwargs):
        self.record("click_box", box, *args, **kwargs)
        if box is not None and box.source == "FOLD":
            return self._transition(False)
        return box is not None

    def click_point(self, x, y, *args, **kwargs):
        self.record("click", x, y, *args, **kwargs)
        if (x, y) == (0.8438, 0.8481):
            return self._transition(True)
        if (x, y) in ((0.5, 0.5), (0.5, 0.55)):
            self.shop_open = False
        elif (x, y) == self.purchase_target:
            if not self.shop_open:
                raise AssertionError("Purchase attempted behind the closed shop")
            self.purchased = True
            self.coins -= 3
        elif 0.66 <= x <= 0.84 and 0.20 <= y <= 0.40:
            self.collection_states.append(self.shop_open)
            return not self.fail_collect
        return True

    def drag_to(self, *args, **kwargs):
        self.record("drag", *args, **kwargs)
        self.collection_states.append(self.shop_open)
        return not self.fail_collect


class CurrencyWarsShopStateTests(unittest.TestCase):
    def setUp(self):
        self.module, self.characters, self.logic, names = fixture.load_isolated_task()
        self.addCleanup(lambda: [sys.modules.pop(name, None) for name in names])
        self.operator = ShopUI()
        self.module.time = types.SimpleNamespace(monotonic=self.operator.monotonic)
        self.task = self.module.CurrencyWars(self.operator, runtimes=1)
        self.task.is_running = True
        self.task._preparation_round = (2, 1)
        self.task.detect_silver_wolf_lv999 = Mock()
        self.task._vision.capture_sample = Mock(return_value=None)
        self.task.get_coins = Mock(side_effect=lambda: self.operator.coins)
        self.task.get_level = Mock(return_value=5)

    def configure_purchase(self):
        character = self.characters.Characters.get_character("希儿")
        self.task.main_c = character.name
        self.task.main_c_search_level = 5
        self.task.strategy_characters = {character.name: 2}
        card = self.logic.ShopCard(0, character, self.task.store_area[0],
                                   raw_text=character.name, price=3,
                                   price_evidence="price_badge")
        self.operator.purchase_target = card.target

        def scan():
            self.assertTrue(self.operator.shop_open, "Card scan needs a visible shop")
            return (self.logic.ShopObservation(self.logic.ShopState.EMPTY)
                    if self.operator.purchased else
                    self.logic.ShopObservation(self.logic.ShopState.READY, (card,)))

        self.task._scan_store = Mock(side_effect=scan)

    def test_local_harvest_folds_shop_before_every_crystal_drag(self):
        self.task.harvest_crystals()
        self.assertEqual(self.operator.transition_actions, [False])
        self.assertEqual(self.operator.collection_states, [False] * 5)
        self.task.detect_silver_wolf_lv999.assert_called_once()

    def test_browser_harvest_folds_shop_before_click_grid(self):
        self.operator.type = "Browser"
        self.task.harvest_crystals()
        self.assertEqual(self.operator.transition_actions, [False])
        self.assertEqual(self.operator.collection_states, [False] * 50)

    def test_character_scan_closes_shop_then_shopping_reopens_and_buys(self):
        self.configure_purchase()
        fielded = self.characters.Characters.get_character("灵砂")
        self.task.strategy_characters[fielded.name] = 2
        self.task._observe_slot = Mock(return_value=self.logic.SlotObservation(
            0, self.logic.SlotState.KNOWN, character=fielded, occupied=True,
            stars=1, evidence="name_match", revision=1))
        # Exercise the actual character-panel cleanup which folds the shop.
        self.task._get_character_in_area(self.task.on_field_area[:1],
            self.task.on_field_character, force=True, equip=True)
        self.assertFalse(self.operator.shop_open)
        result = self.task.shopping()
        self.assertEqual(result.confirmed_purchases, 1)
        self.assertEqual(result.reason, "main_c_placement")
        self.assertEqual(self.operator.coins, 47)
        self.assertEqual(self.operator.transition_actions, [True, False])
        self.assertFalse(self.operator.shop_open)

    def test_delayed_transitions_need_confirmation_without_repeated_clicks(self):
        self.operator.transition_delay = 0.5
        self.assertTrue(self.task._set_shop_open(False))
        self.assertFalse(self.operator.shop_open)
        self.assertTrue(self.task._set_shop_open(True))
        self.assertTrue(self.operator.shop_open)
        self.assertEqual(self.operator.transition_actions, [False, True])

    def test_already_requested_state_is_observed_twice_without_clicks(self):
        for opened in (True, False):
            with self.subTest(opened=opened):
                self.operator.shop_open = opened
                self.operator.calls.clear()
                self.assertTrue(self.task._set_shop_open(opened))
                fold_reads = [1 for name, args, _ in self.operator.calls
                              if name == "locate" and args[0] == "FOLD"
                              or name == "locate_any" and "FOLD" in args[0]]
                self.assertGreaterEqual(len(fold_reads), 2)
        self.assertEqual(self.operator.transition_actions, [])

    def test_preparation_title_is_positive_evidence_when_battle_button_absent(self):
        self.operator.shop_open = False
        self.operator.preparation_marker = "PREPARATION_STAGE"
        self.assertTrue(self.task._set_shop_open(False))
        self.assertTrue(self.task._set_shop_open(True))
        self.assertEqual(self.operator.transition_actions, [True])

    def test_unknown_page_never_opens_or_confirms_closed_shop(self):
        self.operator.preparation = False
        self.assertFalse(self.task._set_shop_open(False))
        self.assertFalse(self.task._set_shop_open(True))
        self.assertEqual(self.operator.transition_actions, [])
        self.assertFalse(any(name in ("click", "click_box", "key", "drag")
                             for name, _, _ in self.operator.calls))

    def test_shop_stuck_open_stops_harvest_without_collection(self):
        self.operator.block_close = True
        with self.assertRaisesRegex(RuntimeError, "crystals_shop_not_closed"):
            self.task.harvest_crystals()
        self.assertEqual(self.operator.transition_actions, [False])
        self.assertEqual(self.operator.collection_states, [])
        self.task.detect_silver_wolf_lv999.assert_not_called()

    def test_shop_stuck_closed_never_scans_or_spends(self):
        self.operator.shop_open = False
        self.operator.block_open = True
        self.task._scan_store = Mock()
        result = self.task.shopping()
        self.assertEqual(result.reason, "shop_not_open")
        self.assertEqual(result.confirmed_purchases, 0)
        self.assertEqual(self.operator.transition_actions, [True])
        self.task._scan_store.assert_not_called()
        self.task.get_coins.assert_not_called()
        self.assertEqual(self.operator.keys(), [])

    def test_failed_collection_input_aborts_remaining_grid_or_drag_rows(self):
        for kind in ("Local", "Browser"):
            with self.subTest(kind=kind):
                self.operator.type = kind
                self.operator.shop_open = False
                self.operator.collection_states.clear()
                self.operator.fail_collect = True
                with self.assertRaises(RuntimeError):
                    self.task.harvest_crystals()
                self.assertEqual(len(self.operator.collection_states), 1)
                self.task.detect_silver_wolf_lv999.assert_not_called()

    def test_shop_cleanup_failure_aborts_before_next_preparation_actions(self):
        self.configure_purchase()
        physical_click = self.operator.click_point

        def block_cleanup_after_purchase(*args, **kwargs):
            accepted = physical_click(*args, **kwargs)
            if self.operator.purchased:
                self.operator.block_close = True
            return accepted

        self.operator.click_point = Mock(side_effect=block_cleanup_after_purchase)
        with self.assertRaisesRegex(RuntimeError, "shopping_shop_not_closed"):
            self.task.shopping()
        self.assertTrue(self.operator.purchased)
        self.assertEqual(self.operator.transition_actions, [False, True, False])

    def test_stop_during_shopping_does_not_click_cleanup(self):
        stop_calls = []

        def stop_scan():
            self.operator.stop_event.set()
            stop_calls.append(len(self.operator.calls))
            raise self.module.ThreadStoppedError("user stop")

        self.task._scan_store = Mock(side_effect=stop_scan)
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task.shopping()
        self.assertTrue(self.operator.shop_open)
        self.assertEqual(self.operator.transition_actions, [False, True])
        self.assertEqual(len(self.operator.calls), stop_calls[0])

    def test_stop_during_visibility_wait_aborts_without_another_input(self):
        self.operator.shop_open = False
        self.operator.block_open = True
        self.operator.stop_on_sleep = True
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task._set_shop_open(True)
        self.assertLessEqual(len(self.operator.transition_actions), 1)

    def run_purchase_merge_recheck(self, *, block_reopen=False):
        character = self.characters.Characters.get_character("希儿")
        self.task.main_c = ""
        self.task.min_level = self.task.mid_level = 5
        self.task.min_coins = 99
        self.task.strategy_characters = {character.name: 2}
        for area in ("on_field", "off_field", "in_hand"):
            for index in range(len(self.task._observations[area])):
                self.task._set_observation(area, self.logic.SlotObservation(
                    index, self.logic.SlotState.EMPTY, occupied=False,
                    evidence="empty_detector", revision=1))
        self.task._set_observation("on_field", self.logic.SlotObservation(
            0, self.logic.SlotState.KNOWN, character=character, occupied=True,
            stars=1, evidence="name_match", revision=1))
        first = self.logic.ShopCard(0, character, self.task.store_area[0],
                                   price=3, price_evidence="price_badge")
        duplicate = self.logic.ShopCard(1, character, self.task.store_area[1],
                                       price=3, price_evidence="price_badge")
        self.operator.purchase_target = first.target
        coordinates = {point: (area, index)
                       for area in ("on_field", "off_field", "in_hand")
                       for index, point in enumerate(getattr(self.task, area + "_area"))}
        selected_slot = None
        field_rechecked = False
        physical_click = self.operator.click_point

        def click(x, y, *args, **kwargs):
            nonlocal selected_slot
            selected_slot = coordinates.get((x, y))
            return physical_click(x, y, *args, **kwargs)

        def read_character(*args, **kwargs):
            nonlocal field_rechecked
            if selected_slot == ("on_field", 0):
                self.assertTrue(self.operator.purchased)
                self.assertFalse(self.operator.shop_open)
                field_rechecked = True
                self.operator.block_open = block_reopen
                return [([[0, 0], [40, 0], [40, 20], [0, 20]], character.name, 0.99)]
            return []

        def scan():
            self.assertTrue(self.operator.shop_open, "Merge recheck must reopen before OCR")
            cards = (duplicate,) if self.operator.purchased else (first, duplicate)
            return self.logic.ShopObservation(self.logic.ShopState.READY, cards)

        self.operator.click_point = Mock(side_effect=click)
        self.operator.ocr = Mock(side_effect=read_character)
        self.operator.locate_all = Mock(return_value=[
            fixture.FakeBox(left=10, source="STAR"),
            fixture.FakeBox(left=20, source="STAR")])
        self.operator.currency_wars_slot_is_empty = lambda area, index: (area, index) != ("on_field", 0)
        self.task._scan_store = Mock(side_effect=scan)
        result = self.task.shopping()
        self.assertTrue(field_rechecked)
        self.assertEqual(result.confirmed_purchases, 1)
        self.assertEqual(self.operator.coins, 47)
        self.assertEqual(self.task._observations["on_field"][0].stars, 2)
        self.assertFalse(self.operator.shop_open)
        self.assertEqual(self.operator.keys(), [])
        return result

    def test_post_purchase_merge_recheck_reopens_before_next_store_scan(self):
        result = self.run_purchase_merge_recheck()
        self.assertEqual(result.reason, "coin_reserve")
        self.assertEqual(self.operator.transition_actions, [False, True, False, True, False])
        # Reuse the transaction-confirmation page until a panel closes it.
        self.assertEqual(self.task._scan_store.call_count, 3)

    def test_failed_reopen_after_merge_recheck_never_rescans_or_spends(self):
        result = self.run_purchase_merge_recheck(block_reopen=True)
        self.assertEqual(result.reason, "shop_not_open_after_recheck")
        self.assertEqual(self.operator.transition_actions, [False, True, False, True])
        self.assertEqual(self.task._scan_store.call_count, 2)


if __name__ == "__main__":
    unittest.main()
