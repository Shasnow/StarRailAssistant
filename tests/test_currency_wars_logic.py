"""Pure regression tests; loading logic.py never imports tasks or SRACore."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path

LOGIC_PATH = Path(__file__).resolve().parents[1] / "tasks" / "currency_wars" / "logic.py"
SPEC = importlib.util.spec_from_file_location("_currency_wars_logic_unit", LOGIC_PATH)
logic = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = logic
SPEC.loader.exec_module(logic)


@dataclass
class FakeCharacter:
    name: str
    stars: int = 2
    is_placed: bool = True


def ocr(text, x=0, y=0, w=40, h=20):
    return ([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], text, 0.99)


class LogicTests(unittest.TestCase):
    def setUp(self):
        self.characters = {name: FakeCharacter(name) for name in (
            "缇宝", "银狼", "银狼LV.999", "千冶·刃", "Saber", "Archer", "007", "备用")}
        self.characters["千冶•刃"] = self.characters["千冶·刃"]
        self.lookup = self.characters.get
        self.store = [(0.25, 0.18), (0.40, 0.18), (0.55, 0.18),
                      (0.68, 0.18), (0.80, 0.18)]
        self.width = 1000

    def shop_ocr(self, text, slot, *, y=0, w=40, offset=0):
        x = (self.store[slot][0] - 0.19) * self.width - w / 2 + offset
        return ocr(text, x=x, y=y, w=w)

    def scan(self, results, **kwargs):
        return logic.scan_store_cards(results, self.lookup, self.store, self.width, **kwargs)

    def test_observations_are_separate_from_mutable_character_state(self):
        c = self.characters["缇宝"]
        first = logic.SlotObservation(0, logic.SlotState.KNOWN, c, True, stars=1)
        second = logic.SlotObservation(1, logic.SlotState.KNOWN, c, True, stars=3)
        self.assertEqual((first.stars, second.stars, c.stars, c.is_placed), (1, 3, 2, True))

    def test_unknown_empty_and_known_are_distinct(self):
        self.assertEqual(set(logic.SlotState), {
            logic.SlotState.UNKNOWN, logic.SlotState.EMPTY,
            logic.SlotState.KNOWN, logic.SlotState.LOCKED,
        })
        unknown = logic.SlotObservation(0, logic.SlotState.UNKNOWN)
        self.assertIsNone(unknown.occupied)
        self.assertIsNone(unknown.character)
        explicit_empty = logic.ShopObservation(logic.ShopState.EMPTY)
        self.assertEqual(explicit_empty.cards, ())

    def test_action_results_do_not_imply_verified_purchase(self):
        result = logic.ShoppingResult(logic.ActionResult.INDETERMINATE, attempted_purchases=1)
        self.assertEqual(result.confirmed_purchases, 0)
        sale = logic.SellResult(logic.ActionResult.FAILED, attempted=1, reason="no_feedback")
        self.assertEqual(sale.confirmed, 0)

    def test_numeric_noise_and_unknown_text_are_not_registered(self):
        before = dict(self.characters)
        for results in (None, [], [ocr("1")], [ocr("...")], [ocr("未收录角色")]):
            with self.subTest(results=results):
                self.assertIsNone(logic.parse_character_name(results, self.lookup))
        self.assertEqual(self.characters, before)

    def test_complete_whitelist_names_support_english_and_numeric(self):
        for name in ("Saber", "Archer", "银狼LV.999", "007"):
            self.assertIs(logic.parse_character_name([ocr(name)], self.lookup), self.characters[name])

    def test_whitespace_and_aliases_use_whitelist(self):
        self.assertIs(logic.parse_character_name([ocr(" 银狼 LV.999 ")], self.lookup),
                      self.characters["银狼LV.999"])
        self.assertIs(logic.parse_character_name([ocr("千冶•刃")], self.lookup),
                      self.characters["千冶·刃"])

    def test_spatial_fragments_are_sorted_before_joining(self):
        parts = [ocr("LV.999", x=45, w=60), ocr("银狼", x=0)]
        self.assertIs(logic.parse_character_name(parts, self.lookup),
                      self.characters["银狼LV.999"])

    def test_split_numbers_remain_available_to_full_name(self):
        parts = [ocr("银狼", x=0), ocr("LV.", x=44, w=30), ocr("999", x=77, w=30)]
        self.assertIs(logic.parse_character_name(parts, self.lookup),
                      self.characters["银狼LV.999"])

    def test_price_does_not_replace_known_name(self):
        parts = [ocr("缇宝", x=0), ocr("1", x=70, w=10)]
        self.assertIs(logic.parse_character_name(parts, self.lookup), self.characters["缇宝"])

    def test_two_line_name_fragments_can_be_joined(self):
        parts = [ocr("LV.999", x=0, y=22, w=65), ocr("银狼", x=0, y=0)]
        self.assertIs(logic.parse_character_name(parts, self.lookup),
                      self.characters["银狼LV.999"])

    def test_distant_name_parts_are_not_joined(self):
        parts = [ocr("银狼", x=0), ocr("LV.999", x=500, w=60)]
        self.assertIsNone(logic.parse_character_name(parts, self.lookup))

    def test_conflicting_or_unrecognized_suffixes_do_not_match_short_name(self):
        for parts in ([ocr("银狼", x=0), ocr("LV.888", x=44, w=60)],
                      [ocr("缇宝", x=0), ocr("Saber", x=44)]):
            self.assertIsNone(logic.parse_character_name(parts, self.lookup))

    def test_invalid_ocr_item_is_not_silently_discarded(self):
        self.assertIsNone(logic.parse_character_name([ocr("缇宝"), ("invalid",)], self.lookup))

    def test_shop_none_and_no_text_remain_unknown(self):
        for results in (None, [], [ocr("")], [ocr("1")], [ocr("...")]):
            self.assertEqual(self.scan(results).state, logic.ShopState.UNKNOWN)

    def test_shop_numeric_whitelist_still_cannot_prove_a_card(self):
        self.assertEqual(self.scan([self.shop_ocr("007", 0)]).state, logic.ShopState.UNKNOWN)

    def test_explicit_full_message_and_split_message(self):
        self.assertEqual(self.scan([ocr("备战席已满")]).state, logic.ShopState.FULL)
        split = [ocr("备战席", x=0), ocr("已满", x=45)]
        self.assertEqual(self.scan(split).state, logic.ShopState.FULL)

    def test_character_with_bei_does_not_trigger_full(self):
        result = self.scan([self.shop_ocr("备用", 2)])
        self.assertEqual(result.state, logic.ShopState.READY)
        self.assertEqual(result.cards[0].slot_index, 2)

    def test_shop_keeps_real_slot_after_unrecognized_card(self):
        result = self.scan([self.shop_ocr("未知角色", 0), self.shop_ocr("缇宝", 4)])
        self.assertEqual(result.state, logic.ShopState.READY)
        self.assertEqual([(c.slot_index, c.target) for c in result.cards], [(4, self.store[4])])
        self.assertEqual(result.reason, "partial_unrecognized_cards")

    def test_shop_holes_and_ocr_order_never_compact_cards(self):
        result = self.scan([self.shop_ocr("Saber", 4), self.shop_ocr("缇宝", 1)])
        self.assertEqual(result.state, logic.ShopState.READY)
        self.assertEqual([c.slot_index for c in result.cards], [1, 4])

    def test_shop_fragment_coordinates_and_full_name(self):
        x = (0.55 - 0.19) * self.width - 40
        results = [ocr("银狼", x=x, w=35), ocr("LV.999", x=x + 38, w=48)]
        result = self.scan(results)
        self.assertEqual(result.state, logic.ShopState.READY)
        self.assertEqual((result.cards[0].slot_index, result.cards[0].character.name),
                         (2, "银狼LV.999"))

    def test_dynamic_price_is_not_guessed_from_character_definition(self):
        character = self.characters["银狼LV.999"]
        character.cost = 5
        result = self.scan([self.shop_ocr("银狼LV.999", 2)])
        self.assertEqual(result.state, logic.ShopState.READY)
        self.assertIsNone(result.cards[0].price)
        self.assertEqual(character.cost, 5)

    def test_split_name_number_is_not_treated_as_a_price(self):
        x = (0.55 - 0.19) * self.width - 45
        result = self.scan([ocr("银狼", x=x, w=30), ocr("LV.", x=x + 31, w=24),
                            ocr("999", x=x + 57, w=30)])
        self.assertEqual(result.state, logic.ShopState.READY)
        self.assertEqual(result.cards[0].character.name, "银狼LV.999")
        self.assertIsNone(result.cards[0].price)
    def test_same_slot_different_names_are_unknown(self):
        result = self.scan([self.shop_ocr("缇宝", 2), self.shop_ocr("Saber", 2, y=22)])
        self.assertEqual(result.state, logic.ShopState.UNKNOWN)
        self.assertEqual(result.reason, "conflicting_slot_names")
        self.assertEqual(result.cards, ())

    def test_duplicated_same_name_detection_does_not_duplicate_purchase(self):
        result = self.scan([self.shop_ocr("缇宝", 2), self.shop_ocr("缇宝", 2)])
        self.assertEqual(result.state, logic.ShopState.READY)
        self.assertEqual(len(result.cards), 1)

    def test_missing_bad_and_outside_geometry_are_unknown(self):
        for item in ((None, "缇宝", 0.99), ocr("缇宝", x=-5), ocr("缇宝", x=1000),
                     ocr("缇宝", x=float("nan"))):
            self.assertEqual(self.scan([item]).state, logic.ShopState.UNKNOWN)

    def test_name_on_slot_boundary_is_not_guessed(self):
        boundary_x = ((0.25 + 0.4) / 2 - 0.19) * self.width
        self.assertEqual(self.scan([ocr("缇宝", x=boundary_x - 20)]).state,
                         logic.ShopState.UNKNOWN)

    def test_changed_crop_origin_is_used(self):
        result = self.scan([ocr("缇宝", x=230)], crop_from_x=0.30)
        self.assertEqual(result.state, logic.ShopState.READY)
        self.assertEqual(result.cards[0].slot_index, 2)

    def test_invalid_window_width_is_unknown(self):
        for width in (0, -1, True, float("nan")):
            result = logic.scan_store_cards([self.shop_ocr("缇宝", 0)], self.lookup, self.store, width)
            self.assertEqual(result.state, logic.ShopState.UNKNOWN)

    def test_invalid_store_area_is_unknown(self):
        for area in ([], [(0.25, 0.18), (0.25, 0.18)], [(1.5, 0.18)], [None]):
            result = logic.scan_store_cards([self.shop_ocr("缇宝", 0)], self.lookup, area, self.width)
            self.assertEqual(result.state, logic.ShopState.UNKNOWN)

    def test_optional_main_c_and_default_main_c_search_level(self):
        self.assertEqual(logic.validate_main_c_config({}, self.lookup), (None, 5))
        self.assertEqual(logic.validate_main_c_config({"main_c": None, "main_c_search_level": 7}, self.lookup),
                         (None, 7))

    def test_main_c_must_be_known_and_in_either_roster(self):
        for area in ("on_field", "off_field"):
            config = {"main_c": "银狼LV.999", area: {"银狼LV.999": 2}}
            self.assertEqual(logic.validate_main_c_config(config, self.lookup), ("银狼LV.999", 5))
        for config in ({"main_c": "缇宝"}, {"main_c": "未知", "on_field": {"未知": 2}},
                       {"main_c": ""}, {"main_c": True}, {"main_c": []}):
            with self.subTest(config=config), self.assertRaises(ValueError):
                logic.validate_main_c_config(config, self.lookup)

    def test_main_c_alias_membership_is_compared_canonically(self):
        config = {"main_c": "千冶•刃", "on_field": {"千冶·刃": 2}, "main_c_search_level": 6}
        self.assertEqual(logic.validate_main_c_config(config, self.lookup), ("千冶·刃", 6))

    def test_main_c_search_level_rejects_bool_noninteger_and_nonpositive(self):
        for value in (True, False, 0, -1, 5.0, "5", None, []):
            with self.subTest(value=value), self.assertRaises(ValueError):
                logic.validate_main_c_config({"main_c_search_level": value}, self.lookup)

    def test_main_c_search_level_nondefaults_follow_documented_schema(self):
        for level in (6, 7):
            config = {"main_c": "缇宝", "on_field": {"缇宝": 2},
                      "main_c_search_level": level, "min_level": 9, "mid_level": 9}
            with self.subTest(level=level):
                self.assertEqual(logic.validate_main_c_config(config, self.lookup), ("缇宝", level))

    def test_invalid_main_c_search_level_is_rejected_when_main_c_enabled(self):
        for value in (True, False, 0, -1, 5.0, 6.5, "6", None):
            config = {"main_c": "缇宝", "on_field": {"缇宝": 2},
                      "main_c_search_level": value}
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "main_c_search_level"):
                logic.validate_main_c_config(config, self.lookup)
    def test_main_c_rejects_malformed_roster(self):
        with self.assertRaises(ValueError):
            logic.validate_main_c_config({"main_c": "缇宝", "on_field": ["缇宝"]}, self.lookup)

    def test_configuration_is_not_mutated(self):
        config = {"main_c": "缇宝", "on_field": {"缇宝": 2}}
        before = {"main_c": "缇宝", "on_field": {"缇宝": 2}}
        logic.validate_main_c_config(config, self.lookup)
        self.assertEqual(config, before)

    def test_labeled_shop_level_formats(self):
        for text in ("Lv.5", "LV 5", "等级5", "商店等级：5", "ＬＶ．５"):
            with self.subTest(text=text):
                result = logic.parse_shop_level([ocr(text)])
                self.assertEqual(result.level, 5)
                self.assertEqual(result.evidence, "explicit_level_label")
                self.assertEqual(result.raw_text, text)

    def test_complete_shop_level_below_touching_buy_experience_button(self):
        for label in ("Lv.6", "等级6"):
            with self.subTest(label=label):
                # The button's bottom and the level label's top share y=20.
                parts = [ocr(label, x=10, y=20, w=45),
                         ocr("购买经验", x=0, y=0, w=80)]
                result = logic.parse_shop_level(parts)
                self.assertEqual(result.level, 6)
                self.assertEqual(result.evidence, "explicit_level_label")

    def test_complete_shop_level_next_to_buy_experience_button(self):
        for label in ("Lv.6", "等级6"):
            for button_on_left in (True, False):
                with self.subTest(label=label, button_on_left=button_on_left):
                    parts = ([ocr(label, x=85, w=45),
                              ocr("购买经验", x=0, w=80)] if button_on_left else
                             [ocr("购买经验", x=50, w=80),
                              ocr(label, x=0, w=45)])
                    self.assertEqual(logic.parse_shop_level(parts).level, 6)

    def test_complete_shop_level_keeps_exp_fraction_and_debug_digits_separate(self):
        parts = [ocr("DEBUG FPS60 999", x=300, y=0, w=160),
                 ocr("6/40", x=60, y=20, w=50),
                 ocr("Lv.6", x=10, y=20, w=45),
                 ocr("购买经验", x=0, y=0, w=80)]
        result = logic.parse_shop_level(parts)
        self.assertEqual(result.level, 6)
        self.assertEqual(result.evidence, "explicit_level_label")

    def test_complete_level_rejects_adjacent_non_shop_labels(self):
        for context in ("经验", "EXP", "角色", "队伍", "人口"):
            for label in ("Lv.6", "等级6"):
                for below in (False, True):
                    with self.subTest(context=context, label=label, below=below):
                        parts = [ocr(context, x=0, y=0, w=80),
                                 ocr(label, x=10 if below else 85,
                                     y=20 if below else 0, w=45)]
                        result = logic.parse_shop_level(parts)
                        self.assertIsNone(result.level)
                        self.assertEqual(result.reason, "non_shop_level_context")

    def test_buy_experience_exception_does_not_accept_other_exp_context(self):
        for context in ("累计经验", "角色购买经验", "队伍购买经验"):
            with self.subTest(context=context):
                parts = [ocr(context, x=0, w=80), ocr("Lv.6", x=85, w=45)]
                result = logic.parse_shop_level(parts)
                self.assertIsNone(result.level)
                self.assertEqual(result.reason, "non_shop_level_context")

    def test_buy_experience_button_does_not_validate_ambiguous_split_level(self):
        cases = (
            [ocr("购买经验", x=0, w=80), ocr("Lv.", x=85, w=25),
             ocr("6", x=113, w=10), ocr("/", x=125, w=8),
             ocr("40", x=135, w=20)],
            [ocr("购买经验", x=0, w=80), ocr("Lv.", x=85, w=25),
             ocr("6", x=113, w=10), ocr("6", x=125, w=10)],
            [ocr("购买经验", x=0, w=80), ocr("Lv.", x=85, w=25),
             ([[float("nan"), 0], [120, 20]], "6", 0.99)],
        )
        for parts in cases:
            with self.subTest(parts=parts):
                self.assertIsNone(logic.parse_shop_level(parts).level)

    def test_buy_experience_button_does_not_hide_conflicting_or_invalid_levels(self):
        for other_level, reason in (("Lv.7", "conflicting_level_labels"),
                                    ("Lv.999", "level_out_of_range")):
            with self.subTest(other_level=other_level):
                parts = [ocr("购买经验", x=0, w=80),
                         ocr("Lv.6", x=85, w=45),
                         ocr(other_level, x=300, w=60)]
                result = logic.parse_shop_level(parts)
                self.assertIsNone(result.level)
                self.assertEqual(result.reason, reason)

    def test_shop_level_fragments_use_spatial_order(self):
        parts = [ocr("5", x=30, w=12), ocr("Lv.", x=0, w=25)]
        self.assertEqual(logic.parse_shop_level(parts).level, 5)
        parts = [ocr("等", x=0, w=18), ocr("级", x=20, w=18), ocr("7", x=40, w=10)]
        self.assertEqual(logic.parse_shop_level(parts).level, 7)

    def test_shop_level_keeps_exp_and_population_separate(self):
        for text in ("5", "经验5/20", "EXP.5", "人口5/9", "5/9", "等级5/9",
                     "Lv.5/9", "角色等级5", "人口:Lv.5", "银狼LV.999"):
            with self.subTest(text=text):
                self.assertIsNone(logic.parse_shop_level([ocr(text)]).level)
        parts = [ocr("Lv.5", x=0), ocr("经验2/10", x=60, w=80)]
        self.assertEqual(logic.parse_shop_level(parts).level, 5)

    def test_shop_level_rejects_separately_labeled_population(self):
        parts = [ocr("人口", x=0), ocr("等级5", x=45, w=60)]
        result = logic.parse_shop_level(parts)
        self.assertIsNone(result.level)
        self.assertEqual(result.reason, "non_shop_level_context")

    def test_shop_level_distant_or_conflicting_fragments_are_unknown(self):
        self.assertIsNone(logic.parse_shop_level([ocr("Lv.", x=0), ocr("5", x=500)]).level)
        result = logic.parse_shop_level([ocr("Lv.5", x=0), ocr("Lv.6", x=100)])
        self.assertIsNone(result.level)
        self.assertEqual(result.reason, "conflicting_level_labels")

    def test_shop_level_rejects_fraction_split_after_label(self):
        parts = [ocr("Lv.", x=0, w=25), ocr("5", x=28, w=10),
                 ocr("/", x=40, w=8), ocr("9", x=50, w=10)]
        self.assertIsNone(logic.parse_shop_level(parts).level)

    def test_shop_level_rejects_out_of_range_or_decimal(self):
        for text in ("Lv.0", "Lv.21", "Lv.999", "Lv.5.0", "等级-1"):
            with self.subTest(text=text):
                self.assertIsNone(logic.parse_shop_level([ocr(text)]).level)

    def test_shop_level_empty_and_malformed_explain_unknown(self):
        for results, reason in ((None, "no_ocr_text"), ([], "no_ocr_text"),
                                ([("invalid",)], "malformed_ocr")):
            result = logic.parse_shop_level(results)
            self.assertIsNone(result.level)
            self.assertEqual(result.reason, reason)

    def test_shop_level_never_reuses_previous_value(self):
        self.assertEqual(logic.parse_shop_level([ocr("LV7")]).level, 7)
        self.assertIsNone(logic.parse_shop_level(None).level)

    def test_store_reads_current_dynamic_price_without_changing_character(self):
        character = self.characters["银狼LV.999"]
        character.cost = 5
        for price in (0, 3, 4, 5):
            results = [self.shop_ocr("银狼LV.999", 2),
                       self.shop_ocr(str(price), 2, offset=35, w=10)]
            with self.subTest(price=price):
                card = self.scan(results).cards[0]
                self.assertEqual(card.price, price)
                self.assertEqual(card.price_evidence, "same_slot_independent_digit")
                self.assertEqual(character.cost, 5)

    def test_store_consumes_name_999_before_finding_price(self):
        x = (0.55 - 0.19) * self.width - 50
        results = [ocr("银狼", x=x, w=28), ocr("LV.", x=x + 30, w=20),
                   ocr("999", x=x + 52, w=24), ocr("4", x=x + 90, w=10)]
        result = self.scan(results)
        self.assertEqual(result.state, logic.ShopState.READY)
        self.assertEqual(result.cards[0].character.name, "银狼LV.999")
        self.assertEqual(result.cards[0].price, 4)

    def test_store_price_on_adjacent_row_can_be_associated(self):
        result = self.scan([self.shop_ocr("缇宝", 2),
                            self.shop_ocr("3", 2, y=24, w=10)])
        self.assertEqual(result.cards[0].price, 3)

    def test_store_never_steals_neighbor_card_price(self):
        result = self.scan([self.shop_ocr("缇宝", 0),
                            self.shop_ocr("Saber", 3),
                            self.shop_ocr("4", 3, offset=35, w=10)])
        self.assertEqual([(c.slot_index, c.price) for c in result.cards], [(0, None), (3, 4)])

    def test_store_conflicting_price_digits_stay_unknown(self):
        results = [self.shop_ocr("缇宝", 2),
                   self.shop_ocr("3", 2, offset=30, w=10),
                   self.shop_ocr("4", 2, offset=45, w=10)]
        card = self.scan(results).cards[0]
        self.assertIsNone(card.price)
        self.assertEqual(card.price_evidence, "ambiguous_price_digits")

    def test_store_duplicate_price_box_does_not_make_two_prices(self):
        price = self.shop_ocr("3", 2, offset=35, w=10)
        card = self.scan([self.shop_ocr("缇宝", 2), price, price]).cards[0]
        self.assertEqual(card.price, 3)

    def test_store_number_overlapping_name_cannot_be_a_price(self):
        card = self.scan([self.shop_ocr("缇宝", 2), self.shop_ocr("3", 2, w=10)]).cards[0]
        self.assertIsNone(card.price)
        self.assertEqual(card.price_evidence, "price_overlaps_name")

    def test_store_distant_number_cannot_be_a_price(self):
        card = self.scan([self.shop_ocr("缇宝", 2),
                          self.shop_ocr("3", 2, y=300, w=10)]).cards[0]
        self.assertIsNone(card.price)
        self.assertEqual(card.price_evidence, "price_not_associated_with_name")

    def test_store_unconsumed_large_number_cannot_be_a_price(self):
        card = self.scan([self.shop_ocr("缇宝", 2),
                          self.shop_ocr("999", 2, offset=35, w=10)]).cards[0]
        self.assertIsNone(card.price)
        self.assertEqual(card.price_evidence, "price_out_of_range")

    def test_purchase_stale_stars_do_not_suppress_target(self):
        card = logic.ShopCard(2, self.characters["缇宝"], self.store[2], price=3)
        result = logic.evaluate_purchase(card, target_stars=2, confirmed_stars=2,
                                         stars_fresh=False, coins=3)
        self.assertTrue(result.can_buy)
        self.assertEqual(result.reason, "eligible")
        self.assertFalse(result.details["stars_trusted"])

    def test_purchase_fresh_stars_explain_target_reached(self):
        card = logic.ShopCard(2, self.characters["缇宝"], self.store[2], price=3)
        result = logic.evaluate_purchase(card, target_stars=2, confirmed_stars=2,
                                         stars_fresh=True, star_source="on_field",
                                         star_revision=12, coins=40, bench_copies=1)
        self.assertFalse(result.can_buy)
        self.assertEqual(result.reason, "target_reached")
        self.assertEqual(result.details["star_source"], "on_field")
        self.assertEqual(result.details["star_revision"], 12)
        self.assertEqual(result.details["bench_copies"], 1)

    def test_purchase_unknown_capacity_is_not_explicit_full(self):
        card = logic.ShopCard(0, self.characters["缇宝"], self.store[0], price=3)
        self.assertTrue(logic.evaluate_purchase(
            card, target_stars=2, coins=3, slot_available=None).can_buy)
        full = logic.evaluate_purchase(card, target_stars=2, coins=3, slot_available=False)
        self.assertFalse(full.can_buy)
        self.assertEqual(full.reason, "bench_full")

    def test_purchase_unknown_level_policy_requires_real_price(self):
        unknown = logic.ShopCard(0, self.characters["银狼LV.999"], self.store[0])
        denied = logic.evaluate_purchase(unknown, target_stars=2, coins=30, require_price=True)
        self.assertFalse(denied.can_buy)
        self.assertEqual(denied.reason, "unknown_price")
        priced = logic.ShopCard(0, unknown.character, self.store[0], price=3)
        self.assertTrue(logic.evaluate_purchase(
            priced, target_stars=2, coins=3, require_price=True).can_buy)

    def test_purchase_pending_and_protected_explain_skip(self):
        card = logic.ShopCard(0, self.characters["缇宝"], self.store[0], price=3)
        for kwargs, reason in (({"pending_purchase": True}, "purchase_pending"),
                               ({"protected": True}, "protected")):
            result = logic.evaluate_purchase(card, target_stars=2, coins=30, **kwargs)
            self.assertFalse(result.can_buy)
            self.assertEqual(result.reason, reason)

    def test_purchase_bench_copies_do_not_prove_star_target(self):
        card = logic.ShopCard(0, self.characters["缇宝"], self.store[0], price=3)
        self.assertTrue(logic.evaluate_purchase(
            card, target_stars=2, bench_copies=3, coins=30).can_buy)

    def test_purchase_cannot_guess_money_or_ignore_real_price(self):
        card = logic.ShopCard(0, self.characters["银狼LV.999"], self.store[0], price=4)
        for coins, reason in ((None, "unknown_coins"), (True, "unknown_coins"),
                              (-1, "unknown_coins"), (3, "insufficient_coins")):
            result = logic.evaluate_purchase(card, target_stars=2, coins=coins)
            self.assertFalse(result.can_buy)
            self.assertEqual(result.reason, reason)
        self.assertTrue(logic.evaluate_purchase(card, target_stars=2, coins=4).can_buy)

    def test_purchase_details_preserve_distinct_character_identity(self):
        for name in ("花火", "火花", "银狼", "银狼LV.999"):
            character = FakeCharacter(name)
            result = logic.evaluate_purchase(
                logic.ShopCard(4, character, self.store[4], price=3),
                target_stars=None, coins=20)
            self.assertEqual(result.reason, "not_in_strategy")
            self.assertEqual(result.details["character_name"], name)
            self.assertEqual(result.details["slot_index"], 4)

    def test_purchase_explicit_free_price_is_supported(self):
        card = logic.ShopCard(0, self.characters["缇宝"], self.store[0], price=0)
        self.assertTrue(logic.evaluate_purchase(
            card, target_stars=2, coins=0, require_price=True).can_buy)


if __name__ == "__main__":
    unittest.main()
