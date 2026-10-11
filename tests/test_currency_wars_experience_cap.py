"""Runtime experience observations with real parsing and fake OCR/input only."""

from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import test_currency_wars_flow as fixture


class ExperienceCapRuntimeTests(unittest.TestCase):
    empty_board = fixture.CurrencyWarsFlowTests.empty_board
    observe = fixture.CurrencyWarsFlowTests.observe

    def setUp(self):
        source_tasks = fixture.ROOT / "tasks" / "currency_wars"
        with patch.object(fixture, "TASKS", source_tasks):
            fixture.CurrencyWarsFlowTests.setUp(self)
        self.assertEqual(Path(self.module.__file__).resolve(),
                         (source_tasks / "CurrencyWars.py").resolve())

    @staticmethod
    def rows(text):
        return [(None, part.strip(), 0.99) for part in text.split("|")]

    def read(self, first, second=None, *, level=9, recognize_cap=True):
        self.operator.ocr = Mock(side_effect=[
            self.rows(first), self.rows(first if second is None else second)])
        result = self.task._read_experience_progress(level, recognize_cap=recognize_cap)
        self.assertEqual(self.operator.ocr.call_count, 2)
        return result

    def test_context_around_adjacent_cap_remains_reliable(self):
        for text in (
            "Lv.9 | MAX",
            "F | 购买经验 | Lv.9 | MAX",
            "Lv.9 | MAX | nder Preset: M",
            "F | 购买经验 | Lv.9 | MAX | Quality(0.6667)(1280",
            "Lv.9 | 满级",
            "Lv.9 | 已满级",
            "Lv.9 | 等级已满",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.read(text), (0, 0))
        self.assertEqual(self.operator.keys(), [])

    def test_fullwidth_level_marker_and_cap_are_normalized(self):
        self.assertEqual(self.read("Ｆ | 购买经验 | Ｌｖ．９ | ＭＡＸ | Overlay"), (0, 0))

    def test_two_frames_require_agreeing_cap_evidence(self):
        self.assertEqual(self.read("Lv.9 | MAX", "F | 购买经验 | Lv.9 | MAX"), (0, 0))
        for second in ("Lv.9", "Lv.9 | 80/84", "Lv.8 | MAX"):
            with self.subTest(second=second):
                self.assertIsNone(self.read("Lv.9 | MAX", second))

    def test_cap_must_be_complete_and_adjacent_to_the_current_level(self):
        for text in (
            "Lv.9 | MAXIMUM", "Lv.9 | MAXED", "Lv.9 | MAX_1",
            "MAX | Lv.9", "Lv.9 | 角色 | MAX", "Lv.9 | note MAX",
            "Lv.8 | MAX", "MAX", "银狼LV.999 | MAX",
            "Lv.9 | MAX | Lv.10", "Lv.9 | MAX | Lv.9",
            "Lv.9 | MAX | MAX", "Lv.9 | 已满级别",
        ):
            with self.subTest(text=text):
                self.assertIsNone(self.read(text))

    def test_any_fraction_conflicts_with_an_explicit_cap(self):
        for text in (
            "Lv.9 | MAX | 8/9", "8/9 | Lv.9 | MAX",
            "Lv.9 | 80/84 | MAX", "Lv.9 | MAX | 0/0",
            "Lv.9 | MAX | 0.5/84", "Lv.9 | MAX | 12345/12345",
            "Lv.9 | MAX | ８／９",
        ):
            with self.subTest(text=text):
                self.assertIsNone(self.read(text))

    def test_missing_progress_does_not_imply_a_cap(self):
        for text in ("Lv.9", "Lv.9 | 0/0", "F | 购买经验", ""):
            with self.subTest(text=text):
                self.assertIsNone(self.read(text))

    def test_ordinary_experience_keeps_its_existing_frame_and_level_checks(self):
        text = "F | 购买经验 | Lv.8 | 58/72 | nder Preset: M | Quality(0.6667)(1280"
        for recognize_cap in (False, True):
            with self.subTest(recognize_cap=recognize_cap):
                self.assertEqual(self.read(text, level=8, recognize_cap=recognize_cap), (58, 72))
                self.assertEqual(self.read("Ｌｖ．８ | ５８／７２", level=8,
                                           recognize_cap=recognize_cap), (58, 72))
                self.assertIsNone(self.read("Lv.8 | 58/72", "Lv.8 | 62/72", level=8,
                                           recognize_cap=recognize_cap))
                self.assertIsNone(self.read("Lv.7 | 58/72", level=8,
                                           recognize_cap=recognize_cap))

    def test_cap_is_not_enabled_for_ordinary_progress_reads(self):
        self.assertIsNone(self.read("F | 购买经验 | Lv.9 | MAX", recognize_cap=False))

    def test_confirmed_cap_with_context_spends_final_round_gold_on_refreshes(self):
        self.empty_board()
        self.task._bench_dirty = False
        self.task._preparation_round = (3, 7)
        self.task.strategy_characters = {}
        self.task.get_level = Mock(return_value=9)
        money = [4]
        self.task.get_coins = Mock(side_effect=lambda: money[0])
        self.task._scan_store = Mock(return_value=self.logic.ShopObservation(self.logic.ShopState.EMPTY))
        self.operator.ocr = Mock(side_effect=[
            self.rows("F | 购买经验 | Lv.9 | MAX | nder Preset: M") for _ in range(2)])

        def spend(key):
            self.assertEqual(key, "d", "A confirmed cap must never buy experience")
            money[0] -= self.task.SHOP_REFRESH_COST

        self.operator.on_press = spend

        result = self.task.shopping()

        self.assertEqual(result.result, self.logic.ActionResult.CONFIRMED)
        self.assertEqual((result.experience_purchases, result.refreshes, money[0]), (0, 2, 0))
        self.assertEqual(result.reason, "final_round_gold_exhausted")
        self.assertEqual(self.operator.keys(), ["d", "d"])
        self.assertEqual(self.operator.ocr.call_count, 2)


if __name__ == "__main__":
    unittest.main()
