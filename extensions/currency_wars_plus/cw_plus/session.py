"""有界的本地会话提示，不包含棋盘观测或可执行动作。
调用方须确认实时页面和角色列表后才能继续。
待处理动作只是供人阅读的摘要，绝不是恢复时重放的指令。
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

CHECKPOINT_VERSION = 5
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
_V4_FIELDS = {"session_mode", "observed_round", "observed_level"}
_V5_FIELDS = {"confirmed_battle_lower_bound"}


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


def _context(mode, observed_round, level):
    if mode not in (None, "standard", "overclock"):
        raise ValueError("Invalid session mode")
    if observed_round is not None:
        if (not isinstance(observed_round, (tuple, list)) or len(observed_round) != 2
                or any(type(v) is not int or not 1 <= v <= 99 for v in observed_round)):
            raise ValueError("Invalid observed round")
        observed_round = tuple(observed_round)
    if level is not None and (type(level) is not int or not 1 <= level <= 20):
        raise ValueError("Invalid observed level")
    return mode, observed_round, level


def _association_issue(old, mode, observed_round, level):
    # 用户约定：同攻略的未结束记录，模式、回合、等级一致就按同一局续跑。
    # 无须再区分相同上下文的人工重开；单独模式一致仍不足以恢复历史。
    # 终局历史不进入新的实时跟踪；终局页由调用方重新认证。
    if old.terminal_outcome != "unknown":
        return "previous_game_terminal"
    if old.session_mode != mode or mode is None:
        return "session_mode_changed_or_unknown"
    if old.observed_round is None or observed_round is None:
        return "session_round_unverified"
    if observed_round != old.observed_round:
        # 停止期间可能手动推进甚至重开，不能从回合差推算战斗次数。
        return "session_round_changed"
    if old.observed_level is None or level is None:
        return "session_level_unverified"
    if level < old.observed_level:
        return "session_level_regressed"
    return None


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
    # 脚本循环包含非战斗节点，绝不用于重建实际战斗历史。
    # None 表示恢复前的历史未知。
    confirmed_battle_count: int | None = 0
    # 历史总数未知时，仍保留本次跟踪中真实完成的场次数下界。
    # 不能把下界冒充精确总数，也不能从循环、回合或入战意图推算。
    confirmed_battle_lower_bound: int = 0
    active_economy_stage_index: int = 0
    pending_battle_id: str | None = None
    last_counted_battle_id: str | None = None
    equipment_battles_since_check: int = 0
    last_equipment_check_battle_id: str | None = None
    equipment_batch_state: str = "idle"
    # 仅用于关联核验，不用于恢复棋盘或推算战斗次数。
    session_mode: str | None = None
    observed_round: tuple[int, int] | None = None
    observed_level: int | None = None


def _validated(checkpoint: SessionCheckpoint) -> SessionCheckpoint:
    if type(checkpoint.version) is not int or checkpoint.version != CHECKPOINT_VERSION:
        raise ValueError("Unsupported checkpoint version")
    _uuid(checkpoint.run_id, "run_id")
    _fingerprint(checkpoint.strategy_fingerprint)
    if type(checkpoint.completed_cycles) is not int or not 0 <= checkpoint.completed_cycles <= MAX_CYCLES:
        raise ValueError("Invalid completed_cycles")
    for label in ("confirmed_battle_count", "confirmed_battle_lower_bound",
                  "active_economy_stage_index", "equipment_battles_since_check"):
        value = getattr(checkpoint, label)
        if label == "confirmed_battle_count" and value is None:
            continue
        if type(value) is not int or not 0 <= value <= MAX_CYCLES:
            raise ValueError(f"Invalid {label}")
    if (checkpoint.confirmed_battle_count is not None
            and checkpoint.confirmed_battle_lower_bound > checkpoint.confirmed_battle_count):
        raise ValueError("Battle lower bound cannot exceed the known total")
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
    mode, observed_round, level = _context(checkpoint.session_mode,
                                         checkpoint.observed_round, checkpoint.observed_level)
    return replace(checkpoint, confirmed_events=events, pending_actions=pending,
                   session_mode=mode, observed_round=observed_round, observed_level=level)


# Yukki：攻略内容指纹用于隔离不同策略的会话提示。
def strategy_fingerprint(path: Path) -> str:
    """对攻略文件的完整原文求哈希，并拒绝异常大的输入。"""
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


# ssyb：存档仅保存上下文与摘要，不存储可重放的界面动作。
class SessionStore:
    """一个明确选定的检查点路径；构造对象时绝不访问磁盘。"""

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
            if type(data.get("version")) is not int or data["version"] not in (1, 2, 3, 4, CHECKPOINT_VERSION):
                return None, "checkpoint_version_unsupported", "Unsupported or missing version"
            legacy_version = data["version"]
            if legacy_version in (1, 2, 3, 4):
                missing = _V5_FIELDS | (_V4_FIELDS if legacy_version < 4 else set()) | (
                    _V3_FIELDS if legacy_version < 3 else set()) | (
                    _V2_FIELDS if legacy_version == 1 else set())
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
            if legacy_version in (1, 2, 3):
                data.update(version=CHECKPOINT_VERSION, session_mode=None,
                            observed_round=None, observed_level=None)
            if legacy_version in (1, 2, 3, 4):
                # 旧档已知总数本身就是可靠下界；未知总数从零积累新增完成证据。
                # 入战事件与 completed_cycles 都不足以补造旧完成场次。
                data.update(version=CHECKPOINT_VERSION,
                            confirmed_battle_lower_bound=data["confirmed_battle_count"]
                            if type(data["confirmed_battle_count"]) is int else 0)
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

    def begin(self, fingerprint: str, *, resume: bool = False, verify_context: bool = False,
              session_mode: str | None = None, observed_round=None,
              observed_level: int | None = None) -> SessionRecovery:
        """恢复匹配的提示或安全地重新开始，绝不重放待处理动作。
        攻略不匹配时建立新的跟踪 ID。
        previous_run_id 仅保留不确定的关联；旧事件和动作计划会丢弃。
        只有明确的新开局才建立战斗次数零点。
        已结束的旧检查点不能说明实时页面已经进行过多少场战斗。
        """
        fingerprint = _fingerprint(fingerprint)
        if type(resume) is not bool:
            raise ValueError("resume must be bool")
        if type(verify_context) is not bool:
            raise ValueError("verify_context must be bool")
        session_mode, observed_round, observed_level = _context(
            session_mode, observed_round, observed_level)
        self._finalization_pending = False
        old, reason, detail = self._read() if resume else (None, "new_game", "")
        resumed = False
        association = "new" if not resume else "uncertain"
        previous = None
        if old is not None and old.finalized:
            reason = "previous_game_finalized"
        elif old is not None and old.strategy_fingerprint != fingerprint:
            reason = "strategy_changed_association_uncertain"
            previous = old.run_id
        elif old is not None and verify_context and (issue := _association_issue(
                old, session_mode, observed_round, observed_level)) is not None:
            reason = issue
            previous = old.run_id
        elif old is not None:
            resumed = True
            reason = "resumed" if old.association != "uncertain" else "resumed_association_uncertain"
            if verify_context and observed_level == old.observed_level:
                # 上面的核验已确认模式、回合及等级；明确记录接受的同局规则。
                reason = "resumed_same_context"
            self.checkpoint = replace(old, association=("uncertain" if old.association == "uncertain"
                                                        else "resumed"), updated_at=_timestamp(),
                                      equipment_batch_state="interrupted"
                                      if old.equipment_batch_state == "in_progress"
                                      else old.equipment_batch_state)
            if verify_context:
                self.checkpoint = replace(self.checkpoint, observed_round=observed_round,
                                          observed_level=observed_level)
        if not resumed:
            stamp = _timestamp()
            self.checkpoint = SessionCheckpoint(
                run_id=str(uuid.uuid4()), strategy_fingerprint=fingerprint,
                association=association, previous_run_id=previous,
                confirmed_battle_count=None if resume else 0,
                session_mode=session_mode, observed_round=observed_round, observed_level=observed_level,
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
               confirmed_battle_lower_bound: int | None = None,
               active_economy_stage_index: int | None = None,
               pending_battle_id: str | None | object = _UNSET,
               last_counted_battle_id: str | None | object = _UNSET,
               equipment_battles_since_check: int | None = None,
               last_equipment_check_battle_id: str | None | object = _UNSET,
               equipment_batch_state: str | None = None,
               observed_round=None, observed_level: int | None = None) -> bool:
        """记录已确认的历史与摘要；数据无效或 I/O 失败时返回 False。
        次数不得倒退。
        本模块不提供也不执行任何改变游戏状态的操作。
        """
        if self.checkpoint is None or self.checkpoint.finalized:
            self.last_error = "No active session"
            return False
        current = self.checkpoint
        try:
            _, round_value, level_value = _context(current.session_mode,
                current.observed_round if observed_round is None else observed_round,
                current.observed_level if observed_level is None else observed_level)
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
            lower_bound = (current.confirmed_battle_lower_bound
                           if confirmed_battle_lower_bound is None else confirmed_battle_lower_bound)
            if type(lower_bound) is not int or lower_bound < current.confirmed_battle_lower_bound:
                raise ValueError("confirmed_battle_lower_bound cannot decrease or be noninteger")
            if battle_count is not None:
                if lower_bound > battle_count:
                    raise ValueError("Battle lower bound cannot exceed the known total")
                # 可靠的精确总数本身提供更强的下界。
                lower_bound = battle_count
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
                # 长局中也只保留数量有界的近期已确认历史。
                # 重新确认会更新最近使用顺序，而不会重复记录事件。
                events = tuple(item for item in events if item != event) + (event,)
                events = events[-MAX_EVENTS:]
            pending = current.pending_actions if pending_actions is None else pending_actions
            candidate = _validated(replace(
                current, phase=current.phase if phase is None else phase,
                completed_cycles=count,
                confirmed_battle_count=battle_count, confirmed_battle_lower_bound=lower_bound,
                active_economy_stage_index=stage_index,
                equipment_battles_since_check=equipment_count, equipment_batch_state=equipment_state,
                last_outcome=current.last_outcome if last_outcome is None else last_outcome,
                confirmed_events=events, pending_actions=pending, updated_at=_timestamp(),
                observed_round=round_value, observed_level=level_value,
                **terminal_changes, **history_changes))
        except (ValueError, TypeError) as exc:
            self.last_error = str(exc)
            return False
        # 再次观测同一页面或事件不会形成新的检查点。
        # 若此前保存失败，即使内存值相同也必须重试。
        if self.last_error is None and replace(candidate, updated_at=current.updated_at) == current:
            return True
        self.checkpoint = candidate
        return self._save()

    def confirm_battle(self, battle_id: str) -> bool:
        """每场观测到的真实战斗只提交一次，不推断旧历史。
        调用方须先认证战斗及其结果或下一阶段。
        待处理 ID 只是身份提示，不授权重放输入。
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
            # 重试失败的保存，不能让内存计数重复增加。
            return self._save()
        if battle_id != current.pending_battle_id:
            self.last_error = "Battle completion does not match the pending battle"
            return False
        count = current.confirmed_battle_count
        return self.record(
            confirmed_battle_count=None if count is None else count + 1,
            confirmed_battle_lower_bound=current.confirmed_battle_lower_bound + 1,
            pending_battle_id=None, last_counted_battle_id=battle_id,
            equipment_battles_since_check=current.equipment_battles_since_check + 1,
            equipment_batch_state="idle" if current.equipment_batch_state == "completed"
            else current.equipment_batch_state)

    def complete_equipment_check(self) -> bool:
        """调用方确认准备界面后，消耗已检查的批次。
        完成表示该批尝试已处理，不能表示合成成功。
        被中断批次继续保留到期区间，直到再次检查。
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
        """标记已确认的游戏结束；用户停止或错误必须改用 record。"""
        if self.checkpoint is None or (self.checkpoint.finalized
                and not getattr(self, "_finalization_pending", False)):
            self.last_error = "No active session"
            return False
        if not self.checkpoint.finalized:
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
        # 结束已在画面中确认，内存保持封闭，禁止恢复动作或再次累计战斗。
        # 保存失败只重试同一终局快照，不接受重试调用传入的新结局。
        self._finalization_pending = True
        persisted = self._save()
        self._finalization_pending = not persisted
        return persisted
