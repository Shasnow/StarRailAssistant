"""Bounded price association, with recorded game OCR and optional pixel replay."""

import copy
import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


from tests.currency_wars_replays import REPLAY_ROOT, OCR_ROOT

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("_currency_wars_shop_prices", ROOT / "tasks/currency_wars/logic.py")
logic = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = logic
spec.loader.exec_module(logic)
FIXTURE = json.loads((ROOT / "tests/fixtures/currency_wars_shop_prices_real_log.json").read_text(encoding="utf-8"))
REAL_SHOP = REPLAY_ROOT / "bench_shop_training/occupied_client.png"


def token(text, left, right, top=8, bottom=40):
    return ([[left, top], [right, top], [right, bottom], [left, bottom]], text, 0.99)


class ShopPriceTests(unittest.TestCase):
    def setUp(self):
        self.characters = {name: SimpleNamespace(name=name, cost=9) for name in (
            "景元", "丹恒·腾荒", "千冶·刃", "那刻夏", "星期日", "爻光", "砂金", "遐蝶",
            "风堇", "缇宝", "杰帕德", "海瑟音", "火花", "真理医生", "希儿", "黑塔", "万敌", "远坂凛")}

    def scan(self, items, **kwargs):
        return logic.scan_store_cards(items, self.characters.get, FIXTURE["store_area"],
                                      kwargs.pop("width", 1920), **kwargs)

    def test_four_real_log_pages_preserve_all_twenty_short_long_and_last_prices(self):
        for index, record in enumerate(FIXTURE["records"]):
            with self.subTest(record=index):
                result = self.scan(record["ocr"])
                self.assertEqual(result.state, logic.ShopState.READY)
                self.assertEqual([card.slot_index for card in result.cards], list(range(5)))
                self.assertEqual([card.price for card in result.cards], record["expected_prices"])
                self.assertTrue(all(card.character.cost == 9 for card in result.cards))

    def test_real_price_boxes_scale_with_window_width(self):
        record = FIXTURE["records"][1]
        for scale in (2 / 3, 4 / 3):
            with self.subTest(scale=scale):
                items = copy.deepcopy(record["ocr"])
                for box, _, _ in items:
                    for point in box:
                        point[:] = [value * scale for value in point]
                self.assertEqual([c.price for c in self.scan(items, width=1920 * scale).cards],
                                 record["expected_prices"])

    def test_missing_price_never_borrows_next_slot_digit(self):
        items = copy.deepcopy(FIXTURE["records"][1]["ocr"])
        del items[1]
        self.assertEqual([c.price for c in self.scan(items).cards], [None, 2, 4, 3, 3])

    def test_free_price_is_explicit_not_missing(self):
        card = self.scan([token("缇宝", 12, 71), token("0", 214, 236)]).cards[0]
        self.assertEqual(card.price, 0)
        self.assertIsNone(self.scan([token("缇宝", 12, 71)]).cards[0].price)

    def test_unique_far_digit_must_be_in_right_price_area_and_same_row(self):
        for digit in (token("3", 145, 165, 8, 28), token("3", 214, 236, 100, 120)):
            with self.subTest(digit=digit):
                card = self.scan([token("缇宝", 12, 50, 8, 28), digit]).cards[0]
                self.assertIsNone(card.price)
                self.assertEqual(card.price_evidence, "price_not_associated_with_name")
        self.assertEqual(self.scan([token("缇宝", 12, 50, 8, 28),
                                    token("3", 214, 236, 8, 28)]).cards[0].price, 3)

    def test_price_box_crossing_slot_boundary_is_rejected_even_if_center_inside(self):
        # Slot 0 ends at crop-local x=259.2. This digit's centre lies inside it.
        card = self.scan([token("缇宝", 12, 71), token("3", 245, 268)]).cards[0]
        self.assertIsNone(card.price)
        self.assertEqual(card.price_evidence, "price_outside_slot")

    def test_small_name_edge_slack_does_not_allow_names_spanning_slots(self):
        # The measured third card's glyph starts 0.2 px left of the midpoint.
        self.assertEqual(self.scan([token("万敌", 547, 610), token("1", 753, 775)]).cards[0].price, 1)
        card = self.scan([token("万敌", 500, 660, 8, 28), token("1", 753, 775, 8, 28)]).cards[0]
        self.assertIsNone(card.price)
        self.assertEqual(card.price_evidence, "price_not_associated_with_name")

    def test_last_price_inside_reviewed_crop_but_outside_old_edge_is_valid(self):
        name = token("希儿", 1089, 1146)
        self.assertEqual(self.scan([name, token("3", 1289, 1311)]).cards[0].price, 3)
        self.assertIsNone(self.scan([name, token("3", 1315, 1330)]).cards[0].price)
        self.assertIsNone(self.scan([name, token("3", 1340, 1360)]).cards[0].price)
        self.assertIsNone(self.scan([name, token("3", 1289, 1311)], crop_to_x=0.86).cards[0].price)

    def test_two_independent_digits_are_ambiguous_even_in_fixed_price_area(self):
        for value in ("3", "4"):
            card = self.scan([token("缇宝", 12, 71), token("3", 204, 220), token(value, 230, 245)]).cards[0]
            self.assertIsNone(card.price)
            self.assertEqual(card.price_evidence, "ambiguous_price_digits")

    def test_experience_or_population_fraction_is_never_a_price(self):
        for value in ("24/52", "5/6", "LV.7"):
            result = self.scan([token("缇宝", 12, 71), token(value, 200, 240)])
            self.assertTrue(not result.cards or result.cards[0].price is None)

    def test_bad_crop_end_is_unknown(self):
        for end in (None, True, float("nan"), 0.19, 1.1):
            result = self.scan([token("缇宝", 12, 71)], crop_to_x=end)
            self.assertEqual((result.state, result.reason), (logic.ShopState.UNKNOWN, "invalid_crop_end"))

    def test_unknown_level_requiring_price_can_use_real_short_name_but_not_missing_price(self):
        known = self.scan(FIXTURE["records"][1]["ocr"]).cards[0]
        result = logic.evaluate_purchase(known, target_stars=2, coins=1, require_price=True)
        self.assertTrue(result.can_buy)
        self.assertEqual(result.reason, "eligible")
        self.assertFalse(logic.evaluate_purchase(known, target_stars=2, coins=0, require_price=True).can_buy)
        missing = self.scan([token("爻光", 12, 71)]).cards[0]
        self.assertFalse(logic.evaluate_purchase(missing, target_stars=2, coins=20, require_price=True).can_buy)

    @unittest.skipUnless(REAL_SHOP.exists() and os.environ.get("SRA_POPULATION_OCR_DEPS"),
                         "optional isolated RapidOCR dependencies not configured")
    def test_real_shop_pixels_confirm_fixed_price_area_and_rightmost_card(self):
        from PIL import Image
        deps = os.environ["SRA_POPULATION_OCR_DEPS"]
        sys.path.insert(0, deps)
        try:
            from rapidocr import RapidOCR
            models = OCR_ROOT / "models"
            engine = RapidOCR(config_path=OCR_ROOT / "config.yaml", params={
                "Global.log_level": "error", "Det.model_path": str(models / "PP-OCRv6_det_small.onnx"),
                "Rec.model_path": str(models / "PP-OCRv6_rec_small.onnx"),
                "Cls.model_path": str(models / "ch_ppocr_mobile_v2.0_cls_mobile.onnx"),
                "EngineConfig.onnxruntime.intra_op_num_threads": 2,
                "EngineConfig.onnxruntime.inter_op_num_threads": 2,
            })
            with Image.open(REAL_SHOP) as frame:
                crop = frame.convert("RGB").crop(tuple(round(v * (frame.width if i % 2 == 0 else frame.height))
                                                       for i, v in enumerate(FIXTURE["crop_roi"])))
            output = engine(crop)
            items = [(box.tolist(), text, float(score)) for box, text, score
                     in zip(output.boxes, output.txts, output.scores) if score > 0.8]
            result = self.scan(items)
            self.assertEqual([(card.slot_index, card.price) for card in result.cards],
                             [(0, 1), (1, 1), (2, 1), (3, 1), (4, 1)], items)
        finally:
            sys.path.remove(deps)


if __name__ == "__main__":
    unittest.main()
