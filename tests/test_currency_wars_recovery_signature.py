"""Semantic recovery checks without importing the game or GUI runtime."""
from __future__ import annotations

from dataclasses import asdict
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest


SPEC = importlib.util.spec_from_file_location(
    "_currency_wars_recovery_signature",
    Path(__file__).resolve().parents[1] / "tasks/currency_wars/preparation.py")
preparation = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = preparation
SPEC.loader.exec_module(preparation)


class CurrencyWarsRecoverySignatureTests(unittest.TestCase):
    def setUp(self):
        self.front = self.slot(0, "known", "绯英", stars=1)
        self.unknown = self.slot(1, "unknown", evidence="uncalibrated_slot")
        self.bench = self.slot(0, "known", "藿藿", stars=1)
        self.observations = {"on_field": [self.front, self.unknown],
                             "off_field": [], "in_hand": [self.bench]}

    @staticmethod
    def slot(index, state, name=None, *, stars=None, evidence="name_match"):
        character = None if name is None else SimpleNamespace(
            name=name, position=3, positioning=3, is_locked=False, is_npc=False)
        return SimpleNamespace(slot_index=index, state=state, character=character,
                               stars=stars, occupied=True if name else None,
                               evidence=evidence, revision=1, stale=False)

    def signature(self, **changes):
        arguments = dict(layout_revision=3, layout_valid=True, capacity=5,
                         population=1)
        arguments.update(changes)
        return preparation.recovery_signature(self.observations, **arguments)

    def test_repeat_ocr_revision_and_unknown_error_text_are_not_progress(self):
        previous = self.signature()
        self.front.revision += 10
        self.front.evidence = "fresh_rescan"
        self.unknown.revision += 10
        self.unknown.evidence = "unrecognized_name"
        self.unknown.timestamp = 1234
        self.assertEqual(previous, self.signature())

    def test_reliable_known_evidence_becoming_stale_changes_signature(self):
        previous = self.signature()
        self.front.evidence = "stale"
        self.assertNotEqual(previous, self.signature())
        untrusted = self.signature()
        self.front.evidence = "pending_drag"
        self.assertEqual(untrusted, self.signature())
        self.front.evidence = "fresh_after_move"
        self.assertEqual(previous, self.signature())

    def test_explicit_stale_flag_changes_reliability(self):
        previous = self.signature()
        self.front.stale = True
        self.assertNotEqual(previous, self.signature())

    def test_known_star_upgrade_and_unknown_star_resolution_are_progress(self):
        signatures = []
        for stars in (None, 1, 2):
            self.front.stars = stars
            signatures.append(self.signature())
        self.assertEqual(len(set(signatures)), 3)

    def test_swap_changes_signature_even_when_all_slot_counts_are_unchanged(self):
        previous = self.signature()
        self.front.character, self.bench.character = self.bench.character, self.front.character
        self.assertNotEqual(previous, self.signature())

    def test_unknown_target_becoming_confirmed_empty_is_progress(self):
        previous = self.signature()
        self.unknown.state = "empty"
        self.unknown.occupied = False
        self.unknown.evidence = "empty_detector"
        self.assertNotEqual(previous, self.signature())

    def test_mutable_character_flags_are_copied_into_the_snapshot(self):
        previous = self.signature()
        self.bench.character.is_locked = True
        self.assertNotEqual(previous, self.signature())
        self.bench.character.is_locked = False
        self.assertEqual(previous, self.signature())
        self.bench.character.is_npc = True
        self.assertNotEqual(previous, self.signature())

    def test_population_capacity_and_layout_changes_are_progress(self):
        previous = self.signature()
        for changes in (dict(population=2), dict(capacity=6),
                        dict(layout_valid=False), dict(layout_revision=4)):
            with self.subTest(changes=changes):
                self.assertNotEqual(previous, self.signature(**changes))

    def test_character_position_change_updates_allowed_placement_signature(self):
        previous = self.signature()
        self.bench.character.position = 1
        self.assertNotEqual(previous, self.signature())
        self.bench.character.position = 3
        self.assertEqual(previous, self.signature())

    def test_default_positioning_change_matters_even_if_strategy_position_is_same(self):
        previous = self.signature()
        self.bench.character.positioning = 2
        self.assertNotEqual(previous, self.signature())
        self.assertEqual(self.bench.character.position, 3)

    def test_dirty_and_excluded_sets_are_order_independent_but_changes_matter(self):
        dirty = (("on_field", 0), ("in_hand", 0))
        excluded = (("in_hand", 0, "on_field", 0), ("in_hand", 0, "on_field", 1))
        before = self.signature(dirty_slots=dirty, excluded_moves=excluded)
        self.assertEqual(before, self.signature(dirty_slots=reversed(dirty),
                                                 excluded_moves=reversed(excluded)))
        self.assertNotEqual(before, self.signature(dirty_slots=dirty[:1], excluded_moves=excluded))
        self.assertNotEqual(before, self.signature(dirty_slots=dirty, excluded_moves=excluded[:1]))
        self.assertNotEqual(self.signature(), self.signature(bench_dirty=True))

    def test_pending_move_is_frozen_and_ignores_before_observation_revision(self):
        pending = dict(source=("in_hand", 0), target=("on_field", 1),
                       source_before=self.bench, target_before=self.unknown,
                       layout=3, positions=((0.2, 0.8), (0.4, 0.4)))
        before = self.signature(pending_move=pending, placement_pending=True)
        self.assertNotEqual(before, self.signature())
        self.bench.revision += 1
        self.unknown.evidence = "unrecognized_name"
        self.assertEqual(before, self.signature(pending_move=pending, placement_pending=True))
        pending["positions"] = ((0.2, 0.8), (0.45, 0.4))
        self.assertNotEqual(before, self.signature(pending_move=pending, placement_pending=True))
        self.assertNotEqual(before, self.signature(pending_move=None, placement_pending=True))

    def test_result_can_preserve_root_cause_without_breaking_positional_arguments(self):
        previous = preparation.PreparationResult(
            preparation.Readiness.BLOCKED, "role_not_ready", 0, 0, 1, ("survival:unknown",))
        self.assertEqual(previous.blocked_reason, "")
        result = preparation.PreparationResult(
            preparation.Readiness.BLOCKED, "preparation_time_budget",
            gaps=previous.gaps, blocked_reason=previous.reason)
        self.assertFalse(result)
        self.assertEqual(asdict(result)["blocked_reason"], "role_not_ready")
        self.assertEqual(result.gaps, ("survival:unknown",))


if __name__ == "__main__":
    unittest.main()
