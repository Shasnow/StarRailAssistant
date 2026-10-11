"""Recovery regressions against source code; all I/O uses offline fakes."""

from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import test_currency_wars_flow as fixture


SOURCE_TASKS = Path(__file__).resolve().parents[1] / "tasks/currency_wars"


class RecoveryRuntimeRegressions(unittest.TestCase):
    character = fixture.CurrencyWarsFlowTests.character
    observe = fixture.CurrencyWarsFlowTests.observe
    empty_board = fixture.CurrencyWarsFlowTests.empty_board

    def setUp(self):
        redirect = patch.object(fixture, "TASKS", SOURCE_TASKS)
        redirect.start()
        self.addCleanup(redirect.stop)
        fixture.CurrencyWarsFlowTests.setUp(self)
        self.assertEqual(Path(self.module.__file__).resolve(),
                         (SOURCE_TASKS / "CurrencyWars.py").resolve())
        self.assertEqual(Path(self.logic.__file__).resolve(),
                         (SOURCE_TASKS / "logic.py").resolve())
        self.empty_board()
        self.task._bench_dirty = False
        self.task._dirty_slots.clear()
        self.task._vision.capture_sample = Mock()

    @staticmethod
    def rows(text, left=0, right=100):
        return [([[left, 0], [right, 0], [right, 30], [left, 30]], text, 0.99)]

    def recover_preparation(self):
        self.task._probe_runtime_page = Mock(return_value=("preparation", None))
        with patch.object(self.module.time, "monotonic", return_value=100):
            self.assertTrue(self.task._recover_runtime_flow(RuntimeError("OCR retry")))

    def test_rewards_are_collected_once_per_preparation(self):
        self.task._begin_preparation()
        revision = self.task._equipment_resource_revision
        self.task.harvest_crystals()
        self.task.harvest_crystals()
        self.assertEqual(len(self.operator.drags()), 5)
        self.assertEqual(self.task._equipment_resource_revision, revision + 1)
        self.task.detect_silver_wolf_lv999.assert_called_once()

    def test_reward_collection_commits_before_event_recognition_failure(self):
        self.task._begin_preparation()
        self.task.detect_silver_wolf_lv999.side_effect = RuntimeError("event OCR")
        with self.assertRaisesRegex(RuntimeError, "event OCR"):
            self.task.harvest_crystals()
        self.assertTrue(self.task._preparation_rewards_collected)
        self.task.harvest_crystals()
        self.assertEqual(len(self.operator.drags()), 5)
        self.task.detect_silver_wolf_lv999.assert_called_once()

    def test_same_preparation_recovery_preserves_rewards_heading_and_known_slots(self):
        self.task._preparation_deadline = 1000
        self.task._preparation_rewards_collected = True
        self.task._preparation_round = (2, 8)
        self.task._field_observed_at = 80
        blade = self.observe("off_field", 0, self.character("千冶·刃"), stars=2)
        self.task.refresh_character = Mock()
        self.task.refresh_backend_character = Mock()
        self.recover_preparation()
        self.assertTrue(self.task._preparation_rewards_collected)
        self.assertEqual(self.task._preparation_round, (2, 8))
        self.assertEqual(self.task._field_observed_at, 80)
        self.assertIs(self.task._observations["off_field"][0], blade)
        self.assertFalse(self.task._bench_dirty)
        self.task.refresh_character.assert_not_called()
        self.task.refresh_backend_character.assert_not_called()
        self.task.harvest_crystals()
        self.assertEqual(self.operator.drags(), [])

    def test_same_preparation_pending_purchase_marks_only_affected_field_slots(self):
        self.task._preparation_deadline = 1000
        self.task._preparation_rewards_collected = True
        self.observe("on_field", 0, self.character("银狼LV.999"), stars=1)
        self.observe("off_field", 0, self.character("千冶·刃"), stars=2)
        self.task._purchase_pending_names = {"银狼LV.999"}
        self.recover_preparation()
        self.assertTrue(self.task._preparation_rewards_collected)
        self.assertTrue(self.task._bench_dirty)
        self.assertEqual(self.task._dirty_slots, {("on_field", 0)})

    def test_confirmed_skip_departure_releases_reward_collection_state(self):
        self.task._preparation_deadline = 1000
        self.task._preparation_rewards_collected = True
        self.task._preparation_departure_confirmed = True
        self.task._field_observed_at = 80
        self.recover_preparation()
        self.assertFalse(self.task._preparation_rewards_collected)
        self.assertTrue(self.task._bench_dirty)
        self.assertIsNone(self.task._field_observed_at)
        self.assertEqual(self.task._confirmed_battle_count, 0)
        self.task.harvest_crystals()
        self.assertEqual(len(self.operator.drags()), 5)

    def test_navigation_recovery_invalidates_cached_heading_before_next_shop(self):
        self.task._preparation_deadline = 1000
        self.task._preparation_rewards_collected = True
        self.task._preparation_round = (2, 8)
        self.task._round_read_attempts = 2
        box = fixture.FakeBox(600, 700, 120, 40, source="下一步")
        self.task._probe_runtime_page = Mock(side_effect=[
            ("advance", ("下一步", box)), ("advance", ("下一步", box)),
            ("preparation", None), ("preparation", None)])
        with patch.object(self.module.time, "monotonic", return_value=100):
            self.assertTrue(self.task._recover_runtime_flow(RuntimeError("transition")))
        self.assertFalse(self.task._preparation_rewards_collected)
        self.assertIsNone(self.task._preparation_round)
        self.assertEqual(self.task._round_read_attempts, 0)
        self.operator.ocr = Mock(return_value=self.rows("备战阶段 | 3-7"))
        self.assertEqual(self.task._read_preparation_round(), (3, 7))
        self.assertEqual(self.operator.ocr.call_count, 4)
        self.assertEqual(self.task._round_read_attempts, 1)
        self.assertEqual(self.task._preparation_round, (3, 7))
        self.assertEqual(self.task._read_preparation_round(), (3, 7))
        self.assertEqual(self.operator.ocr.call_count, 4)

    def test_round_heading_is_cached_only_within_one_preparation(self):
        self.task._begin_preparation()
        self.operator.ocr = Mock(return_value=self.rows("备战阶段 | 2-8"))
        self.assertEqual(self.task._read_preparation_round(), (2, 8))
        reads = self.operator.ocr.call_count
        self.assertEqual(self.task._read_preparation_round(), (2, 8))
        self.assertEqual(self.operator.ocr.call_count, reads)
        self.task._preparation_deadline = None
        self.task._begin_preparation()
        self.operator.ocr.return_value = self.rows("备战阶段 | 3-7")
        self.assertEqual(self.task._read_preparation_round(), (3, 7))
        self.assertGreater(self.operator.ocr.call_count, reads)

    def test_layout_recovery_keeps_collection_flag_and_does_not_rescan_frontline(self):
        self.task._preparation_deadline = 1000
        self.task._preparation_rewards_collected = True
        self.task._layout_valid = False
        self.task.refresh_character = Mock()
        self.task.refresh_backend_character = Mock(side_effect=lambda **kwargs:
            setattr(self.task, "_layout_valid", True))
        self.recover_preparation()
        self.assertTrue(self.task._preparation_rewards_collected)
        self.task.refresh_backend_character.assert_called_once_with(
            equip=False, recover_layout=True)
        self.task.refresh_character.assert_not_called()

    def test_exact_blade_ocr_alias_requires_canonical_whitelist(self):
        blade = self.character("千冶·刃")
        lookup = lambda name: blade if name == blade.name else None
        self.assertIs(self.logic.parse_character_name(self.rows("干冶·刃"), lookup), blade)
        self.assertIsNone(self.logic.parse_character_name(self.rows("干冶·刃"), lambda _: None))
        for noise in ("干冶·刃额外", "干治·刃", "干冶刃"):
            with self.subTest(noise=noise):
                self.assertIsNone(self.logic.parse_character_name(self.rows(noise), lookup))

    def test_blade_alias_keeps_name_tokens_and_same_slot_price_geometry(self):
        blade = self.character("千冶·刃")
        lookup = lambda name: blade if name == blade.name else None
        raw = self.rows("干冶", 14, 55) + self.rows("·刃", 58, 99)
        tokens, malformed = self.logic._tokens(raw)
        self.assertFalse(malformed)
        character, reason, name_tokens = self.logic._resolve_name_details(tokens, lookup)
        self.assertIs(character, blade)
        self.assertEqual(reason, "")
        self.assertEqual([token.text for token in name_tokens], ["干冶", "·刃"])
        self.assertEqual(name_tokens, tuple(tokens))
        price_tokens, _ = self.logic._tokens(self.rows("2", 110, 125))
        self.assertEqual(self.logic._parse_card_price(tokens + price_tokens, name_tokens),
                         (2, "same_slot_independent_digit"))

    def configure_fee_gate(self):
        name = "银狼LV.999"
        self.task.economy_config = self.module.EconomyConfig(
            5, (self.module.EconomyStage(0, 9, 20, None),))
        self.task.formation_config = self.module.FormationConfig(
            {}, {}, {}, (self.module.FormationStage("core", 0, (name,), ()),),
            upgrade_gate=self.module.UpgradeGate(7, fielded={name: 1}, prices={name: 4}),
            purchase_targets={name: 2})
        self.task.strategy_characters = {name: 2}
        self.observe("on_field", 0, self.character(name), stars=1)
        self.observe("in_hand", 0, self.character(name), stars=1)
        self.task._observed_prices = {name: 3}
        return name

    def test_fielded_core_bench_material_continues_rolling_for_fee_upgrade(self):
        name = self.configure_fee_gate()
        allowed, actionable, prepare, reason = self.task._economy_upgrade_gate(7, {name: 2})
        self.assertEqual((allowed, actionable, prepare), (False, True, False))
        self.assertEqual(reason, "core_price:银狼LV.999:4")
        decision = self.module.next_economy_action(
            level=7, coins=44, target_level=9, reserve_gold=20, purchase_reserve_gold=5,
            xp_cost=4, roll_cost=2, upgrade_allowed=allowed,
            has_purchase_targets=True, gate_has_purchase_targets=actionable,
            space_safe=True, needs_prepare=prepare)
        self.assertEqual((decision.action, decision.reason), ("roll", "upgrade_gate_procurement"))

    def test_fee_gate_allows_xp_after_confirmed_four_cost_core(self):
        name = self.configure_fee_gate()
        self.task._observed_prices[name] = 4
        self.assertEqual(self.task._economy_upgrade_gate(7, {name: 2})[:3],
                         (True, False, False))

    def test_unknown_core_fee_does_not_masquerade_as_purchase_gap(self):
        name = self.configure_fee_gate()
        self.task._observed_prices.clear()
        self.assertEqual(self.task._economy_upgrade_gate(7, {name: 2}),
                         (None, None, False, "upgrade_gate_price_unknown"))


if __name__ == "__main__":
    unittest.main()
