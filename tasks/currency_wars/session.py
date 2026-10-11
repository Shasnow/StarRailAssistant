"""Bounded local session hints; no board observations or executable actions.

A caller must confirm the live page and roster before continuing. Pending actions
are human-readable summaries only, never instructions to replay on recovery.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Sequence
import uuid

CHECKPOINT_VERSION = 3
DEFAULT_MAX_BYTES = 64 * 1024
MAX_FILE_BYTES = 1024 * 1024
MAX_EVENTS = 64
MAX_PENDING_ACTIONS = 16
MAX_SUMMARY_CHARS = 256
MAX_CYCLES = 2**31 - 1
_UNSET = object()
_V2_FIELDS = {"last_battle_outcome", "terminal_outcome", "terminal_evidence",
              "terminal_confirmed_at", "execution_status", "terminal_navigation_step"}
_V3_FIELDS = {"confirmed_battle_count", "active_economy_stage_index", "pending_battle_id",
              "last_counted_battle_id", "equipment_battles_since_check",
              "last_equipment_check_battle_id", "equipment_batch_state"}


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _text(value: object, label: str, limit: int) -> str:
    if (not isinstance(value, str) or not value.strip() or len(value) > limit
            or any(ord(char) < 32 for char in value)):
        raise ValueError(f"Invalid {label}")
    return value


def _uuid(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Invalid {label}")
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise ValueError(f"Invalid {label}") from exc
    if str(parsed) != value:
        raise ValueError(f"Invalid {label}")
    return value


def _fingerprint(value: object) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("strategy_fingerprint must be a SHA256 hex digest")
    return value


def _summaries(value: object, label: str, maximum: int) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)) or len(value) > maximum:
        raise ValueError(f"Invalid {label}")
    result = tuple(_text(item, label, MAX_SUMMARY_CHARS) for item in value)
    if len(set(result)) != len(result):
        raise ValueError(f"Duplicate {label}")
    return result


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate checkpoint field")
        result[key] = value
    return result


@dataclass(frozen=True)
class SessionCheckpoint:
    run_id: str
    strategy_fingerprint: str
    version: int = CHECKPOINT_VERSION
    completed_cycles: int = 0
    phase: str = "unknown"
    last_outcome: str = "none"
    confirmed_events: tuple[str, ...] = ()
    pending_actions: tuple[str, ...] = ()
    finalized: bool = False
    association: str = "new"
    previous_run_id: str | None = None
    created_at: str = ""
    updated_at: str = ""
    last_battle_outcome: str = "unknown"
    terminal_outcome: str = "unknown"
    terminal_evidence: str = "none"
    terminal_confirmed_at: str = "none"
    execution_status: str = "running"
    terminal_navigation_step: str = "none"
    # Script cycles include noncombat nodes and are never used to reconstruct
    # the real battle history. None means the history before recovery is unknown.
    confirmed_battle_count: int | None = 0
    active_economy_stage_index: int = 0
    pending_battle_id: str | None = None
    last_counted_battle_id: str | None = None
    equipment_battles_since_check: int = 0
    last_equipment_check_battle_id: str | None = None
    equipment_batch_state: str = "idle"


def _validated(checkpoint: SessionCheckpoint) -> SessionCheckpoint:
    if type(checkpoint.version) is not int or checkpoint.version != CHECKPOINT_VERSION:
        raise ValueError("Unsupported checkpoint version")
    _uuid(checkpoint.run_id, "run_id")
    _fingerprint(checkpoint.strategy_fingerprint)
    if type(checkpoint.completed_cycles) is not int or not 0 <= checkpoint.completed_cycles <= MAX_CYCLES:
        raise ValueError("Invalid completed_cycles")
    for label in ("confirmed_battle_count", "active_economy_stage_index", "equipment_battles_since_check"):
        value = getattr(checkpoint, label)
        if label == "confirmed_battle_count" and value is None:
            continue
        if type(value) is not int or not 0 <= value <= MAX_CYCLES:
            raise ValueError(f"Invalid {label}")
    for label in ("pending_battle_id", "last_counted_battle_id", "last_equipment_check_battle_id"):
        value = getattr(checkpoint, label)
        if value is not None:
            _uuid(value, label)
    if (checkpoint.pending_battle_id is not None
            and checkpoint.pending_battle_id == checkpoint.last_counted_battle_id):
        raise ValueError("A counted battle cannot remain pending")
    if checkpoint.equipment_batch_state not in ("idle", "in_progress", "completed", "interrupted"):
        raise ValueError("Invalid equipment_batch_state")
    _text(checkpoint.phase, "phase", 64)
    _text(checkpoint.last_outcome, "last_outcome", 64)
    if checkpoint.last_battle_outcome not in ("unknown", "success", "failure"):
        raise ValueError("Invalid battle outcome")
    if checkpoint.terminal_outcome not in ("unknown", "won", "lost"):
        raise ValueError("Invalid terminal outcome")
    if checkpoint.execution_status not in ("running", "stopped", "error", "completed"):
        raise ValueError("Invalid execution status")
    _text(checkpoint.terminal_evidence, "terminal_evidence", MAX_SUMMARY_CHARS)
    _text(checkpoint.terminal_navigation_step, "terminal_navigation_step", 64)
    _text(checkpoint.terminal_confirmed_at, "terminal_confirmed_at", 64)
    if checkpoint.terminal_confirmed_at != "none":
        stamp = datetime.fromisoformat(checkpoint.terminal_confirmed_at.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("Invalid terminal confirmation time")
    events = _summaries(checkpoint.confirmed_events, "confirmed_events", MAX_EVENTS)
    pending = _summaries(checkpoint.pending_actions, "pending_actions", MAX_PENDING_ACTIONS)
    if type(checkpoint.finalized) is not bool:
        raise ValueError("Invalid finalized flag")
    if checkpoint.association not in ("new", "resumed", "uncertain"):
        raise ValueError("Invalid session association")
    if checkpoint.previous_run_id is not None:
        _uuid(checkpoint.previous_run_id, "previous_run_id")
        if checkpoint.previous_run_id == checkpoint.run_id:
            raise ValueError("Invalid previous_run_id")
    for label in ("created_at", "updated_at"):
        stamp = _text(getattr(checkpoint, label), label, 64)
        try:
            parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"Invalid {label}") from exc
        if parsed.tzinfo is None:
            raise ValueError(f"Invalid {label}")
    if checkpoint.finalized and (checkpoint.pending_actions or checkpoint.pending_battle_id is not None):
        raise ValueError("Finalized sessions cannot retain pending actions")
    return replace(checkpoint, confirmed_events=events, pending_actions=pending)


def strategy_fingerprint(path: Path) -> str:
    """Hash the exact strategy file, rejecting unexpectedly large inputs."""
    with Path(path).open("rb") as handle:
        data = handle.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("Strategy file too large")
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class SessionRecovery:
    checkpoint: SessionCheckpoint
    reason: str
    resumed: bool
    persisted: bool
    detail: str = ""


class SessionStore:
    """One explicitly selected checkpoint path. Construction never touches disk."""

    def __init__(self, path: Path, max_bytes: int = DEFAULT_MAX_BYTES):
        if type(max_bytes) is not int or not 256 <= max_bytes <= MAX_FILE_BYTES:
            raise ValueError("Invalid checkpoint size limit")
        self.path = Path(path)
        self.max_bytes = max_bytes
        self.checkpoint: SessionCheckpoint | None = None
        self.last_error: str | None = None

    def _read(self) -> tuple[SessionCheckpoint | None, str, str]:
        try:
            with self.path.open("rb") as handle:
                raw = handle.read(self.max_bytes + 1)
        except FileNotFoundError:
            return None, "checkpoint_missing", ""
        except OSError as exc:
            return None, "checkpoint_read_failed", str(exc)
        if len(raw) > self.max_bytes:
            return None, "checkpoint_too_large", "Size limit exceeded"
        try:
            data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
            if not isinstance(data, dict):
                raise ValueError("Checkpoint must be an object")
            if type(data.get("version")) is not int or data["version"] not in (1, 2, CHECKPOINT_VERSION):
                return None, "checkpoint_version_unsupported", "Unsupported or missing version"
            legacy_version = data["version"]
            if legacy_version in (1, 2):
                missing = _V3_FIELDS | (_V2_FIELDS if legacy_version == 1 else set())
                if set(data) != {item.name for item in fields(SessionCheckpoint)} - missing:
                    raise ValueError("Unexpected or missing legacy checkpoint fields")
            if legacy_version == 1:
                data.update(
                            last_battle_outcome=data["last_outcome"] if data["last_outcome"] in ("success", "failure") else "unknown",
                            terminal_outcome="won" if data["last_outcome"] == "game_won" else "lost" if data["last_outcome"] == "game_lost" else "unknown",
                            terminal_evidence="legacy_checkpoint", terminal_confirmed_at="none",
                            execution_status="completed" if data["finalized"] else "running",
                            terminal_navigation_step="complete" if data["finalized"] else "none")
            if legacy_version in (1, 2):
                data.update(version=CHECKPOINT_VERSION, confirmed_battle_count=None,
                            active_economy_stage_index=0, pending_battle_id=None,
                            last_counted_battle_id=None, equipment_battles_since_check=0,
                            last_equipment_check_battle_id=None, equipment_batch_state="idle")
            if set(data) != {item.name for item in fields(SessionCheckpoint)}:
                raise ValueError("Unexpected or missing checkpoint fields")
            snapshot = _validated(SessionCheckpoint(**data))
        except (UnicodeError, ValueError, TypeError, RecursionError, OverflowError) as exc:
            return None, "checkpoint_invalid", str(exc)
        return snapshot, "loaded", ""

    def _save(self) -> bool:
        temporary: Path | None = None
        self.last_error = None
        try:
            if self.checkpoint is None:
                raise ValueError("Session has not started")
            snapshot = _validated(self.checkpoint)
            payload = json.dumps(asdict(snapshot), ensure_ascii=False, sort_keys=True,
                                 separators=(",", ":")).encode("utf-8")
            if len(payload) > self.max_bytes:
                raise ValueError("Checkpoint size limit exceeded")
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="wb", dir=self.path.parent,
                                             prefix=self.path.name + ".", suffix=".tmp",
                                             delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            temporary = None
            return True
        except (OSError, ValueError, TypeError) as exc:
            self.last_error = str(exc)
            return False
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

    def begin(self, fingerprint: str, *, resume: bool = False) -> SessionRecovery:
        """Resume matching hints or start safely, never replaying pending actions.

        A strategy mismatch starts a new tracking ID. previous_run_id preserves
        only the uncertain association; old event and action plans are discarded.
        Only an explicitly fresh game establishes battle zero. A finalized old
        checkpoint says nothing about battles already played on the live page.
        """
        fingerprint = _fingerprint(fingerprint)
        if type(resume) is not bool:
            raise ValueError("resume must be bool")
        old, reason, detail = self._read() if resume else (None, "new_game", "")
        resumed = False
        association = "new" if not resume else "uncertain"
        previous = None
        if old is not None and old.finalized:
            reason = "previous_game_finalized"
        elif old is not None and old.strategy_fingerprint != fingerprint:
            reason = "strategy_changed_association_uncertain"
            previous = old.run_id
        elif old is not None:
            resumed = True
            reason = "resumed" if old.association != "uncertain" else "resumed_association_uncertain"
            self.checkpoint = replace(old, association=("uncertain" if old.association == "uncertain"
                                                        else "resumed"), updated_at=_timestamp(),
                                      equipment_batch_state="interrupted"
                                      if old.equipment_batch_state == "in_progress"
                                      else old.equipment_batch_state)
        if not resumed:
            stamp = _timestamp()
            self.checkpoint = SessionCheckpoint(
                run_id=str(uuid.uuid4()), strategy_fingerprint=fingerprint,
                association=association, previous_run_id=previous,
                confirmed_battle_count=None if resume else 0,
                created_at=stamp, updated_at=stamp)
        persisted = self._save()
        return SessionRecovery(self.checkpoint, reason, resumed, persisted, detail)

    def record(self, *, phase: str | None = None, completed_cycles: int | None = None,
               last_outcome: str | None = None, confirmed_event: str | None = None,
               pending_actions: Sequence[str] | None = None,
               last_battle_outcome: str | None = None, terminal_outcome: str | None = None,
               terminal_evidence: str | None = None, execution_status: str | None = None,
               terminal_navigation_step: str | None = None,
               confirmed_battle_count: int | None | object = _UNSET,
               active_economy_stage_index: int | None = None,
               pending_battle_id: str | None | object = _UNSET,
               last_counted_battle_id: str | None | object = _UNSET,
               equipment_battles_since_check: int | None = None,
               last_equipment_check_battle_id: str | None | object = _UNSET,
               equipment_batch_state: str | None = None) -> bool:
        """Record confirmed history and summaries. Return False on invalid/I/O data.

        Counts must not move backwards. No state-changing game operation is
        exposed or performed by this module.
        """
        if self.checkpoint is None or self.checkpoint.finalized:
            self.last_error = "No active session"
            return False
        current = self.checkpoint
        try:
            if (current.terminal_outcome != "unknown" and terminal_outcome is not None
                    and terminal_outcome != current.terminal_outcome):
                raise ValueError("Confirmed terminal outcome cannot be overwritten")
            terminal_changes = {key: value for key, value in {
                "last_battle_outcome": last_battle_outcome, "terminal_outcome": terminal_outcome,
                "terminal_evidence": terminal_evidence, "execution_status": execution_status,
                "terminal_navigation_step": terminal_navigation_step}.items() if value is not None}
            if terminal_outcome in ("won", "lost") and current.terminal_confirmed_at == "none":
                terminal_changes["terminal_confirmed_at"] = _timestamp()
            if terminal_outcome in ("won", "lost"):
                last_outcome = "game_won" if terminal_outcome == "won" else "game_lost"
            count = current.completed_cycles if completed_cycles is None else completed_cycles
            if type(count) is not int or count < current.completed_cycles:
                raise ValueError("completed_cycles cannot decrease or be noninteger")
            battle_count = (current.confirmed_battle_count if confirmed_battle_count is _UNSET
                            else confirmed_battle_count)
            if current.confirmed_battle_count is None:
                if battle_count is not None:
                    raise ValueError("Unknown battle history cannot be reconstructed from local counts")
            elif type(battle_count) is not int or battle_count < current.confirmed_battle_count:
                raise ValueError("confirmed_battle_count cannot decrease or become unknown")
            stage_index = (current.active_economy_stage_index if active_economy_stage_index is None
                           else active_economy_stage_index)
            if type(stage_index) is not int or stage_index < current.active_economy_stage_index:
                raise ValueError("active_economy_stage_index cannot decrease or be noninteger")
            equipment_count = (current.equipment_battles_since_check if equipment_battles_since_check is None
                               else equipment_battles_since_check)
            equipment_state = (current.equipment_batch_state if equipment_batch_state is None
                               else equipment_batch_state)
            if (type(equipment_count) is not int or equipment_count < 0
                    or (equipment_count < current.equipment_battles_since_check
                        and not (equipment_count == 0 and equipment_state == "completed"))):
                raise ValueError("Equipment interval can reset only after a completed batch")
            history_changes = {
                key: value for key, value in {
                    "pending_battle_id": pending_battle_id,
                    "last_counted_battle_id": last_counted_battle_id,
                    "last_equipment_check_battle_id": last_equipment_check_battle_id,
                }.items() if value is not _UNSET
            }
            events = current.confirmed_events
            if confirmed_event is not None:
                event = _text(confirmed_event, "confirmed_event", MAX_SUMMARY_CHARS)
                # Keep recent confirmed history bounded through long games.
                # Reconfirmation refreshes recency without duplicating an event.
                events = tuple(item for item in events if item != event) + (event,)
                events = events[-MAX_EVENTS:]
            pending = current.pending_actions if pending_actions is None else pending_actions
            candidate = _validated(replace(
                current, phase=current.phase if phase is None else phase,
                completed_cycles=count,
                confirmed_battle_count=battle_count, active_economy_stage_index=stage_index,
                equipment_battles_since_check=equipment_count, equipment_batch_state=equipment_state,
                last_outcome=current.last_outcome if last_outcome is None else last_outcome,
                confirmed_events=events, pending_actions=pending, updated_at=_timestamp(),
                **terminal_changes, **history_changes))
        except (ValueError, TypeError) as exc:
            self.last_error = str(exc)
            return False
        # Re-observing the same page/event is not a new checkpoint. An earlier
        # failed save must still retry even if the in-memory values are equal.
        if self.last_error is None and replace(candidate, updated_at=current.updated_at) == current:
            return True
        self.checkpoint = candidate
        return self._save()

    def confirm_battle(self, battle_id: str) -> bool:
        """Commit one observed real battle once, without inferring old history.

        The caller must authenticate combat and its result/next stage first.
        A pending ID is only an identity hint, never permission to replay input.
        """
        if self.checkpoint is None or self.checkpoint.finalized:
            self.last_error = "No active session"
            return False
        try:
            _uuid(battle_id, "battle_id")
        except ValueError as exc:
            self.last_error = str(exc)
            return False
        current = self.checkpoint
        if battle_id == current.last_counted_battle_id:
            # Retry a failed save without incrementing the in-memory count twice.
            return self._save()
        if battle_id != current.pending_battle_id:
            self.last_error = "Battle completion does not match the pending battle"
            return False
        count = current.confirmed_battle_count
        return self.record(
            confirmed_battle_count=None if count is None else count + 1,
            pending_battle_id=None, last_counted_battle_id=battle_id,
            equipment_battles_since_check=current.equipment_battles_since_check + 1,
            equipment_batch_state="idle" if current.equipment_batch_state == "completed"
            else current.equipment_batch_state)

    def complete_equipment_check(self) -> bool:
        """Consume an inspected batch after the caller confirms preparation UI.

        Completion describes the batch of attempts, not synthesis success.
        Interrupted batches retain their due interval until inspected again.
        """
        if self.checkpoint is None or self.checkpoint.finalized:
            self.last_error = "No active session"
            return False
        if self.checkpoint.equipment_batch_state == "completed":
            return self._save()
        if self.checkpoint.equipment_batch_state != "in_progress":
            self.last_error = "No equipment batch is in progress"
            return False
        return self.record(equipment_battles_since_check=0, equipment_batch_state="completed",
                           last_equipment_check_battle_id=self.checkpoint.last_counted_battle_id)

    def finalize(self, outcome: str) -> bool:
        """Mark a confirmed game ending. User stops/errors must use record instead."""
        if self.checkpoint is None or self.checkpoint.finalized:
            self.last_error = "No active session"
            return False
        try:
            if self.checkpoint.terminal_outcome in ("won", "lost"):
                outcome = "game_won" if self.checkpoint.terminal_outcome == "won" else "game_lost"
            candidate = _validated(replace(self.checkpoint, phase="finished", last_outcome=outcome,
                                           finalized=True, pending_actions=(), pending_battle_id=None,
                                           updated_at=_timestamp(),
                                           execution_status="completed", terminal_navigation_step="complete"))
        except (ValueError, TypeError) as exc:
            self.last_error = str(exc)
            return False
        self.checkpoint = candidate
        return self._save()
