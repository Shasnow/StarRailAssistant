"""Equipment scope decisions without a live game or application imports."""

import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("_currency_wars_equipment_policy", ROOT / "tasks/currency_wars/equipment_policy.py")
policy = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = policy
spec.loader.exec_module(policy)


class EquipmentPolicyTests(unittest.TestCase):
    def setUp(self):
        self.raw = {"priority_characters": ["银狼LV.999"], "others_from_round": "3-4", "interval_battles": 2}
        self.config = policy.parse_equipment_config(self.raw)

    def test_before_threshold_and_unknown_round_only_allow_deployed_priority(self):
        for current in (None, "", "2-9", "3-3", (3, 3), "3/4", "03-4", "3-10", True, (True, 4)):
            with self.subTest(current=current):
                self.assertEqual(policy.allowed_order(self.config, ["缇宝", "银狼LV.999", "符玄"], current),
                                 ("银狼LV.999",))

    def test_threshold_is_inclusive_and_priority_precedes_other_eligible_units(self):
        for current in ("3-4", (3, 4), "3-7", (4, 1)):
            with self.subTest(current=current):
                self.assertEqual(policy.allowed_order(self.config, ["符玄", "银狼LV.999", "缇宝"], current),
                                 ("银狼LV.999", "符玄", "缇宝"))

    def test_missing_or_benched_priority_is_never_invented(self):
        self.assertEqual(policy.allowed_order(self.config, ["符玄"], "3-3"), ())
        self.assertEqual(policy.allowed_order(self.config, ["符玄"], "3-4"), ("符玄",))
        self.assertEqual(policy.allowed_order(self.config, [], "3-7"), ())

    def test_multiple_priorities_follow_configuration_order(self):
        self.raw["priority_characters"] = ["银狼LV.999", "火花"]
        config = policy.parse_equipment_config(self.raw)
        self.assertEqual(policy.allowed_order(config, ["火花", "符玄", "银狼LV.999"], "3-4"),
                         ("银狼LV.999", "火花", "符玄"))

    def test_no_new_configuration_preserves_legacy_eligible_order(self):
        self.assertIsNone(policy.parse_equipment_config(None))
        self.assertEqual(policy.allowed_order(None, ["符玄", "银狼LV.999", "符玄"]),
                         ("符玄", "银狼LV.999", "符玄"))

    def test_lookup_normalizes_names_and_rejects_unusable_characters(self):
        char = SimpleNamespace(name="银狼LV.999", is_locked=False, is_npc=False)
        self.raw["priority_characters"] = ["别名"]
        self.assertEqual(policy.parse_equipment_config(self.raw, lambda _: char).priority_characters,
                         ("银狼LV.999",))
        for bad in (None, SimpleNamespace(name="未知", is_locked=True), SimpleNamespace(name="未知", is_npc=True)):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                policy.parse_equipment_config(self.raw, lambda _: bad)
        self.raw["priority_characters"] = ["别名", "银狼LV.999"]
        with self.assertRaises(ValueError):
            policy.parse_equipment_config(self.raw, lambda _: char)

    def test_invalid_configuration_fails_before_changing_runtime_policy(self):
        cases = [False, [], {}, dict(self.raw, unknown=True),
                 dict(self.raw, priority_characters=[]), dict(self.raw, priority_characters="银狼LV.999"),
                 dict(self.raw, priority_characters=["银狼LV.999", "银狼LV.999"]),
                 dict(self.raw, priority_characters=[None]), dict(self.raw, others_from_round="3/4"),
                 dict(self.raw, others_from_round="3-10"), dict(self.raw, others_from_round=[3, 4]),
                 dict(self.raw, interval_battles=True), dict(self.raw, interval_battles=0)]
        for raw in cases:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                policy.parse_equipment_config(raw)

    def test_shipped_strategy_has_one_equipment_configuration(self):
        data = json.loads((ROOT / "tasks/currency_wars/strategies/silver_wolf_lv999_aha_time_stop.json")
                          .read_text(encoding="utf-8-sig"))
        config = policy.parse_equipment_config(data["equipment"])
        self.assertEqual(config.priority_characters, ("银狼LV.999", "爻光", "火花", "符玄"))
        self.assertEqual((config.others_from_round, config.interval_battles), ((3, 4), 2))
        self.assertNotIn("equipment_interval_battles", data)
        self.assertNotIn("all_in_round", data["economy"])


if __name__ == "__main__":
    unittest.main()
