"""Offline purchase-ledger checks without application or game dependencies."""

from enum import Enum
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "_currency_wars_shopping_batch", ROOT / "tasks/currency_wars/shopping_batch.py")
batch_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = batch_module
spec.loader.exec_module(batch_module)
ShoppingBatch = batch_module.ShoppingBatch


class State(str, Enum):
    KNOWN = "known"
    EMPTY = "empty"
    UNKNOWN = "unknown"


def slot(name=None, stars=None, state=None):
    return SimpleNamespace(
        state=state or (State.KNOWN if name else State.EMPTY),
        character=SimpleNamespace(name=name, stars=3) if name else None,
        stars=stars,
    )


def board(on=(), off=(), hand=(), empty_spaces=8):
    return {"on_field": list(on), "off_field": list(off),
            "in_hand": list(hand) + [slot() for _ in range(empty_spaces)]}


class ShoppingBatchTests(unittest.TestCase):
    def test_existing_one_star_plus_two_confirmed_purchases_stops_before_fourth_copy(self):
        batch = ShoppingBatch.from_observations(board(off=[slot("花火", 1)]))
        self.assertEqual(batch.missing_goals({"花火": 2}), {"花火": 2})
        for _ in range(2):
            self.assertTrue(batch.can_buy("花火", 2))
            batch.record_purchase("花火")
        self.assertFalse(batch.can_buy("花火", 2))
        self.assertEqual(batch.missing_goals({"花火": 2}), {})
        self.assertEqual(batch.pending_names, {"花火"})
        self.assertEqual(batch.pending_count, 2)

    def test_counts_all_areas_and_three_star_target_needs_nine_one_star_copies(self):
        batch = ShoppingBatch.from_observations(board(
            on=[slot("符玄", 2)], off=[slot("符玄", 2)], hand=[slot("符玄", 1)]))
        self.assertFalse(batch.can_buy("符玄", 2))
        batch.record_purchase("符玄")
        self.assertTrue(batch.can_buy("符玄", 3))
        batch.record_purchase("符玄")
        self.assertFalse(batch.can_buy("符玄", 3))
        self.assertEqual(batch.missing_goals({"符玄": 3}), {})

    def test_completed_three_star_unit_already_satisfies_target(self):
        batch = ShoppingBatch.from_observations(board(hand=[slot("火花", 3)]))
        self.assertFalse(batch.can_buy("火花", 3))
        self.assertEqual(batch.missing_goals({"火花": 3, "花火": 2}), {"花火": 2})

    def test_predicted_merge_never_creates_safe_space(self):
        batch = ShoppingBatch.from_observations(board(
            off=[slot("花火", 1)], hand=[slot("花火", 1)], empty_spaces=1))
        batch.record_purchase("花火")
        self.assertFalse(batch.space_safe)
        self.assertFalse(batch.can_buy("符玄", 2))
        self.assertEqual(batch.missing_goals({"符玄": 2}), {"符玄": 2})
        with self.assertRaises(ValueError):
            batch.record_purchase("符玄")
        self.assertEqual(batch.pending_count, 1)
        self.assertEqual(batch.pending_names, {"花火"})

    def test_empty_field_slots_do_not_count_as_bench_space(self):
        batch = ShoppingBatch.from_observations(board(on=[slot()] * 4, off=[slot()] * 5, empty_spaces=0))
        self.assertFalse(batch.space_safe)
        self.assertFalse(batch.can_buy("花火", 1))
        self.assertEqual(batch.missing_goals({"花火": 1}), {"花火": 1})

    def test_repeated_planning_does_not_record_unconfirmed_purchases(self):
        batch = ShoppingBatch.from_observations(board(empty_spaces=1))
        for _ in range(4):
            self.assertTrue(batch.can_buy("火花", 1))
            self.assertEqual(batch.missing_goals({"火花": 1}), {"火花": 1})
        self.assertEqual(batch.pending_count, 0)
        self.assertEqual(batch.pending_names, set())
        self.assertTrue(batch.space_safe)

    def test_independent_targets_and_pending_names(self):
        batch = ShoppingBatch.from_observations(board(off=[slot("花火", 1)]))
        batch.record_purchase("符玄")
        batch.record_purchase("花火")
        self.assertEqual(batch.missing_goals({"符玄": 1, "花火": 2, "火花": 3}),
                         {"花火": 2, "火花": 3})
        self.assertEqual(batch.pending_names, {"符玄", "花火"})
        self.assertEqual(batch.pending_count, 2)
        batch.pending_names.clear()
        self.assertEqual(batch.pending_names, {"符玄", "花火"})

    def test_unknown_slot_anywhere_rejects_batch(self):
        for area in ("on_field", "off_field", "in_hand"):
            with self.subTest(area=area):
                observations = board()
                observations[area].append(slot("花火", 1, State.UNKNOWN))
                self.assertIsNone(ShoppingBatch.from_observations(observations))

    def test_unknown_or_invalid_stars_and_identity_reject_batch(self):
        for stars in (None, 0, 4, -1, True, 1.0, "2"):
            with self.subTest(stars=stars):
                self.assertIsNone(ShoppingBatch.from_observations(board(on=[slot("花火", stars)])))
        for name in (None, "", " ", 42):
            with self.subTest(name=name):
                self.assertIsNone(ShoppingBatch.from_observations(board(on=[slot(name, 1, State.KNOWN)])))

    def test_missing_area_or_malformed_snapshot_rejects_batch(self):
        for observations in (None, {}, {"on_field": [], "off_field": []},
                             dict(board(), in_hand=None), dict(board(), off_field="empty"),
                             board(on=[SimpleNamespace(state="unexpected")])):
            with self.subTest(observations=observations):
                self.assertIsNone(ShoppingBatch.from_observations(observations))

    def test_string_states_supported_and_snapshot_and_shared_character_are_untouched(self):
        observed = slot("花火", 1, "KNOWN")
        observations = board(off=[observed], empty_spaces=2)
        batch = ShoppingBatch.from_observations(observations)
        batch.record_purchase("花火")
        self.assertEqual(observed.stars, 1)
        self.assertEqual(observed.character.stars, 3)
        self.assertEqual(len(observations["in_hand"]), 2)
        observed.stars = 3
        self.assertTrue(batch.can_buy("花火", 2))

    def test_invalid_goals_or_purchase_names_never_change_ledger(self):
        batch = ShoppingBatch.from_observations(board(empty_spaces=1))
        for goal in (None, 0, 4, True, 2.0, "2"):
            with self.subTest(goal=goal):
                self.assertFalse(batch.can_buy("花火", goal))
                with self.assertRaises(ValueError):
                    batch.missing_goals({"花火": goal})
        for name in (None, "", " ", 42):
            with self.subTest(name=name):
                self.assertFalse(batch.can_buy(name, 2))
                with self.assertRaises(ValueError):
                    batch.record_purchase(name)
        self.assertEqual(batch.pending_count, 0)
        self.assertTrue(batch.space_safe)


if __name__ == "__main__":
    unittest.main()
