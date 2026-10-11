"""Offline session checkpoint tests use temporary directories exclusively."""

from dataclasses import fields
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "_currency_wars_session_unit",
    Path(__file__).resolve().parents[1] / "tasks/currency_wars/session.py")
session = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = session
SPEC.loader.exec_module(session)

FP = hashlib.sha256(b"silver wolf strategy").hexdigest()
OTHER_FP = hashlib.sha256(b"changed strategy").hexdigest()


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = self.root / "checkpoints" / "current.json"
        self.store = session.SessionStore(self.path)

    def start(self):
        recovery = self.store.begin(FP)
        self.assertTrue(recovery.persisted, self.store.last_error)
        return recovery

    def read_data(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def write_data(self, data):
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def assert_safe_new_session(self, reason):
        recovery = session.SessionStore(self.path).begin(FP, resume=True)
        self.assertFalse(recovery.resumed)
        self.assertEqual(recovery.reason, reason)
        self.assertTrue(recovery.persisted)
        self.assertEqual(recovery.checkpoint.completed_cycles, 0)
        self.assertIsNone(recovery.checkpoint.confirmed_battle_count)
        self.assertEqual(recovery.checkpoint.confirmed_events, ())
        self.assertEqual(recovery.checkpoint.pending_actions, ())
        self.assertEqual(recovery.checkpoint.association, "uncertain")

    def test_construction_does_not_create_or_read_files(self):
        self.assertFalse(self.path.parent.exists())
        self.assertIsNone(self.store.checkpoint)
        self.assertIsNone(self.store.last_error)
        self.assertFalse(self.path.parent.exists())

    def test_v1_checkpoint_is_migrated_without_replaying_pending_actions(self):
        self.start()
        self.store.record(completed_cycles=18, phase="stopped", last_outcome="script_error",
                          pending_actions=["observe terminal page"])
        data = self.read_data()
        for name in session._V2_FIELDS | session._V3_FIELDS:
            del data[name]
        data["version"] = 1
        self.write_data(data)
        recovered = session.SessionStore(self.path).begin(FP, resume=True)
        self.assertTrue(recovered.resumed)
        self.assertEqual(recovered.checkpoint.version, session.CHECKPOINT_VERSION)
        self.assertEqual(recovered.checkpoint.completed_cycles, 18)
        self.assertIsNone(recovered.checkpoint.confirmed_battle_count)
        self.assertEqual(recovered.checkpoint.equipment_battles_since_check, 0)
        self.assertEqual(recovered.checkpoint.pending_actions, ("observe terminal page",))
        self.assertEqual(recovered.checkpoint.terminal_outcome, "unknown")

    def test_v2_migration_preserves_terminal_history_but_never_infers_battles_from_cycles(self):
        self.start()
        self.assertTrue(self.store.record(completed_cycles=18, terminal_outcome="won",
                                          terminal_evidence="final_header_labels_template"))
        data = self.read_data()
        for name in session._V3_FIELDS:
            del data[name]
        data["version"] = 2
        self.write_data(data)
        recovered = session.SessionStore(self.path).begin(FP, resume=True)
        self.assertTrue(recovered.resumed)
        self.assertEqual(recovered.checkpoint.version, 3)
        self.assertEqual(recovered.checkpoint.completed_cycles, 18)
        self.assertIsNone(recovered.checkpoint.confirmed_battle_count)
        self.assertEqual(recovered.checkpoint.active_economy_stage_index, 0)
        self.assertEqual(recovered.checkpoint.equipment_battles_since_check, 0)
        self.assertEqual(recovered.checkpoint.terminal_outcome, "won")
        self.assertEqual(recovered.checkpoint.terminal_evidence, "final_header_labels_template")
        self.assertEqual(self.read_data()["version"], 3)

    def test_legacy_files_cannot_smuggle_new_history_or_omit_old_fields(self):
        self.start()
        original = self.read_data()
        for version in (1, 2):
            data = {key: value for key, value in original.items()
                    if key not in session._V3_FIELDS
                    and (version != 1 or key not in session._V2_FIELDS)}
            data["version"] = version
            for change in ("extra", "missing"):
                with self.subTest(version=version, change=change):
                    malformed = dict(data)
                    if change == "extra":
                        malformed["confirmed_battle_count"] = 12
                    else:
                        del malformed["completed_cycles"]
                    self.write_data(malformed)
                    self.assert_safe_new_session("checkpoint_invalid")

    def test_new_game_resets_battle_history_stage_and_equipment_state(self):
        self.start()
        first = str(uuid.uuid4())
        self.assertEqual(self.store.checkpoint.confirmed_battle_count, 0)
        self.assertTrue(self.store.record(pending_battle_id=first))
        self.assertTrue(self.store.confirm_battle(first))
        self.assertTrue(self.store.record(active_economy_stage_index=2,
                                          equipment_batch_state="in_progress"))
        self.assertTrue(self.store.complete_equipment_check())
        fresh = self.store.begin(FP)
        self.assertEqual(fresh.checkpoint.confirmed_battle_count, 0)
        self.assertEqual(fresh.checkpoint.active_economy_stage_index, 0)
        self.assertEqual(fresh.checkpoint.equipment_battles_since_check, 0)
        self.assertIsNone(fresh.checkpoint.pending_battle_id)
        self.assertIsNone(fresh.checkpoint.last_counted_battle_id)
        self.assertIsNone(fresh.checkpoint.last_equipment_check_battle_id)
        self.assertEqual(fresh.checkpoint.equipment_batch_state, "idle")

    def test_battle_confirmation_is_atomic_and_idempotent_across_resume(self):
        self.start()
        battle_id = str(uuid.uuid4())
        self.assertTrue(self.store.record(pending_battle_id=battle_id, completed_cycles=19,
                                          active_economy_stage_index=2))
        before = self.path.read_bytes()
        self.assertFalse(self.store.confirm_battle(str(uuid.uuid4())))
        self.assertEqual(self.path.read_bytes(), before)
        restored = session.SessionStore(self.path)
        restored.begin(FP, resume=True)
        self.assertEqual(restored.checkpoint.pending_battle_id, battle_id)
        self.assertTrue(restored.confirm_battle(battle_id))
        self.assertTrue(restored.confirm_battle(battle_id))
        self.assertEqual(restored.checkpoint.completed_cycles, 19)
        self.assertEqual(restored.checkpoint.confirmed_battle_count, 1)
        self.assertEqual(restored.checkpoint.equipment_battles_since_check, 1)
        self.assertIsNone(restored.checkpoint.pending_battle_id)
        self.assertEqual(restored.checkpoint.last_counted_battle_id, battle_id)
        resumed = session.SessionStore(self.path)
        resumed.begin(FP, resume=True)
        self.assertTrue(resumed.confirm_battle(battle_id))
        self.assertEqual(resumed.checkpoint.confirmed_battle_count, 1)
        self.assertEqual(resumed.checkpoint.equipment_battles_since_check, 1)
        self.assertEqual(resumed.checkpoint.active_economy_stage_index, 2)

    def test_old_battle_reconfirmation_does_not_clear_the_next_pending_battle(self):
        self.start()
        first, second = str(uuid.uuid4()), str(uuid.uuid4())
        self.assertTrue(self.store.record(pending_battle_id=first))
        self.assertTrue(self.store.confirm_battle(first))
        self.assertTrue(self.store.record(pending_battle_id=second))
        self.assertTrue(self.store.confirm_battle(first))
        self.assertEqual(self.store.checkpoint.pending_battle_id, second)
        self.assertTrue(self.store.confirm_battle(second))
        self.assertEqual(self.store.checkpoint.confirmed_battle_count, 2)
        self.assertFalse(self.store.confirm_battle(first))

    def test_unknown_history_keeps_local_equipment_count_separate(self):
        self.start()
        self.assertTrue(self.store.record(confirmed_battle_count=8, active_economy_stage_index=2))
        changed = session.SessionStore(self.path)
        recovery = changed.begin(OTHER_FP, resume=True)
        self.assertIsNone(recovery.checkpoint.confirmed_battle_count)
        self.assertEqual(recovery.checkpoint.active_economy_stage_index, 0)
        for _ in range(2):
            battle_id = str(uuid.uuid4())
            self.assertTrue(changed.record(pending_battle_id=battle_id))
            self.assertTrue(changed.confirm_battle(battle_id))
        self.assertIsNone(changed.checkpoint.confirmed_battle_count)
        self.assertEqual(changed.checkpoint.equipment_battles_since_check, 2)
        self.assertFalse(changed.record(confirmed_battle_count=2))
        self.assertTrue(changed.record(active_economy_stage_index=1))
        self.assertTrue(changed.record(equipment_batch_state="in_progress"))
        self.assertTrue(changed.complete_equipment_check())
        restored = session.SessionStore(self.path).begin(OTHER_FP, resume=True)
        self.assertIsNone(restored.checkpoint.confirmed_battle_count)
        self.assertEqual(restored.checkpoint.equipment_battles_since_check, 0)
        self.assertEqual(restored.checkpoint.active_economy_stage_index, 1)

    def test_equipment_interruption_retains_due_interval_until_confirmed_batch_completion(self):
        self.start()
        for _ in range(2):
            battle_id = str(uuid.uuid4())
            self.assertTrue(self.store.record(pending_battle_id=battle_id))
            self.assertTrue(self.store.confirm_battle(battle_id))
        self.assertFalse(self.store.complete_equipment_check())
        self.assertTrue(self.store.record(equipment_batch_state="in_progress"))
        self.assertTrue(self.store.record(equipment_batch_state="interrupted"))
        self.assertFalse(self.store.complete_equipment_check())
        resumed = session.SessionStore(self.path)
        resumed.begin(FP, resume=True)
        self.assertEqual(resumed.checkpoint.equipment_battles_since_check, 2)
        self.assertEqual(resumed.checkpoint.equipment_batch_state, "interrupted")
        self.assertTrue(resumed.record(equipment_batch_state="in_progress"))
        self.assertTrue(resumed.complete_equipment_check())
        self.assertTrue(resumed.complete_equipment_check())
        self.assertEqual(resumed.checkpoint.equipment_battles_since_check, 0)
        self.assertEqual(resumed.checkpoint.confirmed_battle_count, 2)
        self.assertEqual(resumed.checkpoint.last_equipment_check_battle_id, battle_id)
        third = str(uuid.uuid4())
        self.assertTrue(resumed.record(pending_battle_id=third))
        self.assertTrue(resumed.confirm_battle(third))
        self.assertEqual(resumed.checkpoint.equipment_batch_state, "idle")
        self.assertFalse(resumed.complete_equipment_check())
        self.assertEqual(resumed.checkpoint.equipment_battles_since_check, 1)

    def test_nullable_fields_can_be_explicitly_cleared_without_omission_resetting_them(self):
        self.start()
        battle_id = str(uuid.uuid4())
        self.assertTrue(self.store.record(pending_battle_id=battle_id))
        self.assertTrue(self.store.record(phase="stopped"))
        self.assertEqual(self.store.checkpoint.pending_battle_id, battle_id)
        self.assertTrue(self.store.record(pending_battle_id=None))
        self.assertIsNone(self.store.checkpoint.pending_battle_id)
        self.assertFalse(self.store.confirm_battle(battle_id))

    def test_crashed_in_progress_batch_recovers_as_interrupted_without_consuming_interval(self):
        self.start()
        self.assertTrue(self.store.record(equipment_battles_since_check=2,
                                          equipment_batch_state="in_progress"))
        recovered = session.SessionStore(self.path).begin(FP, resume=True)
        self.assertEqual(recovered.checkpoint.equipment_batch_state, "interrupted")
        self.assertEqual(recovered.checkpoint.equipment_battles_since_check, 2)
        self.assertIsNone(recovered.checkpoint.last_equipment_check_battle_id)

    def test_new_history_fields_reject_regression_and_malformed_values_without_mutation(self):
        self.start()
        self.assertTrue(self.store.record(confirmed_battle_count=5, active_economy_stage_index=2,
                                          equipment_battles_since_check=2))
        original = self.store.checkpoint
        before = self.path.read_bytes()
        cases = (
            {"confirmed_battle_count": 4}, {"confirmed_battle_count": None},
            {"confirmed_battle_count": True}, {"confirmed_battle_count": session.MAX_CYCLES + 1},
            {"active_economy_stage_index": 1}, {"active_economy_stage_index": 3.0},
            {"equipment_battles_since_check": 1}, {"equipment_battles_since_check": -1},
            {"equipment_battles_since_check": True}, {"equipment_batch_state": "successful_synthesis"},
            {"pending_battle_id": "not-a-uuid"}, {"last_counted_battle_id": ""},
            {"last_equipment_check_battle_id": 1},
        )
        for change in cases:
            with self.subTest(change=change):
                self.assertFalse(self.store.record(**change))
                self.assertEqual(self.store.checkpoint, original)
                self.assertEqual(self.path.read_bytes(), before)

    def test_failed_battle_commit_retries_without_double_increment(self):
        self.start()
        battle_id = str(uuid.uuid4())
        self.assertTrue(self.store.record(pending_battle_id=battle_id))
        before = self.path.read_bytes()
        with patch.object(session.os, "replace", side_effect=OSError("replace blocked")):
            self.assertFalse(self.store.confirm_battle(battle_id))
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.store.checkpoint.confirmed_battle_count, 1)
        self.assertTrue(self.store.confirm_battle(battle_id))
        self.assertEqual(self.read_data()["confirmed_battle_count"], 1)
        self.assertEqual(self.read_data()["equipment_battles_since_check"], 1)

    def test_finalization_discards_pending_battle_and_disables_counting(self):
        self.start()
        battle_id = str(uuid.uuid4())
        self.assertTrue(self.store.record(pending_battle_id=battle_id))
        self.assertTrue(self.store.finalize("game_lost"))
        self.assertIsNone(self.store.checkpoint.pending_battle_id)
        self.assertFalse(self.store.confirm_battle(battle_id))
        self.assertFalse(self.store.complete_equipment_check())

    def test_win_and_pending_navigation_survive_stop_and_reload(self):
        self.start()
        self.store.record(terminal_outcome="won", terminal_evidence="final_header_labels_template",
                          terminal_navigation_step="final_summary_pending", pending_actions=["observe next page"])
        confirmed_at = self.store.checkpoint.terminal_confirmed_at
        self.assertNotEqual(confirmed_at, "none")
        self.store.record(phase="stopped", execution_status="error")
        restored = session.SessionStore(self.path)
        restored.begin(FP, resume=True)
        self.assertEqual((restored.checkpoint.terminal_outcome, restored.checkpoint.last_outcome,
                          restored.checkpoint.execution_status), ("won", "game_won", "error"))
        self.assertEqual(restored.checkpoint.terminal_confirmed_at, confirmed_at)
        self.assertFalse(restored.record(terminal_outcome="lost"))
        self.assertFalse(restored.record(terminal_outcome="unknown"))
        self.assertTrue(restored.finalize("returned_to_main_menu"))
        self.assertEqual(restored.checkpoint.last_outcome, "game_won")
        self.assertEqual(restored.checkpoint.execution_status, "completed")
        self.assertEqual(restored.checkpoint.pending_actions, ())
        self.assertFalse(restored.finalize("returned_to_main_menu"))

    def test_new_game_always_has_new_id_and_clears_history(self):
        first = self.start()
        self.assertTrue(self.store.record(completed_cycles=11, confirmed_event="main_c_first_fielded",
                                          pending_actions=["buy:符玄 (unconfirmed)"]))
        second = self.store.begin(FP)
        self.assertNotEqual(first.checkpoint.run_id, second.checkpoint.run_id)
        self.assertEqual(second.reason, "new_game")
        self.assertFalse(second.resumed)
        self.assertEqual(second.checkpoint.completed_cycles, 0)
        self.assertEqual(second.checkpoint.confirmed_events, ())
        self.assertEqual(second.checkpoint.pending_actions, ())

    def test_matching_strategy_resumes_only_hints_without_replaying_actions(self):
        first = self.start()
        pending = ("move:in_hand[7] -> off_field[1] (unconfirmed)",)
        self.assertTrue(self.store.record(completed_cycles=10, phase="battle",
                                          confirmed_event="expert_silver_wolf_confirmed",
                                          pending_actions=pending))
        # Recovery exposes immutable text summaries, no game operator/callback.
        fresh = session.SessionStore(self.path)
        recovered = fresh.begin(FP, resume=True)
        self.assertTrue(recovered.resumed)
        self.assertEqual(recovered.reason, "resumed")
        self.assertEqual(recovered.checkpoint.run_id, first.checkpoint.run_id)
        self.assertEqual(recovered.checkpoint.completed_cycles, 10)
        self.assertEqual(recovered.checkpoint.phase, "battle")
        self.assertEqual(recovered.checkpoint.pending_actions, pending)
        self.assertEqual(recovered.checkpoint.confirmed_events, ("expert_silver_wolf_confirmed",))
        self.assertTrue(fresh.record(pending_actions=[]))
        self.assertEqual(fresh.checkpoint.pending_actions, ())

    def test_user_stop_and_exception_preserve_resume_hints(self):
        for outcome in ("user_stopped", "script_error"):
            with self.subTest(outcome=outcome):
                first = self.start()
                self.assertTrue(self.store.record(completed_cycles=4, phase="result",
                                                  last_outcome=outcome))
                recovered = session.SessionStore(self.path).begin(FP, resume=True)
                self.assertTrue(recovered.resumed)
                self.assertEqual(recovered.checkpoint.run_id, first.checkpoint.run_id)
                self.assertEqual(recovered.checkpoint.completed_cycles, 4)
                self.assertEqual(recovered.checkpoint.phase, "result")
                self.assertEqual(recovered.checkpoint.last_outcome, outcome)
                self.assertFalse(recovered.checkpoint.finalized)

    def test_strategy_change_discards_plans_events_and_marks_uncertain_association(self):
        first = self.start()
        self.store.record(completed_cycles=5, confirmed_event="old_event",
                          pending_actions=["old_strategy_move"])
        changed = session.SessionStore(self.path).begin(OTHER_FP, resume=True)
        self.assertFalse(changed.resumed)
        self.assertEqual(changed.reason, "strategy_changed_association_uncertain")
        self.assertNotEqual(changed.checkpoint.run_id, first.checkpoint.run_id)
        self.assertEqual(changed.checkpoint.previous_run_id, first.checkpoint.run_id)
        self.assertEqual(changed.checkpoint.association, "uncertain")
        self.assertEqual(changed.checkpoint.completed_cycles, 0)
        self.assertEqual(changed.checkpoint.confirmed_events, ())
        self.assertEqual(changed.checkpoint.pending_actions, ())
        resumed = session.SessionStore(self.path).begin(OTHER_FP, resume=True)
        self.assertTrue(resumed.resumed)
        self.assertEqual(resumed.reason, "resumed_association_uncertain")
        self.assertEqual(resumed.checkpoint.association, "uncertain")

    def test_finalized_game_cannot_be_reused_by_next_resume(self):
        first = self.start()
        self.store.record(completed_cycles=16, pending_actions=["settlement_check"])
        self.assertTrue(self.store.finalize("game_lost"))
        data = self.read_data()
        self.assertTrue(data["finalized"])
        self.assertEqual(data["phase"], "finished")
        self.assertEqual(data["last_outcome"], "game_lost")
        self.assertEqual(data["pending_actions"], [])
        self.assertFalse(self.store.record(last_outcome="user_stopped"))
        fresh = session.SessionStore(self.path).begin(FP, resume=True)
        self.assertFalse(fresh.resumed)
        self.assertEqual(fresh.reason, "previous_game_finalized")
        self.assertNotEqual(fresh.checkpoint.run_id, first.checkpoint.run_id)
        self.assertEqual(fresh.checkpoint.completed_cycles, 0)
        self.assertEqual(fresh.checkpoint.association, "uncertain")
        self.assertIsNone(fresh.checkpoint.confirmed_battle_count)
        self.assertFalse(fresh.checkpoint.finalized)

    def test_resume_after_finalized_game_keeps_live_history_unknown_for_any_strategy(self):
        for fingerprint in (FP, OTHER_FP):
            with self.subTest(fingerprint=fingerprint):
                ended = self.start()
                self.assertTrue(self.store.record(
                    completed_cycles=16, confirmed_battle_count=12,
                    active_economy_stage_index=2, equipment_battles_since_check=2,
                    confirmed_event="main_c_first_fielded"))
                self.assertTrue(self.store.finalize("game_won"))
                resumed = session.SessionStore(self.path)
                recovery = resumed.begin(fingerprint, resume=True)
                checkpoint = recovery.checkpoint
                self.assertFalse(recovery.resumed)
                self.assertTrue(recovery.persisted)
                self.assertNotEqual(checkpoint.run_id, ended.checkpoint.run_id)
                self.assertEqual(checkpoint.strategy_fingerprint, fingerprint)
                self.assertEqual(checkpoint.association, "uncertain")
                self.assertIsNone(checkpoint.confirmed_battle_count)
                self.assertEqual(checkpoint.active_economy_stage_index, 0)
                self.assertEqual(checkpoint.equipment_battles_since_check, 0)
                self.assertEqual(checkpoint.equipment_batch_state, "idle")
                self.assertEqual(checkpoint.confirmed_events, ())
                self.assertEqual(checkpoint.pending_actions, ())
                self.assertIsNone(checkpoint.pending_battle_id)
                self.assertIsNone(checkpoint.last_counted_battle_id)
                self.assertIsNone(checkpoint.last_equipment_check_battle_id)
                self.assertEqual(checkpoint.terminal_outcome, "unknown")

                # Local progress drives equipment without inventing the total
                # history before this takeover, even after another restart.
                for _ in range(2):
                    battle_id = str(uuid.uuid4())
                    self.assertTrue(resumed.record(pending_battle_id=battle_id))
                    self.assertTrue(resumed.confirm_battle(battle_id))
                restored = session.SessionStore(self.path)
                after_restart = restored.begin(fingerprint, resume=True)
                self.assertTrue(after_restart.resumed)
                self.assertEqual(after_restart.reason, "resumed_association_uncertain")
                self.assertEqual(after_restart.checkpoint.run_id, checkpoint.run_id)
                self.assertIsNone(after_restart.checkpoint.confirmed_battle_count)
                self.assertEqual(after_restart.checkpoint.equipment_battles_since_check, 2)
                self.assertFalse(restored.record(confirmed_battle_count=2))

    def test_explicit_fresh_game_after_finalized_checkpoint_starts_at_battle_zero(self):
        self.start()
        self.assertTrue(self.store.record(confirmed_battle_count=12,
                                          active_economy_stage_index=2))
        self.assertTrue(self.store.finalize("game_won"))
        fresh = session.SessionStore(self.path).begin(FP, resume=False)
        self.assertEqual(fresh.reason, "new_game")
        self.assertEqual(fresh.checkpoint.association, "new")
        self.assertEqual(fresh.checkpoint.confirmed_battle_count, 0)
        self.assertEqual(fresh.checkpoint.active_economy_stage_index, 0)
        self.assertEqual(fresh.checkpoint.equipment_battles_since_check, 0)

    def test_missing_resume_checkpoint_is_uncertain_new_tracking(self):
        recovered = self.store.begin(FP, resume=True)
        self.assertEqual(recovered.reason, "checkpoint_missing")
        self.assertEqual(recovered.checkpoint.association, "uncertain")
        self.assertFalse(recovered.resumed)

    def test_schema_has_no_restorable_roster_slots_stars_or_operator_actions(self):
        self.start()
        data = self.read_data()
        self.assertEqual(set(data), {item.name for item in fields(session.SessionCheckpoint)})
        for forbidden in ("observations", "slots", "stars", "roster", "on_field", "off_field",
                          "in_hand", "is_placed", "execute", "operator"):
            self.assertNotIn(forbidden, data)
        self.assertEqual(data["version"], session.CHECKPOINT_VERSION)

    def test_unknown_observation_fields_fail_closed_instead_of_restoring(self):
        self.start()
        data = self.read_data()
        data["observations"] = {"on_field": [{"state": "KNOWN", "stars": 3}]}
        self.write_data(data)
        self.assert_safe_new_session("checkpoint_invalid")

    def test_corrupt_json_utf8_and_nonobject_fail_closed(self):
        self.start()
        for payload in (b"{broken", b"\xff\xfe", b"[]", b"null", b"123", b"[" * 2000):
            with self.subTest(payload=payload[:20]):
                self.path.write_bytes(payload)
                self.assert_safe_new_session("checkpoint_invalid")

    def test_duplicate_json_keys_fail_closed(self):
        self.start()
        original = self.path.read_text(encoding="utf-8")
        self.path.write_text('{"version": 1,' + original[1:], encoding="utf-8")
        self.assert_safe_new_session("checkpoint_invalid")

    def test_unsupported_or_boolean_version_is_not_loaded(self):
        self.start()
        original = self.read_data()
        for version in (0, session.CHECKPOINT_VERSION + 1, True, "1", None):
            with self.subTest(version=version):
                data = dict(original, version=version)
                self.write_data(data)
                self.assert_safe_new_session("checkpoint_version_unsupported")

    def test_malformed_fields_and_untrusted_nested_plans_fail_closed(self):
        self.start()
        original = self.read_data()
        cases = {"run_id": "wrong", "strategy_fingerprint": "not a digest",
                 "completed_cycles": True, "phase": "", "last_outcome": "\nerror",
                 "confirmed_events": {"old": True}, "pending_actions": [{"execute": "move"}],
                 "finalized": 1, "association": "verified", "created_at": "yesterday",
                 "updated_at": "2026-10-08", "previous_run_id": original["run_id"]}
        for key, value in cases.items():
            with self.subTest(key=key):
                self.write_data(dict(original, **{key: value}))
                self.assert_safe_new_session("checkpoint_invalid")

    def test_missing_fields_and_finalized_pending_actions_are_invalid(self):
        self.start()
        original = self.read_data()
        data = dict(original)
        del data["pending_actions"]
        self.write_data(data)
        self.assert_safe_new_session("checkpoint_invalid")
        self.write_data(dict(original, finalized=True, pending_actions=["unresolved_move"]))
        self.assert_safe_new_session("checkpoint_invalid")

    def test_oversized_file_is_bounded_before_json_parsing(self):
        self.start()
        self.path.write_bytes(b" " * 2048)
        small = session.SessionStore(self.path, max_bytes=1024)
        with patch.object(session.json, "loads", side_effect=AssertionError("must not parse")):
            recovered = small.begin(FP, resume=True)
        self.assertFalse(recovered.resumed)
        self.assertEqual(recovered.reason, "checkpoint_too_large")
        self.assertTrue(recovered.persisted)

    def test_events_are_idempotent_and_counts_are_cumulative(self):
        self.start()
        self.assertTrue(self.store.record(completed_cycles=10, confirmed_event="first_main_confirmed"))
        self.assertTrue(self.store.record(completed_cycles=11, confirmed_event="first_main_confirmed"))
        self.assertEqual(self.store.checkpoint.confirmed_events, ("first_main_confirmed",))
        before = self.path.read_bytes()
        for count in (10, -1, True, 12.0, session.MAX_CYCLES + 1):
            with self.subTest(count=count):
                self.assertFalse(self.store.record(completed_cycles=count))
                self.assertEqual(self.store.checkpoint.completed_cycles, 11)
                self.assertEqual(self.path.read_bytes(), before)

    def test_summary_and_collection_limits_reject_without_changing_existing_state(self):
        self.start()
        before = self.path.read_bytes()
        for pending in ("move", ["x" * 257], ["same", "same"],
                        [f"action_{i}" for i in range(session.MAX_PENDING_ACTIONS + 1)]):
            with self.subTest(pending_type=type(pending).__name__):
                self.assertFalse(self.store.record(pending_actions=pending))
                self.assertEqual(self.path.read_bytes(), before)
                self.assertEqual(self.store.checkpoint.pending_actions, ())
        for phase in ("", "x" * 65, "line\nbreak", 7):
            with self.subTest(phase=phase):
                self.assertFalse(self.store.record(phase=phase))
                self.assertEqual(self.path.read_bytes(), before)
        for index in range(session.MAX_EVENTS):
            self.assertTrue(self.store.record(confirmed_event=f"event_{index}"))
        self.assertTrue(self.store.record(confirmed_event="next_recent_event"))
        self.assertEqual(len(self.store.checkpoint.confirmed_events), session.MAX_EVENTS)
        self.assertNotIn("event_0", self.store.checkpoint.confirmed_events)
        self.assertEqual(self.store.checkpoint.confirmed_events[-1], "next_recent_event")
        saved = self.path.read_bytes()
        self.assertFalse(self.store.record(confirmed_event="x" * 257))
        self.assertEqual(self.path.read_bytes(), saved)


    def test_long_game_keeps_recent_events_and_checkpoints_after_cycle_64(self):
        started = self.start()
        for cycle in range(1, 81):
            self.assertTrue(self.store.record(completed_cycles=cycle,
                confirmed_event=f"cycle:{cycle}"), self.store.last_error)
        recovered = session.SessionStore(self.path).begin(FP, resume=True)
        self.assertTrue(recovered.resumed)
        self.assertTrue(recovered.persisted)
        self.assertEqual(recovered.checkpoint.run_id, started.checkpoint.run_id)
        self.assertEqual(recovered.checkpoint.completed_cycles, 80)
        self.assertEqual(recovered.checkpoint.confirmed_events,
                         tuple(f"cycle:{cycle}" for cycle in range(17, 81)))
        self.assertTrue(self.store.record(confirmed_event="cycle:17"))
        self.assertEqual(self.store.checkpoint.confirmed_events[-1], "cycle:17")
        self.assertEqual(len(self.store.checkpoint.confirmed_events), session.MAX_EVENTS)

    def test_oversized_events_in_loaded_file_still_fail_closed(self):
        self.start()
        data = self.read_data()
        data["confirmed_events"] = [f"event:{index}" for index in range(session.MAX_EVENTS + 1)]
        self.write_data(data)
        self.assert_safe_new_session("checkpoint_invalid")

    def test_atomic_replace_keeps_old_checkpoint_visible_until_commit(self):
        self.start()
        before = self.path.read_bytes()
        replace_file = session.os.replace

        def verify_then_replace(source, destination):
            self.assertEqual(Path(source).parent, self.path.parent)
            self.assertEqual(Path(destination), self.path)
            self.assertEqual(self.path.read_bytes(), before)
            candidate = json.loads(Path(source).read_text(encoding="utf-8"))
            self.assertEqual(candidate["completed_cycles"], 3)
            return replace_file(source, destination)

        with patch.object(session.os, "replace", side_effect=verify_then_replace) as replace_mock:
            self.assertTrue(self.store.record(completed_cycles=3))
        self.assertEqual(replace_mock.call_count, 1)
        self.assertEqual(self.read_data()["completed_cycles"], 3)
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_replace_failure_preserves_old_file_and_removes_temporary_file(self):
        self.start()
        before = self.path.read_bytes()
        with patch.object(session.os, "replace", side_effect=OSError("replace blocked")):
            self.assertFalse(self.store.record(completed_cycles=3))
        self.assertIn("replace blocked", self.store.last_error)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])
        recovered = session.SessionStore(self.path).begin(FP, resume=True)
        self.assertEqual(recovered.checkpoint.completed_cycles, 0)

    def test_fsync_failure_keeps_old_file_and_cleans_temporary_file(self):
        self.start()
        before = self.path.read_bytes()
        with patch.object(session.os, "fsync", side_effect=OSError("flush blocked")):
            self.assertFalse(self.store.record(last_outcome="script_error"))
        self.assertEqual(self.path.read_bytes(), before)
        self.assertIn("flush blocked", self.store.last_error)
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_new_file_write_failure_is_reported_without_raising(self):
        self.path.parent.mkdir(parents=True)
        self.path.mkdir()
        result = self.store.begin(FP)
        self.assertFalse(result.persisted)
        self.assertTrue(self.store.last_error)
        self.assertIsNotNone(result.checkpoint)
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_read_io_error_does_not_resume_previous_session(self):
        self.start()
        original_id = self.store.checkpoint.run_id
        with patch.object(Path, "open", side_effect=PermissionError("read blocked")):
            recovered = session.SessionStore(self.path).begin(FP, resume=True)
        self.assertFalse(recovered.resumed)
        self.assertEqual(recovered.reason, "checkpoint_read_failed")
        self.assertIn("read blocked", recovered.detail)
        self.assertNotEqual(recovered.checkpoint.run_id, original_id)

    def test_serialized_byte_limit_rejects_large_unicode_summaries(self):
        small = session.SessionStore(self.path, max_bytes=1024)
        self.assertTrue(small.begin(FP).persisted)
        before = self.path.read_bytes()
        self.assertFalse(small.record(pending_actions=["符" * 256, "玄" * 256]))
        self.assertIn("size limit", small.last_error)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_strategy_fingerprint_is_exact_bounded_file_hash(self):
        strategy = self.root / "strategy.json"
        strategy.write_bytes(b'{"main_c":"silver wolf"}')
        self.assertEqual(session.strategy_fingerprint(strategy), hashlib.sha256(strategy.read_bytes()).hexdigest())
        strategy.write_bytes(b" " * (session.MAX_FILE_BYTES + 1))
        with self.assertRaises(ValueError):
            session.strategy_fingerprint(strategy)

    def test_invalid_store_configuration_and_begin_arguments_are_rejected(self):
        for limit in (True, 0, 255, 1.0, session.MAX_FILE_BYTES + 1):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                session.SessionStore(self.path, max_bytes=limit)
        for fingerprint in ("wrong", "0" * 63, "A" * 64, None):
            with self.subTest(fingerprint=fingerprint), self.assertRaises(ValueError):
                self.store.begin(fingerprint)
        with self.assertRaises(ValueError):
            self.store.begin(FP, resume=1)
        self.assertFalse(self.store.record(completed_cycles=1))
        self.assertFalse(self.store.finalize("game_lost"))
        self.assertFalse(self.path.exists())


if __name__ == "__main__":
    unittest.main()
