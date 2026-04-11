import importlib.util
import pathlib
import unittest


def load_module():
    module_path = pathlib.Path(__file__).with_name("tasks").joinpath("currency_wars", "placement_logic.py")
    spec = importlib.util.spec_from_file_location("currency_wars_placement_logic", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


placement_logic = load_module()


class TestPlacementLogic(unittest.TestCase):
    def test_strategy_roles_are_processed_before_fillers(self):
        front, back = placement_logic.build_placement_plan(
            [
                ("乱破", "on", False),
                ("星期日", "on", False),
                ("忘归人", "off", False),
                ("佩拉", "off", False),
                ("黑塔", "both", False),
            ],
            {"星期日", "希儿"},
            {"佩拉", "桑博"},
        )

        self.assertEqual(front, [1, 0, 4])
        self.assertEqual(back, [3, 2, 4])

    def test_placed_or_empty_cards_are_skipped(self):
        front, back = placement_logic.build_placement_plan(
            [
                (None, "on", False),
                ("星期日", "on", True),
                ("佩拉", "off", False),
            ],
            {"星期日"},
            {"佩拉"},
        )

        self.assertEqual(front, [])
        self.assertEqual(back, [2])

    def test_only_strategy_characters_get_auto_equip(self):
        strategy_names = {"星期日", "佩拉", "桑博"}

        self.assertTrue(placement_logic.should_auto_equip_character("佩拉", strategy_names))
        self.assertFalse(placement_logic.should_auto_equip_character("飞霄", strategy_names))
        self.assertFalse(placement_logic.should_auto_equip_character(None, strategy_names))


if __name__ == "__main__":
    unittest.main()
