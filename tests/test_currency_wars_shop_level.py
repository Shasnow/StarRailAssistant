"""Shop flow regression with real level parsing and fake game input."""

from __future__ import annotations

import sys
import unittest
from unittest.mock import Mock

from test_currency_wars_flow import FakeOperator, load_isolated_task


def ocr(text, x=0, y=0, w=40, h=20):
    return ([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], text, 0.99)


class CurrencyWarsShopLevelTests(unittest.TestCase):
    def test_buy_experience_button_above_level_does_not_block_search_or_upgrade(self):
        module, characters, logic, module_names = load_isolated_task()
        self.addCleanup(lambda: [sys.modules.pop(name, None) for name in module_names])
        operator = FakeOperator()
        task = module.CurrencyWars(operator, runtimes=1)
        task.is_running = True
        task._preparation_round = (2, 1)
        task._set_shop_open = Mock(return_value=True)
        main_c = characters.Characters.get_character("灵砂")
        task.main_c = main_c.name
        task.strategy_characters = {main_c.name: 2}
        task._set_observation("on_field", logic.SlotObservation(
            0, logic.SlotState.KNOWN, character=main_c, occupied=True,
            evidence="name_match", revision=1, stars=1))
        self.assertTrue(task._confirm_main_c_fielded())

        # Level 6 permits a refresh, followed by the no-purchase upgrade branch.
        task.min_level, task.mid_level = 6, 7
        task.shopping_budget["refreshes"] = 1
        task.get_coins = Mock(side_effect=[55, 53, 49])
        before = logic.ShopObservation(logic.ShopState.READY, cards=(logic.ShopCard(
            0, characters.Characters.get_character("佩拉"), task.store_area[0]),))
        after = logic.ShopObservation(logic.ShopState.READY, cards=(logic.ShopCard(
            0, characters.Characters.get_character("椒丘"), task.store_area[0]),))
        task._scan_store = Mock(side_effect=[before, after, after])
        upgraded = False
        level_reads = []

        def press(key):
            nonlocal upgraded
            if key == "f":
                upgraded = True

        def read_level(parser):
            # The previous row's bottom exactly touches the complete level box.
            tokens = [ocr(f"Lv.{7 if upgraded else 6}", x=10, y=20, w=45),
                      ocr("购买经验", x=0, y=0, w=80)]
            observation = parser(tokens)
            level_reads.append(observation)
            return observation

        operator.on_press = press
        task._vision.read_level = Mock(side_effect=read_level)
        result = task.shopping()

        self.assertEqual(operator.keys(), ["d", "f"])
        self.assertEqual(result.result, logic.ActionResult.CONFIRMED)
        self.assertEqual(result.refreshes, 1)
        self.assertEqual(result.experience_purchases, 1)
        self.assertEqual(result.confirmed_purchases, 0)
        self.assertEqual(result.reason, "refresh_budget")
        # Refreshing preserves the level; only the XP input needs a new read.
        self.assertEqual([item.level for item in level_reads], [6, 7])
        self.assertTrue(all(item.evidence == "explicit_level_label" for item in level_reads))


if __name__ == "__main__":
    unittest.main()
