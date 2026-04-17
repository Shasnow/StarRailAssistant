import importlib.util
import pathlib
import sys
import unittest


def load_module():
    module_path = pathlib.Path(__file__).with_name("tasks").joinpath("currency_wars", "shopping_logic.py")
    spec = importlib.util.spec_from_file_location("currency_wars_shopping_logic", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


shopping_logic = load_module()


class DummyCharacter:
    def __init__(self, name: str):
        self.name = name


class TestShoppingLogic(unittest.TestCase):
    def test_store_scan_with_prices_is_valid(self):
        self.assertTrue(
            shopping_logic.is_store_scan_valid(
                [
                    ([[0, 0]], "佩拉", 0.99),
                    ([[0, 0]], "2", 0.99),
                ]
            )
        )

    def test_store_scan_without_prices_or_reserve_marker_is_invalid(self):
        self.assertFalse(
            shopping_logic.is_store_scan_valid(
                [
                    ([[0, 0]], "品前台区域", 0.88),
                ]
            )
        )

    def test_pending_post_refresh_scan_skips_early_exit_once(self):
        self.assertIsNone(
            shopping_logic.get_pre_refresh_exit_reason(
                coins=2,
                min_coins=40,
                is_overclock=False,
                pending_post_refresh_scan=True,
            )
        )

    def test_low_coins_still_exit_before_normal_store_scan(self):
        reason = shopping_logic.get_pre_refresh_exit_reason(
            coins=2,
            min_coins=40,
            is_overclock=False,
            pending_post_refresh_scan=False,
        )

        self.assertIn("金币不足4", reason)

    def test_detects_reserve_full_marker_from_store_ocr(self):
        self.assertTrue(
            shopping_logic.store_has_reserve_full_marker(
                [
                    ([[0, 0]], "备战席已满", 0.99),
                    ([[0, 0]], "桑博", 0.99),
                ]
            )
        )
        self.assertFalse(
            shopping_logic.store_has_reserve_full_marker(
                [
                    ([[0, 0]], "桑博", 0.99),
                    ([[0, 0]], "佩拉", 0.99),
                ]
            )
        )

    def test_purchase_still_visible_in_same_slot_means_failure(self):
        result = shopping_logic.evaluate_purchase_attempt(
            3,
            "桑博",
            [DummyCharacter("灵砂"), DummyCharacter("风堇"), DummyCharacter("Saber"), DummyCharacter("桑博")],
            reserve_full=True,
            store_scan_valid=True,
        )

        self.assertFalse(result.succeeded)
        self.assertTrue(result.should_clear_reserve)
        self.assertFalse(result.should_reopen_store)

    def test_purchase_disappearing_from_target_slot_means_success(self):
        result = shopping_logic.evaluate_purchase_attempt(
            3,
            "桑博",
            [DummyCharacter("灵砂"), DummyCharacter("风堇"), DummyCharacter("Saber")],
            reserve_full=False,
            store_scan_valid=True,
        )

        self.assertTrue(result.succeeded)
        self.assertFalse(result.should_clear_reserve)
        self.assertFalse(result.should_reopen_store)

    def test_failed_purchase_without_reserve_full_does_not_trigger_cleanup(self):
        result = shopping_logic.evaluate_purchase_attempt(
            0,
            "佩拉",
            [DummyCharacter("佩拉")],
            reserve_full=False,
            store_scan_valid=True,
        )

        self.assertFalse(result.succeeded)
        self.assertFalse(result.should_clear_reserve)
        self.assertFalse(result.should_reopen_store)

    def test_invalid_store_scan_requests_reopen_instead_of_false_success(self):
        result = shopping_logic.evaluate_purchase_attempt(
            1,
            "桑博",
            [],
            reserve_full=False,
            store_scan_valid=False,
        )

        self.assertFalse(result.succeeded)
        self.assertFalse(result.should_clear_reserve)
        self.assertTrue(result.should_reopen_store)


if __name__ == "__main__":
    unittest.main()
