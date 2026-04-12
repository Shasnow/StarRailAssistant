import importlib.util
import pathlib
import sys
import unittest


def load_module():
    module_path = pathlib.Path(__file__).with_name("tasks").joinpath("currency_wars", "sell_logic.py")
    spec = importlib.util.spec_from_file_location("currency_wars_sell_logic", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sell_logic = load_module()


class DummyCharacter:
    def __init__(self, name: str, priority: int, is_placed: bool):
        self.name = name
        self.priority = priority
        self.is_placed = is_placed


class TestSellLogic(unittest.TestCase):
    def test_force_sell_prefers_placed_non_strategy_over_unplaced_strategy(self):
        characters = [
            DummyCharacter("希儿", 99, False),
            DummyCharacter("黑天鹅", 5, True),
            DummyCharacter("银狼", 94, True),
            DummyCharacter("娜塔莎", 95, False),
            DummyCharacter("佩拉", 93, True),
            DummyCharacter("花火", 90, True),
            DummyCharacter("杰帕德", 96, True),
            DummyCharacter("星期日", 98, True),
        ]

        result = sell_logic.build_sell_plan(
            characters,
            {"希儿": 1, "银狼": 1, "娜塔莎": 1, "佩拉": 1, "花火": 1, "杰帕德": 1, "星期日": 1},
            force=True,
            target_hand_count=7,
        )

        self.assertEqual([item[1].name for item in result], ["黑天鹅"])

    def test_sell_plan_prefers_lower_priority_within_same_protection_group(self):
        characters = [
            DummyCharacter("风堇", 2, False),
            DummyCharacter("翡翠", 1, False),
            DummyCharacter("椒丘", 3, False),
            DummyCharacter("忘归人", 4, False),
            DummyCharacter("缇宝", 2, False),
            DummyCharacter("大丽花", 1, False),
            DummyCharacter("貊泽", 1, False),
            DummyCharacter("那刻夏", 3, False),
        ]

        result = sell_logic.build_sell_plan(
            characters,
            {},
            target_hand_count=7,
        )

        self.assertEqual(result[0][1].priority, 1)

    def test_tied_candidates_sell_later_slot_first(self):
        characters = [
            DummyCharacter("星期日", 98, False),
            DummyCharacter("风堇", 1, False),
            DummyCharacter("娜塔莎", 95, False),
            DummyCharacter("杰帕德", 96, False),
            DummyCharacter("佩拉", 93, False),
            DummyCharacter("花火", 90, False),
            DummyCharacter("缇宝", 1, False),
            DummyCharacter("大丽花", 1, False),
        ]

        result = sell_logic.build_sell_plan(
            characters,
            {"星期日": 1, "娜塔莎": 1, "杰帕德": 1, "佩拉": 1, "花火": 1},
            target_hand_count=7,
        )

        self.assertEqual(result[0][0], 7)


if __name__ == "__main__":
    unittest.main()
